"""
Tests for the hide command and HIDDEN movement mechanics.

Tests stealth checks, combat blocking, unskilled penalty,
and stealth-on-room-entry behaviour.
"""

from unittest.mock import patch

from evennia.utils.test_resources import EvenniaCommandTest

from commands.all_char_cmds.cmd_hide import CmdHide
from enums.condition import Condition
from enums.mastery_level import MasteryLevel
from enums.skills_enum import skills

_ROOM = "typeclasses.terrain.rooms.room_base.RoomBase"
_CHAR = "typeclasses.actors.character.FCMCharacter"


def _set_stealth(char, mastery=MasteryLevel.BASIC):
    """Give a character the stealth skill at a given mastery level."""
    if not char.db.class_skill_mastery_levels:
        char.db.class_skill_mastery_levels = {}
    char.db.class_skill_mastery_levels[skills.STEALTH.value] = {"mastery": mastery.value, "classes": ["Thief"]}


def _set_alertness(char, mastery=MasteryLevel.BASIC):
    """Give a character the alertness skill at a given mastery level."""
    if not char.db.general_skill_mastery_levels:
        char.db.general_skill_mastery_levels = {}
    char.db.general_skill_mastery_levels[skills.ALERTNESS.value] = mastery.value


class TestCmdHideBasic(EvenniaCommandTest):
    """Tests for basic hide command flow."""
    room_typeclass = _ROOM
    character_typeclass = _CHAR

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        _set_stealth(self.char1, MasteryLevel.BASIC)

    def test_hide_empty_room_succeeds(self):
        """Hiding with no perceivers should auto-succeed."""
        # Move char2 out so room is empty except char1
        self.char2.location = None
        self.call(CmdHide(), "")
        self.assertTrue(self.char1.has_condition(Condition.HIDDEN))

    def test_hide_already_hidden(self):
        """Hiding when already hidden should show message."""
        self.char1.add_condition(Condition.HIDDEN)
        self.call(CmdHide(), "", "You are already hidden.")

    @patch("utils.dice_roller.DiceRoller.roll_with_advantage_or_disadvantage")
    def test_hide_unskilled_can_attempt(self, mock_roll):
        """UNSKILLED characters can attempt to hide (with penalty)."""
        _set_stealth(self.char1, MasteryLevel.UNSKILLED)
        self.char2.location = None  # empty room = auto-succeed
        mock_roll.return_value = 10
        self.call(CmdHide(), "")
        self.assertTrue(self.char1.has_condition(Condition.HIDDEN))

    @patch("utils.dice_roller.DiceRoller.roll_with_advantage_or_disadvantage")
    def test_hide_no_mastery_dict_can_attempt(self, mock_roll):
        """Character with no mastery data can still attempt hide (returns unskilled)."""
        self.char1.db.class_skill_mastery_levels = None
        self.char2.location = None  # empty room = auto-succeed
        mock_roll.return_value = 10
        self.call(CmdHide(), "")
        self.assertTrue(self.char1.has_condition(Condition.HIDDEN))

    def test_hide_in_combat_blocked(self):
        """Cannot hide while in combat."""
        from combat.combat_handler import CombatHandler
        self.char1.scripts.add(CombatHandler, autostart=False)
        self.call(CmdHide(), "", "You can't hide while in combat!")


class TestCmdHideContested(EvenniaCommandTest):
    """Tests for contested stealth checks."""
    room_typeclass = _ROOM
    character_typeclass = _CHAR

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        _set_stealth(self.char1, MasteryLevel.BASIC)

    @patch("utils.dice_roller.DiceRoller.roll_with_advantage_or_disadvantage")
    def test_hide_succeeds_high_roll(self, mock_roll):
        """High stealth roll should succeed against perceiver."""
        mock_roll.return_value = 20
        self.call(CmdHide(), "")
        self.assertTrue(self.char1.has_condition(Condition.HIDDEN))

    @patch("utils.dice_roller.DiceRoller.roll_with_advantage_or_disadvantage")
    def test_hide_fails_low_roll(self, mock_roll):
        """Low stealth roll should fail against perceiver."""
        mock_roll.return_value = 1
        _set_alertness(self.char2, MasteryLevel.GRANDMASTER)
        self.char2.wisdom = 18  # high WIS for strong perception
        self.call(CmdHide(), "", "You look for a place to hide")
        self.assertFalse(self.char1.has_condition(Condition.HIDDEN))

    @patch("utils.dice_roller.DiceRoller.roll_with_advantage_or_disadvantage")
    def test_hide_success_shows_roll(self, mock_roll):
        """Successful hide should show stealth roll details."""
        mock_roll.return_value = 15
        # char2 has default stats — low passive perception
        self.call(CmdHide(), "")
        self.assertTrue(self.char1.has_condition(Condition.HIDDEN))

    @patch("utils.dice_roller.DiceRoller.roll_with_advantage_or_disadvantage")
    def test_mastery_scaling_helps(self, mock_roll):
        """Higher mastery should make hiding easier."""
        _set_alertness(self.char2, MasteryLevel.SKILLED)
        self.char2.wisdom = 14
        mock_roll.return_value = 5  # mediocre roll

        # BASIC mastery — might fail
        _set_stealth(self.char1, MasteryLevel.BASIC)
        basic_bonus = self.char1.effective_stealth_bonus

        # GRANDMASTER mastery — much higher bonus
        _set_stealth(self.char1, MasteryLevel.GRANDMASTER)
        gm_bonus = self.char1.effective_stealth_bonus

        self.assertGreater(gm_bonus, basic_bonus)


