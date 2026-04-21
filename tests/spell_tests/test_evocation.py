"""
Tests for the evocation spell school.

Tests:
    - MagicMissile: damage scaling with tier, auto-hit, multi-perspective messages
    - Fireball: unsafe AoE, fire damage, hits everything including caster
    - ConeOfCold: safe AoE with diminishing accuracy, cold + SLOWED
    - FlameBurst: safe AoE fire, diminishing accuracy, scales 3d6→6d6 (SKILLED+)
    - Frostbolt: single-target cold debuff, contested SLOWED, flat 1d6 damage
    - PowerWordDeath: instant kill mechanics, contested save, nat 1/nat 20

evennia test --settings settings tests.spell_tests.test_evocation
"""

from unittest.mock import patch, MagicMock

from evennia.utils.test_resources import EvenniaTest

from enums.condition import Condition
from enums.mastery_level import MasteryLevel
from enums.skills_enum import skills
from world.spells.registry import SPELL_REGISTRY, get_spell


class TestMagicMissile(EvenniaTest):
    """Test MagicMissile spell execution."""

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.spell = get_spell("magic_missile")
        self.char1.db.class_skill_mastery_levels = {"evocation": 1}
        self.char1.mana = 100

    def test_deals_damage(self):
        """Magic Missile should reduce target HP."""
        self.char2.hp = 50
        self.char2.hp_max = 50
        success, result = self.spell.cast(self.char1, self.char2)
        self.assertTrue(success)
        self.assertLess(self.char2.hp, 50)

    def test_tier1_one_missile(self):
        """At tier 1, fires 1 missile (1d4+1 damage, so 2-5)."""
        self.char2.hp = 100
        self.char2.hp_max = 100
        success, result = self.spell.cast(self.char1, self.char2)
        self.assertTrue(success)
        damage = 100 - self.char2.hp
        self.assertGreaterEqual(damage, 2)
        self.assertLessEqual(damage, 5)
        self.assertIn("1 glowing missile", result["first"])

    def test_first_person_message(self):
        """First-person message should start with 'You'."""
        self.char2.hp = 100
        self.char2.hp_max = 100
        success, result = self.spell.cast(self.char1, self.char2)
        self.assertTrue(result["first"].startswith("You"))

    def test_second_person_message(self):
        """Second-person message should contain caster name."""
        self.char2.hp = 100
        self.char2.hp_max = 100
        success, result = self.spell.cast(self.char1, self.char2)
        self.assertIn(self.char1.key, result["second"])

    def test_third_person_message(self):
        """Third-person message should contain both caster and target names."""
        self.char2.hp = 100
        self.char2.hp_max = 100
        success, result = self.spell.cast(self.char1, self.char2)
        self.assertIn(self.char1.key, result["third"])
        self.assertIn(self.char2.key, result["third"])

    def test_tier3_three_missiles(self):
        """At tier 3, fires 3 missiles (3d4+3 damage, so 6-15)."""
        self.char1.db.class_skill_mastery_levels = {"evocation": 3}
        self.char2.hp = 100
        self.char2.hp_max = 100
        success, result = self.spell.cast(self.char1, self.char2)
        self.assertTrue(success)
        damage = 100 - self.char2.hp
        self.assertGreaterEqual(damage, 6)
        self.assertLessEqual(damage, 15)
        self.assertIn("3 glowing missiles", result["first"])

    def test_tier5_five_missiles(self):
        """At tier 5 (GRANDMASTER), fires 5 missiles (5d4+5 damage, so 10-25)."""
        self.char1.db.class_skill_mastery_levels = {"evocation": 5}
        self.char2.hp = 100
        self.char2.hp_max = 100
        success, result = self.spell.cast(self.char1, self.char2)
        self.assertTrue(success)
        damage = 100 - self.char2.hp
        self.assertGreaterEqual(damage, 10)
        self.assertLessEqual(damage, 25)
        self.assertIn("5 glowing missiles", result["first"])

    def test_hp_floors_at_zero(self):
        """Target HP should not go below 0."""
        self.char1.db.class_skill_mastery_levels = {"evocation": 5}
        self.char2.hp = 1
        self.char2.hp_max = 100
        self.spell.cast(self.char1, self.char2)
        self.assertGreaterEqual(self.char2.hp, 0)


