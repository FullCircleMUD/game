"""
Tests for rules.damage_descriptors — percentage-based combat message verbs.

evennia test --settings settings tests.utils_tests.test_damage_descriptors
"""

from evennia.utils.test_resources import EvenniaTest

from enums.damage_type import DamageType
from rules.damage_descriptors import get_descriptor, get_miss_verb


class TestGetDescriptorSlashing(EvenniaTest):
    """Test slashing descriptor tiers."""

    def create_script(self):
        pass

    def test_lowest_tier(self):
        """0-4% damage → lowercase nick/nicks."""
        second, third = get_descriptor(DamageType.SLASHING, 1, 100)
        self.assertEqual(second, "nick")
        self.assertEqual(third, "nicks")

    def test_mid_tier(self):
        """11-20% damage → lowercase slash/slashes."""
        second, third = get_descriptor(DamageType.SLASHING, 15, 100)
        self.assertEqual(second, "slash")
        self.assertEqual(third, "slashes")

    def test_mixed_case_tier(self):
        """36-50% → Title case Rend/Rends."""
        second, third = get_descriptor(DamageType.SLASHING, 40, 100)
        self.assertEqual(second, "Rend")
        self.assertEqual(third, "Rends")

    def test_highest_tier(self):
        """96%+ → ALL CAPS DECAPITATE/DECAPITATES."""
        second, third = get_descriptor(DamageType.SLASHING, 98, 100)
        self.assertEqual(second, "DECAPITATE")
        self.assertEqual(third, "DECAPITATES")

    def test_overflow_beyond_100_pct(self):
        """Damage exceeding max HP still returns highest tier."""
        second, third = get_descriptor(DamageType.SLASHING, 200, 100)
        self.assertEqual(second, "DECAPITATE")
        self.assertEqual(third, "DECAPITATES")


class TestGetDescriptorPiercing(EvenniaTest):
    """Test piercing has distinct verbs from slashing."""

    def create_script(self):
        pass

    def test_lowest_tier(self):
        second, third = get_descriptor(DamageType.PIERCING, 1, 100)
        self.assertEqual(second, "prick")

    def test_mid_tier(self):
        second, third = get_descriptor(DamageType.PIERCING, 15, 100)
        self.assertEqual(second, "pierce")


class TestGetDescriptorBludgeoning(EvenniaTest):
    """Test bludgeoning has distinct verbs."""

    def create_script(self):
        pass

    def test_lowest_tier(self):
        second, third = get_descriptor(DamageType.BLUDGEONING, 1, 100)
        self.assertEqual(second, "tap")

    def test_high_tier(self):
        second, third = get_descriptor(DamageType.BLUDGEONING, 98, 100)
        self.assertEqual(second, "PULVERIZE")


class TestGetDescriptorEdgeCases(EvenniaTest):
    """Edge cases for the descriptor lookup."""

    def create_script(self):
        pass

    def test_zero_hp_max_no_crash(self):
        """target_hp_max=0 should not divide by zero."""
        second, third = get_descriptor(DamageType.SLASHING, 5, 0)
        # max(1, 0) = 1, so 5*100//1 = 500% → highest tier
        self.assertEqual(second, "DECAPITATE")

    def test_zero_damage(self):
        """0 damage → 0% → lowest tier."""
        second, third = get_descriptor(DamageType.SLASHING, 0, 100)
        self.assertEqual(second, "nick")

    def test_percentage_scales_with_target_hp(self):
        """Same raw damage, different targets → different tiers."""
        # 5 damage on 10 HP target = 50%
        second_weak, _ = get_descriptor(DamageType.SLASHING, 5, 10)
        # 5 damage on 100 HP target = 5%
        second_strong, _ = get_descriptor(DamageType.SLASHING, 5, 100)
        self.assertNotEqual(second_weak, second_strong)

    def test_capitalisation_low_is_lowercase(self):
        """Low-tier descriptors are fully lowercase."""
        second, third = get_descriptor(DamageType.SLASHING, 1, 100)
        self.assertTrue(second.islower())
        self.assertTrue(third.islower())

    def test_capitalisation_high_is_uppercase(self):
        """High-tier descriptors are fully uppercase."""
        second, third = get_descriptor(DamageType.SLASHING, 98, 100)
        self.assertTrue(second.isupper())
        self.assertTrue(third.isupper())


class TestGetDescriptorAllTypes(EvenniaTest):
    """Every DamageType returns a valid descriptor without errors."""

    def create_script(self):
        pass

    def test_all_damage_types_have_descriptors(self):
        """Every DamageType enum member returns a tuple of two strings."""
        for dt in DamageType:
            second, third = get_descriptor(dt, 50, 100)
            self.assertIsInstance(second, str, f"{dt} second_person not str")
            self.assertIsInstance(third, str, f"{dt} third_person not str")
            self.assertTrue(len(second) > 0, f"{dt} second_person empty")
            self.assertTrue(len(third) > 0, f"{dt} third_person empty")


class TestGetMissVerb(EvenniaTest):
    """Test miss verb lookup."""

    def create_script(self):
        pass

    def test_slashing_miss(self):
        second, third = get_miss_verb(DamageType.SLASHING)
        self.assertEqual(second, "swing")
        self.assertEqual(third, "swings")

    def test_piercing_miss(self):
        second, third = get_miss_verb(DamageType.PIERCING)
        self.assertEqual(second, "thrust")
        self.assertEqual(third, "thrusts")

    def test_bludgeoning_miss(self):
        second, third = get_miss_verb(DamageType.BLUDGEONING)
        self.assertEqual(second, "swing")

    def test_all_types_have_miss_verbs(self):
        """Every DamageType returns a valid miss verb tuple."""
        for dt in DamageType:
            second, third = get_miss_verb(dt)
            self.assertIsInstance(second, str)
            self.assertIsInstance(third, str)
