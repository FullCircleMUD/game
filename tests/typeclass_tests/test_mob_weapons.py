"""
Tests for MobWeapon classes and spawn_mob_item().

Verifies:
    - MobWeapon mastery mechanics match NFT weapon equivalents
    - spawn_mob_item() creates correct mob weapon from prototype
    - spawn_mob_item() handles missing/invalid prototypes gracefully
    - MobWeapon has no durability (reduce_durability is no-op)
    - MobWeapon isinstance checks work with WeaponMechanicsMixin

evennia test --settings settings tests.typeclass_tests.test_mob_weapons
"""

from evennia.utils.test_resources import EvenniaTest
from evennia.utils import create

from enums.mastery_level import MasteryLevel
from typeclasses.items.mob_items.mob_item import MobItem
from typeclasses.items.weapons.weapon_mechanics_mixin import WeaponMechanicsMixin


def _set_mastery(char, weapon_key, level_int):
    """Set char's weapon mastery to the given integer level."""
    levels = char.db.weapon_skill_mastery_levels or {}
    levels[weapon_key] = level_int
    char.db.weapon_skill_mastery_levels = levels


class TestMobDaggerMasteryParity(EvenniaTest):
    """Verify MobDagger has identical mastery mechanics to DaggerNFTItem."""

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.nft_dagger = create.create_object(
            "typeclasses.items.weapons.dagger_nft_item.DaggerNFTItem",
            key="NFT Dagger",
            nohome=True,
        )
        self.mob_dagger = create.create_object(
            "typeclasses.items.mob_items.mob_weapons.MobDagger",
            key="Mob Dagger",
            nohome=True,
        )

    def test_weapon_type_key_matches(self):
        self.assertEqual(self.nft_dagger.weapon_type_key, self.mob_dagger.weapon_type_key)
        self.assertEqual(self.mob_dagger.weapon_type_key, "dagger")

    def test_is_finesse_matches(self):
        self.assertEqual(self.nft_dagger.is_finesse, self.mob_dagger.is_finesse)
        self.assertTrue(self.mob_dagger.is_finesse)

    def test_can_dual_wield_matches(self):
        self.assertEqual(self.nft_dagger.can_dual_wield, self.mob_dagger.can_dual_wield)
        self.assertTrue(self.mob_dagger.can_dual_wield)

    def test_extra_attacks_match_all_levels(self):
        """Extra attacks should be identical at every mastery level."""
        for level in range(6):
            _set_mastery(self.char1, "dagger", level)
            nft_val = self.nft_dagger.get_extra_attacks(self.char1)
            mob_val = self.mob_dagger.get_extra_attacks(self.char1)
            self.assertEqual(nft_val, mob_val, f"Mismatch at mastery {level}")

    def test_crit_modifier_match_all_levels(self):
        """Crit threshold modifier should be identical at every mastery level."""
        for level in range(6):
            _set_mastery(self.char1, "dagger", level)
            nft_val = self.nft_dagger.get_mastery_crit_threshold_modifier(self.char1)
            mob_val = self.mob_dagger.get_mastery_crit_threshold_modifier(self.char1)
            self.assertEqual(nft_val, mob_val, f"Mismatch at mastery {level}")

    def test_offhand_attacks_match_all_levels(self):
        """Off-hand attacks should be identical at every mastery level."""
        for level in range(6):
            _set_mastery(self.char1, "dagger", level)
            nft_val = self.nft_dagger.get_offhand_attacks(self.char1)
            mob_val = self.mob_dagger.get_offhand_attacks(self.char1)
            self.assertEqual(nft_val, mob_val, f"Mismatch at mastery {level}")

    def test_parries_zero_all_levels(self):
        """Daggers should have 0 parries at all levels (both NFT and mob)."""
        for level in range(6):
            _set_mastery(self.char1, "dagger", level)
            self.assertEqual(self.mob_dagger.get_parries_per_round(self.char1), 0)


class TestMobLongswordMasteryParity(EvenniaTest):
    """Verify MobLongsword has identical mastery mechanics to LongswordNFTItem."""

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.nft_sword = create.create_object(
            "typeclasses.items.weapons.longsword_nft_item.LongswordNFTItem",
            key="NFT Longsword",
            nohome=True,
        )
        self.mob_sword = create.create_object(
            "typeclasses.items.mob_items.mob_weapons.MobLongsword",
            key="Mob Longsword",
            nohome=True,
        )

    def test_weapon_type_key_matches(self):
        self.assertEqual(self.nft_sword.weapon_type_key, self.mob_sword.weapon_type_key)

    def test_parries_match_all_levels(self):
        for level in range(6):
            _set_mastery(self.char1, "long_sword", level)
            nft_val = self.nft_sword.get_parries_per_round(self.char1)
            mob_val = self.mob_sword.get_parries_per_round(self.char1)
            self.assertEqual(nft_val, mob_val, f"Mismatch at mastery {level}")

    def test_extra_attacks_match_all_levels(self):
        for level in range(6):
            _set_mastery(self.char1, "long_sword", level)
            nft_val = self.nft_sword.get_extra_attacks(self.char1)
            mob_val = self.mob_sword.get_extra_attacks(self.char1)
            self.assertEqual(nft_val, mob_val, f"Mismatch at mastery {level}")

    def test_hit_bonus_match_all_levels(self):
        for level in range(6):
            _set_mastery(self.char1, "long_sword", level)
            nft_val = self.nft_sword.get_mastery_hit_bonus(self.char1)
            mob_val = self.mob_sword.get_mastery_hit_bonus(self.char1)
            self.assertEqual(nft_val, mob_val, f"Mismatch at mastery {level}")

    def test_parry_advantage_match_all_levels(self):
        for level in range(6):
            _set_mastery(self.char1, "long_sword", level)
            nft_val = self.nft_sword.get_parry_advantage(self.char1)
            mob_val = self.mob_sword.get_parry_advantage(self.char1)
            self.assertEqual(nft_val, mob_val, f"Mismatch at mastery {level}")


