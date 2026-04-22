"""
Rent command — safely log out at an inn.

Available only in RoomInn rooms. The character stays at the inn
(keeping their location and all equipment) and the player returns
to the OOC account menu.

Usage:
    rent
"""

from evennia import Command

from commands.command import FCMCommandMixin


class CmdRent(FCMCommandMixin, Command):
    """
    Rest at the inn and leave the game safely.

    Usage:
        rent

    Your character stays at the inn with all equipment intact.
    You return to the account menu.
    """

    key = "rent"
    locks = "cmd:all()"
    help_category = "Inn"

    def func(self):
        caller = self.caller

        if caller.scripts.get("combat_handler"):
            caller.msg("You can't rent a room while in combat!")
            return

        session = self.session
        account = getattr(caller, "account", None)

        if not account:
            caller.msg("Cannot find your account.")
            return

        caller.msg(
            "|cYou rent a room at the inn and settle in for a rest.\n"
            "Your belongings are safe.|n"
        )
        caller.location.msg_contents(
            f"{caller.key} rents a room and retires for the night.",
            exclude=[caller],
            from_obj=caller,
        )

        account.msg(
            account.at_look(
                target=account.characters,
                session=account.sessions.get()[0],
            )
        )
        account.mark_graceful_logout()
        account.unpuppet_object(session)
