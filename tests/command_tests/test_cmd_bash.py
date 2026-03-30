"""
Tests for the bash command (BASH skill — warrior combat maneuver).

evennia test --settings settings tests.command_tests.test_cmd_bash
"""

from unittest.mock import patch

from evennia.utils.test_resources import EvenniaCommandTest
from evennia.utils import create

from commands.class_skill_cmdsets.class_skill_cmds.cmd_bash import CmdBash, BASH_COOLDOWNS
from combat.combat_utils import enter_combat
from enums.mastery_level import MasteryLevel
from enums.skills_enum import skills


class _BashTestBase(EvenniaCommandTest):
    """Shared setUp/tearDown for bash tests."""

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

    def _set_bash_mastery(self, char, level):
        if not char.db.class_skill_mastery_levels:
            char.db.class_skill_mastery_levels = {}
        char.db.class_skill_mastery_levels[skills.BASH.value] = {"mastery": level.value, "classes": ["Warrior"]}


# ================================================================== #
#  Gate Tests
# ================================================================== #


class TestBashGates(_BashTestBase):
    """Test bash command gate checks."""

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
        """Unskilled characters can't bash."""
        self._set_bash_mastery(self.char1, MasteryLevel.UNSKILLED)
        result = self.call(CmdBash(), self.char2.key)
        self.assertIn("need training", result)

    def test_no_args_out_of_combat(self):
        """Bash with no args out of combat → funny stumble message."""
        self._set_bash_mastery(self.char1, MasteryLevel.BASIC)
        result = self.call(CmdBash(), "")
        self.assertIn("trip over", result)

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_bash_self_blocked(self, mock_ticker):
        """Can't bash yourself."""
        self._set_bash_mastery(self.char1, MasteryLevel.BASIC)
        enter_combat(self.char1, self.mob)
        result = self.call(CmdBash(), self.char1.key)
        self.assertIn("can't bash yourself", result)

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_not_in_combat_starts_combat(self, mock_ticker):
        """Bash <target> out of combat starts combat."""
        self._set_bash_mastery(self.char1, MasteryLevel.BASIC)
        # Char1 is NOT in combat — bash should start it
        with patch("combat.combat_utils.roll_initiative", return_value=10):
            with patch("utils.dice_roller.DiceRoller.roll", side_effect=[18, 5] + [10] * 50):
                result = self.call(CmdBash(), self.mob.key, caller=self.char1)
        # Char1 should now have a combat handler
        self.assertTrue(bool(self.char1.scripts.get("combat_handler")))


# ================================================================== #
#  Combat Tests
# ================================================================== #