class TestFireball(EvenniaTest):
    """Test Fireball spell execution."""

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.spell = get_spell("fireball")
        self.char1.db.class_skill_mastery_levels = {"evocation": 3}
        self.char1.mana = 500
        self.char1.db.spell_cooldowns = {}
        self.char1.hp = 100
        self.char1.hp_max = 100
        self.char1.damage_resistances = {}
        self.char2.hp = 200
        self.char2.hp_max = 200
        self.char2.damage_resistances = {}

    def test_registered(self):
        """Fireball should be in the registry."""
        self.assertIn("fireball", SPELL_REGISTRY)

    def test_attributes(self):
        """Fireball should have correct class attributes."""
        self.assertEqual(self.spell.name, "Fireball")
        self.assertEqual(self.spell.min_mastery, MasteryLevel.EXPERT)
        self.assertEqual(self.spell.target_type, "actor_hostile")
        self.assertEqual(self.spell.aoe, "unsafe")

    def test_mana_costs(self):
        """Fireball mana costs should match design."""
        self.assertEqual(self.spell.mana_cost, {3: 28, 4: 39, 5: 49})

    def test_hits_primary_target(self):
        """Fireball should damage the primary target."""
        start_hp = self.char2.hp
        self.spell.cast(self.char1, self.char2)
        self.assertLess(self.char2.hp, start_hp)

    def test_hits_caster_in_secondaries(self):
        """Fireball should damage the caster when they're in secondaries (unsafe AoE)."""
        start_hp = self.char1.hp
        # Caster is in secondaries — simulates being at the same height
        self.spell.cast(self.char1, self.char2, secondaries=[self.char1])
        self.assertLess(self.char1.hp, start_hp)

    def test_hits_secondaries(self):
        """Fireball should damage all secondaries."""
        start_hp = self.char2.hp
        # char2 is primary, char1 is secondary
        self.spell.cast(self.char1, self.char2, secondaries=[self.char1])
        self.assertLess(self.char2.hp, start_hp)
        self.assertLess(self.char1.hp, 100)  # caster also took damage

    def test_deducts_mana(self):
        """Fireball should deduct correct mana."""
        start_mana = self.char1.mana
        self.spell.cast(self.char1, self.char2)
        self.assertEqual(self.char1.mana, start_mana - 28)

    def test_returns_message_dict(self):
        """Successful cast should return message dict."""
        success, result = self.spell.cast(self.char1, self.char2)
        self.assertTrue(success)
        self.assertIsInstance(result, dict)
        self.assertIn("first", result)
        self.assertIn("third", result)

    def test_expert_damage_range(self):
        """At EXPERT tier, 8d6 = 8-48 full, 4-24 half (with save)."""
        self.char2.hp = 200
        self.spell.cast(self.char1, self.char2)
        damage = 200 - self.char2.hp
        # Min is 4 (half of 8 on save), max is 48 (full on fail)
        self.assertGreaterEqual(damage, 4)
        self.assertLessEqual(damage, 48)

    def test_mastery_too_low(self):
        """Should fail if mastery below EXPERT."""
        self.char1.db.class_skill_mastery_levels = {"evocation": 2}
        success, msg = self.spell.cast(self.char1, self.char2)
        self.assertFalse(success)
        self.assertIn("mastery", msg.lower())

    def test_fire_resistance_reduces_damage(self):
        """Fire resistance should reduce fireball damage."""
        self.char2.damage_resistances = {"fire": 50}
        self.char2.hp = 200
        self.spell.cast(self.char1, self.char2)
        damage = 200 - self.char2.hp
        # 50% resist on max 48 = max 24, half save on max 24 = max 12
        self.assertLessEqual(damage, 24)

    @patch("world.spells.evocation.fireball.dice")
    def test_save_full_damage_on_fail(self, mock_dice):
        """Failed DEX save should deal full damage on primary target."""
        # damage roll, save DC roll, primary target save
        # High DC (20), low save (1) → fail → full damage
        mock_dice.roll.side_effect = [24, 20, 1]
        self.char2.hp = 200
        self.char2.dexterity = 10
        self.spell.cast(self.char1, self.char2)
        # char2 takes full 24 damage (no resistance)
        self.assertEqual(self.char2.hp, 200 - 24)

    @patch("world.spells.evocation.fireball.dice")
    def test_save_half_damage_on_success(self, mock_dice):
        """Successful DEX save should deal half damage on primary target."""
        # damage roll, save DC roll, primary target save
        # Low DC (1), high save (20) → save → half damage
        mock_dice.roll.side_effect = [24, 1, 20]
        self.char2.hp = 200
        self.char2.dexterity = 10
        self.spell.cast(self.char1, self.char2)
        # char2 takes half of 24 = 12
        self.assertEqual(self.char2.hp, 200 - 12)

    @patch("world.spells.evocation.fireball.dice")
    def test_save_dc_shown_in_message(self, mock_dice):
        """Save DC should appear in caster message."""
        mock_dice.roll.side_effect = [24, 15, 1]
        success, result = self.spell.cast(self.char1, self.char2)
        self.assertIn("Save DC", result["first"])


