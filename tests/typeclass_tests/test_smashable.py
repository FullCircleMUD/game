"""
Tests for SmashableMixin — damage, resistance, vulnerability, immunity, break.

evennia test --settings settings tests.typeclass_tests.test_smashable
"""

from evennia.utils.test_resources import EvenniaTest
from evennia.utils import create

from enums.damage_type import DamageType


WALLET_A = "0xAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"


class TestSmashableChest(EvenniaTest):

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)

    def _make_chest(self, smashable=True, hp=20, locked=True, resistances=None):
        chest = create.create_object(
            "typeclasses.world_objects.chest.WorldChest",
            key="iron chest",
            location=self.room1,
            nohome=True,
        )
        chest.is_smashable = smashable
        chest.smash_hp_max = hp
        chest.smash_hp = hp
        chest.is_locked = locked
        chest.is_open = False
        if resistances:
            chest.smash_resistances = resistances
        return chest

    # ------------------------------------------------------------------ #
    #  Basic damage
    # ------------------------------------------------------------------ #

    def test_non_smashable_takes_no_damage(self):
        chest = self._make_chest(smashable=False)
        damage, broke = chest.take_smash_damage(10)
        self.assertEqual(damage, 0)
        self.assertFalse(broke)
        self.assertTrue(chest.is_locked)

    def test_smashable_takes_damage(self):
        chest = self._make_chest(hp=20)
        damage, broke = chest.take_smash_damage(5)
        self.assertEqual(damage, 5)
        self.assertFalse(broke)
        self.assertEqual(chest.smash_hp, 15)

    def test_smashable_breaks_at_zero(self):
        chest = self._make_chest(hp=10)
        damage, broke = chest.take_smash_damage(10)
        self.assertEqual(damage, 10)
        self.assertTrue(broke)
        self.assertEqual(chest.smash_hp, 0)
        self.assertTrue(chest.is_open)
        self.assertFalse(chest.is_locked)

    def test_overkill_clamps_to_zero(self):
        chest = self._make_chest(hp=5)
        damage, broke = chest.take_smash_damage(100)
        self.assertTrue(broke)
        self.assertEqual(chest.smash_hp, 0)

    def test_already_broken_takes_no_damage(self):
        chest = self._make_chest(hp=5)
        chest.take_smash_damage(5)  # break it
        damage, broke = chest.take_smash_damage(10)
        self.assertEqual(damage, 0)
        self.assertFalse(broke)

    # ------------------------------------------------------------------ #
    #  Damage types and resistance
    # ------------------------------------------------------------------ #

    def test_resistance_reduces_damage(self):
        chest = self._make_chest(hp=100, resistances={"slashing": 50})
        damage, broke = chest.take_smash_damage(20, DamageType.SLASHING)
        self.assertEqual(damage, 10)  # 50% reduction
        self.assertEqual(chest.smash_hp, 90)

    def test_immunity_blocks_all_damage(self):
        chest = self._make_chest(hp=100, resistances={"psychic": 100})
        damage, broke = chest.take_smash_damage(50, DamageType.PSYCHIC)
        self.assertEqual(damage, 0)
        self.assertFalse(broke)
        self.assertEqual(chest.smash_hp, 100)

    def test_vulnerability_amplifies_damage(self):
        chest = self._make_chest(hp=100, resistances={"slashing": -50})
        damage, broke = chest.take_smash_damage(20, DamageType.SLASHING)
        self.assertEqual(damage, 30)  # 50% MORE damage
        self.assertEqual(chest.smash_hp, 70)

    def test_unresisted_type_normal_damage(self):
        chest = self._make_chest(hp=100, resistances={"psychic": 100})
        damage, broke = chest.take_smash_damage(20, DamageType.BLUDGEONING)
        self.assertEqual(damage, 20)
        self.assertEqual(chest.smash_hp, 80)

    def test_untyped_damage_ignores_resistances(self):
        chest = self._make_chest(hp=100, resistances={"slashing": 50})
        damage, broke = chest.take_smash_damage(20)
        self.assertEqual(damage, 20)
        self.assertEqual(chest.smash_hp, 80)

    def test_minimum_damage_one(self):
        """Even with high resistance, minimum damage is 1."""
        chest = self._make_chest(hp=100, resistances={"slashing": 75})
        damage, broke = chest.take_smash_damage(1, DamageType.SLASHING)
        self.assertEqual(damage, 1)  # min 1, not 0

    # ------------------------------------------------------------------ #
    #  Break behavior
    # ------------------------------------------------------------------ #

    def test_break_unlocks_and_opens(self):
        chest = self._make_chest(hp=1, locked=True)
        chest.take_smash_damage(1)
        self.assertTrue(chest.is_open)
        self.assertFalse(chest.is_locked)

    def test_break_unlocked_chest_opens(self):
        chest = self._make_chest(hp=1, locked=False)
        chest.take_smash_damage(1)
        self.assertTrue(chest.is_open)


class TestSmashableDoor(EvenniaTest):

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)

    def _make_door(self, smashable=True, hp=20, locked=True, resistances=None):
        door = create.create_object(
            "typeclasses.terrain.exits.exit_door.ExitDoor",
            key="oak door",
            location=self.room1,
            destination=self.room2,
            nohome=True,
        )
        door.is_smashable = smashable
        door.smash_hp_max = hp
        door.smash_hp = hp
        door.is_locked = locked
        door.is_open = False
        if resistances:
            door.smash_resistances = resistances
        return door

    def test_smash_door_open(self):
        door = self._make_door(hp=10, locked=True)
        damage, broke = door.take_smash_damage(10)
        self.assertTrue(broke)
        self.assertTrue(door.is_open)
        self.assertFalse(door.is_locked)

    def test_smashed_door_allows_traverse(self):
        door = self._make_door(hp=1, locked=True)
        door.take_smash_damage(1)
        door.at_traverse(self.char1, self.room2)
        self.assertEqual(self.char1.location, self.room2)

    def test_door_resistance(self):
        door = self._make_door(hp=100, resistances={"fire": 75})
        damage, broke = door.take_smash_damage(20, DamageType.FIRE)
        self.assertEqual(damage, 5)
        self.assertEqual(door.smash_hp, 95)
