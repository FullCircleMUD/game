"""
Inset command — embed an enchanted gem into a weapon.

Available in jeweller crafting rooms. Consumes the enchanted gem,
transfers its effects to the weapon, and gives the weapon a unique
LLM-generated name.

Syntax:
    inset <gem> in <weapon>

This is a standalone command (not a recipe through cmd_craft) because:
- No new NFT is minted — the weapon keeps its token_id
- The weapon is modified in-place, not spawned fresh
- Doesn't fit the "consume inputs → spawn output" crafting pipeline
"""

from evennia import Command
from evennia.utils import delay

from blockchain.xrpl.models import NFTGameState
from commands.command import FCMCommandMixin
from enums.mastery_level import MasteryLevel
from enums.room_crafting_type import RoomCraftingType
from enums.skills_enum import skills
from llm.name_generator import name_generator
from typeclasses.items.weapons.weapon_nft_item import WeaponNFTItem


# ── Insetting delay configuration ──
INSET_TICK_SECONDS = 3
INSET_TICKS = 2          # 2 ticks × 3 seconds = 6 seconds
_BAR_WIDTH = 10

# XP awarded for insetting
INSET_XP = 10

# Gem tier → required jeweller mastery level
_GEM_MASTERY_REQUIREMENT = {
    "enchanted ruby": MasteryLevel.BASIC,
    "enchanted emerald": MasteryLevel.EXPERT,
    "enchanted diamond": MasteryLevel.GRANDMASTER,
}


