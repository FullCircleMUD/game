"""
Tests for the retreat command (STRATEGY skill — group strategic withdrawal).

evennia test --settings settings tests.command_tests.test_cmd_retreat
"""

from unittest.mock import patch

from evennia.utils.test_resources import EvenniaCommandTest
from evennia.utils import create

from commands.class_skill_cmdsets.class_skill_cmds.cmd_retreat import CmdRetreat
from combat.combat_utils import enter_combat
from enums.mastery_level import MasteryLevel
from enums.skills_enum import skills


class _RetreatTestBase(EvenniaCommandTest):
    """Shared setUp/tearDown for retreat tests."""

    character_typeclass = "typeclasses.actors.character.FCMCharacter"
    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.room1.allow_combat = True
        self.room2.allow_combat = True
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

    def _set_mastery(self, char, level):
        if not char.db.class_skill_mastery_levels:
            char.db.class_skill_mastery_levels = {}
        char.db.class_skill_mastery_levels[skills.STRATEGY.value] = {"mastery": level.value, "classes": ["Warrior"]}


# ================================================================== #
#  Gate Tests
# ================================================================== #


class TestRetreatGates(_RetreatTestBase):
    """Test retreat command gate checks."""

    def test_unskilled_blocked(self):
        """Unskilled characters can't retreat."""
        self._set_mastery(self.char1, MasteryLevel.UNSKILLED)
        result = self.call(CmdRetreat(), "")
        self.assertIn("need training", result)

    def test_not_in_combat(self):
        """Can't retreat if not in combat."""
        self._set_mastery(self.char1, MasteryLevel.BASIC)
        result = self.call(CmdRetreat(), "")
        self.assertIn("not in combat", result)

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_follower_cannot_retreat(self, mock_ticker):
        """Only the group leader can order retreat."""
        self._set_mastery(self.char1, MasteryLevel.BASIC)
        mob = create.create_object(
            "typeclasses.actors.mobs.dire_wolf.DireWolf",
            key="dire wolf",
            location=self.room1,
        )
        mob.hp = 30
        mob.hp_max = 30
        try:
            enter_combat(self.char1, mob)
            self.char1.following = self.char2
            result = self.call(CmdRetreat(), "", caller=self.char1)
            self.assertIn("Only the group leader", result)
        finally:
            self.char1.following = None
            for h in mob.scripts.get("combat_handler") or []:
                h.stop()
                h.delete()
            mob.delete()

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_no_exits(self, mock_ticker):
        """Retreat blocked when no exits."""
        self._set_mastery(self.char1, MasteryLevel.BASIC)
        # Create a room with no exits
        isolated = create.create_object(
            "typeclasses.terrain.rooms.room_base.RoomBase",
            key="isolated",
        )
        isolated.allow_combat = True
        mob = create.create_object(
            "typeclasses.actors.mobs.dire_wolf.DireWolf",
            key="dire wolf",
            location=isolated,
        )
        mob.hp = 30
        mob.hp_max = 30
        self.char1.move_to(isolated, quiet=True)
        try:
            enter_combat(self.char1, mob)
            result = self.call(CmdRetreat(), "", caller=self.char1)
            self.assertIn("nowhere to go", result)
        finally:
            for h in self.char1.scripts.get("combat_handler") or []:
                h.stop()
                h.delete()
            for h in mob.scripts.get("combat_handler") or []:
                h.stop()
                h.delete()
            self.char1.move_to(self.room1, quiet=True)
            mob.delete()
            isolated.delete()


# ================================================================== #
#  Mechanic Tests
# ================================================================== #


