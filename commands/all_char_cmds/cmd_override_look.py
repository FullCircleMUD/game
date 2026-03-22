"""
FCM look command — adds darkness check, container inspection, and brief bypass.

Overrides Evennia's default ``look`` to prevent inspecting objects/NPCs
in the room when it's too dark to see.  Looking at the room itself still
works (the room's ``return_appearance`` handles the dark template).
Looking at items in your own inventory is always allowed.

Also adds ``look in <container>`` syntax for viewing container contents.

Passes ``ignore_brief=True`` so that an explicit ``look`` always shows
the full room description, even when the player has brief mode enabled.
"""

from evennia.commands.default.general import CmdLook as _EvenniaCmdLook


class CmdLook(_EvenniaCmdLook):
    """
    Look at location or object.

    Usage:
        look
        look <obj>
        look in <container>

    Observes your location or objects in your vicinity.
    In darkness, you can only see the room layout and your own inventory.
    Use 'look in' to view the contents of a container.
    """

    help_category = "General"

    def func(self):
        caller = self.caller

        # --- "look in <container>" ---
        if self.args:
            lower = self.args.lower().strip()
            if lower.startswith("in "):
                container_name = self.args.strip()[3:].strip()
                if container_name:
                    self._look_in_container(caller, container_name)
                    return

        if self.args and caller.location:
            room = caller.location
            if hasattr(room, "is_dark") and room.is_dark(caller):
                # In darkness, only allow looking at items in your inventory.
                target = caller.search(self.args)
                if not target:
                    return
                if target.location == room:
                    caller.msg("It's too dark to see anything.")
                    return
                # Target is in inventory — allow the look.
                desc = caller.at_look(target)
                self.msg(text=(desc, {"type": "look"}), options=None)
                return

        # --- Room detail check (fallback when no real object matches) ---
        if self.args and caller.location:
            # Quiet search — if a real object exists, let super() handle it
            found = caller.search(self.args, quiet=True)
            if not found:
                room = caller.location
                details = getattr(room, "details", None)
                if details:
                    key = self.args.strip().lower()
                    for detail_key, desc in details.items():
                        if detail_key.lower() == key:
                            caller.msg(desc)
                            return

        # Explicit 'look' always shows full description (bypass brief mode).
        # Looking at the room (no args) — pass ignore_brief.
        if not self.args:
            if caller.location and caller.location.access(caller, "view"):
                desc = caller.at_look(caller.location, ignore_brief=True)
                self.msg(text=(desc, {"type": "look"}), options=None)
                return

        super().func()

    def _look_in_container(self, caller, container_name):
        """Display contents of a container."""
        room = caller.location

        # Darkness check — can only inspect containers in inventory when dark
        if room and hasattr(room, "is_dark") and room.is_dark(caller):
            container = caller.search(
                container_name, location=caller, quiet=True
            )
            if not container:
                caller.msg("It's too dark to see anything.")
                return
            if isinstance(container, list):
                container = container[0]
        else:
            # Search inventory first, then room
            container = caller.search(
                container_name, location=caller, quiet=True
            )
            if not container:
                container = caller.search(
                    container_name, location=caller.location, quiet=True
                )
            if not container:
                caller.msg(f"You don't see '{container_name}' here.")
                return
            if isinstance(container, list):
                container = container[0]

        if not getattr(container, "is_container", False):
            caller.msg(f"{container.key} is not a container.")
            return

        # Closed container check (chests, etc.)
        if hasattr(container, "is_open") and not container.is_open:
            caller.msg(f"{container.key} is closed.")
            return

        caller.msg(container.get_container_display())