class TestMobWeaponProperties(EvenniaTest):
    """Test MobWeapon base class properties."""

    def create_script(self):
        pass

    def test_mob_weapon_is_weapon_mechanics_mixin(self):
        weapon = create.create_object(
            "typeclasses.items.mob_items.mob_weapons.MobDagger",
            key="test dagger",
            nohome=True,
        )
        self.assertIsInstance(weapon, WeaponMechanicsMixin)

    def test_mob_weapon_is_mob_item(self):
        weapon = create.create_object(
            "typeclasses.items.mob_items.mob_weapons.MobDagger",
            key="test dagger",
            nohome=True,
        )
        self.assertIsInstance(weapon, MobItem)

    def test_reduce_durability_is_noop(self):
        """MobWeapons should not track durability."""
        weapon = create.create_object(
            "typeclasses.items.mob_items.mob_weapons.MobDagger",
            key="test dagger",
            nohome=True,
        )
        # Should not raise — just a no-op
        weapon.reduce_durability(1)
        weapon.reduce_durability(100)

    def test_mob_weapon_not_nft(self):
        """MobWeapon should NOT be a BaseNFTItem."""
        from typeclasses.items.base_nft_item import BaseNFTItem
        weapon = create.create_object(
            "typeclasses.items.mob_items.mob_weapons.MobDagger",
            key="test dagger",
            nohome=True,
        )
        self.assertNotIsInstance(weapon, BaseNFTItem)


class TestSpawnMobItem(EvenniaTest):
    """Test MobItem.spawn_mob_item() factory method."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def test_spawn_mob_dagger_from_prototype(self):
        """spawn_mob_item should create a MobDagger from iron_dagger prototype."""
        from typeclasses.items.mob_items.mob_weapons import MobDagger
        weapon = MobItem.spawn_mob_item("iron_dagger", location=self.room1)
        self.assertIsNotNone(weapon)
        self.assertIsInstance(weapon, MobDagger)
        self.assertEqual(weapon.location, self.room1)

    def test_spawn_mob_longsword_from_prototype(self):
        """spawn_mob_item should create a MobLongsword from iron_longsword prototype."""
        from typeclasses.items.mob_items.mob_weapons import MobLongsword
        weapon = MobItem.spawn_mob_item("iron_longsword", location=self.room1)
        self.assertIsNotNone(weapon)
        self.assertIsInstance(weapon, MobLongsword)

    def test_spawn_mob_item_applies_stats(self):
        """Spawned mob weapon should have stats from the prototype."""
        weapon = MobItem.spawn_mob_item("iron_dagger", location=self.room1)
        self.assertIsNotNone(weapon)
        self.assertEqual(weapon.key, "Iron Dagger")
        self.assertEqual(weapon.base_damage, "d4")
        self.assertEqual(weapon.material, "iron")

    def test_spawn_mob_item_no_durability(self):
        """Spawned mob weapon should not have max_durability set."""
        weapon = MobItem.spawn_mob_item("iron_dagger", location=self.room1)
        self.assertIsNotNone(weapon)
        # MobItem doesn't have max_durability — should be default (None or 0)
        self.assertFalse(getattr(weapon, "max_durability", 0))

    def test_spawn_mob_item_invalid_key_returns_none(self):
        """Invalid prototype_key should return None."""
        result = MobItem.spawn_mob_item("nonexistent_weapon_xyz")
        self.assertIsNone(result)

    def test_spawn_mob_item_no_location(self):
        """Spawning without location should work (location=None)."""
        weapon = MobItem.spawn_mob_item("iron_dagger")
        self.assertIsNotNone(weapon)
        self.assertIsNone(weapon.location)

    def test_spawn_mob_item_is_weapon_mechanics_mixin(self):
        """Spawned mob weapon should be a WeaponMechanicsMixin instance."""
        weapon = MobItem.spawn_mob_item("iron_dagger", location=self.room1)
        self.assertIsNotNone(weapon)
        self.assertIsInstance(weapon, WeaponMechanicsMixin)
