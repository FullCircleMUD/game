"""
Refill command — top up a water container from a fountain in the room.

Usage:
    refill <container>   — refill a specific container by name
    refill               — refill the first non-full water container

Requires a `FountainFixture` (or any object with `is_water_source = True`)
in the current room. Future zones will tag rivers, wells, and the
spring-fed pool the same way.
"""

from evennia import Command

from commands.command import FCMCommandMixin


class CmdRefill(FCMCommandMixin, Command):
    """
    Refill a water container from a fountain or other water source in
    the room.

    Usage:
        refill
        refill <container>
    """

    key = "refill"
    aliases = ["refill"]
    locks = "cmd:all()"
    help_category = "Items"

    def func(self):
        caller = self.caller
        if not caller.location:
            caller.msg("You can't refill anything here.")
            return

        source = self._find_water_source(caller.location)
        if source is None:
            caller.msg("There is no water source here to refill from.")
            return

        query = self.args.strip()
        if query:
            container = caller.search(query, location=caller)
            if not container:
                return
            if not getattr(container, "is_water_container", False):
                caller.msg(f"You can't refill {container.key}.")
                return
        else:
            container = self._first_non_full_container(caller)
            if container is None:
                caller.msg("You have no water container to refill.")
                return

        success, msg = container.refill_to_full()
        if not success:
            caller.msg(msg)
            return

        caller.msg(f"|cYou refill {container.key} at {source.key}.|n")
        if caller.location:
            caller.location.msg_contents(
                f"$You() $conj(refill) {container.key} at {source.key}.",
                from_obj=caller,
                exclude=[caller],
            )

    @staticmethod
    def _find_water_source(room):
        for obj in room.contents:
            if getattr(obj, "is_water_source", False):
                return obj
        return None

    @staticmethod
    def _first_non_full_container(caller):
        for obj in caller.contents:
            if not getattr(obj, "is_water_container", False):
                continue
            if getattr(obj, "is_full", False):
                continue
            return obj
        return None
