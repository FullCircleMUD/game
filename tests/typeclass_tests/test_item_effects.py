"""
Tests for the data-driven item effect system — wear_effects on items,
apply_effect/remove_effect on characters, and the inheritance hierarchy.

evennia test --settings settings tests.typeclass_tests.test_item_effects
"""

from evennia.utils.test_resources import EvenniaTest
from evennia.utils import create

from enums.wearslot import HumanoidWearSlot


WALLET_A = "0xAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"


# ── Helpers ──────────────────────────────────────────────────────────────

def _make_wearable(key, wearslot_value, wear_effects=None, location=None):
    """Create a WearableNFTItem with given wearslot and effects."""
    obj = create.create_object(
        "typeclasses.items.wearables.wearable_nft_item.WearableNFTItem",
        key=key,
        nohome=True,
    )
    obj.wearslot = wearslot_value
    if wear_effects is not None:
        obj.wear_effects = wear_effects
    if location:
        obj.move_to(location, quiet=True)
    return obj


def _make_weapon(key, wear_effects=None, location=None):
    """Create a WeaponNFTItem with optional effects."""
    obj = create.create_object(
        "typeclasses.items.weapons.weapon_nft_item.WeaponNFTItem",
        key=key,
        nohome=True,
    )
    if wear_effects is not None:
        obj.wear_effects = wear_effects
    if location:
        obj.move_to(location, quiet=True)
    return obj


def _make_holdable(key, wear_effects=None, location=None):
    """Create a HoldableNFTItem with optional effects."""
    obj = create.create_object(
        "typeclasses.items.holdables.holdable_nft_item.HoldableNFTItem",
        key=key,
        nohome=True,
    )
    if wear_effects is not None:
        obj.wear_effects = wear_effects
    if location:
        obj.move_to(location, quiet=True)
    return obj


# ── Base Test Class ──────────────────────────────────────────────────────