class TestBashCombat(_BashTestBase):
    """Test bash in combat."""

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
        """Can't bash an ally (PCs are allies in non-PvP rooms)."""
        self._set_bash_mastery(self.char1, MasteryLevel.BASIC)
        enter_combat(self.char1, self.mob)
        enter_combat(self.char2, self.mob)

        result = self.call(CmdBash(), self.char2.key, caller=self.char1)
        self.assertIn("not an enemy", result)

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_target_not_in_combat(self, mock_ticker):
        """Can't bash a target that isn't in combat."""
        self._set_bash_mastery(self.char1, MasteryLevel.BASIC)
        enter_combat(self.char1, self.mob)
        # Create a second mob NOT in combat
        mob2 = create.create_object(
            "typeclasses.actors.mobs.dire_wolf.DireWolf",
            key="wolf2",
            location=self.room1,
        )
        mob2.hp = 20
        mob2.hp_max = 20

        try:
            result = self.call(CmdBash(), "wolf2", caller=self.char1)
            self.assertIn("not in combat", result)
        finally:
            mob2.delete()

    @patch("combat.combat_handler.TICKER_HANDLER")
    @patch("utils.dice_roller.DiceRoller.roll")
    def test_bash_success_knocks_prone(self, mock_roll, mock_ticker):
        """Successful bash knocks target prone."""
        self._set_bash_mastery(self.char1, MasteryLevel.BASIC)
        enter_combat(self.char1, self.mob)

        # Attacker rolls 18, defender rolls 5
        mock_roll.side_effect = [18, 5]
        result = self.call(CmdBash(), self.mob.key, caller=self.char1)

        self.assertIn("*BASH*", result)
        self.assertTrue(self.mob.has_effect("prone"))

    @patch("combat.combat_handler.TICKER_HANDLER")
    @patch("utils.dice_roller.DiceRoller.roll")
    def test_bash_success_grants_advantage(self, mock_roll, mock_ticker):
        """Successful bash grants advantage to allies against the prone target."""
        self._set_bash_mastery(self.char1, MasteryLevel.BASIC)
        enter_combat(self.char1, self.mob)
        enter_combat(self.char2, self.mob)

        # Attacker rolls 18, defender rolls 5
        mock_roll.side_effect = [18, 5]
        self.call(CmdBash(), self.mob.key, caller=self.char1)

        # Both allies should have advantage against the mob
        handler1 = self.char1.scripts.get("combat_handler")[0]
        handler2 = self.char2.scripts.get("combat_handler")[0]
        self.assertTrue(handler1.has_advantage(self.mob))
        self.assertTrue(handler2.has_advantage(self.mob))

    @patch("combat.combat_handler.TICKER_HANDLER")
    @patch("utils.dice_roller.DiceRoller.roll")
    def test_bash_failure_dex_save_pass(self, mock_roll, mock_ticker):
        """Failed bash with passed DEX save — basher stays standing."""
        self._set_bash_mastery(self.char1, MasteryLevel.BASIC)
        enter_combat(self.char1, self.mob)

        # Attacker rolls 3 (loses), defender rolls 18, DEX save rolls 15 (passes DC 10)
        mock_roll.side_effect = [3, 18, 15]
        result = self.call(CmdBash(), self.mob.key, caller=self.char1)

        self.assertIn("miss", result)
        self.assertFalse(self.char1.has_effect("prone"))

    @patch("combat.combat_handler.TICKER_HANDLER")
    @patch("utils.dice_roller.DiceRoller.roll")
    def test_bash_failure_dex_save_fail(self, mock_roll, mock_ticker):
        """Failed bash with failed DEX save — basher falls prone."""
        self._set_bash_mastery(self.char1, MasteryLevel.BASIC)
        enter_combat(self.char1, self.mob)

        # Attacker rolls 3 (loses), defender rolls 18, DEX save rolls 2 (fails DC 10)
        mock_roll.side_effect = [3, 18, 2]
        result = self.call(CmdBash(), self.mob.key, caller=self.char1)

        self.assertIn("BASH FAIL", result)
        self.assertTrue(self.char1.has_effect("prone"))

    @patch("combat.combat_handler.TICKER_HANDLER")
    @patch("utils.dice_roller.DiceRoller.roll")
    def test_bash_sets_cooldown(self, mock_roll, mock_ticker):
        """Bash sets the correct cooldown on the handler."""
        self._set_bash_mastery(self.char1, MasteryLevel.BASIC)
        enter_combat(self.char1, self.mob)

        mock_roll.side_effect = [18, 5]
        self.call(CmdBash(), self.mob.key, caller=self.char1)

        handler = self.char1.scripts.get("combat_handler")[0]
        self.assertEqual(handler.bash_cooldown, BASH_COOLDOWNS[MasteryLevel.BASIC])

    @patch("combat.combat_handler.TICKER_HANDLER")
    @patch("utils.dice_roller.DiceRoller.roll")
    def test_cooldown_blocks_reuse(self, mock_roll, mock_ticker):
        """Can't bash again while on cooldown."""
        self._set_bash_mastery(self.char1, MasteryLevel.BASIC)
        enter_combat(self.char1, self.mob)

        # First bash succeeds
        mock_roll.side_effect = [18, 5]
        self.call(CmdBash(), self.mob.key, caller=self.char1)

        # Clear prone so we can try again
        self.mob.remove_named_effect("prone")

        # Second bash should be blocked by cooldown
        result = self.call(CmdBash(), self.mob.key, caller=self.char1)
        self.assertIn("cooldown", result)

    @patch("combat.combat_handler.TICKER_HANDLER")
    @patch("utils.dice_roller.DiceRoller.roll")
    def test_mastery_cooldown_scaling(self, mock_roll, mock_ticker):
        """Higher mastery gives shorter cooldowns."""
        for mastery, expected_cooldown in BASH_COOLDOWNS.items():
            # Reset combat state and HP between iterations
            for char in (self.char1, self.mob):
                char.hp = char.hp_max
                handlers = char.scripts.get("combat_handler")
                if handlers:
                    for h in handlers:
                        h.stop()
                        h.delete()

            self._set_bash_mastery(self.char1, mastery)
            # Patch initiative so it doesn't consume from the dice mock
            with patch("combat.combat_utils.roll_initiative", return_value=10):
                mock_roll.side_effect = [10] * 50
                enter_combat(self.char1, self.mob)

                # Bash contest (20 beats 1) + generous padding
                mock_roll.side_effect = [20, 1] + [10] * 20
                self.call(CmdBash(), self.mob.key, caller=self.char1)

            handler = self.char1.scripts.get("combat_handler")[0]
            self.assertEqual(
                handler.bash_cooldown, expected_cooldown,
                f"Mastery {mastery.name}: expected cooldown {expected_cooldown}, "
                f"got {handler.bash_cooldown}",
            )
            # Clear prone for next iteration
            self.mob.remove_named_effect("prone")

    @patch("combat.combat_handler.TICKER_HANDLER")
    @patch("utils.dice_roller.DiceRoller.roll")
    def test_no_args_defaults_to_current_target(self, mock_roll, mock_ticker):
        """Bash with no args in combat defaults to current attack target."""
        self._set_bash_mastery(self.char1, MasteryLevel.BASIC)
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
        result = self.call(CmdBash(), "", caller=self.char1)

        self.assertIn("*BASH*", result)
        self.assertTrue(self.mob.has_effect("prone"))

    @patch("combat.combat_handler.TICKER_HANDLER")
    @patch("utils.dice_roller.DiceRoller.roll")
    def test_bash_opener_starts_combat(self, mock_roll, mock_ticker):
        """Bash <target> from out of combat starts combat and bashes."""
        self._set_bash_mastery(self.char1, MasteryLevel.BASIC)

        # Patch initiative so it doesn't consume from the dice mock.
        # Rolls: mob free attack (hit, damage), then bash contest (20 beats 1).
        with patch("combat.combat_utils.roll_initiative", return_value=10):
            mock_roll.side_effect = [10, 4, 20, 1] + [10] * 50
            result = self.call(CmdBash(), self.mob.key, caller=self.char1)

        # Should have entered combat
        self.assertTrue(bool(self.char1.scripts.get("combat_handler")))
        # Should have bashed
        self.assertTrue(self.mob.has_effect("prone"))

    def test_combat_not_allowed_in_room(self):
        """Bash blocked in no-combat rooms."""
        self._set_bash_mastery(self.char1, MasteryLevel.BASIC)
        self.room1.allow_combat = False
        result = self.call(CmdBash(), self.char2.key, caller=self.char1)
        self.assertIn("not allowed", result)
