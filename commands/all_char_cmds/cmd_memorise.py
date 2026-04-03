"""
Memorise and Forget commands — manage spell memorisation.

Usage:
    memorise <spell>    — memorise a known spell (has delay)
    forget <spell>      — forget a memorised spell (instant)

Memorisation is capped by class level + ability bonus + equipment.
Memorise has a timed delay with progress bar. Forget is instant.
"""

from evennia import Command
from evennia.utils import delay

from commands.command import FCMCommandMixin
from world.spells.registry import get_spell, SPELL_REGISTRY


# ── Memorisation delay configuration ──
MEMORISE_TICK_SECONDS = 2
MEMORISE_NUM_TICKS = 3
_BAR_WIDTH = 10


class CmdMemorise(FCMCommandMixin, Command):
    """
    Memorise a known spell so it can be cast.

    Usage:
        memorise <spell>
        memorize <spell>

    Examples:
        memorise magic missile
        memorize cure wounds

    Memorisation takes a few seconds. You must know the spell
    (in your spellbook) and have a free memory slot.
    """

    key = "memorise"
    aliases = ["memorize", "mem"]
    locks = "cmd:all()"
    help_category = "Magic"

    def func(self):
        caller = self.caller

        if not self.args:
            caller.msg("Memorise what? Usage: memorise <spell>")
            return

        if getattr(caller.ndb, "is_memorising", False):
            caller.msg("You are already memorising a spell.")
            return

        # Find the spell by name/key
        spell_match = self._find_spell(self.args.strip())
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

        # Start memorisation with delay
        caller.ndb.is_memorising = True
        caller.msg(f"You begin memorising {spell_match.name}...")

        def _tick(step):
            if step < MEMORISE_NUM_TICKS:
                filled = _BAR_WIDTH * step // MEMORISE_NUM_TICKS
                bar = "#" * filled + "-" * (_BAR_WIDTH - filled)
                caller.msg(f"Memorising... [{bar}]")
                delay(MEMORISE_TICK_SECONDS, _tick, step + 1)
            else:
                bar = "#" * _BAR_WIDTH
                caller.msg(f"Memorising... [{bar}]")
                caller.ndb.is_memorising = False
                success, msg = caller.memorise_spell(spell_match.key)
                caller.msg(msg)

        delay(MEMORISE_TICK_SECONDS, _tick, 1)

    def _find_spell(self, args):
        """Find a spell by name, key, or alias (case insensitive)."""
        args_lower = args.lower()
        # Exact match on name, key, or alias
        for spell_key, spell_obj in SPELL_REGISTRY.items():
            if spell_obj.name.lower() == args_lower:
                return spell_obj
            if spell_key.replace("_", " ") == args_lower:
                return spell_obj
            for alias in getattr(spell_obj, "aliases", []):
                if alias.lower() == args_lower:
                    return spell_obj
        # Substring fallback
        for spell_key, spell_obj in SPELL_REGISTRY.items():
            if args_lower in spell_obj.name.lower():
                return spell_obj
            if args_lower in spell_key.replace("_", " "):
                return spell_obj
        return None


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
    aliases = ["for"]
    locks = "cmd:all()"
    help_category = "Magic"

    def func(self):
        caller = self.caller

        if not self.args:
            caller.msg("Forget what? Usage: forget <spell>")
            return

        # Find the spell by name/key
        spell_match = self._find_spell(self.args.strip())
        if not spell_match:
            caller.msg("You don't know a spell by that name.")
            return

        success, msg = caller.forget_spell(spell_match.key)
        caller.msg(msg)

    def _find_spell(self, args):
        """Find a spell by name, key, or alias (case insensitive)."""
        args_lower = args.lower()
        # Exact match on name, key, or alias
        for spell_key, spell_obj in SPELL_REGISTRY.items():
            if spell_obj.name.lower() == args_lower:
                return spell_obj
            if spell_key.replace("_", " ") == args_lower:
                return spell_obj
            for alias in getattr(spell_obj, "aliases", []):
                if alias.lower() == args_lower:
                    return spell_obj
        # Substring fallback
        for spell_key, spell_obj in SPELL_REGISTRY.items():
            if args_lower in spell_obj.name.lower():
                return spell_obj
            if args_lower in spell_key.replace("_", " "):
                return spell_obj
        return None
