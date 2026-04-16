"""
Knock — conjuration spell, available from SKILLED mastery.

Magically unlocks a door, chest, or other lockable object. The caster
conjures a force that operates the lock, defeating any mundane locking
mechanism whose ``lock_dc`` is within the caster's tier ceiling.

Tier-gated DC ceilings (deterministic, no roll):

    SKILLED(2):     lock_dc <= 15
    EXPERT(3):      lock_dc <= 20
    MASTER(4):      lock_dc <= 25
    GRANDMASTER(5): no limit ("skeleton key")

On success the spell:
    1. Sets target.is_locked = False
    2. Calls target.at_unlock(caster) so reciprocal doors sync state
    3. Opens the target if it has CloseableMixin (target.open(caster))
    4. Cancels any pending auto-relock script on the target

Knock works on **anything with LockableMixin** by duck-typing on
``is_locked`` — no special-case typeclass branching. ExitDoor,
WorldChest, TrapChest, and any future lockable type all work.

Failure modes (return (False, msg) — mana is still consumed since the
check happens inside ``_execute()`` after Spell.cast() has deducted it,
matching the existing convention):

    - target is not lockable
    - target is already unlocked
    - target's lock_dc exceeds the caster's tier ceiling
    - (target visibility is filtered earlier by ``resolve_spell_target``)
"""

from enums.mastery_level import MasteryLevel
from enums.skills_enum import skills
from world.spells.base_spell import Spell
from world.spells.registry import register_spell


# Maximum lock_dc each caster tier can defeat. None = no ceiling.
_TIER_DC_CEILING = {
    MasteryLevel.SKILLED.value: 15,
    MasteryLevel.EXPERT.value: 20,
    MasteryLevel.MASTER.value: 25,
    MasteryLevel.GRANDMASTER.value: None,
}


@register_spell
class Knock(Spell):
    key = "knock"
    aliases = []
    name = "Knock"
    school = skills.CONJURATION
    min_mastery = MasteryLevel.SKILLED
    mana_cost = {2: 12, 3: 18, 4: 25, 5: 35}
    target_type = "items_all_room_then_inventory"
    description = (
        "Magically unlock and open a door, chest, or other lockable "
        "object. The caster conjures an unseen force that operates the "
        "lock — no key needed, but the difficulty of the lock is gated "
        "by the caster's mastery."
    )
    mechanics = (
        "Tier-gated lock DC ceiling — no roll, deterministic:\n"
        "  SKILLED:     lock_dc <= 15\n"
        "  EXPERT:      lock_dc <= 20\n"
        "  MASTER:      lock_dc <= 25\n"
        "  GRANDMASTER: no limit\n"
        "Works on any object with LockableMixin (doors, chests, etc.).\n"
        "Opens the target after unlocking. Cancels auto-relock timers.\n"
        "Mana is still consumed on failure (e.g. lock too strong)."
    )

    def _execute(self, caster, target):
        # Duck-type the target — anything with is_locked is fair game
        if not hasattr(target, "is_locked"):
            return (False, f"{target.key} cannot be magically unlocked.")

        if not target.is_locked:
            return (False, f"{target.key} is not locked.")

        tier = self.get_caster_tier(caster)
        ceiling = _TIER_DC_CEILING.get(tier)
        target_dc = getattr(target, "lock_dc", 0) or 0

        if ceiling is not None and target_dc > ceiling:
            return (
                False,
                f"The lock on {target.key} resists your magic — it is "
                f"too intricate for your current mastery (DC {target_dc}).",
            )

        # ── Unlock the target ──────────────────────────────────
        target.is_locked = False
        if hasattr(target, "at_unlock"):
            try:
                target.at_unlock(caster)
            except Exception:
                pass  # at_unlock side effects are best-effort

        # Cancel any pending relock script (set by a prior key unlock)
        try:
            target.scripts.delete("relock_timer")
        except Exception:
            pass

        # Open the target if it has CloseableMixin
        opened = False
        if hasattr(target, "is_open") and not target.is_open:
            if hasattr(target, "open"):
                try:
                    target.open(caster)
                    opened = True
                except Exception:
                    # If open() rejects (e.g. via can_open hook), the
                    # spell still counts as a success — the lock is gone.
                    pass

        # ── Multi-perspective messages ────────────────────────
        if opened:
            first = (
                f"|cYou speak the word of opening. The lock on {target.key} "
                f"clicks free, and {target.key} swings open.|n"
            )
            third = (
                f"{caster.key} speaks a word of magic. {target.key} unlocks "
                f"and swings open of its own accord."
            )
        else:
            first = (
                f"|cYou speak the word of opening. The lock on {target.key} "
                f"clicks free.|n"
            )
            third = (
                f"{caster.key} speaks a word of magic. The lock on "
                f"{target.key} clicks free."
            )

        return (True, {"first": first, "second": None, "third": third})
