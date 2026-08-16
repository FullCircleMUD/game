from evennia import Command

from commands.command import FCMCommandMixin
from utils.health_desc import health_description as _health_description
from utils.targeting.helpers import resolve_target
from utils.visibility import looker_is_blind


class CmdDiagnose(FCMCommandMixin, Command):
    """
    Assess the health of a character or creature.

    Usage:
        diagnose <target>
        diagnose

    Without arguments, diagnoses yourself.
    """

    key = "diagnose"
    aliases = []
    help_category = "General"
    locks = "cmd:all()"
    allow_while_sleeping = True

    def func(self):
        caller = self.caller

        if not self.args or not self.args.strip():
            target = caller
        else:
            # Reading someone's wounds is visual, so it needs working
            # eyes — a dark room or the BLINDED condition both stop it.
            # Diagnosing yourself short-circuits above and is unaffected:
            # you know your own injuries by feel.
            if looker_is_blind(caller):
                caller.msg("It's too dark to see anything.")
                return

            # Filtering lives in the resolvers, not here: p_living, then
            # p_can_see either way — helping someone means picking the
            # right person, in or out of a fight.
            target, _ = resolve_target(
                caller, self.args.strip(), "actor_friendly",
            )
            if not target:
                return  # actor resolver already messaged

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
