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

    def test_hidden_social_proceeds_and_breaks_hiding(self):
        """Hiding doesn't block a social — performing one gives you away."""
        from enums.condition import Condition

        self.char1.add_condition(Condition.HIDDEN)
        result = self.call(CmdTestBow(), "", caller=self.char1)
        self.assertIn("You bow gracefully", result)
        self.assertFalse(self.char1.has_condition(Condition.HIDDEN))

    def test_unresolvable_target_keeps_hiding(self):
        """A social that never happens must not cost you your concealment."""
        from enums.condition import Condition

        self.char1.add_condition(Condition.HIDDEN)
        self.call(CmdTestBow(), "nosuchperson", caller=self.char1)
        self.assertTrue(self.char1.has_condition(Condition.HIDDEN))

    def test_invisibility_survives_a_social(self):
        """Magical concealment doesn't depend on staying out of sight."""
        from enums.condition import Condition

        self.char1.add_condition(Condition.INVISIBLE)
        self.call(CmdTestBow(), "", caller=self.char1)
        self.assertTrue(self.char1.has_condition(Condition.INVISIBLE))


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


class TestSocialTargetVisibility(EvenniaCommandTest):
    """Socials can only target what the caller can perceive."""

    character_typeclass = "typeclasses.actors.character.FCMCharacter"
    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def test_cannot_target_invisible_character(self):
        from enums.condition import Condition
        self.char2.add_condition(Condition.INVISIBLE)
        result = self.call(CmdTestBow(), "Char2", caller=self.char1)
        self.assertNotIn("bow before", result.lower())

    def test_can_target_invisible_with_detect_invis(self):
        from enums.condition import Condition
        self.char2.add_condition(Condition.INVISIBLE)
        self.char1.add_condition(Condition.DETECT_INVIS)
        result = self.call(CmdTestBow(), "Char2", caller=self.char1)
        self.assertIn("bow before", result.lower())

    def test_cannot_target_hidden_character(self):
        from enums.condition import Condition
        self.char2.add_condition(Condition.HIDDEN)
        result = self.call(CmdTestBow(), "Char2", caller=self.char1)
        self.assertNotIn("bow before", result.lower())

    def test_can_target_hidden_with_true_sight(self):
        from enums.condition import Condition
        self.char2.add_condition(Condition.HIDDEN)
        self.char1.apply_true_sight(duration_seconds=300)
        result = self.call(CmdTestBow(), "Char2", caller=self.char1)
        self.assertIn("bow before", result.lower())

    def test_invisible_caller_can_still_target_self(self):
        """Concealment must not stop you socialling at yourself."""
        from enums.condition import Condition
        self.char1.add_condition(Condition.INVISIBLE)
        result = self.call(CmdTestBow(), self.char1.key, caller=self.char1)
        self.assertIn("yourself", result.lower())