class TestRetreatMechanics(_RetreatTestBase):
    """Test retreat mechanics."""

    def setUp(self):
        super().setUp()
        self.mob = create.create_object(
            "typeclasses.actors.mobs.dire_wolf.DireWolf",
            key="dire wolf",
            location=self.room1,
        )
        self.mob.hp = 30
        self.mob.hp_max = 30

    def tearDown(self):
        handlers = self.mob.scripts.get("combat_handler")
        if handlers:
            for h in handlers:
                h.stop()
                h.delete()
        self.mob.delete()
        super().tearDown()

    @patch("combat.combat_handler.TICKER_HANDLER")
    @patch("utils.dice_roller.DiceRoller.roll")
    def test_retreat_success_leaves_combat(self, mock_roll, mock_ticker):
        """Successful retreat removes combat handler."""
        self._set_mastery(self.char1, MasteryLevel.BASIC)
        enter_combat(self.char1, self.mob)

        mock_roll.return_value = 15  # 15 + mods >= DC 10
        with patch("commands.class_skill_cmdsets.class_skill_cmds.cmd_retreat.random.choice") as mock_choice:
            mock_choice.return_value = self.exit
            result = self.call(CmdRetreat(), "", caller=self.char1)

        self.assertIn("*RETREAT*", result)
        self.assertFalse(bool(self.char1.scripts.get("combat_handler")))

    @patch("combat.combat_handler.TICKER_HANDLER")
    @patch("utils.dice_roller.DiceRoller.roll")
    def test_retreat_success_moves_to_exit(self, mock_roll, mock_ticker):
        """Successful retreat moves caller to exit destination."""
        self._set_mastery(self.char1, MasteryLevel.BASIC)
        enter_combat(self.char1, self.mob)

        mock_roll.return_value = 15
        with patch("commands.class_skill_cmdsets.class_skill_cmds.cmd_retreat.random.choice") as mock_choice:
            mock_choice.return_value = self.exit
            self.call(CmdRetreat(), "", caller=self.char1)

        self.assertEqual(self.char1.location, self.room2)

    @patch("combat.combat_handler.TICKER_HANDLER")
    @patch("utils.dice_roller.DiceRoller.roll")
    def test_retreat_success_moves_group(self, mock_roll, mock_ticker):
        """Successful retreat moves all group members."""
        self._set_mastery(self.char1, MasteryLevel.BASIC)
        enter_combat(self.char1, self.mob)
        enter_combat(self.char2, self.mob)
        self.char2.following = self.char1

        mock_roll.return_value = 15
        with patch("commands.class_skill_cmdsets.class_skill_cmds.cmd_retreat.random.choice") as mock_choice:
            mock_choice.return_value = self.exit
            self.call(CmdRetreat(), "", caller=self.char1)

        self.assertEqual(self.char1.location, self.room2)
        self.assertEqual(self.char2.location, self.room2)
        self.assertFalse(bool(self.char1.scripts.get("combat_handler")))
        self.assertFalse(bool(self.char2.scripts.get("combat_handler")))

        self.char2.following = None

    @patch("combat.combat_handler.TICKER_HANDLER")
    @patch("utils.dice_roller.DiceRoller.roll")
    def test_retreat_failure_grants_advantage_to_leader(self, mock_roll, mock_ticker):
        """Failed retreat grants enemies advantage against the leader."""
        self._set_mastery(self.char1, MasteryLevel.BASIC)
        enter_combat(self.char1, self.mob)

        mock_roll.return_value = 1  # 1 + mods < DC 10
        result = self.call(CmdRetreat(), "", caller=self.char1)

        self.assertIn("FAILED", result)
        mob_handler = self.mob.scripts.get("combat_handler")
        if mob_handler:
            self.assertTrue(mob_handler[0].has_advantage(self.char1))

    @patch("combat.combat_handler.TICKER_HANDLER")
    @patch("utils.dice_roller.DiceRoller.roll")
    def test_retreat_failure_nobody_moves(self, mock_roll, mock_ticker):
        """Failed retreat leaves everyone in place."""
        self._set_mastery(self.char1, MasteryLevel.BASIC)
        enter_combat(self.char1, self.mob)

        mock_roll.return_value = 1
        self.call(CmdRetreat(), "", caller=self.char1)

        self.assertEqual(self.char1.location, self.room1)
        self.assertTrue(bool(self.char1.scripts.get("combat_handler")))

    @patch("combat.combat_handler.TICKER_HANDLER")
    @patch("utils.dice_roller.DiceRoller.roll")
    def test_retreat_with_direction(self, mock_roll, mock_ticker):
        """Retreat with a direction argument uses that exit."""
        self._set_mastery(self.char1, MasteryLevel.BASIC)
        enter_combat(self.char1, self.mob)

        mock_roll.return_value = 15
        result = self.call(CmdRetreat(), self.exit.key, caller=self.char1)

        self.assertIn("*RETREAT*", result)
        self.assertEqual(self.char1.location, self.room2)

    @patch("combat.combat_handler.TICKER_HANDLER")
    @patch("utils.dice_roller.DiceRoller.roll")
    def test_mastery_bonus_applies(self, mock_roll, mock_ticker):
        """Higher mastery adds bonus to the retreat roll."""
        # With a roll of 3 and BASIC mastery (bonus=0), 3 + INT_mod + CHA_mod
        # might fail. With GM mastery (bonus=8), 3+8 = 11 >= DC 10 even with
        # no stat mods. We test that GM succeeds where BASIC would fail.
        self._set_mastery(self.char1, MasteryLevel.GRANDMASTER)
        # Set stats low so only mastery bonus matters
        self.char1.intelligence = 10  # +0 mod
        self.char1.charisma = 10      # +0 mod
        enter_combat(self.char1, self.mob)

        # Roll 3 + 0 (INT) + 0 (CHA) + 8 (GM bonus) = 11 >= 10
        mock_roll.return_value = 3
        with patch("commands.class_skill_cmdsets.class_skill_cmds.cmd_retreat.random.choice") as mock_choice:
            mock_choice.return_value = self.exit
            result = self.call(CmdRetreat(), "", caller=self.char1)

        self.assertIn("*RETREAT*", result)
