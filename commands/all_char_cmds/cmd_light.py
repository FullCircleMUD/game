"""
Light and extinguish commands for light sources (torches, lanterns).

Usage:
    light <item>       — light an equipped light source
    extinguish <item>  — put out a lit light source

Light sources must be equipped (held/worn) to be lit or extinguished.
Neither command requires sight — you can light a torch by touch in
the dark, and if a torch is lit the room isn't dark.
"""

from evennia import Command

from commands.command import FCMCommandMixin
from utils.targeting.helpers import resolve_target
from utils.targeting.predicates import p_can_see


class CmdLight(FCMCommandMixin, Command):
    """
    Light a torch, lantern, or other light source.

    Usage:
        light <item>

    The item must be equipped (held or worn). You can light a torch
    in the dark by touch — no sight required.
    """

    key = "light"
    aliases = ()
    locks = "cmd:all()"
    help_category = "Items"

    def func(self):
        caller = self.caller

        if not self.args:
            caller.msg("Light what?")
            return

        query = self.args.strip()

        # No darkness check — you can light an equipped torch by touch
        item, _ = resolve_target(
            caller, query, "items_equipped",
            extra_predicates=(p_can_see,),
        )
        if not item:
            caller.msg(f"You aren't wearing '{query}'.")
            return

        # Must be a light source
        if not getattr(item, "is_light_source", False):
            caller.msg("That's not something you can light.")
            return

        # Light it
        success, msg = item.light(lighter=caller)
        if success:
            caller.msg(f"|yYou light {item.key}.|n")
            caller.location.msg_contents(
                f"$You() $conj(light) {item.key}.",
                from_obj=caller,
                exclude=[caller],
            )
        else:
            caller.msg(msg)


class CmdExtinguish(FCMCommandMixin, Command):
    """
    Extinguish a lit light source.

    Usage:
        extinguish <item>
        douse <item>
        snuff <item>

    Puts out an equipped torch, lantern, or other light source.
    Remaining fuel is preserved.
    """

    key = "extinguish"
    aliases = ["douse", "snuff"]
    locks = "cmd:all()"
    help_category = "Items"

    def func(self):
        caller = self.caller

        if not self.args:
            caller.msg("Extinguish what?")
            return

        query = self.args.strip()

        # No darkness check — if a light source is lit, the room isn't dark
        item, _ = resolve_target(
            caller, query, "items_equipped",
            extra_predicates=(p_can_see,),
        )
        if not item:
            caller.msg(f"You aren't wearing '{query}'.")
            return

        if not getattr(item, "is_light_source", False):
            caller.msg("That's not something you can extinguish.")
            return

        success, msg = item.extinguish(extinguisher=caller)
        if success:
            caller.msg(f"|xYou extinguish {item.key}.|n")
            caller.location.msg_contents(
                f"$You() $conj(extinguish) {item.key}.",
                from_obj=caller,
                exclude=[caller],
            )
        else:
            caller.msg(msg)
