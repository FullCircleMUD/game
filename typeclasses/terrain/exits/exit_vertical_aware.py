"""
ExitVerticalAware — exit with direction system, vertical checks, and
height adapter support.

Provides:
  - Direction system (set_direction, get_display_name, DIRECTION_ALIASES)
  - Encumbrance checks (flying/swimming/ground)
  - Height/depth compatibility checks against destination room
  - Height gating (exit only visible/usable at certain heights)
  - Height adaptation (arrive at a different height than you left)
  - Fall warning messages (before dangerous height transitions)

All height features default to None — existing exits work identically.
Builders override attributes only when height transitions are needed.

See design/VERTICAL_MOVEMENT.md for full design and examples.
"""

from evennia import AttributeProperty
from evennia.objects.objects import ExitCommand

from commands.command import FCMCommandMixin
from .exit_base import ExitBase


class _HeightAwareExitCommand(FCMCommandMixin, ExitCommand):
    """
    Exit command that denies 'cmd' access when the exit's height
    requirements aren't met by the caller. This prevents height-gated
    exits from appearing in command disambiguation.
    """

    def access(self, srcobj, access_type="cmd", default=False):
        if access_type == "cmd" and self.obj:
            if hasattr(self.obj, "is_height_accessible"):
                height = getattr(srcobj, "room_vertical_position", 0)
                if not self.obj.is_height_accessible(height):
                    return False
        return super().access(srcobj, access_type=access_type, default=default)


