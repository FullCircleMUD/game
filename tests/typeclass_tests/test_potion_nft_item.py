"""
Tests for PotionNFTItem — dice-based restore, anti-stacking via named effects,
integration with EffectsManagerMixin, and potion_scaling named_effect_key.

evennia test --settings settings tests.typeclass_tests.test_potion_nft_item
"""

from unittest.mock import patch
import unittest

from evennia.utils.test_resources import EvenniaTest
from evennia.utils import create


def _make_potion(key, potion_effects, duration=0, location=None,
                 named_effect_key=""):
    """Create a PotionNFTItem with given effects."""
    obj = create.create_object(
        "typeclasses.items.consumables.potion_nft_item.PotionNFTItem",
        key=key,
        nohome=True,
    )
    obj.potion_effects = potion_effects
    obj.duration = duration
    if named_effect_key:
        obj.named_effect_key = named_effect_key
    if location:
        obj.move_to(location, quiet=True)
    return obj


# ── Dice-Based Restore ─────────────────────────────────────────────

class TestPotionDiceRestore(EvenniaTest):
    """Test dice strings in restore effects."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    @patch("typeclasses.items.consumables.potion_nft_item.dice_roller.roll",
           return_value=10)
    def test_restore_with_dice_string(self, mock_roll):
        """Effect with 'dice' key should roll and restore that amount."""
        self.char1.hp = 5
        self.char1.hp_max = 50

        potion = _make_potion(
            "test potion",
            [{"type": "restore", "stat": "hp", "dice": "2d4+1"}],
        )
        success, msg = potion.at_consume(self.char1)

        self.assertTrue(success)
        mock_roll.assert_called_once_with("2d4+1")
        self.assertEqual(self.char1.hp, 15)
        self.assertIn("recover 10 hp", msg)

    def test_restore_with_value_int(self):
        """Existing int 'value' field should still work."""
        self.char1.hp = 5
        self.char1.hp_max = 50

        potion = _make_potion(
            "test potion",
            [{"type": "restore", "stat": "hp", "value": 8}],
        )
        success, msg = potion.at_consume(self.char1)

        self.assertTrue(success)
        self.assertEqual(self.char1.hp, 13)
        self.assertIn("recover 8 hp", msg)

    @patch("typeclasses.items.consumables.potion_nft_item.dice_roller.roll",
           return_value=50)
    def test_restore_dice_caps_at_max(self, mock_roll):
        """Dice restore should not exceed effective max."""
        cap = self.char1.effective_hp_max
        self.char1.hp = cap - 3  # 3 below max

        potion = _make_potion(
            "test potion",
            [{"type": "restore", "stat": "hp", "dice": "10d4+5"}],
        )
        success, msg = potion.at_consume(self.char1)

        self.assertTrue(success)
        # Capped at effective_hp_max, only recovered 3
        self.assertEqual(self.char1.hp, cap)
        self.assertIn("recover 3 hp", msg)

    @patch("typeclasses.items.consumables.potion_nft_item.dice_roller.roll",
           return_value=8)
    def test_restore_dice_mana(self, mock_roll):
        """Dice-based mana restore should work."""
        self.char1.mana = 10
        self.char1.mana_max = 50

        potion = _make_potion(
            "test potion",
            [{"type": "restore", "stat": "mana", "dice": "2d4+1"}],
        )
        success, msg = potion.at_consume(self.char1)

        self.assertTrue(success)
        self.assertEqual(self.char1.mana, 18)
        self.assertIn("recover 8 mana", msg)


# ── Condition Effects ──────────────────────────────────────────────

class TestPotionCondition(EvenniaTest):
    """Test condition effects in potions."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def test_condition_applied(self):
        """Potion with condition effect should apply via named effect."""
        potion = _make_potion(
            "test potion",
            [{"type": "condition", "condition": "darkvision"}],
            duration=60,
            named_effect_key="potion_test",
        )
        success, _ = potion.at_consume(self.char1)

        self.assertTrue(success)
        self.assertTrue(self.char1.has_condition("darkvision"))
        self.assertTrue(self.char1.has_effect("potion_test"))


# ── Anti-Stacking ─────────────────────────────────────────────────

