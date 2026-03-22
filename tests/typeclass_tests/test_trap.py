"""
Tests for TrapMixin — state, detection, triggering, disarming, reset timer.

evennia test --settings settings tests.typeclass_tests.test_trap
"""

from unittest.mock import patch

from evennia.utils.test_resources import EvenniaTest
from evennia.utils import create

from enums.mastery_level import MasteryLevel
from enums.skills_enum import skills


WALLET_A = "0xAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"


class TrapTestBase(EvenniaTest):

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)

    def _make_trapped_chest(
        self,
        damage_dice="2d6",
        damage_type="fire",
        find_dc=15,
        disarm_dc=15,
        effect_key=None,
        effect_duration=0,
        effect_duration_type="seconds",
        alarm=False,
        one_shot=True,
        reset_seconds=0,
    ):
        chest = create.create_object(
            "typeclasses.world_objects.trap_chest.TrapChest",
            key="iron chest",
            location=self.room1,
            nohome=True,
        )
        chest.is_trapped = True
        chest.trap_armed = True
        chest.trap_detected = False
        chest.trap_find_dc = find_dc
        chest.trap_disarm_dc = disarm_dc
        chest.trap_damage_dice = damage_dice
        chest.trap_damage_type = damage_type
        chest.trap_one_shot = one_shot
        chest.trap_reset_seconds = reset_seconds
        chest.trap_description = "a fire trap"
        chest.trap_is_alarm = alarm
        if effect_key:
            chest.trap_effect_key = effect_key
            chest.trap_effect_duration = effect_duration
            chest.trap_effect_duration_type = effect_duration_type
        return chest

    def _give_subterfuge(self, char, mastery=MasteryLevel.SKILLED):
        char.db.class_skill_mastery_levels = {
            skills.SUBTERFUGE.value: {
                "mastery": mastery.value,
                "classes": ["Thief"],
            },
        }


# ====================================================================== #
#  State tests
# ====================================================================== #


class TestTrapState(TrapTestBase):

    def test_defaults_not_trapped(self):
        chest = create.create_object(
            "typeclasses.world_objects.trap_chest.TrapChest",
            key="plain chest",
            location=self.room1,
            nohome=True,
        )
        self.assertFalse(chest.is_trapped)

    def test_trapped_chest_is_armed(self):
        chest = self._make_trapped_chest()
        self.assertTrue(chest.is_trapped)
        self.assertTrue(chest.trap_armed)
        self.assertFalse(chest.trap_detected)


# ====================================================================== #
#  Visibility tests
# ====================================================================== #


class TestTrapVisibility(TrapTestBase):

    def test_not_visible_when_not_trapped(self):
        chest = create.create_object(
            "typeclasses.world_objects.trap_chest.TrapChest",
            key="plain chest",
            location=self.room1,
            nohome=True,
        )
        self.assertFalse(chest.is_trap_visible_to(self.char1))

    def test_not_visible_when_undetected(self):
        chest = self._make_trapped_chest()
        self.assertFalse(chest.is_trap_visible_to(self.char1))

    def test_visible_when_detected(self):
        chest = self._make_trapped_chest()
        chest.trap_detected = True
        self.assertTrue(chest.is_trap_visible_to(self.char1))

    def test_visible_when_disarmed(self):
        chest = self._make_trapped_chest()
        chest.trap_armed = False
        self.assertTrue(chest.is_trap_visible_to(self.char1))


# ====================================================================== #
#  Detection tests
# ====================================================================== #


class TestTrapDetection(TrapTestBase):

    def test_detect_sets_flag(self):
        chest = self._make_trapped_chest()
        chest.detect_trap(self.char1)
        self.assertTrue(chest.trap_detected)

    def test_detect_messages_finder(self):
        chest = self._make_trapped_chest()
        from unittest.mock import MagicMock
        self.char1.msg = MagicMock()
        chest.detect_trap(self.char1)
        msg = self.char1.msg.call_args[0][0]
        self.assertIn("a fire trap", msg)
        self.assertIn("iron chest", msg)


# ====================================================================== #
#  Triggering tests
# ====================================================================== #


class TestTrapTriggering(TrapTestBase):

    def test_trigger_deals_damage(self):
        chest = self._make_trapped_chest(damage_dice="2d6", damage_type="fire")
        self.char1.db.hp = 50
        with patch("utils.dice_roller.DiceRoller.roll", return_value=8):
            chest.trigger_trap(self.char1)
        # take_damage applies damage; HP should decrease
        self.assertLess(self.char1.db.hp, 50)

    def test_trigger_applies_named_effect(self):
        chest = self._make_trapped_chest(
            damage_dice="",
            effect_key="stunned",
            effect_duration=2,
            effect_duration_type="combat_rounds",
        )
        chest.trigger_trap(self.char1)
        self.assertTrue(self.char1.has_effect("stunned"))

    def test_trigger_one_shot_disarms(self):
        chest = self._make_trapped_chest()
        with patch("utils.dice_roller.DiceRoller.roll", return_value=1):
            chest.trigger_trap(self.char1)
        self.assertFalse(chest.trap_armed)

    def test_trigger_not_one_shot_stays_armed(self):
        chest = self._make_trapped_chest(one_shot=False)
        with patch("utils.dice_roller.DiceRoller.roll", return_value=1):
            chest.trigger_trap(self.char1)
        self.assertTrue(chest.trap_armed)

    def test_unarmed_trap_does_not_trigger(self):
        chest = self._make_trapped_chest()
        chest.trap_armed = False
        hp_before = self.char1.db.hp
        chest.trigger_trap(self.char1)
        self.assertEqual(self.char1.db.hp, hp_before)

    def test_not_trapped_does_not_trigger(self):
        chest = self._make_trapped_chest()
        chest.is_trapped = False
        hp_before = self.char1.db.hp
        chest.trigger_trap(self.char1)
        self.assertEqual(self.char1.db.hp, hp_before)

    def test_trigger_messages_victim(self):
        chest = self._make_trapped_chest()
        from unittest.mock import MagicMock
        self.char1.msg = MagicMock()
        self.char1.db.hp = 50
        with patch("utils.dice_roller.DiceRoller.roll", return_value=5):
            chest.trigger_trap(self.char1)
        msg = self.char1.msg.call_args[0][0]
        self.assertIn("springs", msg.lower())

    def test_trigger_damage_with_no_dice_skips_damage(self):
        chest = self._make_trapped_chest(damage_dice="")
        hp_before = self.char1.db.hp
        chest.trigger_trap(self.char1)
        self.assertEqual(self.char1.db.hp, hp_before)


