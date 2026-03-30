"""
Tests for the assist command (BATTLESKILLS — combat + non-combat advantage).

evennia test --settings settings tests.command_tests.test_cmd_assist
"""

from unittest.mock import patch

from evennia.utils.test_resources import EvenniaCommandTest
from evennia.utils import create

from commands.all_char_cmds.cmd_attack import CmdAttack
from commands.class_skill_cmdsets.class_skill_cmds.cmd_assist import CmdAssist, ASSIST_ROUNDS
from combat.combat_utils import enter_combat
from enums.mastery_level import MasteryLevel
from enums.skills_enum import skills


class _AssistTestBase(EvenniaCommandTest):
    """Shared setUp/tearDown for assist tests."""

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

    def _set_battleskills_mastery(self, char, level):
        if not char.db.general_skill_mastery_levels:
            char.db.general_skill_mastery_levels = {}
        char.db.general_skill_mastery_levels[skills.BATTLESKILLS.value] = level.value


# ================================================================== #
#  Gate Tests
# ================================================================== #


class TestAssistGates(_AssistTestBase):
    """Test assist command gate checks."""

    def test_no_args(self):
        """Assist with no args → error."""
        self._set_battleskills_mastery(self.char1, MasteryLevel.BASIC)
        result = self.call(CmdAssist(), "")
        self.assertIn("Assist who?", result)

    def test_assist_self_blocked(self):
        """Can't assist yourself."""
        self._set_battleskills_mastery(self.char1, MasteryLevel.BASIC)
        result = self.call(CmdAssist(), self.char1.key)
        self.assertIn("can't assist yourself", result)

    def test_unskilled_blocked(self):
        """Unskilled characters can't assist."""
        self._set_battleskills_mastery(self.char1, MasteryLevel.UNSKILLED)
        result = self.call(CmdAssist(), self.char2.key)
        self.assertIn("battle skills", result.lower())

    def test_target_not_found(self):
        """Assist a nonexistent target → standard Evennia 'not found'."""
        self._set_battleskills_mastery(self.char1, MasteryLevel.BASIC)
        result = self.call(CmdAssist(), "nobody_here")
        # Evennia search failure message
        self.assertIn("Could not find", result)


# ================================================================== #
#  Combat Tests
# ================================================================== #


class TestAssistCombat(_AssistTestBase):
    """Test assist in combat."""

    def setUp(self):
        super().setUp()
        # Non-PvP: PCs are allies, NPCs are enemies
        # Create a mob as the enemy
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
    def test_assist_sets_advantage_on_ally(self, mock_ticker):
        """Assist sets advantage on ally against all enemies."""
        self._set_battleskills_mastery(self.char1, MasteryLevel.BASIC)
        # Both chars enter combat against the mob
        enter_combat(self.char1, self.mob)
        enter_combat(self.char2, self.mob)

        # char1 assists char2
        result = self.call(CmdAssist(), self.char2.key, caller=self.char1)
        self.assertIn("assist", result.lower())

        # char2 should have advantage against the mob
        ally_handler = self.char2.scripts.get("combat_handler")[0]
        self.assertTrue(ally_handler.has_advantage(self.mob))
        self.assertEqual(
            ally_handler.advantage_against[self.mob.id],
            ASSIST_ROUNDS[MasteryLevel.BASIC],
        )

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_assist_skips_assister_attack(self, mock_ticker):
        """Assist costs the assister their next attack."""
        self._set_battleskills_mastery(self.char1, MasteryLevel.BASIC)
        enter_combat(self.char1, self.mob)
        enter_combat(self.char2, self.mob)

        self.call(CmdAssist(), self.char2.key, caller=self.char1)

        handler = self.char1.scripts.get("combat_handler")[0]
        self.assertTrue(handler.skip_next_action)

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_mastery_scaling(self, mock_ticker):
        """Higher mastery grants more rounds of advantage."""
        for mastery, expected_rounds in ASSIST_ROUNDS.items():
            # Reset combat state
            for char in (self.char1, self.char2, self.mob):
                handlers = char.scripts.get("combat_handler")
                if handlers:
                    for h in handlers:
                        h.stop()
                        h.delete()

            # Reset HP so nobody dies from combat during enter_combat
            self.char1.hp = self.char1.hp_max
            self.char2.hp = self.char2.hp_max
            self.mob.hp = self.mob.hp_max

            self._set_battleskills_mastery(self.char1, mastery)
            enter_combat(self.char1, self.mob)
            enter_combat(self.char2, self.mob)

            self.call(CmdAssist(), self.char2.key, caller=self.char1)

            ally_handler = self.char2.scripts.get("combat_handler")[0]
            self.assertEqual(
                ally_handler.advantage_against[self.mob.id],
                expected_rounds,
                f"Mastery {mastery.name}: expected {expected_rounds} rounds",
            )

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_assist_enemy_blocked(self, mock_ticker):
        """Can't assist an enemy."""
        self._set_battleskills_mastery(self.char1, MasteryLevel.BASIC)
        enter_combat(self.char1, self.mob)

        result = self.call(CmdAssist(), self.mob.key, caller=self.char1)
        self.assertIn("not an ally", result)

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_assist_target_not_in_combat(self, mock_ticker):
        """Can't assist an ally who isn't in combat."""
        self._set_battleskills_mastery(self.char1, MasteryLevel.BASIC)
        enter_combat(self.char1, self.mob)
        # char2 is NOT in combat

        result = self.call(CmdAssist(), self.char2.key, caller=self.char1)
        self.assertIn("not in combat", result)

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_assister_not_in_combat_noncombat_path(self, mock_ticker):
        """If assister is not in combat, uses non-combat path."""
        self._set_battleskills_mastery(self.char1, MasteryLevel.BASIC)
        # Neither in combat

        result = self.call(CmdAssist(), self.char2.key, caller=self.char1)
        # Should use non-combat path — sets non_combat_advantage
        self.assertIn("next task", result)
        self.assertTrue(self.char2.db.non_combat_advantage)


