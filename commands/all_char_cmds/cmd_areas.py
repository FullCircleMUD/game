"""
CmdAreas — list game areas with level ranges and locations.

Usage:
    areas
    zones
"""

from evennia import Command

from commands.command import FCMCommandMixin


class CmdAreas(FCMCommandMixin, Command):
    """
    List game areas with level ranges and locations.

    Usage:
        areas

    Shows all known areas grouped by zone, with suggested
    level ranges and how to reach them.
    """

    key = "areas"
    aliases = ("zones",)
    locks = "cmd:all()"
    arg_regex = r"\s|$"
    help_category = "Exploration"
    allow_while_sleeping = True

    # Column widths
    _COL_DISTRICT = 22
    _COL_LEVEL = 7
    _COL_LOCATION = 26
    _COL_NOTES = 16

    def func(self):
        from world.game_world.area_registry import AREA_REGISTRY

        w = (self._COL_DISTRICT + self._COL_LEVEL
             + self._COL_LOCATION + self._COL_NOTES + 7)

        lines = []
        lines.append(f"+{'-' * (w - 2)}+")
        lines.append(
            f"| {'Area':<{self._COL_DISTRICT}}"
            f" {'Level':<{self._COL_LEVEL}}"
            f" {'Location':<{self._COL_LOCATION}}"
            f" {'Notes':<{self._COL_NOTES}}"
            f"|"
        )
        lines.append(f"+{'-' * (w - 2)}+")

        current_zone = None
        for entry in AREA_REGISTRY:
            zone = entry["zone"]
            if zone != current_zone:
                current_zone = zone
                lines.append(
                    f"| |w{zone:<{w - 4}}|n |"
                )

            district = entry["district"]
            levels = entry.get("levels", "?")
            location = entry.get("location", "")
            notes = entry.get("notes", "")

            # Truncate if needed
            if len(district) > self._COL_DISTRICT:
                district = district[:self._COL_DISTRICT - 1] + "~"
            if len(location) > self._COL_LOCATION:
                location = location[:self._COL_LOCATION - 1] + "~"
            if len(notes) > self._COL_NOTES:
                notes = notes[:self._COL_NOTES - 1] + "~"

            lines.append(
                f"|   {district:<{self._COL_DISTRICT - 2}}"
                f" {levels:<{self._COL_LEVEL}}"
                f" {location:<{self._COL_LOCATION}}"
                f" {notes:<{self._COL_NOTES}}"
                f"|"
            )

        lines.append(f"+{'-' * (w - 2)}+")
        self.caller.msg("\n".join(lines))
