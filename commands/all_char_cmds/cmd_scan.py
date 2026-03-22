from evennia import Command

from enums.condition import Condition


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


def _can_see_hidden(entity):
    """Check if entity can see HIDDEN actors."""
    if not hasattr(entity, "has_effect"):
        return False
    if entity.has_effect("true_sight"):
        return True
    if (
        entity.has_effect("holy_sight")
        and (getattr(entity.db, "holy_sight_tier", 0) or 0) >= 4
    ):
        return True
    return False


def _get_visible_characters(room, looker):
    """Return list of visible character names in *room* for *looker*.

    Filters out the looker, hidden, and invisible characters.
    Returns empty list if room is dark for the looker.
    """
    if hasattr(room, "is_dark") and room.is_dark(looker):
        return None  # dark — can't see

    characters = room.contents_get(content_type="character")
    looker_has_detect = (
        hasattr(looker, "has_condition")
        and looker.has_condition(Condition.DETECT_INVIS)
    )
    see_hidden = _can_see_hidden(looker)

    names = []
    for char in characters:
        if char == looker:
            continue
        if hasattr(char, "has_condition"):
            if char.has_condition(Condition.HIDDEN) and not see_hidden:
                continue
            if char.has_condition(Condition.INVISIBLE) and not looker_has_detect:
                continue
        names.append(char.get_display_name(looker))
    return names


class CmdScan(Command):
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

            # Don't scan through closed doors
            if hasattr(exit_obj, "is_open") and not exit_obj.is_open:
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
                            # Don't scan through closed doors
                            if hasattr(ex, "is_open") and not ex.is_open:
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