class CmdInset(FCMCommandMixin, Command):
    """
    Inset an enchanted gem into a weapon.

    Usage:
        inset <gem> in <weapon>

    Consumes the enchanted gem and transfers its magical effects
    to the weapon. The weapon gains the gem's effects and receives
    a unique name. Requires jeweller skill and a jeweller workshop.
    """

    key = "inset"
    aliases = []
    locks = "cmd:all()"
    help_category = "Crafting"

    def func(self):
        caller = self.caller
        room = caller.location

        # --- Busy check ---
        if caller.ndb.is_processing:
            caller.msg(
                "You are already busy. Wait until your current task finishes."
            )
            return

        if not self.args or " in " not in self.args:
            caller.msg("Usage: inset <gem> in <weapon>")
            return

        # --- Parse arguments ---
        parts = self.args.strip().split(" in ", 1)
        gem_name = parts[0].strip()
        weapon_name = parts[1].strip()

        if not gem_name or not weapon_name:
            caller.msg("Usage: inset <gem> in <weapon>")
            return

        # --- Check room is a jeweller workshop ---
        crafting_type_str = room.crafting_type
        try:
            crafting_type = RoomCraftingType(crafting_type_str)
        except ValueError:
            caller.msg("This room isn't set up for crafting.")
            return

        if crafting_type != RoomCraftingType.JEWELLER:
            caller.msg("You need to be in a jeweller's workshop to inset gems.")
            return

        # --- Find the gem ---
        gem = caller.search(gem_name, location=caller, quiet=True)
        if not gem:
            caller.msg(f"You don't have '{gem_name}'.")
            return
        gem = gem[0] if isinstance(gem, list) else gem

        if not gem.db.wear_effects:
            caller.msg(f"{gem.key} is not an enchanted gem.")
            return

        # --- Check jeweller mastery for this gem tier ---
        gem_key_lower = gem.key.lower()
        required_mastery = None
        for name, mastery in _GEM_MASTERY_REQUIREMENT.items():
            if name in gem_key_lower:
                required_mastery = mastery
                break

        if required_mastery is None:
            caller.msg(f"{gem.key} cannot be inset into a weapon.")
            return

        char_mastery = (caller.db.general_skill_mastery_levels or {}).get(
            skills.JEWELLER.value, 0
        )
        if char_mastery < required_mastery.value:
            mastery_name = required_mastery.name
            caller.msg(
                f"You need at least |w{mastery_name}|n mastery in "
                f"|wJeweller|n to inset {gem.key}."
            )
            return

        # --- Find the weapon ---
        weapon = caller.search(weapon_name, location=caller, quiet=True)
        if not weapon:
            caller.msg(f"You don't have '{weapon_name}'.")
            return
        weapon = weapon[0] if isinstance(weapon, list) else weapon

        if not isinstance(weapon, WeaponNFTItem):
            caller.msg(f"{weapon.key} is not a weapon.")
            return

        # --- Check weapon not wielded ---
        if hasattr(caller, "is_worn") and caller.is_worn(weapon):
            caller.msg(
                f"You must remove {weapon.key} before insetting a gem."
            )
            return

        # --- Check weapon doesn't already have an inset gem ---
        if weapon.is_inset:
            caller.msg(
                f"{weapon.key} already has an inset gem. "
                f"A weapon can only hold one gem."
            )
            return

        # --- Check gold ---
        total_gold = room.craft_cost

        if not caller.has_gold(total_gold):
            caller.msg(
                f"You need {total_gold} gold (workshop fee) "
                f"but only have {caller.get_gold()}."
            )
            return

        # --- Confirmation ---
        gem_effects = gem.db.wear_effects
        effect_desc = ", ".join(
            _describe_effect(e) for e in gem_effects
        )

        answer = yield (
            f"\n|y--- Inset {gem.key} into {weapon.key} ---|n"
            f"\nGem effects: {effect_desc}"
            f"\nWorkshop fee: {total_gold} gold"
            f"\n|rThe gem will be consumed.|n"
            f"\n\nInset {gem.key} into {weapon.key}? Y/[N]"
        )

        if answer.lower() not in ("y", "yes"):
            caller.msg("Insetting cancelled.")
            return

        # --- Re-validate after confirmation ---
        if gem not in caller.contents:
            caller.msg("You no longer have the gem.")
            return
        if weapon not in caller.contents:
            caller.msg("You no longer have the weapon.")
            return
        if not caller.has_gold(total_gold):
            caller.msg("You no longer have enough gold.")
            return

        # --- Consume gold ---
        caller.return_gold_to_sink(total_gold)

        # --- Capture gem data before deletion (read directly from the
        # gem's existing fields — wear_effects + ItemRestrictionMixin
        # fields. No custom storage; same field names that exist on the
        # weapon, so transfer is just field-by-field copy/merge.) ---
        gem_effects = list(gem.db.wear_effects)
        gem_restrictions = {
            "required_classes": list(gem.required_classes or []),
            "excluded_classes": list(gem.excluded_classes or []),
            "required_races":   list(gem.required_races or []),
            "excluded_races":   list(gem.excluded_races or []),
            "min_alignment_score": gem.min_alignment_score,
            "max_alignment_score": gem.max_alignment_score,
        }

        # --- Consume the gem (delete → NFTService → RESERVE) ---
        gem.delete()

        # --- Lock and start insetting ---
        caller.ndb.is_processing = True

        caller.location.msg_contents_with_invis_alt(
            f"{caller.key} begins carefully setting a gem at the {room.key}.",
            f"Tiny tools seem to move on their own at the {room.key}, "
            f"setting something into place...",
            from_obj=caller,
        )

        # --- Chain delayed progress ticks ---
        def _tick(step):
            if step < INSET_TICKS:
                filled = _BAR_WIDTH * step // INSET_TICKS
                bar = '#' * filled + '-' * (_BAR_WIDTH - filled)
                caller.msg(f"Insetting {gem_effects[0].get('stat', gem_effects[0].get('condition', 'gem'))}... [{bar}]")
                delay(INSET_TICK_SECONDS, _tick, step + 1)
            else:
                bar = '#' * _BAR_WIDTH
                caller.msg(f"Insetting... [{bar}] Done!")

                try:
                    # Transfer gem effects → weapon.wear_effects (extend)
                    weapon.wear_effects = (
                        list(weapon.wear_effects or []) + gem_effects
                    )

                    # Transfer gem restrictions → weapon ItemRestrictionMixin
                    # fields. Lists are unioned (deduplicated); alignment
                    # bounds take the more restrictive value.
                    _merge_list_field(weapon, "required_classes", gem_restrictions)
                    _merge_list_field(weapon, "excluded_classes", gem_restrictions)
                    _merge_list_field(weapon, "required_races",   gem_restrictions)
                    _merge_list_field(weapon, "excluded_races",   gem_restrictions)
                    _merge_min_bound(weapon, "min_alignment_score", gem_restrictions)
                    _merge_max_bound(weapon, "max_alignment_score", gem_restrictions)

                    weapon.is_inset = True

                    # Generate LLM name
                    new_name = name_generator.generate_inset_name(
                        weapon.key, gem_effects, caller
                    )
                    weapon.key = new_name

                    # Persist updated fields to NFTGameState metadata so the
                    # weapon survives despawn/respawn. Uses the same field
                    # names as ItemRestrictionMixin / WearableMixin —
                    # no custom keys.
                    nft = NFTGameState.objects.get(
                        nftoken_id=str(weapon.token_id),
                    )
                    nft.metadata["name"] = new_name
                    nft.metadata["wear_effects"] = weapon.wear_effects
                    nft.metadata["required_classes"] = list(weapon.required_classes or [])
                    nft.metadata["excluded_classes"] = list(weapon.excluded_classes or [])
                    nft.metadata["required_races"]   = list(weapon.required_races or [])
                    nft.metadata["excluded_races"]   = list(weapon.excluded_races or [])
                    nft.metadata["min_alignment_score"] = weapon.min_alignment_score
                    nft.metadata["max_alignment_score"] = weapon.max_alignment_score
                    nft.metadata["is_inset"] = True
                    nft.save(update_fields=["metadata", "updated_at"])

                except Exception as err:
                    caller.msg(f"|rInsetting failed: {err}|n")
                    caller.ndb.is_processing = False
                    return

                caller.msg(
                    f"|gYou inset the gem into the weapon, "
                    f"creating |w{new_name}|g!|n"
                )

                # Award XP
                multiplier = room.craft_xp_multiplier or 1.0
                xp = int(INSET_XP * multiplier)
                if xp > 0:
                    caller.at_gain_experience_points(xp)

                caller.location.msg_contents_with_invis_alt(
                    f"{caller.key} finishes gem setting at the {room.key}.",
                    f"The tools at the {room.key} clatter to a stop. "
                    f"A newly enhanced weapon gleams on the workbench.",
                    from_obj=caller,
                )
                caller.ndb.is_processing = False

        # Start first tick
        delay(INSET_TICK_SECONDS, _tick, 1)


