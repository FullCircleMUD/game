from evennia import Command

from commands.command import FCMCommandMixin
from utils.health_desc import health_description as _health_description


class CmdDiagnose(FCMCommandMixin, Command):
    """
    Assess the health of a character or creature.

    Usage:
        diagnose <target>
        diagnose

    Without arguments, diagnoses yourself.
    """

    key = "diagnose"
    aliases = ["diag"]
    help_category = "General"
    locks = "cmd:all()"
    allow_while_sleeping = True

    def func(self):
        caller = self.caller

        if not self.args or not self.args.strip():
            target = caller
        else:
            target = caller.search(self.args.strip())
            if not target:
                return

        if not hasattr(target, "hp"):
            caller.msg("You can't diagnose that.")
            return

        hp = target.hp
        hp_max = target.effective_hp_max
        desc = _health_description(hp, hp_max)

        if target == caller:
            caller.msg(f"You are {desc}. ({hp}/{hp_max} HP)")
        else:
            caller.msg(f"{target.key} {desc}. ({hp}/{hp_max} HP)")