# ================================================================== #
#  Non-Combat Tests
# ================================================================== #


class TestAssistNonCombat(_AssistTestBase):
    """Test assist out of combat."""

    def test_noncombat_assist_sets_flag(self):
        """Out-of-combat assist sets non_combat_advantage on target."""
        self._set_battleskills_mastery(self.char1, MasteryLevel.BASIC)
        result = self.call(CmdAssist(), self.char2.key, caller=self.char1)
        self.assertIn("next task", result)
        self.assertTrue(self.char2.db.non_combat_advantage)

    def test_noncombat_assist_message(self):
        """Assist message includes target name."""
        self._set_battleskills_mastery(self.char1, MasteryLevel.EXPERT)
        result = self.call(CmdAssist(), self.char2.key, caller=self.char1)
        self.assertIn(self.char2.key, result)

    def test_noncombat_assist_target_not_here(self):
        """Can't assist someone in a different room."""
        self._set_battleskills_mastery(self.char1, MasteryLevel.BASIC)
        # Move char2 to a different room
        room2 = create.create_object(
            "typeclasses.terrain.rooms.room_base.RoomBase",
            key="another room",
        )
        self.char2.location = room2
        try:
            result = self.call(CmdAssist(), self.char2.key, caller=self.char1)
            # Should not find them (Evennia search limited to room)
            self.assertNotIn("next task", result)
        finally:
            self.char2.location = self.room1
            room2.delete()


# ================================================================== #
#  Advantage Consumption Tests
# ================================================================== #


class TestAdvantageConsumption(_AssistTestBase):
    """Test that non-combat advantage/disadvantage is consumed properly."""

    def test_advantage_consumed_on_skill_check(self):
        """Non-combat advantage is consumed after a skill check."""
        self.char1.db.non_combat_advantage = True
        self.char1.db.non_combat_disadvantage = False

        # Trigger a skill check — hide (stealth roll)
        from commands.class_skill_cmdsets.class_skill_cmds.cmd_hide import CmdHide
        self.char1.db.class_skill_mastery_levels = {
            skills.STEALTH.value: {"mastery": MasteryLevel.BASIC.value, "classes": ["Thief"]},
        }
        self.call(CmdHide(), "", caller=self.char1)

        # Advantage should be consumed
        self.assertFalse(getattr(self.char1.db, "non_combat_advantage", False))
        self.assertFalse(getattr(self.char1.db, "non_combat_disadvantage", False))

    def test_disadvantage_consumed_on_skill_check(self):
        """Non-combat disadvantage is consumed after a skill check."""
        self.char1.db.non_combat_advantage = False
        self.char1.db.non_combat_disadvantage = True

        from commands.class_skill_cmdsets.class_skill_cmds.cmd_hide import CmdHide
        self.char1.db.class_skill_mastery_levels = {
            skills.STEALTH.value: {"mastery": MasteryLevel.BASIC.value, "classes": ["Thief"]},
        }
        self.call(CmdHide(), "", caller=self.char1)

        self.assertFalse(getattr(self.char1.db, "non_combat_advantage", False))
        self.assertFalse(getattr(self.char1.db, "non_combat_disadvantage", False))

    def test_both_cancel_and_consumed(self):
        """Both advantage and disadvantage cancel and both are consumed."""
        self.char1.db.non_combat_advantage = True
        self.char1.db.non_combat_disadvantage = True

        from commands.class_skill_cmdsets.class_skill_cmds.cmd_hide import CmdHide
        self.char1.db.class_skill_mastery_levels = {
            skills.STEALTH.value: {"mastery": MasteryLevel.BASIC.value, "classes": ["Thief"]},
        }
        self.call(CmdHide(), "", caller=self.char1)

        # Both should be consumed
        self.assertFalse(getattr(self.char1.db, "non_combat_advantage", False))
        self.assertFalse(getattr(self.char1.db, "non_combat_disadvantage", False))

    @patch("utils.dice_roller.DiceRoller.roll_with_advantage_or_disadvantage")
    def test_advantage_passed_to_dice_roller(self, mock_roll):
        """Verify advantage flag is passed to dice roller."""
        mock_roll.return_value = 15
        self.char1.db.non_combat_advantage = True
        self.char1.db.non_combat_disadvantage = False

        from commands.class_skill_cmdsets.class_skill_cmds.cmd_hide import CmdHide
        self.char1.db.class_skill_mastery_levels = {
            skills.STEALTH.value: {"mastery": MasteryLevel.BASIC.value, "classes": ["Thief"]},
        }
        self.call(CmdHide(), "", caller=self.char1)

        mock_roll.assert_called_with(advantage=True, disadvantage=False)

    @patch("utils.dice_roller.DiceRoller.roll_with_advantage_or_disadvantage")
    def test_disadvantage_passed_to_dice_roller(self, mock_roll):
        """Verify disadvantage flag is passed to dice roller."""
        mock_roll.return_value = 10
        self.char1.db.non_combat_advantage = False
        self.char1.db.non_combat_disadvantage = True

        from commands.class_skill_cmdsets.class_skill_cmds.cmd_hide import CmdHide
        self.char1.db.class_skill_mastery_levels = {
            skills.STEALTH.value: {"mastery": MasteryLevel.BASIC.value, "classes": ["Thief"]},
        }
        self.call(CmdHide(), "", caller=self.char1)

        mock_roll.assert_called_with(advantage=False, disadvantage=True)
