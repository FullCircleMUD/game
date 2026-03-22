"""
Tests for the taunt command (PROTECT skill — provoke mobs).

evennia test --settings settings tests.command_tests.test_cmd_taunt
"""

import time
from unittest.mock import patch

from evennia.utils.test_resources import EvenniaCommandTest
from evennia.utils import create

from commands.class_skill_cmdsets.class_skill_cmds.cmd_taunt import (
    CmdTaunt, TAUNT_COOLDOWNS, TAUNT_OOC_FAIL_COOLDOWN,
)
from combat.combat_utils import enter_combat
from enums.mastery_level import MasteryLevel
from enums.skills_enum import skills


class _TauntTestBase(EvenniaCommandTest):
    """Shared setUp/tearDown for taunt tests."""

    character_typeclass = "typeclasses.actors.character.FCMCharacter"
    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.room1.allow_combat = True
        self.char1.hp = 20
        self.char1.hp_max = 20
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
        if not char.db.skill_mastery_levels:
            char.db.skill_mastery_levels = {}
        char.db.skill_mastery_levels[skills.PROTECT.value] = level.value


# ================================================================== #
#  Gate Tests
# ================================================================== #


class TestTauntGates(_TauntTestBase):
    """Test taunt command gate checks."""

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

    def test_unskilled_blocked(self):
        """Unskilled characters can't taunt."""
        self._set_mastery(self.char1, MasteryLevel.UNSKILLED)
        result = self.call(CmdTaunt(), self.mob.key)
        self.assertIn("need training", result)

    def test_no_args_out_of_combat(self):
        """Taunt with no args out of combat → 'Taunt who?'."""
        self._set_mastery(self.char1, MasteryLevel.BASIC)
        result = self.call(CmdTaunt(), "")
        self.assertIn("Taunt who?", result)

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_taunt_self_blocked(self, mock_ticker):
        """Can't taunt yourself."""
        self._set_mastery(self.char1, MasteryLevel.BASIC)
        enter_combat(self.char1, self.mob)
        result = self.call(CmdTaunt(), self.char1.key)
        self.assertIn("can't taunt yourself", result)

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_taunt_non_mob(self, mock_ticker):
        """Taunting another player has no effect."""
        self._set_mastery(self.char1, MasteryLevel.BASIC)
        enter_combat(self.char1, self.mob)
        result = self.call(CmdTaunt(), self.char2.key)
        self.assertIn("Taunting other players has no effect", result)

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_in_combat_cooldown_blocks_reuse(self, mock_ticker):
        """Taunt cooldown blocks reuse."""
        self._set_mastery(self.char1, MasteryLevel.BASIC)
        enter_combat(self.char1, self.mob)
        handler = self.char1.scripts.get("combat_handler")[0]
        handler.taunt_cooldown = 3
        result = self.call(CmdTaunt(), self.mob.key)
        self.assertIn("cooldown", result)

    def test_combat_not_allowed_in_room(self):
        """Taunt blocked in no-combat rooms."""
        self._set_mastery(self.char1, MasteryLevel.BASIC)
        self.room1.allow_combat = False
        result = self.call(CmdTaunt(), self.mob.key)
        self.assertIn("Combat is not allowed here", result)


# ================================================================== #
#  In-Combat Tests
# ================================================================== #