class TestConeOfCold(EvenniaTest):
    """Test Cone of Cold spell execution."""

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.spell = get_spell("cone_of_cold")
        self.char1.db.class_skill_mastery_levels = {"evocation": 4}
        self.char1.mana = 500
        self.char1.db.spell_cooldowns = {}
        self.char1.hp = 100
        self.char1.hp_max = 100
        self.char2.hp = 200
        self.char2.hp_max = 200
        self.char2.damage_resistances = {}

    def test_registered(self):
        """Cone of Cold should be in the registry."""
        self.assertIn("cone_of_cold", SPELL_REGISTRY)

    def test_attributes(self):
        """Cone of Cold should have correct class attributes."""
        self.assertEqual(self.spell.name, "Cone of Cold")
        self.assertEqual(self.spell.min_mastery, MasteryLevel.MASTER)
        self.assertEqual(self.spell.target_type, "actor_hostile")
        self.assertEqual(self.spell.aoe, "safe")

    def test_mana_costs(self):
        """Cone of Cold mana costs should match design."""
        self.assertEqual(self.spell.mana_cost, {4: 35, 5: 46})

    def test_deducts_mana(self):
        """Cone of Cold should deduct correct mana."""
        start_mana = self.char1.mana
        self.spell.cast(self.char1, self.char2)
        self.assertEqual(self.char1.mana, start_mana - 35)

    def test_mastery_too_low(self):
        """Should fail if mastery below MASTER."""
        self.char1.db.class_skill_mastery_levels = {"evocation": 3}
        success, msg = self.spell.cast(self.char1, self.char2)
        self.assertFalse(success)

    def test_primary_target_always_hit(self):
        """Primary target is a guaranteed hit — always takes damage."""
        for _ in range(5):
            self.char2.hp = 200
            self.char1.mana = 500
            self.char1.db.spell_cooldowns = {}
            self.spell.cast(self.char1, self.char2)
            self.assertLess(self.char2.hp, 200)

    def test_primary_target_slowed(self):
        """Primary target should be SLOWED on hit."""
        self.spell.cast(self.char1, self.char2)
        self.assertTrue(self.char2.has_condition(Condition.SLOWED))

    def test_returns_message_dict(self):
        """Successful cast should return message dict."""
        success, result = self.spell.cast(self.char1, self.char2)
        self.assertTrue(success)
        self.assertIsInstance(result, dict)
        self.assertIn("first", result)


