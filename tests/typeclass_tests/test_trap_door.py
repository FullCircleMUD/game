"""
Tests for TrapDoor — trapped door that triggers on open/smash.

evennia test --settings settings tests.typeclass_tests.test_trap_door
"""

from unittest.mock import patch

from evennia.utils.test_resources import EvenniaTest
from evennia.utils import create

from enums.damage_type import DamageType


WALLET_A = "0xAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"


class TestTrapDoor(EvenniaTest):

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)

    def _make_trap_door(
        self, damage_dice="2d6", damage_type="piercing", disarm_dc=15,
        locked=False, smashable=False, hp=20,
    ):
        door = create.create_object(
            "typeclasses.terrain.exits.exit_trap_door.TrapDoor",
            key="iron door",
            location=self.room1,
            destination=self.room2,
            nohome=True,
        )
        door.is_trapped = True
        door.trap_armed = True
        door.trap_damage_dice = damage_dice
        door.trap_damage_type = damage_type
        door.trap_disarm_dc = disarm_dc
        door.trap_description = "a dart trap"
        door.is_open = False
        door.is_locked = locked
        door.is_smashable = smashable
        door.smash_hp_max = hp
        door.smash_hp = hp
        return door

    # ── Open triggers trap ──

    def test_open_trapped_door_triggers(self):
        door = self._make_trap_door()
        self.char1.db.hp = 50
        with patch("utils.dice_roller.DiceRoller.roll", return_value=6):
            door.open(self.char1)
        self.assertLess(self.char1.db.hp, 50)
        self.assertTrue(door.is_open)

    def test_open_detected_door_still_triggers(self):
        """Detection doesn't prevent triggering — must disarm."""
        door = self._make_trap_door()
        door.trap_detected = True
        self.char1.db.hp = 50
        with patch("utils.dice_roller.DiceRoller.roll", return_value=6):
            door.open(self.char1)
        self.assertLess(self.char1.db.hp, 50)

    def test_open_disarmed_door_safe(self):
        door = self._make_trap_door()
        door.trap_armed = False
        hp_before = self.char1.db.hp
        door.open(self.char1)
        self.assertEqual(self.char1.db.hp, hp_before)
        self.assertTrue(door.is_open)

    def test_open_not_trapped_door_safe(self):
        door = self._make_trap_door()
        door.is_trapped = False
        hp_before = self.char1.db.hp
        door.open(self.char1)
        self.assertEqual(self.char1.db.hp, hp_before)

    # ── Smash triggers trap ──

    def test_smash_trapped_door_triggers(self):
        door = self._make_trap_door(smashable=True, hp=1)
        self.char1.db.hp = 50
        with patch("utils.dice_roller.DiceRoller.roll", return_value=5):
            door.take_smash_damage(1)
        # Trap triggered on room occupants
        self.assertLess(self.char1.db.hp, 50)
        # Door broke open
        self.assertTrue(door.is_open)

    # ── Display ──

    def test_display_shows_trapped_when_detected(self):
        door = self._make_trap_door()
        door.trap_detected = True
        name = door.get_display_name(looker=self.char1)
        self.assertIn("trapped", name.lower())

    def test_display_hides_trap_when_undetected(self):
        door = self._make_trap_door()
        name = door.get_display_name(looker=self.char1)
        self.assertNotIn("trapped", name.lower())

    def test_display_hides_trap_when_disarmed(self):
        door = self._make_trap_door()
        door.trap_detected = True
        door.trap_armed = False
        name = door.get_display_name(looker=self.char1)
        # Disarmed traps are visible but not marked "(trapped)"
        self.assertNotIn("(trapped)", name.lower())
