"""
Tests for the protect command (PROTECT skill — intercept attacks for allies).

evennia test --settings settings tests.command_tests.test_cmd_protect
"""

from unittest.mock import patch

from evennia.utils.test_resources import EvenniaCommandTest
from evennia.utils import create

from commands.class_skill_cmdsets.class_skill_cmds.cmd_protect import CmdProtect
from combat.combat_utils import enter_combat, execute_attack, INTERCEPT_CHANCE
from enums.mastery_level import MasteryLevel
from enums.skills_enum import skills


class _ProtectTestBase(EvenniaCommandTest):
    """Shared setUp/tearDown for protect tests."""

    character_typeclass = "typeclasses.actors.character.FCMCharacter"
    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.room1.allow_combat = True
        self.char1.hp = 50
        self.char1.hp_max = 50
        self.char2.hp = 50
        self.char2.hp_max = 50

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


class TestProtectGates(_ProtectTestBase):
    """Test protect command gate checks."""

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
        """Unskilled characters can't protect."""
        self._set_mastery(self.char1, MasteryLevel.UNSKILLED)
        result = self.call(CmdProtect(), self.char2.key)
        self.assertIn("need training", result)

    def test_not_in_combat(self):
        """Can't protect outside of combat."""
        self._set_mastery(self.char1, MasteryLevel.BASIC)
        result = self.call(CmdProtect(), self.char2.key)
        self.assertIn("must be in combat", result)

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_protect_self_blocked(self, mock_ticker):
        """Can't protect yourself."""
        self._set_mastery(self.char1, MasteryLevel.BASIC)
        enter_combat(self.char1, self.mob)
        result = self.call(CmdProtect(), self.char1.key)
        self.assertIn("can't protect yourself", result)

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_no_args_not_protecting(self, mock_ticker):
        """Protect with no args when not protecting → error."""
        self._set_mastery(self.char1, MasteryLevel.BASIC)
        enter_combat(self.char1, self.mob)
        result = self.call(CmdProtect(), "")
        self.assertIn("aren't protecting anyone", result)

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_protect_enemy_blocked(self, mock_ticker):
        """Can't protect an enemy mob."""
        self._set_mastery(self.char1, MasteryLevel.BASIC)
        enter_combat(self.char1, self.mob)
        result = self.call(CmdProtect(), self.mob.key)
        self.assertIn("not an ally", result)

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_protect_dead_target(self, mock_ticker):
        """Can't protect a dead ally."""
        self._set_mastery(self.char1, MasteryLevel.BASIC)
        enter_combat(self.char1, self.mob)
        self.char2.hp = 0
        result = self.call(CmdProtect(), self.char2.key)
        self.assertIn("already dead", result)


# ================================================================== #
#  Toggle Tests
# ================================================================== #


class TestProtectToggle(_ProtectTestBase):
    """Test protect toggle mechanics."""

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
    def test_activate_protection(self, mock_ticker):
        """Protect <ally> sets handler.protecting and shows chance."""
        self._set_mastery(self.char1, MasteryLevel.BASIC)
        enter_combat(self.char1, self.mob)
        enter_combat(self.char2, self.mob)
        result = self.call(CmdProtect(), self.char2.key)
        handler = self.char1.scripts.get("combat_handler")[0]
        self.assertEqual(handler.protecting, self.char2.id)
        self.assertIn("40%", result)

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_cancel_same_target(self, mock_ticker):
        """Protect same target again toggles off."""
        self._set_mastery(self.char1, MasteryLevel.BASIC)
        enter_combat(self.char1, self.mob)
        enter_combat(self.char2, self.mob)
        handler = self.char1.scripts.get("combat_handler")[0]
        handler.protecting = self.char2.id
        result = self.call(CmdProtect(), self.char2.key)
        self.assertIsNone(handler.protecting)
        self.assertIn("stop protecting", result)

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_cancel_no_args(self, mock_ticker):
        """Protect with no args cancels active protection."""
        self._set_mastery(self.char1, MasteryLevel.BASIC)
        enter_combat(self.char1, self.mob)
        enter_combat(self.char2, self.mob)
        handler = self.char1.scripts.get("combat_handler")[0]
        handler.protecting = self.char2.id
        result = self.call(CmdProtect(), "")
        self.assertIsNone(handler.protecting)
        self.assertIn("stop protecting", result)

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_switch_target(self, mock_ticker):
        """Protecting a different ally switches protection."""
        self._set_mastery(self.char1, MasteryLevel.SKILLED)
        # Create a third PC as the new protect target
        char3 = create.create_object(
            self.character_typeclass,
            key="char3",
            location=self.room1,
        )
        char3.hp = 50
        char3.hp_max = 50
        enter_combat(self.char1, self.mob)
        enter_combat(self.char2, self.mob)
        enter_combat(char3, self.mob)
        handler = self.char1.scripts.get("combat_handler")[0]
        handler.protecting = self.char2.id

        result = self.call(CmdProtect(), "char3")
        self.assertEqual(handler.protecting, char3.id)
        self.assertIn("50%", result)

        # Cleanup
        h = char3.scripts.get("combat_handler")
        if h:
            for hh in h:
                hh.stop()
                hh.delete()
        char3.delete()


