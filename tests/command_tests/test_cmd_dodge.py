"""
Tests for the dodge command (BATTLESKILLS general skill — combat evasion).

evennia test --settings settings tests.command_tests.test_cmd_dodge
"""

from unittest.mock import patch

from evennia.utils.test_resources import EvenniaCommandTest
from evennia.utils import create

from commands.class_skill_cmdsets.class_skill_cmds.cmd_dodge import CmdDodge
from combat.combat_utils import enter_combat
from enums.mastery_level import MasteryLevel
from enums.skills_enum import skills


class _DodgeTestBase(EvenniaCommandTest):
    """Shared setUp/tearDown for dodge tests."""

    character_typeclass = "typeclasses.actors.character.FCMCharacter"
    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.room1.allow_combat = True
        self.room1.allow_pvp = True
        self.char1.hp = 20
        self.char1.hp_max = 20
        self.char1.move = 100
        self.char2.hp = 20
        self.char2.hp_max = 20

    def tearDown(self):
        for char in (self.char1, self.char2):
            handlers = char.scripts.get("combat_handler")
            if handlers:
                for h in handlers:
                    h.stop()
                    h.delete()
        super().tearDown()

    def _set_battleskills(self, char, level):
        if not char.db.general_skill_mastery_levels:
            char.db.general_skill_mastery_levels = {}
        char.db.general_skill_mastery_levels[skills.BATTLESKILLS.value] = level.value


# ================================================================== #
#  Gate Tests
# ================================================================== #


class TestDodgeGates(_DodgeTestBase):
    """Test dodge command gate checks."""

    def test_not_in_combat(self):
        """Dodge outside combat shows error."""
        self._set_battleskills(self.char1, MasteryLevel.BASIC)
        result = self.call(CmdDodge(), "", caller=self.char1)
        self.assertIn("not in combat", result)

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_unskilled_can_dodge(self, mock_ticker):
        """Even unskilled characters can dodge (with clumsy message)."""
        self._set_battleskills(self.char1, MasteryLevel.UNSKILLED)
        enter_combat(self.char1, self.char2)
        result = self.call(CmdDodge(), "", caller=self.char1)
        self.assertIn("clumsily", result)

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_basic_dodge_message(self, mock_ticker):
        """Basic mastery shows weaving message."""
        self._set_battleskills(self.char1, MasteryLevel.BASIC)
        enter_combat(self.char1, self.char2)
        result = self.call(CmdDodge(), "", caller=self.char1)
        self.assertIn("weaving defensively", result)


# ================================================================== #
#  Mechanic Tests
# ================================================================== #


class TestDodgeMechanics(_DodgeTestBase):
    """Test dodge combat mechanics."""

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_dodge_sets_skip_next_action(self, mock_ticker):
        """Dodge sets skip_next_action on the handler."""
        self._set_battleskills(self.char1, MasteryLevel.BASIC)
        enter_combat(self.char1, self.char2)
        handler = self.char1.scripts.get("combat_handler")[0]

        self.assertFalse(handler.skip_next_action)
        self.call(CmdDodge(), "", caller=self.char1)
        self.assertTrue(handler.skip_next_action)

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_dodge_gives_enemies_disadvantage(self, mock_ticker):
        """Dodge gives all enemies disadvantage against the dodger."""
        self._set_battleskills(self.char1, MasteryLevel.BASIC)
        enter_combat(self.char1, self.char2)
        enemy_handler = self.char2.scripts.get("combat_handler")[0]

        self.assertFalse(enemy_handler.has_disadvantage(self.char1))
        self.call(CmdDodge(), "", caller=self.char1)
        self.assertTrue(enemy_handler.has_disadvantage(self.char1))

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_dodge_multiple_enemies(self, mock_ticker):
        """Dodge gives disadvantage to all enemies, not just one."""
        self._set_battleskills(self.char1, MasteryLevel.BASIC)

        mob = create.create_object(
            "typeclasses.actors.mobs.aggressive_mob.AggressiveMob",
            key="test_mob",
            location=self.room1,
        )
        mob.hp = 10
        mob.hp_max = 10

        enter_combat(self.char1, self.char2)
        enter_combat(self.char1, mob)

        self.call(CmdDodge(), "", caller=self.char1)

        char2_handler = self.char2.scripts.get("combat_handler")[0]
        mob_handler = mob.scripts.get("combat_handler")

        self.assertTrue(char2_handler.has_disadvantage(self.char1))
        if mob_handler:
            self.assertTrue(mob_handler[0].has_disadvantage(self.char1))

        mob.delete()

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_dodge_skip_consumed_on_next_tick(self, mock_ticker):
        """skip_next_action is consumed after one tick."""
        self._set_battleskills(self.char1, MasteryLevel.BASIC)
        enter_combat(self.char1, self.char2)
        handler = self.char1.scripts.get("combat_handler")[0]

        self.call(CmdDodge(), "", caller=self.char1)
        self.assertTrue(handler.skip_next_action)

        # Execute one tick — skip consumed, no attack happens
        with patch("combat.combat_utils.dice") as mock_dice:
            mock_dice.roll_with_advantage_or_disadvantage.return_value = 15
            mock_dice.roll.return_value = 3
            handler.execute_next_action()

        self.assertFalse(handler.skip_next_action)


# ================================================================== #
#  Mob Dodge Tests
# ================================================================== #


class TestMobDodge(_DodgeTestBase):
    """Test mob dodge fallback."""

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_mob_dodge_sets_disadvantage(self, mock_ticker):
        """Mob dodge (no mastery data) still sets disadvantage."""
        mob = create.create_object(
            "typeclasses.actors.mobs.aggressive_mob.AggressiveMob",
            key="test_mob",
            location=self.room1,
        )
        mob.hp = 10
        mob.hp_max = 10

        enter_combat(mob, self.char1)
        char_handler = self.char1.scripts.get("combat_handler")[0]

        self.call(CmdDodge(), "", caller=mob)
        self.assertTrue(char_handler.has_disadvantage(mob))

        mob.delete()
