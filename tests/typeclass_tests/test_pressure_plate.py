"""
Tests for PressurePlateRoom — room with pressure plate trap.

evennia test --settings settings tests.typeclass_tests.test_pressure_plate
"""

from unittest.mock import patch, MagicMock

from evennia.utils.test_resources import EvenniaTest
from evennia.utils import create

from enums.mastery_level import MasteryLevel
from enums.skills_enum import skills


WALLET_A = "0xAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"


class TestPressurePlate(EvenniaTest):

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)

    def _make_plate_room(self, damage_dice="3d6", damage_type="fire",
                         find_dc=15, disarm_dc=15):
        room = create.create_object(
            "typeclasses.terrain.rooms.room_pressure_plate.PressurePlateRoom",
            key="narrow passage",
            nohome=True,
        )
        room.is_trapped = True
        room.trap_armed = True
        room.trap_damage_dice = damage_dice
        room.trap_damage_type = damage_type
        room.trap_find_dc = find_dc
        room.trap_disarm_dc = disarm_dc
        room.trap_description = "a pressure plate"
        return room

    # ── Entry triggers freeze ──

    def test_entering_freezes_victim(self):
        plate_room = self._make_plate_room()
        self.char1.db.hp = 50
        plate_room.at_object_receive(self.char1, self.room1)
        self.assertEqual(plate_room.pressure_plate_victim, self.char1)

    def test_second_character_not_frozen(self):
        plate_room = self._make_plate_room()
        plate_room.at_object_receive(self.char1, self.room1)
        plate_room.at_object_receive(self.char2, self.room1)
        # Only first character is frozen
        self.assertEqual(plate_room.pressure_plate_victim, self.char1)

    def test_unarmed_plate_no_freeze(self):
        plate_room = self._make_plate_room()
        plate_room.trap_armed = False
        plate_room.at_object_receive(self.char1, self.room1)
        self.assertIsNone(plate_room.pressure_plate_victim)

    def test_not_trapped_no_freeze(self):
        plate_room = self._make_plate_room()
        plate_room.is_trapped = False
        plate_room.at_object_receive(self.char1, self.room1)
        self.assertIsNone(plate_room.pressure_plate_victim)

    # ── Leave triggers explosion ──

    def test_leave_while_frozen_triggers_explosion(self):
        plate_room = self._make_plate_room()
        self.char1.db.hp = 50
        self.char1.move_to(plate_room, quiet=True)
        # at_object_receive freezes char1 (sets pressure_plate_victim)
        with patch("utils.dice_roller.DiceRoller.roll", return_value=8):
            allowed, msg = plate_room.check_pre_leave(self.char1, self.room1)
        self.assertFalse(allowed)
        self.assertLess(self.char1.db.hp, 50)

    def test_leave_while_frozen_disarms_plate(self):
        plate_room = self._make_plate_room()
        self.char1.db.hp = 50
        self.char1.move_to(plate_room, quiet=True)
        with patch("utils.dice_roller.DiceRoller.roll", return_value=1):
            plate_room.check_pre_leave(self.char1, self.room1)
        self.assertFalse(plate_room.trap_armed)
        self.assertIsNone(plate_room.pressure_plate_victim)

    def test_leave_after_disarm_allowed(self):
        plate_room = self._make_plate_room()
        plate_room.trap_armed = False
        plate_room.pressure_plate_victim = None
        allowed, msg = plate_room.check_pre_leave(self.char1, self.room1)
        self.assertTrue(allowed)

    def test_non_victim_can_leave(self):
        plate_room = self._make_plate_room()
        plate_room.pressure_plate_victim = self.char1
        allowed, msg = plate_room.check_pre_leave(self.char2, self.room1)
        self.assertTrue(allowed)

    def test_explosion_damages_all_occupants(self):
        plate_room = self._make_plate_room()
        self.char1.db.hp = 50
        self.char2.db.hp = 50
        # Both characters enter the plate room
        self.char1.move_to(plate_room, quiet=True)
        self.char2.move_to(plate_room, quiet=True)
        # char1 is frozen (first to enter via at_object_receive)
        with patch("utils.dice_roller.DiceRoller.roll", return_value=6):
            plate_room.check_pre_leave(self.char1, self.room1)
        self.assertLess(self.char1.db.hp, 50)
        self.assertLess(self.char2.db.hp, 50)

    # ── Disarm unfreezes ──

    def test_disarm_unfreezes_victim(self):
        plate_room = self._make_plate_room()
        plate_room.trap_detected = True
        plate_room.pressure_plate_victim = self.char1
        self.char1.msg = MagicMock()

        self._give_subterfuge(self.char2)
        with patch("utils.dice_roller.DiceRoller.roll", return_value=20):
            success, msg = plate_room.disarm_trap(self.char2)
        self.assertTrue(success)
        self.assertIsNone(plate_room.pressure_plate_victim)
        # Victim gets unfreeze message
        self.char1.msg.assert_called()
        unfreeze_msg = self.char1.msg.call_args[0][0]
        self.assertIn("move freely", unfreeze_msg.lower())

    # ── Reset timer ──

    def test_reset_re_arms_plate(self):
        plate_room = self._make_plate_room()
        plate_room.trap_reset_seconds = 300
        self.char1.db.hp = 50
        self.char1.move_to(plate_room, quiet=True)
        with patch("utils.dice_roller.DiceRoller.roll", return_value=1):
            plate_room.check_pre_leave(self.char1, self.room1)
        # Reset timer should be started
        timer_scripts = plate_room.scripts.get("trap_reset_timer")
        self.assertTrue(len(timer_scripts) > 0)

    def _give_subterfuge(self, char, mastery=MasteryLevel.SKILLED):
        char.db.class_skill_mastery_levels = {
            skills.SUBTERFUGE.value: {
                "mastery": mastery.value,
                "classes": ["Thief"],
            },
        }