class ExitVerticalAware(ExitBase):
    """
    Exit that enforces vertical position (flying/swimming) and
    encumbrance checks before allowing traversal.

    Supports a ``direction`` attribute that auto-generates compass
    aliases and formats the exit display as "direction: description".

    Height adapter attributes (all default None = no effect):

    ``required_min_height`` / ``required_max_height``
        Gate exit visibility and access by the character's current
        vertical position. Only characters within the range [min, max]
        can see or use this exit. Set one or both bounds.

        Examples:
            required_min_height=1          → only flying characters
            required_min_height=-3,
            required_max_height=-3         → only at depth -3
            required_min_height=0,
            required_max_height=0          → ground level only

    ``arrival_heights``
        Dict mapping the character's current height to their arrival
        height in the destination room. Heights not in the dict cannot
        use the exit (implicit gate). None = keep current height.

        Examples:
            {1: 0, 2: 1}   → height 1 lands (arrival 0),
                              height 2 stays airborne (arrival 1),
                              ground level blocked (not in dict)
            {0: 2}          → ground level → arrive at height 2
                              (e.g. jumping out a tower window)
            {0: -3}         → ground level → arrive at depth -3
                              (e.g. emerging from underwater cave)

    ``fall_warning``
        Warning message shown before traversal that would cause a fall
        (arrival height > 0 without FLY condition). The character still
        moves — the warning is informational, not a prompt. If None,
        uses a generic default.

        Example:
            "You step off the wall and plummet!"
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

    # Use height-aware exit command for command matching
    exit_command = _HeightAwareExitCommand

    # ── Height adapter attributes ───────────────────────────────────
    # All default to None = no height gating, no height adaptation.
    # Override per-exit to create height-dependent behavior.

    required_min_height = AttributeProperty(None)
    """Minimum height to see/use this exit. None = no lower bound.
    E.g. required_min_height=1 means only flying characters can
    see or use this exit."""

    required_max_height = AttributeProperty(None)
    """Maximum height to see/use this exit. None = no upper bound.
    Use with required_min_height for a range. E.g. min=-3, max=-3
    means only characters at depth -3 can see or use this exit."""

    arrival_heights = AttributeProperty(None)
    """Dict {current_height: arrival_height}. None = keep current
    height (default). Heights not in dict cannot use exit (implicit
    gate). E.g. {1: 0, 2: 1} means height 1 lands on arrival,
    height 2 stays airborne. Ground level (0) is blocked because
    it's not in the dict."""

    fall_warning = AttributeProperty(None)
    """Warning message shown before a fall. None = generic default.
    E.g. 'You step off the wall and plummet!'"""

    # ── Direction methods ───────────────────────────────────────────

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

    # ── Access control ───────────────────────────────────────────────

    def access(self, accessing_obj, access_type="read", default=False,
               no_superuser_bypass=False, **kwargs):
        """
        Override access to deny 'cmd' and 'traverse' when height is
        inaccessible.

        Denying 'cmd' access prevents the exit command from matching
        during Evennia's command parser phase, which eliminates
        disambiguation prompts when multiple exits share the same
        direction at different heights.
        """
        if access_type in ("cmd", "traverse"):
            height = getattr(accessing_obj, "room_vertical_position", 0)
            if not self.is_height_accessible(height):
                return False
        return super().access(
            accessing_obj, access_type=access_type, default=default,
            no_superuser_bypass=no_superuser_bypass, **kwargs
        )

    # ── Height accessibility ────────────────────────────────────────

    def is_height_accessible(self, height):
        """
        Check if a character at the given height can see/use this exit.

        Returns True if:
          - No height gating is configured (default), AND
          - No arrival_heights dict, OR the height has a mapping.

        Used by room display filtering (get_display_exits, CmdExits,
        CmdLook direction handler) to hide inaccessible exits.

        Args:
            height (int): The character's room_vertical_position.

        Returns:
            bool: True if the exit is accessible at this height.
        """
        # Check explicit height range gate
        if self.required_min_height is not None:
            if height < self.required_min_height:
                return False
        if self.required_max_height is not None:
            if height > self.required_max_height:
                return False

        # Check arrival_heights implicit gate
        # Note: Evennia may serialize dict keys as strings, so check both
        if self.arrival_heights is not None:
            if height not in self.arrival_heights and str(height) not in self.arrival_heights:
                return False

        return True

    # ── Traversal checks ───────────────────────────────────────────

    def at_traverse(self, traversing_object, destination, **kwargs):

        # --- Encumbrance check (before height/depth checks) ---
        if getattr(traversing_object, "is_encumbered", False):
            height = getattr(
                traversing_object, "room_vertical_position", 0
            )
            room = traversing_object.location
            max_depth = getattr(room, "max_depth", 0) if room else 0

            if height > 0:
                traversing_object.msg(
                    "|rYou are carrying too much to stay airborne!|n"
                )
                if hasattr(traversing_object, "_check_fall"):
                    traversing_object._check_fall()
                return
            elif max_depth < 0:
                traversing_object.msg(
                    "|rYou are carrying too much to swim!|n"
                )
                if height > max_depth:
                    traversing_object.room_vertical_position = max_depth
                if hasattr(traversing_object, "start_breath_timer"):
                    traversing_object.start_breath_timer()
                return
            else:
                traversing_object.msg(
                    "You are carrying too much to move."
                )
                return

        height = getattr(traversing_object, "room_vertical_position", 0)

        # --- Height gating ---
        if not self.is_height_accessible(height):
            traversing_object.msg("You can't go that way from here.")
            return

        # --- Determine arrival height ---
        # Note: Evennia may serialize dict keys as strings, so check both
        arrival_height = height  # default: keep current height
        if self.arrival_heights is not None:
            if height in self.arrival_heights:
                arrival_height = self.arrival_heights[height]
            elif str(height) in self.arrival_heights:
                arrival_height = self.arrival_heights[str(height)]

        # --- Destination height/depth compatibility ---
        # Use arrival_height for the check, not current height
        max_h = getattr(destination, "max_height", 0)
        min_h = getattr(destination, "max_depth", 0)

        if arrival_height > max_h:
            if max_h == 0:
                traversing_object.msg(
                    "You can only go this way at ground level."
                )
                return
            else:
                traversing_object.msg(
                    "There is no way to proceed at this height, "
                    "you'll need to descend."
                )
                return

        if arrival_height < min_h:
            if min_h == 0:
                traversing_object.msg(
                    "There is no water that way, you'll need to "
                    "surface before proceeding"
                )
                return
            else:
                traversing_object.msg(
                    "The water gets shallower that way, you'll "
                    "need to ascend before proceeding."
                )
                return

        # --- Fall warning ---
        # If arrival puts character in the air without FLY, warn them
        # and trigger fall damage after movement completes.
        will_fall = False
        if arrival_height > 0:
            has_fly = False
            try:
                from enums.condition import Condition
                if hasattr(traversing_object, "has_condition"):
                    has_fly = traversing_object.has_condition(Condition.FLY)
            except Exception:
                pass
            if not has_fly:
                will_fall = True
                warning = self.fall_warning or (
                    "|rYou brace yourself for the fall...|n"
                )
                traversing_object.msg(warning)

        # --- Set arrival height BEFORE movement ---
        # Must be before move_to() so the destination room's display
        # shows the correct height on arrival.
        if self.arrival_heights is not None:
            traversing_object.room_vertical_position = arrival_height

        # --- Movement ---
        super().at_traverse(traversing_object, destination, **kwargs)

        # --- Post-movement fall ---
        if will_fall and hasattr(traversing_object, "_check_fall"):
            traversing_object._check_fall()