class TestTauntInCombat(_TauntTestBase):
    """Test taunt mechanics in combat."""

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
    def test_taunt_success_switches_target(self, mock_roll, mock_ticker):
        """Successful taunt switches mob's target to the taunter."""
        self._set_mastery(self.char1, MasteryLevel.BASIC)
        self._set_mastery(self.char2, MasteryLevel.BASIC)
        enter_combat(self.char1, self.mob)
        enter_combat(self.char2, self.mob)

        # Set mob to attack char2 initially
        mob_handler = self.mob.scripts.get("combat_handler")[0]
        mob_handler.queue_action({
            "key": "attack", "target": self.char2, "dt": 4, "repeat": True,
        })

        # Caller rolls 18, mob rolls 5 → success
        mock_roll.side_effect = [18, 5]
        with patch("commands.class_skill_cmdsets.class_skill_cmds.cmd_taunt.random.randint", return_value=4):
            result = self.call(CmdTaunt(), self.mob.key, caller=self.char1)

        self.assertIn("*TAUNT*", result)
        # Mob should now target char1
        mob_action = mob_handler.action_dict
        self.assertEqual(mob_action.get("target"), self.char1)

    @patch("combat.combat_handler.TICKER_HANDLER")
    @patch("utils.dice_roller.DiceRoller.roll")
    def test_taunt_failure_no_switch(self, mock_roll, mock_ticker):
        """Failed taunt doesn't switch mob's target."""
        self._set_mastery(self.char1, MasteryLevel.BASIC)
        self._set_mastery(self.char2, MasteryLevel.BASIC)
        enter_combat(self.char1, self.mob)
        enter_combat(self.char2, self.mob)

        mob_handler = self.mob.scripts.get("combat_handler")[0]
        mob_handler.queue_action({
            "key": "attack", "target": self.char2, "dt": 4, "repeat": True,
        })

        # Caller rolls 3, mob rolls 18 → failure
        mock_roll.side_effect = [3, 18]
        result = self.call(CmdTaunt(), self.mob.key, caller=self.char1)

        self.assertIn("ignores you", result)
        mob_action = mob_handler.action_dict
        self.assertEqual(mob_action.get("target"), self.char2)

    @patch("combat.combat_handler.TICKER_HANDLER")
    @patch("utils.dice_roller.DiceRoller.roll")
    def test_taunt_sets_round_cooldown(self, mock_roll, mock_ticker):
        """Taunt sets round-based cooldown regardless of outcome."""
        self._set_mastery(self.char1, MasteryLevel.SKILLED)
        enter_combat(self.char1, self.mob)

        mock_roll.side_effect = [18, 5]
        with patch("commands.class_skill_cmdsets.class_skill_cmds.cmd_taunt.random.randint", return_value=4):
            self.call(CmdTaunt(), self.mob.key, caller=self.char1)

        handler = self.char1.scripts.get("combat_handler")[0]
        self.assertEqual(handler.taunt_cooldown, TAUNT_COOLDOWNS[MasteryLevel.SKILLED])

    @patch("combat.combat_handler.TICKER_HANDLER")
    @patch("utils.dice_roller.DiceRoller.roll")
    def test_no_args_defaults_to_current_target(self, mock_roll, mock_ticker):
        """Taunt with no args in combat defaults to attack target."""
        self._set_mastery(self.char1, MasteryLevel.BASIC)
        enter_combat(self.char1, self.mob)
        handler = self.char1.scripts.get("combat_handler")[0]
        handler.queue_action({
            "key": "attack", "target": self.mob, "dt": 4, "repeat": True,
        })

        mock_roll.side_effect = [18, 5]
        with patch("commands.class_skill_cmdsets.class_skill_cmds.cmd_taunt.random.randint", return_value=4):
            result = self.call(CmdTaunt(), "", caller=self.char1)

        self.assertIn("*TAUNT*", result)

    @patch("combat.combat_handler.TICKER_HANDLER")
    @patch("utils.dice_roller.DiceRoller.roll")
    def test_mastery_cooldown_scaling(self, mock_roll, mock_ticker):
        """Higher mastery = shorter cooldown."""
        for level in [MasteryLevel.BASIC, MasteryLevel.EXPERT, MasteryLevel.GRANDMASTER]:
            self._set_mastery(self.char1, level)
            enter_combat(self.char1, self.mob)
            handler = self.char1.scripts.get("combat_handler")[0]
            handler.taunt_cooldown = 0

            mock_roll.side_effect = [18, 5]
            with patch("commands.class_skill_cmdsets.class_skill_cmds.cmd_taunt.random.randint", return_value=4):
                self.call(CmdTaunt(), self.mob.key, caller=self.char1)

            self.assertEqual(handler.taunt_cooldown, TAUNT_COOLDOWNS[level])


# ================================================================== #
#  Opener Tests
# ================================================================== #


class TestTauntOpener(_TauntTestBase):
    """Test taunt as combat opener."""

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
    def test_opener_success_mob_attacks_taunter(self, mock_roll, mock_ticker):
        """Successful opener taunt makes mob attack the taunter."""
        self._set_mastery(self.char1, MasteryLevel.BASIC)

        # Caller rolls 18, mob rolls 5 → success
        mock_roll.side_effect = [18, 5]
        result = self.call(CmdTaunt(), self.mob.key, caller=self.char1)

        self.assertIn("*TAUNT*", result)
        self.assertIn("attacks you", result)
        # Both should now be in combat
        self.assertTrue(bool(self.char1.scripts.get("combat_handler")))
        self.assertTrue(bool(self.mob.scripts.get("combat_handler")))

    @patch("utils.dice_roller.DiceRoller.roll")
    def test_opener_failure_no_combat(self, mock_roll):
        """Failed opener taunt doesn't start combat."""
        self._set_mastery(self.char1, MasteryLevel.BASIC)

        # Caller rolls 3, mob rolls 18 → failure
        mock_roll.side_effect = [3, 18]
        result = self.call(CmdTaunt(), self.mob.key, caller=self.char1)

        self.assertIn("ignores your taunts", result)
        self.assertFalse(bool(self.char1.scripts.get("combat_handler")))
        self.assertFalse(bool(self.mob.scripts.get("combat_handler")))

    @patch("utils.dice_roller.DiceRoller.roll")
    def test_opener_failure_sets_5min_cooldown(self, mock_roll):
        """Failed opener sets 5-minute timestamp cooldown."""
        self._set_mastery(self.char1, MasteryLevel.BASIC)

        mock_roll.side_effect = [3, 18]
        self.call(CmdTaunt(), self.mob.key, caller=self.char1)

        cooldown_until = self.char1.db.taunt_cooldown_until
        self.assertIsNotNone(cooldown_until)
        self.assertGreater(cooldown_until, time.time())
        self.assertLessEqual(cooldown_until, time.time() + TAUNT_OOC_FAIL_COOLDOWN + 1)

    @patch("utils.dice_roller.DiceRoller.roll")
    def test_opener_5min_cooldown_blocks_retry(self, mock_roll):
        """5-minute cooldown blocks a second out-of-combat taunt."""
        self._set_mastery(self.char1, MasteryLevel.BASIC)

        # First attempt fails
        mock_roll.side_effect = [3, 18]
        self.call(CmdTaunt(), self.mob.key, caller=self.char1)

        # Second attempt blocked
        mock_roll.side_effect = [18, 5]
        result = self.call(CmdTaunt(), self.mob.key, caller=self.char1)
        self.assertIn("still recovering", result)
