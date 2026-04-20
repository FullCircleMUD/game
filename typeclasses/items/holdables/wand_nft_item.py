"""
WandNFTItem — an enchanted wand that casts a bound spell when zapped.

A wand is a HoldableNFTItem that remembers which spell it's bound to
and how many charges remain. It is crafted by a mage in a wizard's
workshop from (matching blank wand component) + (arcane dust) +
(a spell the mage currently knows at matching mastery). Mana for every
charge is pre-paid by the enchanter at craft time; zapping the wand
costs zero mana.

Phase 2 ships with a single generic "Enchanted Wand" ``NFTItemType``.
Per-instance state (``spell_key`` and ``charges_remaining``) is stored
both as an Evennia ``AttributeProperty`` (fast in-memory lookup,
survives server restart) and mirrored into ``NFTGameState.metadata``
via ``persist_wand_state()`` so the state survives on-chain round-trips
and unrelated cache events. This is the same dual-persist pattern used
by ``DurabilityMixin._persist_durability`` and gem insetting.

The ``zap`` command, not this class, is responsible for checking
``can_use``, decrementing charges, and deleting the wand at zero.

Usage gates (via ``can_use``):
    - Mage class characters can zap any wand.
    - Thieves / ninjas with Magical Secrets mastery >= the bound spell's
      ``min_mastery`` can zap the wand.
    - Everyone else is rejected.
"""

from evennia.typeclasses.attributes import AttributeProperty

from typeclasses.items.holdables.holdable_nft_item import HoldableNFTItem


class WandNFTItem(HoldableNFTItem):
    """Enchanted wand — holds a bound spell + charges."""

    spell_key = AttributeProperty("")
    charges_remaining = AttributeProperty(0)
    charges_max = AttributeProperty(0)

    # ── Display ────────────────────────────────────────────────

    def get_display_name(self, looker=None, **kwargs):
        base = super().get_display_name(looker=looker, **kwargs)
        if self.charges_max <= 0:
            return base
        if self.charges_remaining > 0:
            return f"{base} ({self.charges_remaining}/{self.charges_max} charges)"
        return f"{base} (expended)"

    # ── Usage gate ─────────────────────────────────────────────

    def can_use(self, character):
        """Return (ok, reason) — mage class OR Magical Secrets at tier."""
        # Respect any base-class restrictions first (level, remort, alignment...)
        base_ok, base_msg = super().can_use(character)
        if not base_ok:
            return False, base_msg

        # Gate 1: mage class
        classes = character.db.classes or {}
        if "mage" in classes:
            return True, ""

        # Gate 2: Magical Secrets mastery >= the bound spell's tier
        from world.spells.registry import SPELL_REGISTRY

        spell = SPELL_REGISTRY.get(self.spell_key)
        if spell is None:
            return False, "This wand's binding is broken."
        required_tier = spell.min_mastery.value

        class_levels = character.db.class_skill_mastery_levels or {}
        entry = class_levels.get("magical secrets", 0)
        if hasattr(entry, "get"):
            magical_secrets = entry.get("mastery", 0)
        else:
            magical_secrets = int(entry or 0)

        if magical_secrets >= required_tier:
            return True, ""

        return False, (
            f"You need the Mage class or Magical Secrets at "
            f"{spell.min_mastery.name} to use this wand."
        )

    # ── Dual-persist of wand state ─────────────────────────────

    def persist_wand_state(self):
        """Mirror spell_key / charges into NFTGameState.metadata.

        Called after every mutation so the DB mirror tracks the in-memory
        AttributeProperty values. Best-effort — never raises.
        """
        persist = getattr(self, "persist_metadata", None)
        if persist is None:
            return
        persist({
            "spell_key": self.spell_key,
            "charges_remaining": self.charges_remaining,
            "charges_max": self.charges_max,
        })
