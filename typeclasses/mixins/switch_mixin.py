"""
SwitchMixin — generic toggle mechanism for world fixtures.

Provides on/off state, configurable verbs and messaging, and
at_activate/at_deactivate hooks for subclasses to define the
effect. The mixin is the mechanism; the effect is always custom.

Usage:
    class TrapLever(SwitchMixin, WorldFixture):
        switch_verb = AttributeProperty("pull")
        switch_name = AttributeProperty("lever")

        def at_activate(self, caller):
            # disarm the trap in this room
            for obj in self.location.contents:
                if hasattr(obj, "trap_armed"):
                    obj.trap_armed = False
"""

from evennia.typeclasses.attributes import AttributeProperty


class SwitchMixin:
    """A toggleable switch — pull, push, turn, flip."""

    is_activated = AttributeProperty(False)
    switch_verb = AttributeProperty("pull")
    switch_name = AttributeProperty("switch")
    can_deactivate = AttributeProperty(True)

    # ── Messaging (supports {verb} and {name} placeholders) ──
    activate_msg = AttributeProperty(
        "You {verb} the {name}."
    )
    deactivate_msg = AttributeProperty(
        "You {verb} the {name} back."
    )
    already_active_msg = AttributeProperty(
        "The {name} is already activated."
    )
    already_inactive_msg = AttributeProperty(
        "The {name} is already in its resting position."
    )

    def activate(self, caller):
        """Activate the switch. Returns True on success."""
        if self.is_activated:
            caller.msg(
                self.already_active_msg.format(
                    name=self.switch_name,
                )
            )
            return False
        self.is_activated = True
        caller.msg(
            self.activate_msg.format(
                verb=self.switch_verb, name=self.switch_name,
            )
        )
        if caller.location:
            caller.location.msg_contents(
                f"{caller.key} {self.switch_verb}s the "
                f"{self.switch_name}.",
                exclude=[caller],
                from_obj=caller,
            )
        self.at_activate(caller)
        return True

    def deactivate(self, caller):
        """Deactivate the switch. Returns True on success."""
        if not self.is_activated:
            caller.msg(
                self.already_inactive_msg.format(
                    name=self.switch_name,
                )
            )
            return False
        if not self.can_deactivate:
            caller.msg("It won't budge.")
            return False
        self.is_activated = False
        caller.msg(
            self.deactivate_msg.format(
                verb=self.switch_verb, name=self.switch_name,
            )
        )
        if caller.location:
            caller.location.msg_contents(
                f"{caller.key} {self.switch_verb}s the "
                f"{self.switch_name} back.",
                exclude=[caller],
                from_obj=caller,
            )
        self.at_deactivate(caller)
        return True

    # ── Override these in subclasses ──

    def at_activate(self, caller):
        """Called after activation. Override to define the effect."""
        pass

    def at_deactivate(self, caller):
        """Called after deactivation. Override to define the reverse."""
        pass