# ================================================================== #
#  Intercept Tests
# ================================================================== #


class TestProtectIntercept(_ProtectTestBase):
    """Test intercept mechanics in execute_attack()."""

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

    def _setup_combat(self, mastery=MasteryLevel.GRANDMASTER):
        """Put char1 (protector) and char2 (protected) in combat with mob."""
        self._set_mastery(self.char1, mastery)
        with patch("combat.combat_handler.TICKER_HANDLER"):
            enter_combat(self.char1, self.mob)
            enter_combat(self.char2, self.mob)
        handler = self.char1.scripts.get("combat_handler")[0]
        handler.protecting = self.char2.id
        return handler

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_intercept_succeeds(self, mock_ticker):
        """When intercept roll succeeds, protector takes damage."""
        self._setup_combat(MasteryLevel.GRANDMASTER)
        char1_hp_before = self.char1.hp
        char2_hp_before = self.char2.hp

        # random.randint(1,100) returns 50 → within GM's 80% chance
        # dice rolls: d20=20 (auto-hit), damage=5
        with patch("combat.combat_utils.random.randint", return_value=50), \
             patch("utils.dice_roller.DiceRoller.roll", return_value=5), \
             patch("utils.dice_roller.DiceRoller.roll_with_advantage_or_disadvantage",
                   return_value=20):
            execute_attack(self.mob, self.char2)

        # Protector (char1) should have taken damage, char2 should be untouched
        self.assertLess(self.char1.hp, char1_hp_before)
        self.assertEqual(self.char2.hp, char2_hp_before)

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_intercept_fails(self, mock_ticker):
        """When intercept roll fails, original target takes damage."""
        self._setup_combat(MasteryLevel.BASIC)
        char1_hp_before = self.char1.hp
        char2_hp_before = self.char2.hp

        # random.randint(1,100) returns 90 → above BASIC's 40% chance
        with patch("combat.combat_utils.random.randint", return_value=90), \
             patch("utils.dice_roller.DiceRoller.roll", return_value=5), \
             patch("utils.dice_roller.DiceRoller.roll_with_advantage_or_disadvantage",
                   return_value=20):
            execute_attack(self.mob, self.char2)

        # Char2 (original target) should have taken damage, char1 untouched
        self.assertEqual(self.char1.hp, char1_hp_before)
        self.assertLess(self.char2.hp, char2_hp_before)

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_protector_takes_lethal_intercept(self, mock_ticker):
        """Protector with low HP takes the hit — target survives.

        FCMCharacter.die() resets HP to 1 (defeat/death flow), so we verify
        the protected target is untouched (protector intercepted the damage).
        """
        self._setup_combat(MasteryLevel.GRANDMASTER)
        self.char1.hp = 2  # protector at low HP
        char2_hp_before = self.char2.hp

        with patch("combat.combat_utils.random.randint", return_value=50), \
             patch("utils.dice_roller.DiceRoller.roll", return_value=50), \
             patch("utils.dice_roller.DiceRoller.roll_with_advantage_or_disadvantage",
                   return_value=20):
            execute_attack(self.mob, self.char2)

        # Protector took the hit (HP was 2, took large damage, die() fires)
        # die() resets HP to 1, so char1.hp is 1
        self.assertLessEqual(self.char1.hp, 2)
        # Original target is untouched
        self.assertEqual(self.char2.hp, char2_hp_before)

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_protector_dead_no_intercept(self, mock_ticker):
        """Dead protector can't intercept."""
        self._setup_combat(MasteryLevel.GRANDMASTER)
        self.char1.hp = 0  # protector is dead
        char2_hp_before = self.char2.hp

        with patch("utils.dice_roller.DiceRoller.roll", return_value=5), \
             patch("utils.dice_roller.DiceRoller.roll_with_advantage_or_disadvantage",
                   return_value=20):
            execute_attack(self.mob, self.char2)

        # Char2 takes damage because char1 is dead (no intercept possible)
        self.assertLess(self.char2.hp, char2_hp_before)

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_no_protection_no_intercept(self, mock_ticker):
        """Without protect active, no intercept happens."""
        self._set_mastery(self.char1, MasteryLevel.GRANDMASTER)
        with patch("combat.combat_handler.TICKER_HANDLER"):
            enter_combat(self.char1, self.mob)
            enter_combat(self.char2, self.mob)
        # NOT setting handler.protecting
        char2_hp_before = self.char2.hp

        with patch("utils.dice_roller.DiceRoller.roll", return_value=5), \
             patch("utils.dice_roller.DiceRoller.roll_with_advantage_or_disadvantage",
                   return_value=20):
            execute_attack(self.mob, self.char2)

        self.assertLess(self.char2.hp, char2_hp_before)

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_mastery_scaling(self, mock_ticker):
        """Verify intercept chances match INTERCEPT_CHANCE dict."""
        expected = {
            MasteryLevel.BASIC: 40,
            MasteryLevel.SKILLED: 50,
            MasteryLevel.EXPERT: 60,
            MasteryLevel.MASTER: 70,
            MasteryLevel.GRANDMASTER: 80,
        }
        for level, chance in expected.items():
            self.assertEqual(INTERCEPT_CHANCE[level], chance)

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_multiple_protectors(self, mock_ticker):
        """Two protectors on one target — first success wins."""
        char3 = create.create_object(
            self.character_typeclass,
            key="char3",
            location=self.room1,
        )
        char3.hp = 50
        char3.hp_max = 50
        self._set_mastery(self.char1, MasteryLevel.GRANDMASTER)
        self._set_mastery(char3, MasteryLevel.GRANDMASTER)

        with patch("combat.combat_handler.TICKER_HANDLER"):
            enter_combat(self.char1, self.mob)
            enter_combat(self.char2, self.mob)
            enter_combat(char3, self.mob)

        h1 = self.char1.scripts.get("combat_handler")[0]
        h3 = char3.scripts.get("combat_handler")[0]
        h1.protecting = self.char2.id
        h3.protecting = self.char2.id

        char2_hp_before = self.char2.hp

        # Both protectors' rolls succeed — first one found takes the hit
        with patch("combat.combat_utils.random.randint", return_value=50), \
             patch("utils.dice_roller.DiceRoller.roll", return_value=5), \
             patch("utils.dice_roller.DiceRoller.roll_with_advantage_or_disadvantage",
                   return_value=20):
            execute_attack(self.mob, self.char2)

        # Char2 should be untouched
        self.assertEqual(self.char2.hp, char2_hp_before)
        # One of the protectors took damage
        protector_took_damage = (
            self.char1.hp < 50 or char3.hp < 50
        )
        self.assertTrue(protector_took_damage)

        # Cleanup
        h = char3.scripts.get("combat_handler")
        if h:
            for hh in h:
                hh.stop()
                hh.delete()
        char3.delete()