class TestFlameBurst(EvenniaTest):
    """Test Flame Burst spell execution."""

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.spell = get_spell("flame_burst")
        self.char1.db.class_skill_mastery_levels = {"evocation": 2}
        self.char1.mana = 500
        self.char1.db.spell_cooldowns = {}
        self.char1.hp = 100
        self.char1.hp_max = 100
        self.char2.hp = 200
        self.char2.hp_max = 200
        self.char2.damage_resistances = {}

    def test_registered(self):
        """Flame Burst should be in the registry."""
        self.assertIn("flame_burst", SPELL_REGISTRY)

    def test_attributes(self):
        """Flame Burst should have correct class attributes."""
        self.assertEqual(self.spell.name, "Flame Burst")
        self.assertEqual(self.spell.school, skills.EVOCATION)
        self.assertEqual(self.spell.min_mastery, MasteryLevel.SKILLED)
        self.assertEqual(self.spell.target_type, "actor_hostile")
        self.assertEqual(self.spell.aoe, "safe")

    def test_mana_costs(self):
        """Flame Burst mana costs should match design."""
        self.assertEqual(self.spell.mana_cost, {2: 11, 3: 14, 4: 18, 5: 21})

    def test_deducts_mana_skilled(self):
        """Flame Burst should deduct correct mana at SKILLED tier."""
        start_mana = self.char1.mana
        self.spell.cast(self.char1, self.char2)
        self.assertEqual(self.char1.mana, start_mana - 11)

    def test_primary_target_always_hit(self):
        """Primary target is a guaranteed hit — always takes damage."""
        for _ in range(5):
            self.char2.hp = 200
            self.char1.mana = 500
            self.char1.db.spell_cooldowns = {}
            self.spell.cast(self.char1, self.char2)
            self.assertLess(self.char2.hp, 200)

    @patch("world.spells.evocation.flame_burst.dice")
    def test_skilled_damage_range(self, mock_dice):
        """At SKILLED tier, 3d6 = 3-18 damage on primary target."""
        mock_dice.roll.side_effect = [11]  # 11 damage
        self.char2.hp = 200
        self.spell.cast(self.char1, self.char2)
        damage = 200 - self.char2.hp
        self.assertEqual(damage, 11)

    @patch("world.spells.evocation.flame_burst.dice")
    def test_gm_damage_range(self, mock_dice):
        """At GM tier (5), 6d6 = 6-36 damage on primary target."""
        self.char1.db.class_skill_mastery_levels = {"evocation": 5}
        mock_dice.roll.side_effect = [21]  # 21 damage
        self.char2.hp = 200
        self.spell.cast(self.char1, self.char2)
        damage = 200 - self.char2.hp
        self.assertEqual(damage, 21)

    def test_returns_message_dict(self):
        """Successful cast should return message dict."""
        success, result = self.spell.cast(self.char1, self.char2)
        self.assertTrue(success)
        self.assertIsInstance(result, dict)
        self.assertIn("first", result)
        self.assertIn("third", result)

    def test_skilled_tier_cooldown(self):
        """Flame Burst inherits the SKILLED tier default cooldown (2 rounds)."""
        self.assertEqual(self.spell.get_cooldown(), 2)

    def test_fire_resistance_reduces_damage(self):
        """Fire resistance should reduce flame burst damage on primary."""
        self.char2.damage_resistances = {"fire": 50}
        self.char2.hp = 200
        self.spell.cast(self.char1, self.char2)
        damage = 200 - self.char2.hp
        # 50% resist on 3-18 raw = 2-9 actual
        self.assertLessEqual(damage, 9)

    def test_mastery_too_low(self):
        """Should fail if mastery is BASIC (1) — needs SKILLED."""
        self.char1.db.class_skill_mastery_levels = {"evocation": 1}
        success, msg = self.spell.cast(self.char1, self.char2)
        self.assertFalse(success)
        self.assertIn("mastery", msg.lower())


