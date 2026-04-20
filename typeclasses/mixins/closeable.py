"""
CloseableMixin — adds open/close state to any Evennia object.

Mix into chests, doors, gates — anything that can be opened and closed.
The mixin tracks state and fires hooks; child classes define behaviour
by overriding at_open() and at_close().

Usage:
    class WorldChest(CloseableMixin, WorldFixture):
        def at_object_creation(self):
            super().at_object_creation()
            self.at_closeable_init()
"""

from evennia.typeclasses.attributes import AttributeProperty


class CloseableMixin:
    """
    Mixin that tracks open/closed state with hooks for subclass behaviour.

    Child classes MUST:
        1. Call at_closeable_init() from at_object_creation()
        2. Optionally override at_open()/at_close() for custom behaviour
    """

    # Default open — containers override to False, doors override to False
    is_open = AttributeProperty(True)

    # Auto-close delay in seconds. 0 = disabled (default for generic closeables).
    # ExitDoor overrides to 300 (5 minutes).
    auto_close_seconds = AttributeProperty(0)

    def at_closeable_init(self):
        """
        Initialize closeable state. Call from at_object_creation().
        Safe to call multiple times.
        """
        pass  # is_open default set via AttributeProperty

    def open(self, opener):
        """
        Attempt to open this object.

        Args:
            opener: The character opening this object.

        Returns:
            (bool, str): Success flag and message.
        """
        if self.is_open:
            return False, f"{self.key} is already open."

        # Hook for LockableMixin or other gates
        can, reason = self.can_open(opener)
        if not can:
            return False, reason

        self.is_open = True
        self.at_open(opener)
        self._start_auto_close_timer()
        return True, f"You open {self.key}."

    def close(self, closer):
        """
        Attempt to close this object.

        Args:
            closer: The character closing this object.

        Returns:
            (bool, str): Success flag and message.
        """
        if not self.is_open:
            return False, f"{self.key} is already closed."

        self.is_open = False
        self._cancel_auto_close_timer()
        self.at_close(closer)
        return True, f"You close {self.key}."

    def can_open(self, opener):
        """
        Check if this object can be opened. Override to add gates
        (e.g. LockableMixin blocks opening when locked).

        Returns:
            (bool, str): (True, None) if openable, (False, reason) if not.
        """
        return True, None

    def at_open(self, opener):
        """Hook called after successfully opening. Override for custom behaviour."""
        pass

    def at_close(self, closer):
        """Hook called after successfully closing. Override for custom behaviour."""
        pass

    def _start_auto_close_timer(self):
        """Start an auto-close timer script if auto_close_seconds > 0."""
        if self.auto_close_seconds and self.auto_close_seconds > 0:
            from typeclasses.scripts.auto_close_timer import AutoCloseTimerScript

            # Remove any existing auto-close timer
            self.scripts.delete("auto_close_timer")

            script = self.scripts.add(
                AutoCloseTimerScript,
                autostart=False,
            )
            script.interval = self.auto_close_seconds
            script.start()

    def _cancel_auto_close_timer(self):
        """Cancel any running auto-close timer."""
        self.scripts.delete("auto_close_timer")
