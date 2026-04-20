"""
Zap command — cast the spell bound to a held wand.

The wand MUST be in the HOLD slot (equipped), not merely in inventory.
This removes any ambiguity about which wand is being activated when a
character is carrying several. To switch wands, ``remove`` the current
one and ``hold`` another.

Zapping is free at use time: the enchanter pre-paid the spell's mana
cost when they crafted the wand. Every zap casts the bound spell as if
the caster were at the spell's own min_mastery — a Magic Missile wand
always casts as BASIC, a Fireball wand always casts as EXPERT — so
wand power is forecastable and doesn't scale with the zapper.

Usage:
    zap <target>

Target resolution follows the bound spell's ``target_type`` (hostile,
friendly, self, none, any) — same rules as the ``cast`` command.

Gates:
    1. A wand must be held (not just carried)
    2. The wand must have at least one charge remaining
    3. The wand's ``can_use()`` must pass (mage class OR magical secrets
       mastery >= bound spell's tier)

On successful zap:
    - Charges decrement by 1
    - NFTGameState.metadata is re-persisted
    - If charges hit 0, the wand is destroyed and removed from inventory
"""

from evennia import Command

from commands.command import FCMCommandMixin
from enums.condition import Condition
from enums.wearslot import HumanoidWearSlot
from typeclasses.items.holdables.wand_nft_item import WandNFTItem
from world.spells.registry import SPELL_REGISTRY
from utils.targeting.helpers import resolve_target
from utils.targeting.predicates import check_range, p_can_see


class CmdZap(FCMCommandMixin, Command):
    """
    Zap the spell bound to your held wand at a target.

    Usage:
        zap <target>
        zap                 (for self-targeting wands)

    You must be holding an enchanted wand. The wand's spell is cast
    exactly as it was enchanted — tier, damage, saves, and messages
    match a normal cast of that spell. Each zap consumes one charge;
    when a wand runs out of charges it is destroyed.
    """

    key = "zap"
    locks = "cmd:all()"
    help_category = "Magic"

    def func(self):
        caller = self.caller

        # ── 1. Find the held wand ─────────────────────────────
        held = caller.get_slot(HumanoidWearSlot.HOLD)
        if held is None:
            caller.msg("You aren't holding anything to zap.")
            return
        if not isinstance(held, WandNFTItem):
            caller.msg(f"{held.key} isn't a wand.")
            return
        wand = held

        # ── 2. Gate checks ────────────────────────────────────
        ok, reason = wand.can_use(caller)
        if not ok:
            caller.msg(reason or "You can't use this wand.")
            return

        if wand.charges_remaining <= 0:
            caller.msg(f"{wand.key} is expended — it has no charges left.")
            return

        spell = SPELL_REGISTRY.get(wand.spell_key)
        if spell is None:
            caller.msg(f"{wand.key}'s binding is broken — the spell is unknown.")
            return

        # ── 3. Resolve target per the spell's target_type ────
        target_str = self.args.strip()
        extra = (p_can_see,) if spell.requires_sight else ()
        target, secondaries = resolve_target(
            caller, target_str, spell.target_type,
            aoe=spell.aoe,
            extra_predicates=extra,
        )
        if target is None and spell.target_type != "none":
            return

        # Range/height check — uses spell's overridable messages
        if target and target is not caller:
            if not check_range(caller, target, spell.range, source=spell):
                return

        # ── 4. Cast via the bound spell, with wand overrides ─
        # Force the caster tier to the spell's base min_mastery, and
        # treat the cast as free (mana was pre-paid at enchant time).
        caller.ndb._wand_caster_tier_override = spell.min_mastery.value
        caller.ndb._wand_free_cast = True
        try:
            success, result = spell.cast(caller, target, secondaries=secondaries)
        finally:
            caller.ndb._wand_caster_tier_override = None
            caller.ndb._wand_free_cast = False

        # ── 5. Break invisibility / sanctuary on hostile zap ─
        if success and spell.target_type == "actor_hostile":
            if (hasattr(caller, "break_invisibility")
                    and caller.has_condition(Condition.INVISIBLE)):
                caller.break_invisibility()
                caller.msg("|yYour invisibility fades as you zap.|n")
            if (hasattr(caller, "break_sanctuary")
                    and caller.has_condition(Condition.SANCTUARY)):
                caller.break_sanctuary()
                caller.msg("|WYour sanctuary fades as you zap an offensive spell!|n")

        # ── 6. Dispatch spell messages (same pattern as cast) ─
        if isinstance(result, str):
            caller.msg(result)
            return  # validation failure — don't decrement charges
        else:
            caller.msg(result["first"])
            if target and target != caller and result.get("second"):
                target.msg(result["second"])
            if caller.location and result.get("third"):
                exclude = [caller]
                if target and target != caller:
                    exclude.append(target)
                caller.location.msg_contents(result["third"], exclude=exclude)

        # ── 7. Decrement charges and destroy if expended ─────
        if not success:
            return  # spell didn't actually fire — charges preserved

        wand.charges_remaining -= 1
        wand.persist_wand_state()

        if wand.charges_remaining <= 0:
            caller.msg(f"|y{wand.key} crumbles to dust — its last charge spent.|n")
            # Unequip before delete so wearslot cleanup runs correctly
            try:
                caller.remove(wand)
            except Exception:
                pass
            wand.delete()
