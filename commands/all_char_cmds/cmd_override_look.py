"""
FCM look command — adds darkness check, container inspection, direction
lookup, hidden/invisible filtering, room exclusion, and brief bypass.

Overrides Evennia's default ``look`` to prevent inspecting objects/NPCs
in the room when it's too dark to see.  Looking at the room itself still
works (the room's ``return_appearance`` handles the dark template).
Looking at items in your own inventory is always allowed.

Also adds ``look in <container>`` syntax for viewing container contents.

Direction lookups (``look n``, ``look south``, etc.) are intercepted
early and handled as directional looks — they never hit the generic
object search, avoiding substring ambiguity.

Passes ``ignore_brief=True`` so that an explicit ``look`` always shows
the full room description, even when the player has brief mode enabled.
"""

from evennia.commands.default.general import CmdLook as _EvenniaCmdLook

from typeclasses.terrain.exits.exit_vertical_aware import ExitVerticalAware

# Build set of all direction strings (abbreviations + full names)
_DIRECTION_STRINGS = set()
for _dir, _aliases in ExitVerticalAware.DIRECTION_ALIASES.items():
    for _alias in _aliases:
        _DIRECTION_STRINGS.add(_alias)


class CmdLook(_EvenniaCmdLook):
    """
    Look at location or object.

    Usage:
        look
        look <obj>
        look <direction>
        look in <container>

    Observes your location or objects in your vicinity.
    In darkness, you can only see the room layout and your own inventory.
    Use 'look in' to view the contents of a container.
    """

    help_category = "General"

    def func(self):
        caller = self.caller

        # --- "look around" → same as bare "look" ---
        if self.args and self.args.strip().lower() == "around":
            self.args = ""

        # --- "look in <container>" ---
        if self.args:
            lower = self.args.lower().strip()
            if lower.startswith("in "):
                container_name = self.args.strip()[3:].strip()
                if container_name:
                    self._look_in_container(caller, container_name)
                    return

        # --- "look <direction>" — intercept before generic search ---
        if self.args and caller.location:
            lower = self.args.strip().lower()
            if lower in _DIRECTION_STRINGS:
                self._look_direction(caller, lower)
                return

        # --- Darkness check ---
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
            # Quiet search — filter out room and hidden/invisible objects
            found = caller.search(self.args, quiet=True)
            if found:
                if not isinstance(found, list):
                    found = [found]
                # Filter out the room itself and hidden/invisible objects
                found = [
                    obj for obj in found
                    if obj != caller.location
                    and (
                        not hasattr(obj, "is_visible_to")
                        or obj.is_visible_to(caller)
                    )
                ]
            if found:
                # Show the first visible match directly (bypass super's
                # search which would re-find the room and disambiguate)
                desc = caller.at_look(found[0])
                self.msg(text=(desc, {"type": "look"}), options=None)
                return
            else:
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

        # Final guard — prevent super() from showing hidden/invis/room objects
        if self.args and caller.location:
            found = caller.search(self.args, quiet=True)
            if found:
                if not isinstance(found, list):
                    found = [found]
                # Filter out room and hidden/invisible objects
                visible = [
                    obj for obj in found
                    if obj != caller.location
                    and (
                        not hasattr(obj, "is_visible_to")
                        or obj.is_visible_to(caller)
                    )
                ]
                if not visible and found:
                    # All matches were room or hidden — check if any were
                    # hidden (no period hint) vs just the room (with period)
                    has_hidden = any(
                        hasattr(obj, "is_visible_to")
                        and not obj.is_visible_to(caller)
                        for obj in found
                        if obj != caller.location
                    )
                    if has_hidden:
                        caller.msg(f"You don't see '{self.args.strip()}' here")
                    else:
                        caller.msg(f"You don't see '{self.args.strip()}' here.")
                    return

        super().func()

    # ── Direction lookup ──────────────────────────────────────────────

    def _look_direction(self, caller, direction_str):
        """
        Look in a compass direction. Finds the exit with that direction
        and shows its details. Hidden/invisible exits are not revealed.
        """
        from typeclasses.terrain.exits.exit_vertical_aware import ExitVerticalAware

        # Resolve abbreviation to canonical direction
        canonical = None
        for d, aliases in ExitVerticalAware.DIRECTION_ALIASES.items():
            if direction_str in aliases:
                canonical = d
                break
        if not canonical:
            caller.msg("You see nothing special in that direction.")
            return

        # Find exit with this direction
        char_height = getattr(caller, "room_vertical_position", 0)
        for ex in caller.location.contents_get(content_type="exit"):
            ex_dir = getattr(ex, "direction", None)
            if ex_dir != canonical:
                continue
            # Check visibility
            if hasattr(ex, "is_visible_to") and not ex.is_visible_to(caller):
                break  # exit exists but is hidden — don't reveal
            # Check height accessibility
            if (
                hasattr(ex, "is_height_accessible")
                and not ex.is_height_accessible(char_height)
            ):
                continue  # exit exists but not at this height — try next
            # Show exit details
            desc = caller.at_look(ex)
            self.msg(text=(desc, {"type": "look"}), options=None)
            return

        caller.msg("You see nothing special in that direction.")

    # ── Container inspection ──────────────────────────────────────────

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
