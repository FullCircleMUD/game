"""
CmdConsider — gauge how tough a target is before fighting.

Compares your stats to the target's and gives a relative assessment
across multiple dimensions: level, health, armor, attacks, and damage.

Usage:
    consider <target>
"""

from evennia import Command

from commands.command import FCMCommandMixin


def _compare(yours, theirs):
    """Return a coloured relative description comparing two numeric values."""
    if theirs == 0 and yours == 0:
        return "|yAbout the same|n"
    if yours == 0:
        ratio = 99
    elif theirs == 0:
        ratio = 0
    else:
        ratio = theirs / yours

    if ratio <= 0.33:
        return "|gMuch lower than yours|n"
    elif ratio <= 0.66:
        return "|gLower than yours|n"
    elif ratio <= 0.85:
        return "|gSlightly lower than yours|n"
    elif ratio <= 1.15:
        return "|yAbout the same|n"
    elif ratio <= 1.5:
        return "|ySlightly higher than yours|n"
    elif ratio <= 2.0:
        return "|rHigher than yours|n"
    else:
        return "|rMuch higher than yours|n"


def _compare_armor(your_ac, their_ac):
    """Compare armor class — lower AC = better armor."""
    diff = your_ac - their_ac  # positive = they're better armored
    if diff >= 8:
        return "|rMuch better armored than you|n"
    elif diff >= 4:
        return "|rBetter armored than you|n"
    elif diff >= 2:
        return "|ySlightly better armored|n"
    elif diff >= -1:
        return "|yAbout the same|n"
    elif diff >= -3:
        return "|gSlightly worse armored|n"
    elif diff >= -7:
        return "|gWorse armored than you|n"
    else:
        return "|gMuch worse armored than you|n"


class CmdConsider(FCMCommandMixin, Command):
    """
    Gauge how tough a target is.

    Usage:
        consider <target>

    Compares your stats to the target's and gives a rough
    estimate across level, health, armor, attacks, and damage.
    """

    key = "consider"
    aliases = ["con"]
    help_category = "Combat"
    locks = "cmd:all()"
    allow_while_sleeping = True

    def func(self):
        caller = self.caller

        if not self.args or not self.args.strip():
            caller.msg("Consider who?")
            return

        target = caller.search(self.args.strip())
        if not target:
            return

        if not hasattr(target, "get_level"):
            caller.msg("You can't consider that.")
            return

        t_name = target.get_display_name(caller)
        c_level = caller.get_level()
        t_level = target.get_level()
        c_hp = getattr(caller, "effective_hp_max", getattr(caller, "hp_max", 1))
        t_hp = getattr(target, "effective_hp_max", getattr(target, "hp_max", 1))
        c_ac = getattr(caller, "effective_ac", 10)
        t_ac = getattr(target, "effective_ac", 10)
        c_att = getattr(caller, "attacks_per_round", 1)
        t_att = getattr(target, "attacks_per_round", 1)
        c_dmg = getattr(caller, "effective_damage_bonus", 0)
        t_dmg = getattr(target, "effective_damage_bonus", 0)

        lines = [f"\n|w{t_name}|n"]
        lines.append(f"  Est. level   : {_compare(c_level, t_level)}")
        lines.append(f"  Est. health  : {_compare(c_hp, t_hp)}")
        lines.append(f"  Est. armor   : {_compare_armor(c_ac, t_ac)}")
        lines.append(f"  Est. attacks : {_compare(c_att, t_att)}")
        lines.append(f"  Est. damage  : {_compare(c_dmg, t_dmg)}")

        caller.msg("\n".join(lines))
