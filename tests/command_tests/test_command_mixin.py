"""
Tests for FCMCommandMixin's posture gate.

``required_position`` names the pose or poses a command will accept, and
``position_error_msg`` replaces the generated refusal. Both are checked in
at_pre_cmd, so a wrongly-posed character never reaches func().

evennia test --settings settings tests.command_tests.test_command_mixin
"""

from evennia import Command
from evennia.utils.test_resources import EvenniaCommandTest

from commands.command import FCMCommandMixin


class _CmdAnyPose(FCMCommandMixin, Command):
    """A command with no posture requirement — the ordinary case."""

    key = "anypose"
    locks = "cmd:all()"

    def func(self):
        self.caller.msg("done")


class _CmdSitOnly(FCMCommandMixin, Command):
    """A command that demands one pose."""

    key = "sitonly"
    locks = "cmd:all()"
    required_position = "sitting"

    def func(self):
        self.caller.msg("done")


class _CmdSitOrRest(FCMCommandMixin, Command):
    """A command that accepts several poses."""

    key = "sitorrest"
    locks = "cmd:all()"
    required_position = ("sitting", "resting")

    def func(self):
        self.caller.msg("done")


class _CmdCustomRefusal(FCMCommandMixin, Command):
    """A command that words its own refusal."""

    key = "customrefusal"
    locks = "cmd:all()"
    required_position = "sitting"
    position_error_msg = "Pull up a chair first."

    def func(self):
        self.caller.msg("done")


class TestPositionGate(EvenniaCommandTest):
    """Test the required_position gate."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def test_no_requirement_runs_in_any_pose(self):
        """A command without required_position is never posture-gated."""
        for position in ("standing", "sitting", "resting", "fighting"):
            self.char1.position = position
            self.call(_CmdAnyPose(), "", "done")

    def test_right_pose_runs(self):
        """The named pose passes the gate."""
        self.char1.position = "sitting"
        self.call(_CmdSitOnly(), "", "done")

    def test_wrong_pose_refused(self):
        """Any other pose is refused before func() runs."""
        for position in ("standing", "resting", "fighting"):
            self.char1.position = position
            result = self.call(_CmdSitOnly(), "")
            self.assertIn("You must be", result)
            self.assertNotIn("done", result)

    def test_several_poses_accepted(self):
        """A tuple accepts any pose it names and refuses the rest."""
        for position in ("sitting", "resting"):
            self.char1.position = position
            self.call(_CmdSitOrRest(), "", "done")
        self.char1.position = "standing"
        result = self.call(_CmdSitOrRest(), "")
        self.assertIn("sitting", result)
        self.assertIn("resting", result)

    def test_custom_refusal_replaces_the_default(self):
        """position_error_msg is used verbatim in place of the generated line."""
        self.char1.position = "standing"
        self.call(_CmdCustomRefusal(), "", "Pull up a chair first.")

    def test_sleeping_gate_answers_first(self):
        """A sleeping character gets the sleep message, not the posture one."""
        self.char1.position = "sleeping"
        result = self.call(_CmdSitOnly(), "")
        self.assertIn("In your dreams", result)
