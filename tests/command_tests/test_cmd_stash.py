"""
Tests for the stash command.

Tests object concealment, actor stashing, mastery requirements,
combat blocking, and integration with the search command's
discovery mechanic.
"""

from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaCommandTest

from commands.class_skill_cmdsets.class_skill_cmds.cmd_stash import CmdStash
from commands.all_char_cmds.cmd_search import CmdSearch
from enums.condition import Condition
from enums.mastery_level import MasteryLevel
from enums.skills_enum import skills

_ROOM = "typeclasses.terrain.rooms.room_base.RoomBase"
_CHAR = "typeclasses.actors.character.FCMCharacter"
_ITEM = "typeclasses.world_objects.base_world_item.WorldItem"


def _set_stealth(char, mastery=MasteryLevel.BASIC):
    """Give a character the stealth skill at a given mastery level."""
    if not char.db.class_skill_mastery_levels:
        char.db.class_skill_mastery_levels = {}
    char.db.class_skill_mastery_levels[skills.STEALTH.value] = {"mastery": mastery.value, "classes": ["Thief"]}


class TestCmdStashBasic(EvenniaCommandTest):
    """Tests for basic stash command flow."""
    room_typeclass = _ROOM
    character_typeclass = _CHAR

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        _set_stealth(self.char1, MasteryLevel.BASIC)
        self.item = create_object(_ITEM, key="Gold Ring", location=self.room1)

    @patch("utils.dice_roller.DiceRoller.roll_with_advantage_or_disadvantage")
    def test_stash_object_succeeds(self, mock_roll):
        """Stashing an object should hide it with the rolled DC."""
        mock_roll.return_value = 15
        self.call(CmdStash(), "Gold Ring", "You stash Gold Ring out of sight.")
        self.assertTrue(self.item.is_hidden)
        self.assertGreater(self.item.find_dc, 0)

    def test_stash_no_args(self):
        """Stash with no target should prompt."""
        self.call(CmdStash(), "", "Stash what?")

    def test_stash_unskilled_blocked(self):
        """UNSKILLED mastery should block stashing."""
        _set_stealth(self.char1, MasteryLevel.UNSKILLED)
        self.call(CmdStash(), "Gold Ring", "You have no idea how to stash")

    def test_stash_no_mastery_dict(self):
        """Character with no mastery data should fail."""
        self.char1.db.class_skill_mastery_levels = None
        self.call(CmdStash(), "Gold Ring", "You have no idea how to stash")

    def test_stash_already_hidden(self):
        """Stashing an already hidden object should show message."""
        self.item.is_hidden = True
        self.call(CmdStash(), "Gold Ring", "Gold Ring is already hidden.")

    def test_stash_in_combat_blocked(self):
        """Cannot stash while in combat."""
        from combat.combat_handler import CombatHandler
        self.char1.scripts.add(CombatHandler, autostart=False)
        self.call(CmdStash(), "Gold Ring", "You can't stash things while in combat!")

    @patch("utils.dice_roller.DiceRoller.roll_with_advantage_or_disadvantage")
    def test_stash_actor_succeeds(self, mock_roll):
        """Stashing an ally with a high roll should hide them."""
        mock_roll.return_value = 20
        # add_condition broadcasts the HIDDEN start message first
        self.call(CmdStash(), self.char2.key, f"{self.char2.key} melts into the shadows")
        self.assertTrue(self.char2.has_condition(Condition.HIDDEN))

    def test_stash_self_blocked(self):
        """Cannot stash yourself."""
        self.call(CmdStash(), self.char1.key, "You can't stash yourself")

    def test_stash_already_hidden_actor(self):
        """Stashing an already hidden ally should show message."""
        self.char2.add_condition(Condition.HIDDEN)
        self.call(CmdStash(), self.char2.key, f"{self.char2.key} is already hidden.")