class TestPowerWordDeath(EvenniaTest):
    """Test Power Word: Death spell execution."""

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.spell = get_spell("power_word_death")
        self.char1.db.class_skill_mastery_levels = {"evocation": 5}
        self.char1.mana = 500
        self.char1.db.spell_cooldowns = {}
        self.char1.intelligence = 18  # +4 mod
        self.char2.hp = 100
        self.char2.hp_max = 100
        self.char2.constitution = 10  # +0 mod

    def test_registered(self):
        """Power Word: Death should be in the registry."""
        self.assertIn("power_word_death", SPELL_REGISTRY)

    def test_attributes(self):
        """PWD should have correct class attributes."""
        self.assertEqual(self.spell.name, "Power Word: Death")
        self.assertEqual(self.spell.min_mastery, MasteryLevel.GRANDMASTER)
        self.assertEqual(self.spell.target_type, "actor_hostile")

    def test_mana_cost(self):
        """PWD mana cost should be 100."""
        self.assertEqual(self.spell.mana_cost, {5: 100})

    def test_deducts_mana(self):
        """PWD should deduct 100 mana."""
        start_mana = self.char1.mana
        self.spell.cast(self.char1, self.char2)
        self.assertEqual(self.char1.mana, start_mana - 100)

    def test_mastery_too_low(self):
        """Should fail if mastery below GRANDMASTER."""
        self.char1.db.class_skill_mastery_levels = {"evocation": 4}
        success, msg = self.spell.cast(self.char1, self.char2)
        self.assertFalse(success)

    @patch("world.spells.evocation.power_word_death.dice")
    def test_below_threshold_instant_kill(self, mock_dice):
        """Target at or below 20 HP should die instantly (unless nat 1)."""
        mock_dice.roll.return_value = 10  # not nat 1
        self.char2.hp = 15
        with patch.object(self.char2, "die", MagicMock()):
            success, result = self.spell.cast(self.char1, self.char2)
        self.assertTrue(success)
        self.assertEqual(self.char2.hp, 0)

    @patch("world.spells.evocation.power_word_death.dice")
    def test_below_threshold_nat1_fails(self, mock_dice):
        """Nat 1 should fail even against target below threshold."""
        mock_dice.roll.return_value = 1
        self.char2.hp = 10
        success, result = self.spell.cast(self.char1, self.char2)
        self.assertTrue(success)  # spell still "succeeds" (mana spent)
        self.assertEqual(self.char2.hp, 10)  # but target lives

    @patch("world.spells.evocation.power_word_death.dice")
    def test_above_threshold_nat20_always_kills(self, mock_dice):
        """Nat 20 should always kill, even against high-HP target."""
        mock_dice.roll.side_effect = [20]  # caster rolls nat 20
        self.char2.hp = 500
        with patch.object(self.char2, "die", MagicMock()):
            success, result = self.spell.cast(self.char1, self.char2)
        self.assertTrue(success)
        self.assertEqual(self.char2.hp, 0)

    @patch("world.spells.evocation.power_word_death.dice")
    def test_above_threshold_contested_kill(self, mock_dice):
        """Caster wins contested roll = target dies."""
        # Caster rolls 15, target rolls 5
        mock_dice.roll.side_effect = [15, 5]
        self.char2.hp = 50  # above threshold (20)
        # Caster: 15 + 4(int) + 8(GM) = 27
        # Target: 5 + 0(con) + 6(30 HP over / 5) = 11
        with patch.object(self.char2, "die", MagicMock()):
            success, result = self.spell.cast(self.char1, self.char2)
        self.assertTrue(success)
        self.assertEqual(self.char2.hp, 0)

    @patch("world.spells.evocation.power_word_death.dice")
    def test_above_threshold_contested_fail(self, mock_dice):
        """Target wins contested roll = target lives, no damage."""
        # Caster rolls 2, target rolls 19
        mock_dice.roll.side_effect = [2, 19]
        self.char2.hp = 50
        success, result = self.spell.cast(self.char1, self.char2)
        self.assertTrue(success)  # spell "succeeds" (mana spent)
        self.assertEqual(self.char2.hp, 50)  # but target lives

    @patch("world.spells.evocation.power_word_death.dice")
    def test_hd_bonus_scaling(self, mock_dice):
        """Target far above threshold should get HD bonus."""
        # Target at 120 HP: (120-20)/5 = 20 HD bonus
        # Caster rolls 15: 15 + 4 + 8 = 27
        # Target rolls 5: 5 + 0 + 20 = 25 → caster wins
        mock_dice.roll.side_effect = [15, 5]
        self.char2.hp = 120
        with patch.object(self.char2, "die", MagicMock()):
            success, result = self.spell.cast(self.char1, self.char2)
        self.assertEqual(self.char2.hp, 0)  # barely wins

    @patch("world.spells.evocation.power_word_death.dice")
    def test_hd_bonus_makes_resist(self, mock_dice):
        """Very high HP target should resist more easily."""
        # Target at 220 HP: (220-20)/5 = 40 HD bonus
        # Caster rolls 15: 15 + 4 + 8 = 27
        # Target rolls 5: 5 + 0 + 40 = 45 → target wins
        mock_dice.roll.side_effect = [15, 5]
        self.char2.hp = 220
        success, result = self.spell.cast(self.char1, self.char2)
        self.assertEqual(self.char2.hp, 220)  # target resists

    def test_first_person_message_on_cast(self):
        """Cast should return first-person message."""
        success, result = self.spell.cast(self.char1, self.char2)
        self.assertTrue(success)
        self.assertIsInstance(result, dict)
        self.assertIn("first", result)

    def test_grandmaster_tier_cooldown(self):
        """PWD inherits the GRANDMASTER tier default cooldown (5 rounds)."""
        self.assertEqual(self.spell.get_cooldown(), 5)


