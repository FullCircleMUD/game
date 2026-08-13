from evennia import Command

from commands.command import FCMCommandMixin
from utils.targeting.predicates import p_can_see


# Canonical scan directions — only follow cardinal + vertical exits
_SCAN_DIRECTIONS = {
    "north", "south", "east", "west",
    "northeast", "northwest", "southeast", "southwest",
    "up", "down",
}

_DIR_ORDER = [
    "north", "east", "south", "west",
    "northeast", "northwest", "southeast", "southwest",
    "up", "down",
]

_DISTANCE_LABELS = {1: "nearby", 2: "not far off", 3: "far off"}


def _can_scan_through(exit_obj, looker):
    """True if *looker* can see past *exit_obj*.

    A sight line, not a route. Exactly two things block one:

    - **The door is shut.** Open means you can see through, closed means you
      cannot. An exit with no door never obstructs anything.
    - **The looker cannot perceive the exit.** Scanning past a hidden or
      invisible door would report who is beyond a passage the looker does not
      know exists — so concealment blocks the sight line whether the door
      stands open or not.

    Lock state is deliberately not read. A lock governs passage, not sight,
    and every locked door is a shut one anyway — ``lock()`` refuses on an open
    door, so an open-and-locked exit is a data anomaly rather than a case to
    handle. The closed check covers every state that can legitimately occur;
    consulting ``is_locked`` here would encode a rule about sight that does
    not exist.

    For the same reason ``open_exits()`` is wrong for scanning, and
    ``p_is_open_exit`` on its own is too: both fold in questions about
    whether you may *go* through.

    Judged from the looker's perspective at any distance, matching how
    ``_get_visible_characters`` treats characters rooms away.
    """
    return getattr(exit_obj, "is_open", True) and p_can_see(exit_obj, looker)


def _get_visible_characters(room, looker):
    """Return list of visible character names in *room* for *looker*.

    Filters out the looker and anyone they can't perceive — concealment
    (HIDDEN / INVISIBLE) and height gating both come from ``p_can_see``.
    Returns None if the room is dark for the looker.
    """
    if hasattr(room, "is_dark") and room.is_dark(looker):
        return None  # dark — can't see

    return [
        char.get_display_name(looker)
        for char in room.contents_get(content_type="character")
        if char != looker and p_can_see(char, looker)
    ]


class CmdScan(FCMCommandMixin, Command):
    """
    Scan your surroundings for characters in nearby rooms.

    Usage:
        scan

    Looks up to 3 rooms in each cardinal direction, reporting any
    characters or creatures spotted. Closed doors and dark rooms
    block scanning beyond that point.
    """

    key = "scan"
    aliases = []
    locks = "cmd:all()"
    help_category = "General"

    def func(self):
        caller = self.caller
        room = caller.location

        if not room:
            caller.msg("You have no location to scan from.")
            return

        lines = []
        found_anything = False

        # Sort exits into canonical direction order
        dir_order = {d: i for i, d in enumerate(_DIR_ORDER)}
        exits = sorted(
            room.exits,
            key=lambda ex: dir_order.get(getattr(ex, "direction", ""), 99),
        )

        for exit_obj in exits:
            direction = getattr(exit_obj, "direction", None)
            if not direction or direction not in _SCAN_DIRECTIONS:
                continue

            if not _can_scan_through(exit_obj, caller):
                continue

            dir_label = direction.capitalize()
            dir_lines = []
            current_room = room

            for distance in range(1, 4):
                # Find the exit in the current direction
                next_exit = None
                if distance == 1:
                    next_exit = exit_obj
                else:
                    for ex in current_room.exits:
                        ex_dir = getattr(ex, "direction", None)
                        if ex_dir == direction:
                            if not _can_scan_through(ex, caller):
                                next_exit = None
                                break
                            next_exit = ex
                            break

                if not next_exit or not next_exit.destination:
                    break

                dest = next_exit.destination
                visible = _get_visible_characters(dest, caller)

                if visible is None:
                    # Dark room — stop scanning in this direction
                    dir_lines.append(
                        f"  |x({_DISTANCE_LABELS[distance]}) Too dark to see.|n"
                    )
                    break

                for name in visible:
                    dir_lines.append(
                        f"  |w({_DISTANCE_LABELS[distance]})|n {name}"
                    )

                current_room = dest

            if dir_lines:
                lines.append(f"|c{dir_label}:|n")
                lines.extend(dir_lines)
                found_anything = True

        if not found_anything:
            caller.msg("You scan your surroundings but see no one nearby.")
        else:
            caller.msg("\n".join(lines))