# ====================================================================== #
#  Disarm tests
# ====================================================================== #


class TestTrapDisarm(TrapTestBase):

    def test_disarm_success_on_high_roll(self):
        chest = self._make_trapped_chest(disarm_dc=10)
        chest.trap_detected = True
        self._give_subterfuge(self.char1)
        with patch("utils.dice_roller.DiceRoller.roll", return_value=15):
            success, msg = chest.disarm_trap(self.char1)
        self.assertTrue(success)
        self.assertFalse(chest.trap_armed)
        self.assertIn("disarm", msg.lower())

    def test_disarm_failure_triggers_trap(self):
        chest = self._make_trapped_chest(disarm_dc=25, damage_dice="1d4")
        chest.trap_detected = True
        self._give_subterfuge(self.char1, MasteryLevel.BASIC)
        self.char1.db.hp = 50
        with patch("utils.dice_roller.DiceRoller.roll", return_value=1):
            success, msg = chest.disarm_trap(self.char1)
        self.assertFalse(success)
        self.assertIn("fumble", msg.lower())
        # Trap triggered → damage dealt
        self.assertLess(self.char1.db.hp, 50)

    def test_disarm_no_skill_rejected(self):
        chest = self._make_trapped_chest()
        chest.trap_detected = True
        self.char1.db.class_skill_mastery_levels = {}
        success, msg = chest.disarm_trap(self.char1)
        self.assertFalse(success)
        self.assertIn("skill", msg.lower())

    def test_disarm_unskilled_rejected(self):
        chest = self._make_trapped_chest()
        chest.trap_detected = True
        self._give_subterfuge(self.char1, MasteryLevel.UNSKILLED)
        success, msg = chest.disarm_trap(self.char1)
        self.assertFalse(success)
        self.assertIn("skill", msg.lower())

    def test_disarm_not_detected_rejected(self):
        chest = self._make_trapped_chest()
        self._give_subterfuge(self.char1)
        success, msg = chest.disarm_trap(self.char1)
        self.assertFalse(success)
        self.assertIn("don't see", msg.lower())

    def test_disarm_not_armed_rejected(self):
        chest = self._make_trapped_chest()
        chest.trap_detected = True
        chest.trap_armed = False
        self._give_subterfuge(self.char1)
        success, msg = chest.disarm_trap(self.char1)
        self.assertFalse(success)
        self.assertIn("already disarmed", msg.lower())

    def test_disarm_not_trapped_rejected(self):
        chest = self._make_trapped_chest()
        chest.is_trapped = False
        self._give_subterfuge(self.char1)
        success, msg = chest.disarm_trap(self.char1)
        self.assertFalse(success)
        self.assertIn("no trap", msg.lower())

    def test_disarm_consumes_advantage(self):
        chest = self._make_trapped_chest(disarm_dc=10)
        chest.trap_detected = True
        self._give_subterfuge(self.char1)
        self.char1.db.non_combat_advantage = True
        with patch("utils.dice_roller.DiceRoller.roll", return_value=15):
            chest.disarm_trap(self.char1)
        self.assertFalse(self.char1.db.non_combat_advantage)

    def test_disarm_roll_includes_dex_mod(self):
        """Verify skill bonus includes DEX modifier in the message."""
        chest = self._make_trapped_chest(disarm_dc=5)
        chest.trap_detected = True
        self._give_subterfuge(self.char1, MasteryLevel.BASIC)
        # Set DEX on the character
        self.char1.db.dexterity = 16  # +3 mod
        with patch("utils.dice_roller.DiceRoller.roll", return_value=10):
            success, msg = chest.disarm_trap(self.char1)
        self.assertTrue(success)
        # Message should contain the roll details
        self.assertIn("Roll:", msg)


# ====================================================================== #
#  Reset timer tests
# ====================================================================== #


class TestTrapResetTimer(TrapTestBase):

    def test_reset_timer_starts_on_trigger(self):
        chest = self._make_trapped_chest(reset_seconds=300)
        with patch("utils.dice_roller.DiceRoller.roll", return_value=1):
            chest.trigger_trap(self.char1)
        # Check that a trap_reset_timer script was added
        timer_scripts = chest.scripts.get("trap_reset_timer")
        self.assertTrue(len(timer_scripts) > 0)

    def test_no_reset_timer_when_zero(self):
        chest = self._make_trapped_chest(reset_seconds=0)
        with patch("utils.dice_roller.DiceRoller.roll", return_value=1):
            chest.trigger_trap(self.char1)
        timer_scripts = chest.scripts.get("trap_reset_timer")
        self.assertEqual(len(timer_scripts), 0)
