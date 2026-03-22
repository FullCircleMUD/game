"""
Tests for the pummel command (PUMMEL skill — warrior/paladin combat maneuver).

evennia test --settings settings tests.command_tests.test_cmd_pummel
"""

from unittest.mock import patch

from evennia.utils.test_resources import EvenniaCommandTest
from evennia.utils import create

from commands.class_skill_cmdsets.class_skill_cmds.cmd_pummel import CmdPummel, PUMMEL_COOLDOWNS
from combat.combat_utils import enter_combat
from enums.mastery_level import MasteryLevel
from enums.skills_enum import skills


class _PummelTestBase(EvenniaCommandTest):
    """Shared setUp/tearDown for pummel tests."""

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

    def _set_pummel_mastery(self, char, level):
        if not char.db.skill_mastery_levels:
            char.db.skill_mastery_levels = {}
        char.db.skill_mastery_levels[skills.PUMMEL.value] = level.value


# ================================================================== #
#  Gate Tests
# ================================================================== #


class TestPummelGates(_PummelTestBase):
    """Test pummel command gate checks."""

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
        """Unskilled characters can't pummel."""
        self._set_pummel_mastery(self.char1, MasteryLevel.UNSKILLED)
        result = self.call(CmdPummel(), self.char2.key)
        self.assertIn("need training", result)

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_no_args_in_combat_no_target(self, mock_ticker):
        """Pummel with no args in combat but no attack target → error."""
        self._set_pummel_mastery(self.char1, MasteryLevel.BASIC)
        enter_combat(self.char1, self.mob)
        result = self.call(CmdPummel(), "")
        self.assertIn("Pummel who?", result)

    def test_no_args_out_of_combat(self):
        """Pummel with no args out of combat → funny flail message."""
        self._set_pummel_mastery(self.char1, MasteryLevel.BASIC)
        result = self.call(CmdPummel(), "")
        self.assertIn("air", result)

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_pummel_self_blocked(self, mock_ticker):
        """Can't pummel yourself."""
        self._set_pummel_mastery(self.char1, MasteryLevel.BASIC)
        enter_combat(self.char1, self.mob)
        result = self.call(CmdPummel(), self.char1.key)
        self.assertIn("can't pummel yourself", result)

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_not_in_combat_starts_combat(self, mock_ticker):
        """Pummel <target> out of combat starts combat."""
        self._set_pummel_mastery(self.char1, MasteryLevel.BASIC)
        with patch("utils.dice_roller.DiceRoller.roll", side_effect=[18, 5]):
            result = self.call(CmdPummel(), self.mob.key, caller=self.char1)
        self.assertIn("rush at", result)
        self.assertTrue(bool(self.char1.scripts.get("combat_handler")))


# ================================================================== #
#  Combat Tests
# ================================================================== #