class TestCmdStashDC(EvenniaCommandTest):
    """Tests for stash DC calculation."""
    room_typeclass = _ROOM
    character_typeclass = _CHAR

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        _set_stealth(self.char1, MasteryLevel.BASIC)
        self.item = create_object(_ITEM, key="Dagger", location=self.room1)

    @patch("utils.dice_roller.DiceRoller.roll_with_advantage_or_disadvantage")
    def test_dc_equals_roll_plus_bonus(self, mock_roll):
        """find_dc should equal the d20 roll + effective stealth bonus."""
        mock_roll.return_value = 12
        expected_dc = 12 + self.char1.effective_stealth_bonus
        self.call(CmdStash(), "Dagger")
        self.assertEqual(self.item.find_dc, expected_dc)

    @patch("utils.dice_roller.DiceRoller.roll_with_advantage_or_disadvantage")
    def test_discovered_by_cleared(self, mock_roll):
        """Stashing should clear prior discoveries."""
        mock_roll.return_value = 10
        self.item.discovered_by = {"some_old_key"}
        self.call(CmdStash(), "Dagger")
        self.assertEqual(self.item.discovered_by, set())


class TestSearchFindsStashed(EvenniaCommandTest):
    """Tests for the search command finding stashed objects."""
    room_typeclass = _ROOM
    character_typeclass = _CHAR

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.item = create_object(_ITEM, key="Hidden Gem", location=self.room1)
        self.item.is_hidden = True
        self.item.find_dc = 12

    @patch("utils.dice_roller.DiceRoller.roll_with_advantage_or_disadvantage")
    def test_search_finds_stashed_object(self, mock_roll):
        """Search with high roll should reveal stashed object."""
        mock_roll.return_value = 20
        # discover() fires room broadcast before search result message
        self.call(CmdSearch(), "", "Char discovers Hidden Gem hidden nearby!")
        self.assertFalse(self.item.is_hidden)

    @patch("utils.dice_roller.DiceRoller.roll_with_advantage_or_disadvantage")
    def test_search_misses_well_stashed_object(self, mock_roll):
        """Search with low roll should not reveal well-stashed object."""
        mock_roll.return_value = 1
        self.item.find_dc = 30  # very high DC
        self.call(CmdSearch(), "", "You search but find nothing unusual.")
        self.assertTrue(self.item.is_hidden)


class TestCmdStashActor(EvenniaCommandTest):
    """Tests for stashing allies (actor branch)."""
    room_typeclass = _ROOM
    character_typeclass = _CHAR

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        _set_stealth(self.char1, MasteryLevel.SKILLED)

    @patch("utils.dice_roller.DiceRoller.roll_with_advantage_or_disadvantage")
    def test_stash_ally_applies_hidden(self, mock_roll):
        """Stashing an ally should apply HIDDEN condition."""
        mock_roll.return_value = 20
        # add_condition broadcasts the HIDDEN start message first
        self.call(CmdStash(), self.char2.key, f"{self.char2.key} melts into the shadows")
        self.assertTrue(self.char2.has_condition(Condition.HIDDEN))

    @patch("utils.dice_roller.DiceRoller.roll_with_advantage_or_disadvantage")
    def test_stash_ally_fails_low_roll(self, mock_roll):
        """Stashing an ally should fail against good perceivers with low roll."""
        mock_roll.return_value = 1
        # Add a third character as a high-perception perceiver
        perceiver = create_object(_CHAR, key="Guard", location=self.room1)
        if not perceiver.db.general_skill_mastery_levels:
            perceiver.db.general_skill_mastery_levels = {}
        perceiver.db.general_skill_mastery_levels[skills.ALERTNESS.value] = (
            MasteryLevel.GRANDMASTER.value
        )
        perceiver.wisdom = 18
        self.call(CmdStash(), self.char2.key, "You try to hide")
        self.assertFalse(self.char2.has_condition(Condition.HIDDEN))

    @patch("utils.dice_roller.DiceRoller.roll_with_advantage_or_disadvantage")
    def test_stash_ally_empty_room_succeeds(self, mock_roll):
        """Stashing an ally in an otherwise empty room should auto-succeed."""
        mock_roll.return_value = 5
        # Only caller and target in the room — no perceivers (DC 0)
        self.call(CmdStash(), self.char2.key, f"{self.char2.key} melts into the shadows")
        self.assertTrue(self.char2.has_condition(Condition.HIDDEN))

    def test_stash_ally_in_combat_blocked(self):
        """Cannot stash an ally who is in combat."""
        from combat.combat_handler import CombatHandler
        self.char2.scripts.add(CombatHandler, autostart=False)
        self.call(CmdStash(), self.char2.key, "You can't stash")
