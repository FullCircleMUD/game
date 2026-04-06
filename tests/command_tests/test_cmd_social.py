"""
Tests for the socials system — data-driven social commands.

evennia test --settings settings tests.command_tests.test_cmd_social
"""

from evennia.utils.test_resources import EvenniaCommandTest

from commands.all_char_cmds.cmd_social import (
    CmdSocialBase,
    CmdSocials,
    _make_social_cmd,
    create_social_commands,
)
from commands.all_char_cmds.socials_data import SOCIALS


# Build a test social command for reuse
_TEST_DATA = {
    "no_target_self": "You bow gracefully.",
    "no_target_room": "$You() $conj(bow) gracefully.",
    "target_self": "You bow before {target}.",
    "target_room": "$You() $conj(bow) before {target}.",
    "target_victim": "{actor} bows before you.",
    "self_self": "You bow to yourself... how odd.",
    "self_room": "$You() $conj(bow) to $pron(yourself)... how odd.",
}
CmdTestBow = _make_social_cmd("bow", _TEST_DATA)


class TestSocialNoTarget(EvenniaCommandTest):
    """Test social with no target argument."""

    character_typeclass = "typeclasses.actors.character.FCMCharacter"
    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def test_no_target_shows_self_msg(self):
        """No args: caller sees first-person message."""
        result = self.call(CmdTestBow(), "", caller=self.char1)
        self.assertIn("You bow gracefully", result)

    def test_no_target_room_msg(self):
        """No args: room receives third-person message."""
        result = self.call(CmdTestBow(), "", caller=self.char1)
        # EvenniaCommandTest.call() returns all messages including room
        self.assertIn("bow", result.lower())


class TestSocialTargeted(EvenniaCommandTest):
    """Test social with a target."""

    character_typeclass = "typeclasses.actors.character.FCMCharacter"
    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def test_target_self_msg(self):
        """With target: caller sees targeted first-person message."""
        result = self.call(CmdTestBow(), "Char2", caller=self.char1)
        self.assertIn("You bow before", result)

    def test_target_victim_msg(self):
        """With target: target receives victim message."""
        result = self.call(CmdTestBow(), "Char2", caller=self.char1)
        # EvenniaCommandTest merges all messages
        self.assertIn("bow", result.lower())

    def test_self_target(self):
        """Targeting self shows self-target message."""
        result = self.call(CmdTestBow(), "Char", caller=self.char1)
        self.assertIn("how odd", result.lower())


class TestSocialGuards(EvenniaCommandTest):
    """Test condition and position guards."""

    character_typeclass = "typeclasses.actors.character.FCMCharacter"
    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def test_sleeping_blocked(self):
        """Sleeping characters can't use socials."""
        self.char1.position = "sleeping"
        result = self.call(CmdTestBow(), "", caller=self.char1)
        self.assertIn("dreams", result.lower())

    def test_hidden_blocked(self):
        """Hidden characters can't use socials."""
        from enums.condition import Condition

        # Directly set condition ref count to avoid messaging
        conds = dict(self.char1.conditions)
        conds[Condition.HIDDEN.value] = 1
        self.char1.conditions = conds
        result = self.call(CmdTestBow(), "", caller=self.char1)
        self.assertIn("hidden", result.lower())
        conds[Condition.HIDDEN.value] = 0
        self.char1.conditions = conds


class TestSocialsList(EvenniaCommandTest):
    """Test the socials list command."""

    character_typeclass = "typeclasses.actors.character.FCMCharacter"
    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def test_socials_lists_commands(self):
        """The socials command shows available socials."""
        result = self.call(CmdSocials(), "", caller=self.char1)
        self.assertIn("bow", result)
        self.assertIn("wave", result)
        self.assertIn("laugh", result)

    def test_socials_shows_count(self):
        """The socials command shows the total count."""
        result = self.call(CmdSocials(), "", caller=self.char1)
        self.assertIn(str(len(SOCIALS)), result)


class TestSocialsData(EvenniaCommandTest):
    """Test the socials data integrity and factory."""

    character_typeclass = "typeclasses.actors.character.FCMCharacter"
    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def test_all_socials_have_required_keys(self):
        """Every social must have at least no_target_self and no_target_room."""
        for name, data in SOCIALS.items():
            self.assertIn(
                "no_target_self",
                data,
                f"Social '{name}' missing 'no_target_self'",
            )
            self.assertIn(
                "no_target_room",
                data,
                f"Social '{name}' missing 'no_target_room'",
            )

    def test_factory_creates_commands(self):
        """create_social_commands() returns one class per social."""
        commands = create_social_commands()
        self.assertEqual(len(commands), len(SOCIALS))

    def test_factory_commands_have_correct_keys(self):
        """Each generated command has the correct key."""
        commands = create_social_commands()
        keys = {cmd.key for cmd in commands}
        for name in SOCIALS:
            self.assertIn(name, keys, f"Missing command for social '{name}'")

    def test_factory_commands_are_command_subclasses(self):
        """Generated commands inherit from CmdSocialBase."""
        commands = create_social_commands()
        for cmd in commands:
            self.assertTrue(
                issubclass(cmd, CmdSocialBase),
                f"{cmd.__name__} is not a CmdSocialBase subclass",
            )


class TestSocialNoRoomMsg(EvenniaCommandTest):
    """Test socials that have no room message for no-target variant."""

    character_typeclass = "typeclasses.actors.character.FCMCharacter"
    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def test_comfort_no_target(self):
        """Comfort with no target shows instruction message."""
        # Comfort has no_target_room=None — should still show self msg
        CmdComfort = _make_social_cmd("comfort", SOCIALS["comfort"])
        result = self.call(CmdComfort(), "", caller=self.char1)
        self.assertIn("comfort someone", result.lower())
