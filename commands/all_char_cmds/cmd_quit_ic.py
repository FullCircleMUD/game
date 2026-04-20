"""
Quit command for characters (IC).

Quitting always dumps all equipment into an abandoned pack on the
ground (with a timed owner-only loot lock), then sends the character
to their home room before unpuppeting.

Players who want a safe logout should use ``rent`` at an inn instead.

Usage:
    quit
"""

from evennia import Command, create_object

from commands.command import FCMCommandMixin


class CmdQuitIC(FCMCommandMixin, Command):
    """
    Leave the game.

    Usage:
        quit

    Quitting drops all your belongings into an abandoned pack
    on the ground and sends your character home. Anyone can loot
    the pack after a short time.

    Use |wrent|n at an inn for a safe logout.
    """

    key = "quit"
    locks = "cmd:all()"
    help_category = "System"
    allow_while_sleeping = True

    def func(self):
        caller = self.caller

        if caller.scripts.get("combat_handler"):
            caller.msg(
                "You can't quit while in combat! "
                "You must flee or end the fight first."
            )
            return

        session = self.session
        account = getattr(caller, "account", None)

        if not account:
            caller.msg("Cannot find your account.")
            return

        # Warn and confirm
        answer = yield (
            "\n|r--- WARNING ---|n"
            "\nQuitting will:"
            "\n  - Drop all your equipment into an abandoned pack here"
            "\n  - Send your character to their home room"
            "\n  - Anyone can loot the pack after a short time"
            "\n\n|yVisit an inn and use |wrent|y to log out safely.|n"
            "\n\nAre you sure you want to quit? Y/[N]"
        )

        if answer.lower() not in ("y", "yes"):
            caller.msg("Quit cancelled.")
            return

        room = caller.location
        self._create_quit_drop(caller, room)
        self._send_home(caller)

        # Return to OOC account menu
        account.msg(
            account.at_look(
                target=account.characters,
                session=account.sessions.get()[0],
            )
        )
        account.unpuppet_object(session)

    def _create_quit_drop(self, caller, room):
        """Unequip everything, create a QuitDrop, move gear into it."""
        from typeclasses.items.base_nft_item import BaseNFTItem
        from typeclasses.world_objects.quit_drop import QuitDrop

        # Unequip all worn/wielded/held items
        if hasattr(caller, "get_all_worn"):
            for item in list(caller.get_all_worn().values()):
                if item is not None:
                    caller.remove(item)

        # Collect transferable items
        nft_items = [
            obj for obj in caller.contents
            if isinstance(obj, BaseNFTItem)
        ]
        gold = caller.get_gold()
        resources = {
            rid: amt
            for rid, amt in caller.get_all_resources().items()
            if amt > 0
        }

        # Nothing to drop? Skip creating the container
        if not nft_items and gold <= 0 and not resources:
            return

        # Create the quit drop container
        quit_drop = create_object(
            QuitDrop,
            key="quit_drop",
            location=room,
            nohome=True,
        )
        quit_drop.owner_character_key = caller.key
        quit_drop.owner_name = caller.key

        # Move NFT items
        for obj in list(nft_items):
            obj.move_to(quit_drop, quiet=True, move_type="teleport")

        # Transfer gold
        if gold > 0:
            caller.transfer_gold_to(quit_drop, gold)

        # Transfer resources
        for rid, amt in resources.items():
            caller.transfer_resource_to(quit_drop, rid, amt)

        # Start loot-lock timers
        quit_drop.start_timers()

        # Announce
        room.msg_contents(
            f"{caller.key} has left the game, abandoning a pack of belongings.",
            exclude=[caller],
            from_obj=caller,
        )
        caller.msg(
            "|rYour belongings have been dropped on the ground.|n"
        )

    def _send_home(self, caller):
        """Move the character to their home room."""
        destination = caller.home
        if destination:
            caller.move_to(destination, quiet=True, move_type="teleport")