def _merge_list_field(weapon, field, gem_restrictions):
    """Union the gem's list-shaped restriction into the weapon's field."""
    incoming = gem_restrictions.get(field) or []
    if not incoming:
        return
    existing = list(getattr(weapon, field, None) or [])
    merged = existing + [v for v in incoming if v not in existing]
    setattr(weapon, field, merged)


def _merge_min_bound(weapon, field, gem_restrictions):
    """Take the more restrictive (higher) min bound."""
    incoming = gem_restrictions.get(field)
    if incoming is None:
        return
    existing = getattr(weapon, field, None)
    setattr(weapon, field, incoming if existing is None else max(existing, incoming))


def _merge_max_bound(weapon, field, gem_restrictions):
    """Take the more restrictive (lower) max bound."""
    incoming = gem_restrictions.get(field)
    if incoming is None:
        return
    existing = getattr(weapon, field, None)
    setattr(weapon, field, incoming if existing is None else min(existing, incoming))


def _describe_effect(effect):
    """Format a single effect dict into a human-readable string."""
    etype = effect.get("type", "")
    if etype == "stat_bonus":
        stat = effect.get("stat", "unknown").replace("_", " ")
        value = effect.get("value", 0)
        sign = "+" if value > 0 else ""
        return f"{sign}{value} {stat}"
    elif etype == "condition":
        return effect.get("condition", "unknown").replace("_", " ")
    elif etype == "damage_resistance":
        dtype = effect.get("damage_type", "unknown")
        return f"{effect.get('value', 0)}% {dtype} resistance"
    elif etype == "hit_bonus":
        wtype = effect.get("weapon_type", "").replace("_", " ")
        value = effect.get("value", 0)
        return f"+{value} hit ({wtype})"
    elif etype == "damage_bonus":
        wtype = effect.get("weapon_type", "").replace("_", " ")
        value = effect.get("value", 0)
        return f"+{value} damage ({wtype})"
    return str(effect)
