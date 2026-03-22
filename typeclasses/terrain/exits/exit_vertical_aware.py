from evennia import AttributeProperty
from .exit_base import ExitBase


class ExitVerticalAware(ExitBase):
    """
    Exit that enforces vertical position (flying/swimming) and
    encumbrance checks before allowing traversal.

    Supports a ``direction`` attribute that auto-generates compass
    aliases and formats the exit display as "direction: description".
    """

    # ── Direction system ────────────────────────────────────────────
    DIRECTION_ALIASES = {
        "north": ["n", "north"],
        "south": ["s", "south"],
        "east": ["e", "east"],
        "west": ["w", "west"],
        "northeast": ["ne", "northeast"],
        "northwest": ["nw", "northwest"],
        "southeast": ["se", "southeast"],
        "southwest": ["sw", "southwest"],
        "up": ["u", "up"],
        "down": ["d", "down"],
        "in": ["in"],
        "out": ["out"],
    }

    direction = AttributeProperty("default")

    def set_direction(self, direction):
        """
        Set the compass direction and auto-add direction aliases.

        Args:
            direction (str): A key from DIRECTION_ALIASES (e.g. "north").
        """
        self.direction = direction
        aliases = self.DIRECTION_ALIASES.get(direction, [])
        current = set(self.aliases.all())
        for alias in aliases:
            if alias not in current:
                self.aliases.add(alias)

    def get_display_name(self, looker=None, **kwargs):
        """
        Format the exit for room display.

        If direction is set (not "default"), returns "direction: description".
        Otherwise falls back to desc or key (backwards compatible).
        """
        desc = self.db.desc or self.key
        if self.direction in self.DIRECTION_ALIASES:
            return f"{self.direction}: {desc}"
        return desc

    # ── Traversal checks ───────────────────────────────────────────

    def at_traverse(self, traversing_object, destination, **kwargs):

        # --- Encumbrance check (before height/depth checks) ---
        if getattr(traversing_object, "is_encumbered", False):
            height = getattr(traversing_object, "room_vertical_position", 0)
            room = traversing_object.location
            max_depth = getattr(room, "max_depth", 0) if room else 0

            if height > 0:
                # Flying while over-encumbered — fall
                traversing_object.msg("|rYou are carrying too much to stay airborne!|n")
                if hasattr(traversing_object, "_check_fall"):
                    traversing_object._check_fall()
                return
            elif max_depth < 0:
                # In water (surface or below) — sink to bottom
                traversing_object.msg("|rYou are carrying too much to swim!|n")
                if height > max_depth:
                    traversing_object.room_vertical_position = max_depth
                if hasattr(traversing_object, "start_breath_timer"):
                    traversing_object.start_breath_timer()
                return
            else:
                # On dry ground — too heavy to move
                traversing_object.msg("You are carrying too much to move.")
                return

        height = getattr(traversing_object, "room_vertical_position", 0)

        # Check target room height
        max_h = getattr(destination, "max_height", 0)
        min_h = getattr(destination, "max_depth", 0)

        if height > max_h:
            if max_h == 0:
                traversing_object.msg(f"You can only go this way at ground level.")
                return  # cancels movement by not calling super()
            else:
                traversing_object.msg(f"There is no way to proceed at this height, you'll need to descend.")
                return  # cancels movement by not calling super()

        if height < min_h:
            if min_h == 0:
                traversing_object.msg(f"There is no water that way, you'll need to surface before proceeding")
                return  # cancels movement by not calling super()
            else:
                traversing_object.msg(f"There water gets shallower that way, you'll need to ascend before proceeding.")
                return  # cancels movement by not calling super()

        # Movement allowed — continue normal traversal
        super().at_traverse(traversing_object, destination, **kwargs)
