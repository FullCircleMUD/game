"""
Verbose exit listing — shows all visible exits with direction,
destination, description, and door state.

Available regardless of the auto_exits preference (auto_exits only
controls the compact ``[ Exits: n s e w ]`` line in the room display).
"""

from evennia import Command


class CmdExits(Command):
    """
    Show detailed exit information for your current room.

    Usage:
        exits

    Lists every visible exit with its direction, destination,
    description, and door state. Unlike the compact auto-exit line,
    this always shows full details including closed/locked doors.
    """

    key = "exits"
    aliases = ["ex"]
    locks = "cmd:all()"
    help_category = "General"

    # Canonical display order
    _DIR_ORDER = [
        "north", "east", "south", "west",
        "northeast", "northwest", "southeast", "southwest",
        "up", "down", "in", "out",
    ]

    def func(self):
        caller = self.caller
        room = caller.location
        if not room:
            caller.msg("You have no location.")
            return

        # Darkness check
        if hasattr(room, "is_dark") and room.is_dark(caller):
            caller.msg("It's too dark to see any exits.")
            return

        exits = room.contents_get(content_type="exit")

        # Filter visibility (hidden/invisible doors, etc.)
        exits = [
            ex for ex in exits
            if not hasattr(ex, "is_visible_to") or ex.is_visible_to(caller)
        ]

        if not exits:
            caller.msg("There are no obvious exits.")
            return

        # Sort by canonical direction order
        dir_order = {d: i for i, d in enumerate(self._DIR_ORDER)}

        def sort_key(ex):
            direction = getattr(ex, "direction", None)
            if direction and direction in dir_order:
                return dir_order[direction]
            return 99

        exits.sort(key=sort_key)

        lines = ["|wObvious exits:|n"]
        for ex in exits:
            direction = getattr(ex, "direction", None)

            # Direction label
            if direction and direction != "default":
                dir_label = direction.capitalize()
            else:
                dir_label = ex.key.capitalize()

            # Destination name
            dest = ex.destination
            dest_name = dest.get_display_name(caller) if dest else "Unknown"

            # Door state
            state = ""
            if hasattr(ex, "is_locked") and ex.is_locked:
                state = " |r(locked)|n"
            elif hasattr(ex, "is_open") and not ex.is_open:
                state = " |y(closed)|n"

            # Description (use closed_desc/open_desc for doors, else db.desc)
            desc = None
            if hasattr(ex, "is_open"):
                if not ex.is_open and getattr(ex, "closed_desc", None):
                    desc = ex.closed_desc
                elif ex.is_open and getattr(ex, "open_desc", None):
                    desc = ex.open_desc
            if not desc:
                desc = ex.db.desc if ex.db.desc else ""
            # Don't show Evennia's default "This is an exit."
            if desc == "This is an exit.":
                desc = ""

            line = f"  |c{dir_label:<12}|n - {dest_name}{state}"
            if desc:
                line += f"\n               {desc}"
            lines.append(line)

        caller.msg("\n".join(lines))
