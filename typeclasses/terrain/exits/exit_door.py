"""
ExitDoor — an exit that can be opened, closed, and locked.

Closed doors block passage. Locked doors block both passage and opening.
Supports key items and lockpicking via LockableMixin.

Features:
    - ``door_name`` alias (default "door") — so ``open door`` works.
      Override to "gate", "portcullis", etc.
    - State-dependent descriptions — ``closed_desc`` / ``open_desc``
      shown in the room exit list depending on door state.
    - Reciprocal pairing — ``link_door_pair(a, b)`` syncs open/close/
      lock/unlock between two sides. Disable with ``sync_state=False``.

Inherits from ExitVerticalAware so all height/depth/encumbrance
checks still apply.

Usage (build script / prototype):
    door = create_object(ExitDoor, key="a heavy oak door",
                         location=room_a, destination=room_b)
    door.set_direction("south")
    door.closed_desc = "A stout oak door blocks your way."
    door.open_desc = "Through an open oak door you see a busy inn."
"""

from evennia import AttributeProperty

from typeclasses.mixins.closeable import CloseableMixin
from typeclasses.mixins.hidden_object import HiddenObjectMixin
from typeclasses.mixins.invisible_object import InvisibleObjectMixin
from typeclasses.mixins.lockable import LockableMixin
from typeclasses.mixins.smashable import SmashableMixin
from typeclasses.terrain.exits.exit_vertical_aware import ExitVerticalAware


class ExitDoor(
    SmashableMixin,
    LockableMixin,
    CloseableMixin,
    InvisibleObjectMixin,
    HiddenObjectMixin,
    ExitVerticalAware,
):
    """
    An exit with a door that can be opened, closed, and locked.

    Doors start closed (override CloseableMixin default).
    Passage is blocked when closed or locked.
    """

    # Doors start closed
    is_open = AttributeProperty(False)

    # Doors auto-close after 5 minutes by default
    auto_close_seconds = AttributeProperty(300)

    # Findable name — players can type "open door" (or "open gate", etc.)
    door_name = AttributeProperty("door")

    # State-dependent descriptions for room exit display
    closed_desc = AttributeProperty(None)
    open_desc = AttributeProperty(None)

    def return_appearance(self, looker, **kwargs):
        """Show door state + destination name when closed, full preview when open."""
        if not self.is_open:
            dest = self.destination
            dest_name = dest.get_display_name(looker) if dest else "somewhere"
            return f"{self.key} is closed. It leads to |c{dest_name}|n."
        return super().return_appearance(looker, **kwargs)

    # Reciprocal door on the other side (set via link_door_pair)
    other_side = AttributeProperty(None)

    # Sync open/close/lock/unlock to other_side (default True)
    sync_state = AttributeProperty(True)

    def at_object_creation(self):
        super().at_object_creation()
        self.at_smashable_init()
        self.at_closeable_init()
        self.at_lockable_init()
        self.at_hidden_init()
        self.at_invisible_init()
        # Add door_name as alias so "open door" works
        if self.door_name and self.door_name not in self.aliases.all():
            self.aliases.add(self.door_name)

    # ------------------------------------------------------------------ #
    #  Reciprocal pairing
    # ------------------------------------------------------------------ #

    @staticmethod
    def link_door_pair(door_a, door_b):
        """Link two doors as a reciprocal pair."""
        door_a.other_side = door_b
        door_b.other_side = door_a

    # ------------------------------------------------------------------ #
    #  Reciprocal hooks (open/close/lock/unlock)
    # ------------------------------------------------------------------ #

    def at_open(self, opener):
        """Open the other side too (with recursion guard)."""
        other = self.other_side
        if other and self.sync_state and not other.is_open:
            other.is_open = True
            if other.location:
                other.location.msg_contents(
                    "{door} opens from the other side.",
                    from_obj=other,
                    mapping={"door": other},
                )

    def at_close(self, closer):
        """Close the other side too (with recursion guard)."""
        other = self.other_side
        if other and self.sync_state and other.is_open:
            other.is_open = False
            if other.location:
                other.location.msg_contents(
                    "{door} closes from the other side.",
                    from_obj=other,
                    mapping={"door": other},
                )

    def at_unlock(self, character):
        """Unlock the other side too."""
        other = self.other_side
        if other and self.sync_state and other.is_locked:
            other.is_locked = False

    def at_lock(self, character):
        """Lock the other side too."""
        other = self.other_side
        if other and self.sync_state and not other.is_locked:
            other.is_locked = True

    # ------------------------------------------------------------------ #
    #  Visibility
    # ------------------------------------------------------------------ #

    def is_visible_to(self, character):
        """Combined hidden + invisible check for room display filtering."""
        if not self.is_hidden_visible_to(character):
            return False
        if not self.is_invis_visible_to(character):
            return False
        return True

    # ------------------------------------------------------------------ #
    #  Traverse gating
    # ------------------------------------------------------------------ #

    def at_traverse(self, traversing_object, destination, **kwargs):
        """Block passage when invisible/hidden, closed, or locked."""
        # Invisible or hidden doors can't be traversed if the character
        # can't see them. Use a generic message to avoid revealing the exit.
        if not self.is_visible_to(traversing_object):
            traversing_object.msg("You can't go that way.")
            return

        if self.is_locked:
            traversing_object.msg(
                f"{self.key} is locked."
            )
            return

        if not self.is_open:
            traversing_object.msg(
                f"{self.key} is closed."
            )
            return

        # Movement messages are not emitted here. at_traverse/at_post_traverse
        # fire regardless of move_to(quiet=...), so a message sent from them
        # cannot be silenced by a caller and would duplicate the announce pair.
        # The door announces only itself — opening, closing, locking.
        # See docs/movement-messages.md.

        # Door is open — continue with height/depth/encumbrance checks
        super().at_traverse(traversing_object, destination, **kwargs)

    # ------------------------------------------------------------------ #
    #  Display
    # ------------------------------------------------------------------ #

    def get_display_name(self, looker=None, **kwargs):
        """
        Show door state in the exit list, with state-dependent descriptions.

        If closed_desc/open_desc is set, prepends the direction prefix and
        uses those. Otherwise falls back to direction-formatted name from
        the parent with a "(closed)"/"(locked)" suffix.
        """
        # Direction prefix for state descriptions (parent handles its own)
        dir_prefix = ""
        if self.direction in self.DIRECTION_ALIASES:
            dir_prefix = f"{self.direction}: "

        if self.is_locked:
            if self.closed_desc:
                return f"{dir_prefix}{self.closed_desc} (locked)"
            return f"{super().get_display_name(looker, **kwargs)} (locked)"
        elif not self.is_open:
            if self.closed_desc:
                return f"{dir_prefix}{self.closed_desc}"
            return f"{super().get_display_name(looker, **kwargs)} (closed)"
        else:
            if self.open_desc:
                return f"{dir_prefix}{self.open_desc}"
            return super().get_display_name(looker, **kwargs)