class EffectTestBase(EvenniaTest):
    """Base class with common setup."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)


# ── Wear Effects Tests ───────────────────────────────────────────────────

class TestWearEffectsEmpty(EffectTestBase):
    """Wearing an item with no effects should not change stats."""

    def test_wear_empty_effects(self):
        item = _make_wearable("Plain Ring", HumanoidWearSlot.LEFT_RING_FINGER, location=self.char1)
        ac_before = self.char1.armor_class
        self.char1.wear(item)
        self.assertEqual(self.char1.armor_class, ac_before)


class TestWearStatBonus(EffectTestBase):
    """Test stat_bonus effect type application and reversal."""

    def test_wear_stat_bonus_applied(self):
        effects = [{"type": "stat_bonus", "stat": "armor_class", "value": 2}]
        item = _make_wearable("Iron Helm", HumanoidWearSlot.HEAD, effects, self.char1)
        ac_before = self.char1.armor_class
        self.char1.wear(item)
        self.assertEqual(self.char1.armor_class, ac_before + 2)

    def test_remove_stat_bonus_reversed(self):
        effects = [{"type": "stat_bonus", "stat": "armor_class", "value": 2}]
        item = _make_wearable("Iron Helm", HumanoidWearSlot.HEAD, effects, self.char1)
        ac_before = self.char1.armor_class
        self.char1.wear(item)
        self.char1.remove(item)
        self.assertEqual(self.char1.armor_class, ac_before)

    def test_multiple_effects(self):
        effects = [
            {"type": "stat_bonus", "stat": "armor_class", "value": 3},
            {"type": "stat_bonus", "stat": "strength", "value": 1},
        ]
        item = _make_wearable("Enchanted Mail", HumanoidWearSlot.BODY, effects, self.char1)
        ac_before = self.char1.armor_class
        str_before = self.char1.strength
        self.char1.wear(item)
        self.assertEqual(self.char1.armor_class, ac_before + 3)
        self.assertEqual(self.char1.strength, str_before + 1)
        self.char1.remove(item)
        self.assertEqual(self.char1.armor_class, ac_before)
        self.assertEqual(self.char1.strength, str_before)

    def test_unknown_effect_type_ignored(self):
        """Unknown effect types should be silently ignored, no error."""
        effects = [{"type": "unknown_thing", "foo": "bar"}]
        item = _make_wearable("Mystery Ring", HumanoidWearSlot.LEFT_RING_FINGER, effects, self.char1)
        ac_before = self.char1.armor_class
        self.char1.wear(item)
        self.assertEqual(self.char1.armor_class, ac_before)


# ── Weapon Effects Tests ─────────────────────────────────────────────────

class TestWeaponEffects(EffectTestBase):
    """Test that weapon wear_effects apply through the at_wear → super chain."""

    def test_weapon_wield_effects(self):
        effects = [{"type": "stat_bonus", "stat": "total_hit_bonus", "value": 1}]
        weapon = _make_weapon("Magic Sword", effects, self.char1)
        hit_before = self.char1.total_hit_bonus
        self.char1.wear(weapon)
        self.assertEqual(self.char1.total_hit_bonus, hit_before + 1)

    def test_weapon_remove_reverses(self):
        effects = [{"type": "stat_bonus", "stat": "total_hit_bonus", "value": 1}]
        weapon = _make_weapon("Magic Sword", effects, self.char1)
        hit_before = self.char1.total_hit_bonus
        self.char1.wear(weapon)
        self.char1.remove(weapon)
        self.assertEqual(self.char1.total_hit_bonus, hit_before)


# ── Holdable Effects Tests ───────────────────────────────────────────────

class TestHoldableEffects(EffectTestBase):
    """Test that holdable wear_effects apply through the at_wear → super chain."""

    def test_holdable_hold_effects(self):
        effects = [{"type": "stat_bonus", "stat": "armor_class", "value": 1}]
        shield = _make_holdable("Wooden Shield", effects, self.char1)
        ac_before = self.char1.armor_class
        self.char1.wear(shield)
        self.assertEqual(self.char1.armor_class, ac_before + 1)

    def test_holdable_remove_reverses(self):
        effects = [{"type": "stat_bonus", "stat": "armor_class", "value": 1}]
        shield = _make_holdable("Wooden Shield", effects, self.char1)
        ac_before = self.char1.armor_class
        self.char1.wear(shield)
        self.char1.remove(shield)
        self.assertEqual(self.char1.armor_class, ac_before)


# ── Inheritance Tests ────────────────────────────────────────────────────

class TestInheritanceHierarchy(EffectTestBase):
    """Verify the new class hierarchy."""

    def test_weapon_is_wearable_subclass(self):
        from typeclasses.items.wearables.wearable_nft_item import WearableNFTItem
        weapon = _make_weapon("Test Sword", location=self.char1)
        self.assertIsInstance(weapon, WearableNFTItem)

    def test_holdable_is_wearable_subclass(self):
        from typeclasses.items.wearables.wearable_nft_item import WearableNFTItem
        holdable = _make_holdable("Test Shield", location=self.char1)
        self.assertIsInstance(holdable, WearableNFTItem)

    def test_weapon_has_wearable_tag(self):
        weapon = _make_weapon("Test Sword", location=self.char1)
        self.assertTrue(weapon.tags.has("wearable", category="item_type"))
        self.assertTrue(weapon.tags.has("weapon", category="item_type"))

    def test_holdable_has_wearable_tag(self):
        holdable = _make_holdable("Test Shield", location=self.char1)
        self.assertTrue(holdable.tags.has("wearable", category="item_type"))
        self.assertTrue(holdable.tags.has("holdable", category="item_type"))

    def test_weapon_default_wearslot(self):
        weapon = _make_weapon("Test Sword", location=self.char1)
        self.assertEqual(weapon.wearslot, HumanoidWearSlot.WIELD)

    def test_holdable_default_wearslot(self):
        holdable = _make_holdable("Test Shield", location=self.char1)
        self.assertEqual(holdable.wearslot, HumanoidWearSlot.HOLD)


# ── Equipment Break Tests ────────────────────────────────────────────────

class TestEquipmentBreak(EffectTestBase):
    """Test that equipment break reverses effects and unequips."""

    def test_break_reverses_wear_effects(self):
        effects = [{"type": "stat_bonus", "stat": "armor_class", "value": 2}]
        item = _make_wearable("Fragile Helm", HumanoidWearSlot.HEAD, effects, self.char1)
        item.max_durability = 5
        item.durability = 5
        ac_before = self.char1.armor_class
        self.char1.wear(item)
        self.assertEqual(self.char1.armor_class, ac_before + 2)

        # Break the item
        item.durability = 1
        item.reduce_durability(1)
        self.assertEqual(self.char1.armor_class, ac_before)

    def test_break_unequips_item(self):
        item = _make_wearable("Fragile Ring", HumanoidWearSlot.LEFT_RING_FINGER, location=self.char1)
        item.max_durability = 1
        item.durability = 1
        self.char1.wear(item)
        self.assertTrue(self.char1.is_worn(item))

        item.reduce_durability(1)
        # Item should be gone (deleted)
        self.assertFalse(self.char1.is_worn(item))


# ── Effective Properties Tests ──────────────────────────────────────────

class TestEffectiveAC(EffectTestBase):
    """effective_ac should combine armor_class + DEX modifier."""

    def test_includes_positive_dex(self):
        self.char1.dexterity = 14  # +2 modifier
        self.char1.armor_class = 10
        self.assertEqual(self.char1.effective_ac, 12)

    def test_includes_negative_dex(self):
        self.char1.dexterity = 8  # -1 modifier
        self.char1.armor_class = 10
        self.assertEqual(self.char1.effective_ac, 9)

    def test_includes_equipment_bonus(self):
        self.char1.base_dexterity = 14  # +2 modifier (base so recalculate preserves it)
        self.char1.dexterity = 14
        effects = [{"type": "stat_bonus", "stat": "armor_class", "value": 3}]
        item = _make_wearable("Plate Helm", HumanoidWearSlot.HEAD, effects, self.char1)
        ac_before = self.char1.armor_class
        self.char1.wear(item)
        # effective = (base_ac + equipment) + DEX mod
        self.assertEqual(self.char1.effective_ac, ac_before + 3 + 2)

    def test_equipment_removal_updates_effective(self):
        self.char1.base_dexterity = 14  # +2 modifier (base so recalculate preserves it)
        self.char1.dexterity = 14
        effects = [{"type": "stat_bonus", "stat": "armor_class", "value": 3}]
        item = _make_wearable("Plate Helm", HumanoidWearSlot.HEAD, effects, self.char1)
        self.char1.wear(item)
        self.char1.remove(item)
        self.assertEqual(self.char1.effective_ac, 10 + 2)


class TestEffectiveInitiative(EffectTestBase):
    """effective_initiative should combine initiative_bonus + DEX modifier."""

    def test_includes_dex(self):
        self.char1.dexterity = 16  # +3 modifier
        self.char1.initiative_bonus = 0
        self.assertEqual(self.char1.effective_initiative, 3)

    def test_includes_equipment_and_dex(self):
        self.char1.base_dexterity = 14  # +2 modifier (base so recalculate preserves it)
        self.char1.dexterity = 14
        effects = [{"type": "stat_bonus", "stat": "initiative_bonus", "value": 1}]
        item = _make_wearable("Quick Ring", HumanoidWearSlot.LEFT_RING_FINGER, effects, self.char1)
        self.char1.wear(item)
        self.assertEqual(self.char1.effective_initiative, 1 + 2)


class TestEffectiveHPMax(EffectTestBase):
    """effective_hp_max should combine hp_max + CON modifier per level."""

    def test_includes_con_at_level_1(self):
        self.char1.constitution = 14  # +2 modifier
        self.char1.hp_max = 20
        self.char1.total_level = 1
        self.assertEqual(self.char1.effective_hp_max, 22)

    def test_con_scales_with_level(self):
        self.char1.constitution = 14  # +2 modifier
        self.char1.hp_max = 50
        self.char1.total_level = 5
        self.assertEqual(self.char1.effective_hp_max, 60)  # 50 + 2*5

    def test_negative_con_reduces_hp(self):
        self.char1.constitution = 8  # -1 modifier
        self.char1.hp_max = 20
        self.char1.total_level = 1
        self.assertEqual(self.char1.effective_hp_max, 19)

    def test_includes_equipment_and_con(self):
        self.char1.base_constitution = 14  # +2 modifier (base so recalculate preserves it)
        self.char1.constitution = 14
        self.char1.base_hp_max = 20
        self.char1.hp_max = 20
        self.char1.total_level = 1
        effects = [{"type": "stat_bonus", "stat": "hp_max", "value": 5}]
        item = _make_wearable("Amulet of Health", HumanoidWearSlot.NECK, effects, self.char1)
        self.char1.wear(item)
        # effective = (20 + 5 equipment) + 2 CON * 1 level = 27
        self.assertEqual(self.char1.effective_hp_max, 27)


class TestEffectiveCarryCapacity(EffectTestBase):
    """get_max_capacity() should include STR modifier (5 kg per +1)."""

    def test_includes_positive_str(self):
        self.char1.strength = 14  # +2 modifier
        self.char1.max_carrying_capacity_kg = 50
        self.assertEqual(self.char1.get_max_capacity(), 60)  # 50 + 2*5

    def test_includes_negative_str(self):
        self.char1.strength = 8  # -1 modifier
        self.char1.max_carrying_capacity_kg = 50
        self.assertEqual(self.char1.get_max_capacity(), 45)  # 50 + (-1)*5

    def test_can_carry_uses_effective(self):
        self.char1.strength = 14  # +2 modifier → 60 kg capacity
        self.char1.max_carrying_capacity_kg = 50
        self.char1.items_weight = 55.0
        # 55 < 60 → can carry 0 more
        self.assertTrue(self.char1.can_carry(4.0))
        self.assertFalse(self.char1.can_carry(6.0))

    def test_encumbrance_display_uses_effective(self):
        self.char1.strength = 14  # +2 modifier → 60 kg capacity
        self.char1.max_carrying_capacity_kg = 50
        display = self.char1.get_encumbrance_display()
        self.assertIn("60.0", display)


class TestEncumbranceConsequences(EffectTestBase):
    """Test _check_encumbrance_consequences on buff removal."""

    def test_str_buff_removal_causes_fall_when_airborne(self):
        """Losing a STR buff while flying + over capacity → fall."""
        self.char1.strength = 10  # base 0 modifier
        self.char1.max_carrying_capacity_kg = 50
        self.char1.items_weight = 55.0
        self.char1.room_vertical_position = 2
        self.char1.hp = 100

        # Apply STR buff (+4 str → +2 modifier → +10 kg → capacity 60)
        effect = {"type": "stat_bonus", "stat": "strength", "value": 4}
        self.char1.apply_effect(effect)
        self.assertFalse(self.char1.is_encumbered)  # 55 < 60

        # Remove buff → capacity drops to 50, weight 55 → encumbered while flying
        self.char1.remove_effect(effect)
        self.assertTrue(self.char1.is_encumbered)
        # Should have fallen
        self.assertEqual(self.char1.room_vertical_position, 0)
        self.assertEqual(self.char1.hp, 80)  # 2 * 10 = 20 damage

    def test_str_buff_removal_causes_sink_when_in_water(self):
        """Losing a STR buff on water surface + over capacity → sink."""
        self.char1.strength = 10
        self.char1.max_carrying_capacity_kg = 50
        self.char1.items_weight = 55.0
        self.char1.room_vertical_position = 0
        self.room1.max_depth = -2

        # Apply STR buff
        effect = {"type": "stat_bonus", "stat": "strength", "value": 4}
        self.char1.apply_effect(effect)
        self.assertFalse(self.char1.is_encumbered)

        # Remove buff → encumbered in water → sink
        self.char1.remove_effect(effect)
        self.assertTrue(self.char1.is_encumbered)
        self.assertEqual(self.char1.room_vertical_position, -2)

    def test_str_buff_removal_no_consequence_on_dry_ground(self):
        """Losing a STR buff on dry ground → no immediate consequence."""
        self.char1.strength = 10
        self.char1.max_carrying_capacity_kg = 50
        self.char1.items_weight = 55.0
        self.char1.room_vertical_position = 0
        self.room1.max_depth = 0
        self.char1.hp = 100

        effect = {"type": "stat_bonus", "stat": "strength", "value": 4}
        self.char1.apply_effect(effect)
        self.char1.remove_effect(effect)

        # Should be encumbered but no damage/position change
        self.assertTrue(self.char1.is_encumbered)
        self.assertEqual(self.char1.room_vertical_position, 0)
        self.assertEqual(self.char1.hp, 100)


# ── Compound Condition Effects Tests ────────────────────────────────────

class TestCompoundConditionEffects(EffectTestBase):
    """
    Test that condition effects with companion bonuses only apply/remove
    on condition transitions (0→1 / →0), not on duplicate wear.
    Standalone stat_bonus effects should continue to stack independently.
    """

    HASTE_EFFECTS = [
        {"type": "condition", "condition": "hasted", "effects": [
            {"type": "stat_bonus", "stat": "attacks_per_round", "value": 1},
        ]},
    ]

    def test_compound_condition_applies_on_first_wear(self):
        """First haste ring grants condition + companion stat bonus."""
        ring = _make_wearable(
            "Haste Ring", HumanoidWearSlot.LEFT_RING_FINGER,
            self.HASTE_EFFECTS, self.char1,
        )
        apr_before = self.char1.attacks_per_round
        self.char1.wear(ring)
        self.assertTrue(self.char1.has_condition("hasted"))
        self.assertEqual(self.char1.attacks_per_round, apr_before + 1)

    def test_compound_condition_skips_on_second_wear(self):
        """Second haste ring increments ref count but does NOT double the bonus."""
        ring1 = _make_wearable(
            "Haste Ring 1", HumanoidWearSlot.LEFT_RING_FINGER,
            self.HASTE_EFFECTS, self.char1,
        )
        ring2 = _make_wearable(
            "Haste Ring 2", HumanoidWearSlot.RIGHT_RING_FINGER,
            self.HASTE_EFFECTS, self.char1,
        )
        apr_before = self.char1.attacks_per_round
        self.char1.wear(ring1)
        self.char1.wear(ring2)
        # Condition ref count is 2, but bonus only applied once
        self.assertEqual(self.char1.get_condition_count("hasted"), 2)
        self.assertEqual(self.char1.attacks_per_round, apr_before + 1)

    def test_compound_condition_keeps_bonus_on_partial_remove(self):
        """Removing one of two haste rings keeps condition and bonus."""
        ring1 = _make_wearable(
            "Haste Ring 1", HumanoidWearSlot.LEFT_RING_FINGER,
            self.HASTE_EFFECTS, self.char1,
        )
        ring2 = _make_wearable(
            "Haste Ring 2", HumanoidWearSlot.RIGHT_RING_FINGER,
            self.HASTE_EFFECTS, self.char1,
        )
        apr_before = self.char1.attacks_per_round
        self.char1.wear(ring1)
        self.char1.wear(ring2)
        self.char1.remove(ring2)
        # Still hasted from ring1, bonus preserved
        self.assertTrue(self.char1.has_condition("hasted"))
        self.assertEqual(self.char1.attacks_per_round, apr_before + 1)

    def test_compound_condition_reverses_on_full_remove(self):
        """Removing the last haste ring removes condition and reverses bonus."""
        ring1 = _make_wearable(
            "Haste Ring 1", HumanoidWearSlot.LEFT_RING_FINGER,
            self.HASTE_EFFECTS, self.char1,
        )
        ring2 = _make_wearable(
            "Haste Ring 2", HumanoidWearSlot.RIGHT_RING_FINGER,
            self.HASTE_EFFECTS, self.char1,
        )
        apr_before = self.char1.attacks_per_round
        self.char1.wear(ring1)
        self.char1.wear(ring2)
        self.char1.remove(ring2)
        self.char1.remove(ring1)
        # Condition gone, bonus reversed
        self.assertFalse(self.char1.has_condition("hasted"))
        self.assertEqual(self.char1.attacks_per_round, apr_before)

    def test_standalone_stat_bonus_still_stacks(self):
        """Two +1 STR rings should stack to +2 STR (regression guard)."""
        str_effects = [{"type": "stat_bonus", "stat": "strength", "value": 1}]
        ring1 = _make_wearable(
            "STR Ring 1", HumanoidWearSlot.LEFT_RING_FINGER,
            str_effects, self.char1,
        )
        ring2 = _make_wearable(
            "STR Ring 2", HumanoidWearSlot.RIGHT_RING_FINGER,
            str_effects, self.char1,
        )
        str_before = self.char1.strength
        self.char1.wear(ring1)
        self.char1.wear(ring2)
        self.assertEqual(self.char1.strength, str_before + 2)
        self.char1.remove(ring1)
        self.char1.remove(ring2)
        self.assertEqual(self.char1.strength, str_before)

    def test_condition_without_companions_unchanged(self):
        """Existing condition-only format still works (no 'effects' key)."""
        from enums.condition import Condition
        effects = [{"type": "condition", "condition": "darkvision"}]
        ring = _make_wearable(
            "Darkvision Ring", HumanoidWearSlot.LEFT_RING_FINGER,
            effects, self.char1,
        )
        self.char1.wear(ring)
        self.assertTrue(self.char1.has_condition(Condition.DARKVISION))
        self.char1.remove(ring)
        self.assertFalse(self.char1.has_condition(Condition.DARKVISION))