class TestPotionAntiStacking(EvenniaTest):
    """Test that named effect anti-stacking prevents double buffs."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.haste_effects = [
            {"type": "condition", "condition": "hasted"},
            {"type": "stat_bonus", "stat": "strength", "value": 2},
        ]

    def test_first_drink_applies_all(self):
        """First potion should apply condition + stat bonus via named effect."""
        original_str = self.char1.strength
        potion = _make_potion(
            "Haste Potion", self.haste_effects, duration=120,
            named_effect_key="potion_test",
        )
        success, _ = potion.at_consume(self.char1)

        self.assertTrue(success)
        self.assertTrue(self.char1.has_condition("hasted"))
        self.assertTrue(self.char1.has_effect("potion_test"))
        self.assertEqual(self.char1.strength, original_str + 2)

    def test_second_drink_blocked(self):
        """Second potion should be blocked — not consumed, potion saved."""
        original_str = self.char1.strength
        # First drink
        potion1 = _make_potion(
            "Haste Potion", self.haste_effects, duration=120,
            named_effect_key="potion_test",
        )
        potion1.at_consume(self.char1)

        # Second drink — should be blocked
        potion2 = _make_potion(
            "Haste Potion", self.haste_effects, duration=120,
            named_effect_key="potion_test",
        )
        success, msg = potion2.at_consume(self.char1)

        self.assertFalse(success)
        self.assertIn("already under this effect", msg)
        # Strength should still be +2, not +4
        self.assertEqual(self.char1.strength, original_str + 2)

    def test_condition_ref_count_stays_1(self):
        """Second potion blocked entirely — ref count stays at 1."""
        potion1 = _make_potion(
            "Haste Potion", self.haste_effects, duration=120,
            named_effect_key="potion_test",
        )
        potion1.at_consume(self.char1)

        potion2 = _make_potion(
            "Haste Potion", self.haste_effects, duration=120,
            named_effect_key="potion_test",
        )
        potion2.at_consume(self.char1)

        # Ref count should be 1 (second drink was blocked)
        conds = dict(self.char1.conditions or {})
        self.assertEqual(conds.get("hasted", 0), 1)

    def test_stat_potions_anti_stack(self):
        """Pure stat potions now anti-stack (fixed bug)."""
        original_str = self.char1.strength
        effects = [{"type": "stat_bonus", "stat": "strength", "value": 1}]

        potion1 = _make_potion(
            "Bull Potion", effects, duration=60,
            named_effect_key="potion_strength",
        )
        potion1.at_consume(self.char1)

        potion2 = _make_potion(
            "Bull Potion", effects, duration=60,
            named_effect_key="potion_strength",
        )
        success, _ = potion2.at_consume(self.char1)

        # Second drink blocked — only +1, not +2
        self.assertFalse(success)
        self.assertEqual(self.char1.strength, original_str + 1)

    def test_restore_blocked_when_buff_active(self):
        """When timed effect is active, entire potion is blocked (not consumed)."""
        self.char1.hp = 10
        self.char1.hp_max = 50
        effects = [
            {"type": "condition", "condition": "hasted"},
            {"type": "restore", "stat": "hp", "value": 5},
        ]

        potion1 = _make_potion(
            "Combo Potion", effects, duration=120,
            named_effect_key="potion_test",
        )
        potion1.at_consume(self.char1)
        self.assertEqual(self.char1.hp, 15)

        potion2 = _make_potion(
            "Combo Potion", effects, duration=120,
            named_effect_key="potion_test",
        )
        success, _ = potion2.at_consume(self.char1)
        # Entire potion blocked — HP unchanged
        self.assertFalse(success)
        self.assertEqual(self.char1.hp, 15)


# ── Named Effect Integration ──────────────────────────────────────

class TestPotionNamedEffect(EvenniaTest):
    """Test integration with EffectsManagerMixin named effects."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def test_named_effect_tracked(self):
        """After drinking, the named effect should be tracked."""
        effects = [{"type": "stat_bonus", "stat": "strength", "value": 2}]
        potion = _make_potion(
            "Bull Potion", effects, duration=60,
            named_effect_key="potion_strength",
        )
        potion.at_consume(self.char1)

        self.assertTrue(self.char1.has_effect("potion_strength"))

    def test_effect_removal_reverses_stat(self):
        """Removing the named effect should reverse the stat bonus."""
        original_str = self.char1.strength
        effects = [{"type": "stat_bonus", "stat": "strength", "value": 3}]
        potion = _make_potion(
            "Bull Potion", effects, duration=60,
            named_effect_key="potion_strength",
        )
        potion.at_consume(self.char1)
        self.assertEqual(self.char1.strength, original_str + 3)

        # Manually remove (simulates timer expiry)
        self.char1.remove_named_effect("potion_strength")

        self.assertEqual(self.char1.strength, original_str)
        self.assertFalse(self.char1.has_effect("potion_strength"))

    def test_instant_potion_no_named_effect(self):
        """Restore potion (duration=0) should not create a named effect."""
        effects = [{"type": "restore", "stat": "hp", "value": 5}]
        self.char1.hp = 10
        self.char1.hp_max = 50

        potion = _make_potion("Heal Potion", effects, duration=0)
        potion.at_consume(self.char1)

        self.assertEqual(self.char1.hp, 15)
        # No named effect since duration=0
        self.assertFalse(self.char1.has_effect("potion_strength"))

    def test_can_drink_after_effect_expires(self):
        """After effect is removed, should be able to drink again."""
        original_str = self.char1.strength
        effects = [{"type": "stat_bonus", "stat": "strength", "value": 2}]

        potion1 = _make_potion(
            "Bull Potion", effects, duration=60,
            named_effect_key="potion_strength",
        )
        potion1.at_consume(self.char1)
        self.assertEqual(self.char1.strength, original_str + 2)

        # Effect expires
        self.char1.remove_named_effect("potion_strength")
        self.assertEqual(self.char1.strength, original_str)

        # Drink again — should work
        potion2 = _make_potion(
            "Bull Potion", effects, duration=60,
            named_effect_key="potion_strength",
        )
        success, _ = potion2.at_consume(self.char1)
        self.assertTrue(success)
        self.assertEqual(self.char1.strength, original_str + 2)


