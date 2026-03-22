"""
Tests for TripwireExit — exit with hidden tripwire trap.

evennia test --settings settings tests.typeclass_tests.test_tripwire_exit
"""

from unittest.mock import patch

from evennia.utils.test_resources import EvenniaTest
from evennia.utils import create


WALLET_A = "0xAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"


class TestTripwireExit(EvenniaTest):

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)

    def _make_tripwire(self, damage_dice="2d6", damage_type="piercing"):
        exit_obj = create.create_object(
            "typeclasses.terrain.exits.exit_tripwire.TripwireExit",
            key="north",
            location=self.room1,
            destination=self.room2,
            nohome=True,
        )
        exit_obj.is_trapped = True
        exit_obj.trap_armed = True
        exit_obj.trap_damage_dice = damage_dice
        exit_obj.trap_damage_type = damage_type
        exit_obj.trap_description = "a tripwire"
        return exit_obj

    # ── Traverse triggering ──

    def test_undetected_tripwire_triggers_and_blocks(self):
        tripwire = self._make_tripwire()
        self.char1.db.hp = 50
        with patch("utils.dice_roller.DiceRoller.roll", return_value=6):
            tripwire.at_traverse(self.char1, self.room2)
        # Damage dealt
        self.assertLess(self.char1.db.hp, 50)
        # Movement blocked — still in room1
        self.assertEqual(self.char1.location, self.room1)

    def test_detected_tripwire_safe_traverse(self):
        tripwire = self._make_tripwire()
        tripwire.trap_detected = True
        hp_before = self.char1.db.hp
        tripwire.at_traverse(self.char1, self.room2)
        # No damage
        self.assertEqual(self.char1.db.hp, hp_before)
        # Movement allowed
        self.assertEqual(self.char1.location, self.room2)

    def test_disarmed_tripwire_normal_traverse(self):
        tripwire = self._make_tripwire()
        tripwire.trap_armed = False
        hp_before = self.char1.db.hp
        tripwire.at_traverse(self.char1, self.room2)
        self.assertEqual(self.char1.db.hp, hp_before)
        self.assertEqual(self.char1.location, self.room2)

    def test_not_trapped_normal_traverse(self):
        tripwire = self._make_tripwire()
        tripwire.is_trapped = False
        tripwire.at_traverse(self.char1, self.room2)
        self.assertEqual(self.char1.location, self.room2)

    def test_tripwire_one_shot_disarms_after_trigger(self):
        tripwire = self._make_tripwire()
        tripwire.trap_one_shot = True
        with patch("utils.dice_roller.DiceRoller.roll", return_value=1):
            tripwire.at_traverse(self.char1, self.room2)
        self.assertFalse(tripwire.trap_armed)

    # ── Display ──

    def test_display_shows_tripwire_when_detected(self):
        tripwire = self._make_tripwire()
        tripwire.trap_detected = True
        name = tripwire.get_display_name(looker=self.char1)
        self.assertIn("tripwire", name.lower())

    def test_display_hides_tripwire_when_undetected(self):
        tripwire = self._make_tripwire()
        name = tripwire.get_display_name(looker=self.char1)
        self.assertNotIn("tripwire", name.lower())