class TestPummelCombat(_PummelTestBase):
    """Test pummel in combat."""

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
    def test_target_not_enemy(self, mock_ticker):
        """Can't pummel an ally."""
        self._set_pummel_mastery(self.char1, MasteryLevel.BASIC)
        enter_combat(self.char1, self.mob)
        enter_combat(self.char2, self.mob)

        result = self.call(CmdPummel(), self.char2.key, caller=self.char1)
        self.assertIn("not an enemy", result)

    @patch("combat.combat_handler.TICKER_HANDLER")
    @patch("utils.dice_roller.DiceRoller.roll")
    def test_pummel_success_stuns(self, mock_roll, mock_ticker):
        """Successful pummel stuns target."""
        self._set_pummel_mastery(self.char1, MasteryLevel.BASIC)
        enter_combat(self.char1, self.mob)

        # Attacker rolls 18, defender rolls 5
        mock_roll.side_effect = [18, 5]
        result = self.call(CmdPummel(), self.mob.key, caller=self.char1)

        self.assertIn("*PUMMEL*", result)
        self.assertTrue(self.mob.has_effect("stunned"))

    @patch("combat.combat_handler.TICKER_HANDLER")
    @patch("utils.dice_roller.DiceRoller.roll")
    def test_pummel_success_no_advantage(self, mock_roll, mock_ticker):
        """Pummel does NOT grant advantage to allies (key difference from bash)."""
        self._set_pummel_mastery(self.char1, MasteryLevel.BASIC)
        enter_combat(self.char1, self.mob)
        enter_combat(self.char2, self.mob)

        # Attacker rolls 18, defender rolls 5
        mock_roll.side_effect = [18, 5]
        self.call(CmdPummel(), self.mob.key, caller=self.char1)

        # Neither ally should have advantage (stunned has no callback)
        handler1 = self.char1.scripts.get("combat_handler")[0]
        handler2 = self.char2.scripts.get("combat_handler")[0]
        self.assertFalse(handler1.has_advantage(self.mob))
        self.assertFalse(handler2.has_advantage(self.mob))

    @patch("combat.combat_handler.TICKER_HANDLER")
    @patch("utils.dice_roller.DiceRoller.roll")
    def test_pummel_failure_nothing_happens(self, mock_roll, mock_ticker):
        """Failed pummel has no effect."""
        self._set_pummel_mastery(self.char1, MasteryLevel.BASIC)
        enter_combat(self.char1, self.mob)

        # Attacker rolls 3, defender rolls 18
        mock_roll.side_effect = [3, 18]
        result = self.call(CmdPummel(), self.mob.key, caller=self.char1)

        self.assertIn("misses", result)
        self.assertFalse(self.mob.has_effect("stunned"))
        # Attacker is fine — no self-penalty
        self.assertFalse(self.char1.has_effect("prone"))
        self.assertFalse(self.char1.has_effect("stunned"))

    @patch("combat.combat_handler.TICKER_HANDLER")
    @patch("utils.dice_roller.DiceRoller.roll")
    def test_pummel_sets_cooldown(self, mock_roll, mock_ticker):
        """Pummel sets the correct cooldown on the handler."""
        self._set_pummel_mastery(self.char1, MasteryLevel.BASIC)
        enter_combat(self.char1, self.mob)

        mock_roll.side_effect = [18, 5]
        self.call(CmdPummel(), self.mob.key, caller=self.char1)

        handler = self.char1.scripts.get("combat_handler")[0]
        self.assertEqual(handler.pummel_cooldown, PUMMEL_COOLDOWNS[MasteryLevel.BASIC])

    @patch("combat.combat_handler.TICKER_HANDLER")
    @patch("utils.dice_roller.DiceRoller.roll")
    def test_cooldown_blocks_reuse(self, mock_roll, mock_ticker):
        """Can't pummel again while on cooldown."""
        self._set_pummel_mastery(self.char1, MasteryLevel.BASIC)
        enter_combat(self.char1, self.mob)

        # First pummel succeeds
        mock_roll.side_effect = [18, 5]
        self.call(CmdPummel(), self.mob.key, caller=self.char1)

        # Clear stunned so we can try again
        self.mob.remove_named_effect("stunned")

        # Second pummel should be blocked by cooldown
        result = self.call(CmdPummel(), self.mob.key, caller=self.char1)
        self.assertIn("cooldown", result)

    @patch("combat.combat_handler.TICKER_HANDLER")
    @patch("utils.dice_roller.DiceRoller.roll")
    def test_mastery_cooldown_scaling(self, mock_roll, mock_ticker):
        """Higher mastery gives shorter cooldowns."""
        for mastery, expected_cooldown in PUMMEL_COOLDOWNS.items():
            # Reset combat state
            for char in (self.char1, self.mob):
                handlers = char.scripts.get("combat_handler")
                if handlers:
                    for h in handlers:
                        h.stop()
                        h.delete()

            self._set_pummel_mastery(self.char1, mastery)
            enter_combat(self.char1, self.mob)

            mock_roll.side_effect = [18, 5]
            self.call(CmdPummel(), self.mob.key, caller=self.char1)

            handler = self.char1.scripts.get("combat_handler")[0]
            self.assertEqual(
                handler.pummel_cooldown, expected_cooldown,
                f"Mastery {mastery.name}: expected cooldown {expected_cooldown}, "
                f"got {handler.pummel_cooldown}",
            )
            # Clear stunned for next iteration
            self.mob.remove_named_effect("stunned")

    @patch("combat.combat_handler.TICKER_HANDLER")
    @patch("utils.dice_roller.DiceRoller.roll")
    def test_no_args_defaults_to_current_target(self, mock_roll, mock_ticker):
        """Pummel with no args in combat defaults to current attack target."""
        self._set_pummel_mastery(self.char1, MasteryLevel.BASIC)
        enter_combat(self.char1, self.mob)

        # Queue an attack action on char1's handler so it has a target
        handler = self.char1.scripts.get("combat_handler")[0]
        handler.queue_action({
            "key": "attack",
            "target": self.mob,
            "dt": 4,
            "repeat": True,
        })

        mock_roll.side_effect = [18, 5]
        result = self.call(CmdPummel(), "", caller=self.char1)

        self.assertIn("*PUMMEL*", result)
        self.assertTrue(self.mob.has_effect("stunned"))

    @patch("combat.combat_handler.TICKER_HANDLER")
    @patch("utils.dice_roller.DiceRoller.roll")
    def test_pummel_opener_starts_combat(self, mock_roll, mock_ticker):
        """Pummel <target> from out of combat starts combat and pummels."""
        self._set_pummel_mastery(self.char1, MasteryLevel.BASIC)

        mock_roll.side_effect = [18, 5]
        result = self.call(CmdPummel(), self.mob.key, caller=self.char1)

        # Should have entered combat
        self.assertTrue(bool(self.char1.scripts.get("combat_handler")))
        # Should have pummeled
        self.assertIn("*PUMMEL*", result)
        self.assertTrue(self.mob.has_effect("stunned"))

    def test_combat_not_allowed_in_room(self):
        """Pummel blocked in no-combat rooms."""
        self._set_pummel_mastery(self.char1, MasteryLevel.BASIC)
        self.room1.allow_combat = False
        result = self.call(CmdPummel(), self.char2.key, caller=self.char1)
        self.assertIn("not allowed", result)