class TestFrostbolt(EvenniaTest):
    """Test Frostbolt spell execution."""

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.spell = get_spell("frostbolt")
        self.char1.db.class_skill_mastery_levels = {"evocation": 1}
        self.char1.mana = 100
        self.char1.db.spell_cooldowns = {}
        self.char1.intelligence = 14  # +2 mod
        self.char2.hp = 200
        self.char2.hp_max = 200
        self.char2.constitution = 10  # +0 mod

    def test_registered(self):
        """Frostbolt should be in the registry."""
        self.assertIn("frostbolt", SPELL_REGISTRY)

    def test_attributes(self):
        """Frostbolt should have correct class attributes."""
        self.assertEqual(self.spell.name, "Frostbolt")
        self.assertEqual(self.spell.school, skills.EVOCATION)
        self.assertEqual(self.spell.min_mastery, MasteryLevel.BASIC)
        self.assertEqual(self.spell.target_type, "actor_hostile")
        self.assertEqual(self.spell.cooldown, 0)

    def test_deals_cold_damage(self):
        """Frostbolt should reduce target HP."""
        start_hp = self.char2.hp
        self.spell.cast(self.char1, self.char2)
        self.assertLess(self.char2.hp, start_hp)

    def test_deducts_mana(self):
        """Frostbolt should deduct 5 mana at tier 1."""
        start_mana = self.char1.mana
        self.spell.cast(self.char1, self.char2)
        self.assertEqual(self.char1.mana, start_mana - 5)

    @patch("world.spells.evocation.frostbolt.dice")
    def test_applies_slowed_on_successful_contest(self, mock_dice):
        """SLOWED should be applied when caster wins contested check."""
        # damage roll, caster d20, target d20
        mock_dice.roll.side_effect = [3, 18, 2]
        self.spell.cast(self.char1, self.char2)
        self.assertTrue(self.char2.has_effect("slowed"))
        self.assertTrue(self.char2.has_condition(Condition.SLOWED))

    @patch("world.spells.evocation.frostbolt.dice")
    def test_no_slow_on_failed_contest(self, mock_dice):
        """SLOWED should NOT be applied when target wins contested check."""
        # damage roll, caster d20, target d20
        mock_dice.roll.side_effect = [3, 2, 18]
        self.spell.cast(self.char1, self.char2)
        self.assertFalse(self.char2.has_effect("slowed"))

    @patch("world.spells.evocation.frostbolt.dice")
    def test_slowed_duration_scales_with_tier(self, mock_dice):
        """Tier 3 should apply SLOWED for 3 rounds."""
        self.char1.db.class_skill_mastery_levels = {"evocation": 3}
        # damage roll, caster d20 (high), target d20 (low)
        mock_dice.roll.side_effect = [3, 20, 1]
        self.spell.cast(self.char1, self.char2)
        effect = self.char2.get_named_effect("slowed")
        self.assertIsNotNone(effect)
        self.assertEqual(effect["duration"], 3)

    @patch("world.spells.evocation.frostbolt.dice")
    def test_damage_flat_across_tiers(self, mock_dice):
        """Damage should be 1d6 regardless of tier."""
        # At tier 1: damage=4, then contest rolls
        mock_dice.roll.side_effect = [4, 2, 18]
        self.char2.hp = 200
        self.spell.cast(self.char1, self.char2)
        tier1_damage = 200 - self.char2.hp

        # At tier 5: same damage=4
        self.char1.db.class_skill_mastery_levels = {"evocation": 5}
        self.char2.hp = 200
        mock_dice.roll.side_effect = [4, 2, 18]
        self.spell.cast(self.char1, self.char2)
        tier5_damage = 200 - self.char2.hp

        self.assertEqual(tier1_damage, tier5_damage)

    def test_cold_resistance_reduces_damage(self):
        """Cold resistance should reduce frostbolt damage."""
        self.char2.damage_resistances = {"cold": 50}
        self.char2.hp = 200
        self.spell.cast(self.char1, self.char2)
        # 1d6 max 6, 50% resist → max 3 damage
        self.assertGreaterEqual(self.char2.hp, 197)

    def test_multi_perspective_messages(self):
        """Cast should return first/second/third person messages."""
        success, result = self.spell.cast(self.char1, self.char2)
        self.assertTrue(success)
        self.assertIsInstance(result, dict)
        self.assertIn("first", result)
        self.assertIn("second", result)
        self.assertIn("third", result)

    def test_mastery_check(self):
        """UNSKILLED should not be able to cast Frostbolt."""
        self.char1.db.class_skill_mastery_levels = {"evocation": 0}
        success, msg = self.spell.cast(self.char1, self.char2)
        self.assertFalse(success)