class TestSocialSilentModality(EvenniaCommandTest):
    """Silent socials vanish for observers who can't see the actor.

    Non-silent ones still reach them, anonymised to "Someone" by
    get_display_name rather than by any authored alternate string.
    """

    character_typeclass = "typeclasses.actors.character.FCMCharacter"
    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        from evennia.utils import create
        from enums.condition import Condition
        self.char3 = create.create_object(
            "typeclasses.actors.character.FCMCharacter",
            key="Char3", location=self.room1, home=self.room1, nohome=False,
        )
        self.room1.always_lit = True
        # Actor is invisible to everyone; char2 and char3 lack DETECT_INVIS.
        self.char1.add_condition(Condition.INVISIBLE)

    def _observer_text(self, cmd, args=""):
        """Run the social and return what the uninvolved observer saw."""
        from unittest.mock import patch
        with patch.object(self.char3, "msg") as mock_msg:
            self.call(cmd, args, caller=self.char1)
            if not mock_msg.call_args:
                return None
            first = mock_msg.call_args[0]
            text = first[0] if first else mock_msg.call_args[1].get("text")
            return text[0] if isinstance(text, (tuple, list)) else text

    # ── Silent (default) ────────────────────────────────────────

    def test_silent_social_hidden_from_observer(self):
        """A bow from an unseen actor reaches nobody."""
        self.assertIsNone(self._observer_text(CmdTestBow()))

    def test_silent_social_target_told_nothing(self):
        from unittest.mock import patch
        with patch.object(self.char2, "msg") as mock_msg:
            self.call(CmdTestBow(), "Char2", caller=self.char1)
            mock_msg.assert_not_called()

    # ── Non-silent ──────────────────────────────────────────────

    def test_non_silent_social_reaches_observer_anonymised(self):
        """A laugh carries, but the actor isn't named."""
        CmdLaugh = _make_social_cmd("laugh", SOCIALS["laugh"])
        text = self._observer_text(CmdLaugh())
        self.assertIsNotNone(text)
        self.assertIn("Someone", text)
        self.assertNotIn(self.char1.key, text)

    def test_non_silent_social_target_told_anonymously(self):
        from unittest.mock import patch
        CmdLaugh = _make_social_cmd("laugh", SOCIALS["laugh"])
        with patch.object(self.char2, "msg") as mock_msg:
            self.call(CmdLaugh(), "Char2", caller=self.char1)
            mock_msg.assert_called()
            sent = " ".join(str(c) for c in mock_msg.call_args[0])
            self.assertIn("Someone", sent)
            self.assertNotIn(self.char1.key, sent)

    def test_seeing_observer_still_gets_the_name(self):
        """DETECT_INVIS means normal attribution, not the anonymised line."""
        from enums.condition import Condition
        self.char3.add_condition(Condition.DETECT_INVIS)
        CmdLaugh = _make_social_cmd("laugh", SOCIALS["laugh"])
        text = self._observer_text(CmdLaugh())
        self.assertIsNotNone(text)
        self.assertIn(self.char1.key, text)


class TestSocialSilentFlagData(EvenniaCommandTest):
    """The silent flag flows from SOCIALS data to the generated command."""

    def create_script(self):
        pass

    def test_default_is_silent(self):
        self.assertTrue(_make_social_cmd("bow", SOCIALS["bow"]).silent)

    def test_declared_non_silent(self):
        self.assertFalse(_make_social_cmd("laugh", SOCIALS["laugh"]).silent)


class TestSocialTargetNameNotLeaked(EvenniaCommandTest):
    """A concealed target isn't named to the room by someone who can see them."""

    character_typeclass = "typeclasses.actors.character.FCMCharacter"
    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        from evennia.utils import create
        from enums.condition import Condition
        self.char3 = create.create_object(
            "typeclasses.actors.character.FCMCharacter",
            key="Char3", location=self.room1, home=self.room1, nohome=False,
        )
        self.room1.always_lit = True
        # char2 is concealed; char1 can see them, char3 cannot.
        self.char2.add_condition(Condition.INVISIBLE)
        self.char1.add_condition(Condition.DETECT_INVIS)

    def _observer_text(self):
        from unittest.mock import patch
        with patch.object(self.char3, "msg") as mock_msg:
            self.call(CmdTestBow(), "Char2", caller=self.char1)
            if not mock_msg.call_args:
                return None
            args = mock_msg.call_args[0]
            text = args[0] if args else mock_msg.call_args[1].get("text")
            return text[0] if isinstance(text, (tuple, list)) else text

    def test_concealed_target_not_named_to_room(self):
        text = self._observer_text()
        self.assertIsNotNone(text)
        self.assertNotIn(self.char2.key, text)
        self.assertIn("Someone", text)

    def test_visible_target_still_named(self):
        from enums.condition import Condition
        self.char3.add_condition(Condition.DETECT_INVIS)
        text = self._observer_text()
        self.assertIsNotNone(text)
        self.assertIn(self.char2.key, text)