# ── Mastery Tier Attribute ────────────────────────────────────────

class TestPotionMasteryTier(EvenniaTest):
    """Test mastery_tier AttributeProperty on PotionNFTItem."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def test_default_mastery_tier(self):
        """New potions default to mastery_tier 1."""
        potion = _make_potion("test", [])
        self.assertEqual(potion.mastery_tier, 1)

    def test_mastery_tier_persists(self):
        """mastery_tier can be set and read back."""
        potion = _make_potion("test", [])
        potion.mastery_tier = 3
        self.assertEqual(potion.mastery_tier, 3)


# ── PotionQuality Enum ───────────────────────────────────────────

class TestPotionQualityEnum(unittest.TestCase):
    """Test PotionQuality enum and get_quality_name helper."""

    def test_all_prefixes(self):
        from enums.potion_quality import PotionQuality
        self.assertEqual(PotionQuality(1).prefix, "Watery")
        self.assertEqual(PotionQuality(2).prefix, "Weak")
        self.assertEqual(PotionQuality(3).prefix, "Standard")
        self.assertEqual(PotionQuality(4).prefix, "Potent")
        self.assertEqual(PotionQuality(5).prefix, "Ascendant")

    def test_get_quality_name(self):
        from world.prototypes.consumables.potions.potion_scaling import (
            get_quality_name,
        )
        self.assertEqual(
            get_quality_name("Potion of the Bull", 1),
            "Watery Potion of the Bull",
        )
        self.assertEqual(
            get_quality_name("Potion of Cat's Grace", 5),
            "Ascendant Potion of Cat's Grace",
        )


# ── Prototype Validation ─────────────────────────────────────────

class TestPotionPrototypesExist(unittest.TestCase):
    """Verify tier-specific prototypes exist for all stat potions."""

    def test_all_stat_potion_prototypes_have_named_effect_key(self):
        """All stat potion prototypes must have a named_effect_key."""
        from world.prototypes.consumables.potions.watery_the_bull import WATERY_THE_BULL
        from world.prototypes.consumables.potions.watery_cats_grace import WATERY_CATS_GRACE
        from world.prototypes.consumables.potions.watery_the_bear import WATERY_THE_BEAR
        from world.prototypes.consumables.potions.watery_foxs_cunning import WATERY_FOXS_CUNNING
        from world.prototypes.consumables.potions.watery_owls_insight import WATERY_OWLS_INSIGHT
        from world.prototypes.consumables.potions.watery_silver_tongue import WATERY_SILVER_TONGUE

        expected = {
            "watery_the_bull": ("potion_strength", WATERY_THE_BULL),
            "watery_cats_grace": ("potion_dexterity", WATERY_CATS_GRACE),
            "watery_the_bear": ("potion_constitution", WATERY_THE_BEAR),
            "watery_foxs_cunning": ("potion_intelligence", WATERY_FOXS_CUNNING),
            "watery_owls_insight": ("potion_wisdom", WATERY_OWLS_INSIGHT),
            "watery_silver_tongue": ("potion_charisma", WATERY_SILVER_TONGUE),
        }
        for proto_key, (expected_key, proto) in expected.items():
            self.assertEqual(
                proto.get("named_effect_key"), expected_key,
                f"{proto_key} missing or wrong named_effect_key",
            )

    def test_restore_prototypes_no_named_effect_key(self):
        """Restore potion prototypes should NOT have named_effect_key."""
        from world.prototypes.consumables.potions.watery_lifes_essence import WATERY_LIFES_ESSENCE
        from world.prototypes.consumables.potions.watery_the_wellspring import WATERY_THE_WELLSPRING
        from world.prototypes.consumables.potions.watery_the_zephyr import WATERY_THE_ZEPHYR

        for proto in (WATERY_LIFES_ESSENCE, WATERY_THE_WELLSPRING, WATERY_THE_ZEPHYR):
            self.assertNotIn(
                "named_effect_key", proto,
                f"{proto['prototype_key']} should not have named_effect_key",
            )
