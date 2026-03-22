"""
Tests for DamageResistanceMixin — resistance, vulnerability, and capping.

Verifies get_resistance(), apply/remove_resistance_effect(), clamping
to [-75, 75], zero-entry cleanup, and stacking.

evennia test --settings settings tests.typeclass_tests.test_damage_resistance
"""

from evennia.utils.test_resources import EvenniaCommandTest

from typeclasses.mixins.damage_resistance import (
    DamageResistanceMixin,
    RESISTANCE_CAP,
)


WALLET_A = "0xAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"


class DamageResistanceTestBase(EvenniaCommandTest):
    """Base class providing a character with DamageResistanceMixin."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)
        # Clear any default resistances
        self.char1.damage_resistances = {}


class TestResistanceCap(DamageResistanceTestBase):
    """Test the resistance cap constant."""

    def test_cap_is_75(self):
        """Resistance cap should be 75."""
        self.assertEqual(RESISTANCE_CAP, 75)


class TestGetResistance(DamageResistanceTestBase):
    """Test get_resistance() method."""

    def test_no_resistance(self):
        """Unknown damage type should return 0."""
        self.assertEqual(self.char1.get_resistance("fire"), 0)

    def test_positive_resistance(self):
        """Should return stored positive resistance."""
        self.char1.damage_resistances = {"fire": 30}
        self.assertEqual(self.char1.get_resistance("fire"), 30)

    def test_negative_resistance_vulnerability(self):
        """Negative value = vulnerability."""
        self.char1.damage_resistances = {"cold": -25}
        self.assertEqual(self.char1.get_resistance("cold"), -25)

    def test_capped_at_positive_75(self):
        """Resistance above 75 should be clamped to 75."""
        self.char1.damage_resistances = {"fire": 100}
        self.assertEqual(self.char1.get_resistance("fire"), 75)

    def test_capped_at_negative_75(self):
        """Vulnerability below -75 should be clamped to -75."""
        self.char1.damage_resistances = {"cold": -100}
        self.assertEqual(self.char1.get_resistance("cold"), -75)

    def test_at_cap_exactly(self):
        """Exactly at cap should return cap value."""
        self.char1.damage_resistances = {"fire": 75}
        self.assertEqual(self.char1.get_resistance("fire"), 75)
        self.char1.damage_resistances = {"fire": -75}
        self.assertEqual(self.char1.get_resistance("fire"), -75)

    def test_multiple_types_independent(self):
        """Different damage types should be independent."""
        self.char1.damage_resistances = {"fire": 30, "cold": -10, "acid": 50}
        self.assertEqual(self.char1.get_resistance("fire"), 30)
        self.assertEqual(self.char1.get_resistance("cold"), -10)
        self.assertEqual(self.char1.get_resistance("acid"), 50)


class TestApplyResistanceEffect(DamageResistanceTestBase):
    """Test apply_resistance_effect() method."""

    def test_apply_new_resistance(self):
        """Applying to empty dict should create entry."""
        self.char1.apply_resistance_effect(
            {"type": "damage_resistance", "damage_type": "fire", "value": 20}
        )
        self.assertEqual(self.char1.damage_resistances.get("fire"), 20)

    def test_apply_stacks(self):
        """Multiple applies should stack additively."""
        self.char1.apply_resistance_effect(
            {"type": "damage_resistance", "damage_type": "fire", "value": 20}
        )
        self.char1.apply_resistance_effect(
            {"type": "damage_resistance", "damage_type": "fire", "value": 15}
        )
        self.assertEqual(self.char1.damage_resistances.get("fire"), 35)

    def test_apply_vulnerability(self):
        """Negative value should create vulnerability."""
        self.char1.apply_resistance_effect(
            {"type": "damage_resistance", "damage_type": "cold", "value": -25}
        )
        self.assertEqual(self.char1.damage_resistances.get("cold"), -25)

    def test_apply_cancels_to_zero_cleaned_up(self):
        """Resistance + equal vulnerability should clean up the entry."""
        self.char1.apply_resistance_effect(
            {"type": "damage_resistance", "damage_type": "fire", "value": 20}
        )
        self.char1.apply_resistance_effect(
            {"type": "damage_resistance", "damage_type": "fire", "value": -20}
        )
        self.assertNotIn("fire", self.char1.damage_resistances)

    def test_raw_value_unclamped(self):
        """Raw stored value should NOT be clamped (only get_resistance clamps)."""
        self.char1.apply_resistance_effect(
            {"type": "damage_resistance", "damage_type": "fire", "value": 100}
        )
        self.assertEqual(self.char1.damage_resistances.get("fire"), 100)
        # But get_resistance should clamp
        self.assertEqual(self.char1.get_resistance("fire"), 75)


class TestRemoveResistanceEffect(DamageResistanceTestBase):
    """Test remove_resistance_effect() method."""

    def test_remove_reduces_value(self):
        """Removing should subtract the effect value."""
        self.char1.damage_resistances = {"fire": 50}
        self.char1.remove_resistance_effect(
            {"type": "damage_resistance", "damage_type": "fire", "value": 20}
        )
        self.assertEqual(self.char1.damage_resistances.get("fire"), 30)

    def test_remove_to_zero_cleaned_up(self):
        """Removing to exactly zero should clean up the entry."""
        self.char1.damage_resistances = {"fire": 20}
        self.char1.remove_resistance_effect(
            {"type": "damage_resistance", "damage_type": "fire", "value": 20}
        )
        self.assertNotIn("fire", self.char1.damage_resistances)

    def test_remove_past_zero_goes_negative(self):
        """Removing more than current should go negative (vulnerability)."""
        self.char1.damage_resistances = {"fire": 10}
        self.char1.remove_resistance_effect(
            {"type": "damage_resistance", "damage_type": "fire", "value": 30}
        )
        self.assertEqual(self.char1.damage_resistances.get("fire"), -20)

    def test_apply_then_remove_restores(self):
        """Apply then remove should restore original state."""
        self.char1.damage_resistances = {"fire": 20}
        effect = {"type": "damage_resistance", "damage_type": "fire", "value": 15}
        self.char1.apply_resistance_effect(effect)
        self.assertEqual(self.char1.damage_resistances.get("fire"), 35)
        self.char1.remove_resistance_effect(effect)
        self.assertEqual(self.char1.damage_resistances.get("fire"), 20)

    def test_no_drift_past_cap(self):
        """Apply over cap then remove should restore exact original value."""
        self.char1.damage_resistances = {"poison": 60}
        effect = {"type": "damage_resistance", "damage_type": "poison", "value": 30}
        self.char1.apply_resistance_effect(effect)
        # Raw = 90, clamped to 75
        self.assertEqual(self.char1.get_resistance("poison"), 75)
        self.char1.remove_resistance_effect(effect)
        # Back to 60 exactly — no drift
        self.assertEqual(self.char1.damage_resistances.get("poison"), 60)
        self.assertEqual(self.char1.get_resistance("poison"), 60)
