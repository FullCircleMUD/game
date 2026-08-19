"""
Conditions command — see what is currently affecting you.

Usage:
    conditions
    affects
"""

from evennia import Command

from commands.command import FCMCommandMixin


def _label(key):
    """Turn an effect/condition key into a readable name."""
    return key.replace("_", " ").capitalize()


def _duration(caller, key, record):
    """Return how long *key* has left, as a short phrase."""
    duration_type = record.get("duration_type")
    if duration_type == "combat_rounds":
        rounds = record.get("duration")
        if rounds is None:
            return "permanent"
        return f"{rounds} round" + ("" if rounds == 1 else "s")
    if duration_type == "seconds":
        remaining = caller.get_effect_remaining_seconds(key)
        if remaining is None:
            remaining = record.get("duration")
        if remaining is None:
            return "permanent"
        if remaining >= 60:
            minutes = int(remaining // 60)
            return f"{minutes} minute" + ("" if minutes == 1 else "s")
        return f"{int(remaining)} seconds"
    return "permanent"


class CmdConditions(FCMCommandMixin, Command):
    """
    List the effects and conditions currently on you.

    Effects are timed — spells, potions and combat results — and show how
    long they have left. Conditions are the flags those effects set, plus
    anything else holding one; a flag held by two sources shows a count.

    Usage:
        conditions
        affects
    """

    key = "conditions"
    aliases = ["affects"]
    locks = "cmd:all()"
    help_category = "Character"
    arg_regex = r"\s|$"
    allow_while_sleeping = True

    def func(self):
        caller = self.caller
        conditions = {
            key: count
            for key, count in (caller.conditions or {}).items()
            if count > 0
        }
        effects = dict(caller.active_effects or {})

        if not conditions and not effects:
            self.msg("Nothing is affecting you.")
            return

        lines = []
        if effects:
            lines.append("|wEffects:|n")
            for key in sorted(effects):
                lines.append(
                    f"  {_label(key)} — {_duration(caller, key, effects[key])}"
                )
        if conditions:
            lines.append("|wConditions:|n")
            for key in sorted(conditions):
                count = conditions[key]
                stack = f" (x{count})" if count > 1 else ""
                lines.append(f"  {_label(key)}{stack}")
        self.msg("\n".join(lines))
