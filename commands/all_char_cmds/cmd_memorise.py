"""
Memorise and Forget commands — manage spell memorisation.

Usage:
    memorise <spell>    — memorise a known spell (has delay)
    forget <spell>      — forget a memorised spell (instant)

Memorisation is capped by class level + ability bonus + equipment.
Memorise has a timed delay with progress bar. Forget is instant.
"""

from evennia import Command

from commands.command import FCMCommandMixin
from utils.busy import check_busy, progress_bar, start_busy_ticks
from world.spells.registry import find_spell


# ── Memorisation delay configuration ──
MEMORISE_TICK_SECONDS = 2
MEMORISE_NUM_TICKS = 3


class CmdMemorise(FCMCommandMixin, Command):
    """
    Memorise a known spell so it can be cast.

    Usage:
        memorise <spell>
        memorize <spell>

    Examples:
        memorise magic missile
        memorize cure wounds

    Memorisation takes a few seconds. You must be sitting, know the spell
    (in your spellbook) and have a free memory slot.
    """

    key = "memorise"
    aliases = ["memorize"]
    locks = "cmd:all()"
    help_category = "Magic"
    allow_while_sleeping = False
    required_position = "sitting"
    position_error_msg = "You must sit down before you can memorise a spell."

    def func(self):
        caller = self.caller

        if not self.args:
            caller.msg("Memorise what? Usage: memorise <spell>")
            return

        if check_busy(caller):
            return

        # Find the spell by name/key
        spell_match = find_spell(self.args.strip(), True)
        if not spell_match:
            caller.msg("You don't know a spell by that name.")
            return

        # Check the character knows the spell
        if not caller.knows_spell(spell_match.key):
            caller.msg(f"You don't know {spell_match.name}.")
            return

        # Check school mastery (remorters may have spells above current mastery)
        mastery_data = (caller.db.class_skill_mastery_levels or {}).get(
            spell_match.school_key, 0
        )
        # Handle nested dict format from chargen: {"mastery": int, "classes": [...]}
        # Note: Evennia wraps db attrs in _SaverDict which may not pass isinstance(dict)
        if hasattr(mastery_data, "get") and not isinstance(mastery_data, (int, float)):
            current_mastery = int(mastery_data.get("mastery", 0))
        else:
            current_mastery = int(mastery_data)
        if current_mastery < spell_match.min_mastery.value:
            school_name = spell_match.school_key.replace("_", " ").title()
            caller.msg(
                f"Your mastery of |w{school_name}|n is too low to memorise "
                f"{spell_match.name}. You need at least "
                f"|w{spell_match.min_mastery.name}|n mastery."
            )
            return

        # Check if already memorised
        if caller.is_memorised(spell_match.key):
            caller.msg(f"{spell_match.name} is already memorised.")
            return

        # Check cap before starting delay
        cap = caller.get_memorisation_cap()
        current_count = len(caller.db.memorised_spells or {})
        if current_count >= cap:
            caller.msg(
                f"You can only memorise {cap} spell{'s' if cap != 1 else ''}. "
                f"Forget one first."
            )
            return

        def _complete():
            # Getting up loses your place — the seat is the whole point.
            if caller.position != "sitting":
                caller.msg(
                    f"You lost your place in the passage on {spell_match.name}."
                )
                return
            success, msg = caller.memorise_spell(spell_match.key)
            caller.msg(msg)

        start_busy_ticks(
            caller,
            MEMORISE_NUM_TICKS,
            MEMORISE_TICK_SECONDS,
            _complete,
            progress=lambda step, total: f"Memorising... [{progress_bar(step, total)}]",
            done_msg=f"Memorising... [{progress_bar(1, 1)}]",
            self_msg=f"You begin memorising {spell_match.name}...",
            busy_msg="You are deep in your spellbook. Finish first.",
            busy_move_msg="You would lose your place. Finish memorising first.",
        )


class CmdForget(FCMCommandMixin, Command):
    """
    Forget a memorised spell to free up a memory slot.

    Usage:
        forget <spell>

    Examples:
        forget magic missile
        forget cure wounds

    Forgetting is instant.
    """

    key = "forget"
    aliases = []
    locks = "cmd:all()"
    help_category = "Magic"
    allow_while_sleeping = True

    def func(self):
        caller = self.caller

        if not self.args:
            caller.msg("Forget what? Usage: forget <spell>")
            return

        spell_name = self.args.strip()

        # Find the spell by name/key
        spell_match = find_spell(spell_name, True, caller.get_memorised_spells())

        if not spell_match:
            caller.msg(f"You don't have {spell_name} memorised.")
            return

        success, msg = caller.forget_spell(spell_match.key)
        caller.msg(msg)