class TestHiddenMovement(EvenniaCommandTest):
    """Tests for stealth checks on room entry while HIDDEN."""
    room_typeclass = _ROOM
    character_typeclass = _CHAR

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        _set_stealth(self.char1, MasteryLevel.BASIC)

    @patch("utils.dice_roller.DiceRoller.roll_with_advantage_or_disadvantage")
    def test_move_hidden_empty_room_stays_hidden(self, mock_roll):
        """Moving HIDDEN into an empty room should auto-succeed."""
        # Create a second room with no occupants
        from evennia.utils.create import create_object
        room2 = create_object(_ROOM, key="Room2")

        self.char1.add_condition(Condition.HIDDEN)
        self.char1.move_to(room2)
        self.assertTrue(self.char1.has_condition(Condition.HIDDEN))

    @patch("utils.dice_roller.DiceRoller.roll_with_advantage_or_disadvantage")
    def test_move_hidden_spotted(self, mock_roll):
        """Moving HIDDEN into a room with a perceiver and rolling low should reveal."""
        mock_roll.return_value = 1
        from evennia.utils.create import create_object
        room2 = create_object(_ROOM, key="Room2")

        # Place a high-perception character in room2
        perceiver = create_object(_CHAR, key="Guard", location=room2)
        _set_alertness(perceiver, MasteryLevel.GRANDMASTER)
        perceiver.wisdom = 18

        self.char1.add_condition(Condition.HIDDEN)
        self.char1.move_to(room2)
        self.assertFalse(self.char1.has_condition(Condition.HIDDEN))

    @patch("utils.dice_roller.DiceRoller.roll_with_advantage_or_disadvantage")
    def test_move_hidden_undetected(self, mock_roll):
        """Moving HIDDEN with a high roll should stay hidden."""
        mock_roll.return_value = 20
        from evennia.utils.create import create_object
        room2 = create_object(_ROOM, key="Room2")

        perceiver = create_object(_CHAR, key="Guard", location=room2)
        _set_alertness(perceiver, MasteryLevel.BASIC)

        self.char1.add_condition(Condition.HIDDEN)
        self.char1.move_to(room2)
        self.assertTrue(self.char1.has_condition(Condition.HIDDEN))

    def test_move_not_hidden_no_check(self):
        """Moving without HIDDEN should not trigger stealth check."""
        from evennia.utils.create import create_object
        room2 = create_object(_ROOM, key="Room2")

        self.char1.move_to(room2)
        self.assertFalse(self.char1.has_condition(Condition.HIDDEN))


class TestSearchFindsHidden(EvenniaCommandTest):
    """Tests for the search command finding hidden characters."""
    room_typeclass = _ROOM
    character_typeclass = _CHAR

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.room1.always_lit = True
        _set_alertness(self.char1, MasteryLevel.BASIC)
        _set_stealth(self.char2, MasteryLevel.BASIC)
        self.char2.add_condition(Condition.HIDDEN)

    @patch("utils.dice_roller.DiceRoller.roll_with_advantage_or_disadvantage")
    def test_search_finds_hidden_character(self, mock_roll):
        """Search with high roll should reveal hidden character."""
        from commands.all_char_cmds.cmd_search import CmdSearch
        mock_roll.return_value = 20
        # remove_condition fires 3rd-person end message to room before search result
        expected = Condition.HIDDEN.get_end_message_third_person(self.char2.key)
        self.call(CmdSearch(), "", expected)
        self.assertFalse(self.char2.has_condition(Condition.HIDDEN))

    @patch("utils.dice_roller.DiceRoller.roll_with_advantage_or_disadvantage")
    def test_search_misses_hidden_character(self, mock_roll):
        """Search with low roll should not reveal well-hidden character."""
        from commands.all_char_cmds.cmd_search import CmdSearch
        mock_roll.return_value = 1
        _set_stealth(self.char2, MasteryLevel.GRANDMASTER)
        self.char2.dexterity = 18
        self.call(CmdSearch(), "", "You search but find nothing unusual.")
        self.assertTrue(self.char2.has_condition(Condition.HIDDEN))
