"""
Tests for the necromancy spell school.

Tests:
    - Registry: all necromancy spells registered with correct attributes
    - Drain Life: damage + heal, resistance interaction, max HP cap
    - Soul Harvest: unsafe AoE drain, caster heals total, excludes caster
    - Necromancy vs Undead: drain spells should not work against undead
    - School membership: get_spells_for_school returns expected set
    - Descriptions and mechanics: all spells have documentation

evennia test --settings settings tests.spell_tests.test_necromancy
"""

from unittest.mock import patch, MagicMock

from evennia.utils.test_resources import EvenniaTest

from enums.condition import Condition
from enums.mastery_level import MasteryLevel
from enums.skills_enum import skills
from world.spells.registry import SPELL_REGISTRY, get_spell, get_spells_for_school


# ================================================================== #
#  Necromancy Registry Tests
# ================================================================== #

class TestNecromancyRegistry(EvenniaTest):
    """Test all necromancy spells are registered correctly."""

    def create_script(self):
        pass

    def test_drain_life_registered(self):
        spell = get_spell("drain_life")
        self.assertIsNotNone(spell)
        self.assertEqual(spell.school, skills.NECROMANCY)
        self.assertEqual(spell.min_mastery, MasteryLevel.BASIC)
        self.assertEqual(spell.target_type, "actor_hostile")
        self.assertEqual(spell.mana_cost, {1: 5, 2: 8, 3: 10, 4: 14, 5: 16})

    def test_raise_dead_registered(self):
        spell = get_spell("raise_dead")
        self.assertIsNotNone(spell)
        self.assertEqual(spell.school, skills.NECROMANCY)
        self.assertEqual(spell.min_mastery, MasteryLevel.SKILLED)
        self.assertEqual(spell.target_type, "none")

    def test_vampiric_touch_registered(self):
        spell = get_spell("vampiric_touch")
        self.assertIsNotNone(spell)
        self.assertEqual(spell.school, skills.NECROMANCY)
        self.assertEqual(spell.min_mastery, MasteryLevel.SKILLED)
        self.assertEqual(spell.target_type, "actor_hostile")

    def test_soul_harvest_registered(self):
        spell = get_spell("soul_harvest")
        self.assertIsNotNone(spell)
        self.assertEqual(spell.school, skills.NECROMANCY)
        self.assertEqual(spell.min_mastery, MasteryLevel.EXPERT)
        self.assertEqual(spell.target_type, "actor_hostile")
        self.assertEqual(spell.aoe, "unsafe_self")
        self.assertEqual(spell.mana_cost, {3: 28, 4: 39, 5: 49})

    def test_raise_lich_registered(self):
        spell = get_spell("raise_lich")
        self.assertIsNotNone(spell)
        self.assertEqual(spell.school, skills.NECROMANCY)
        self.assertEqual(spell.min_mastery, MasteryLevel.MASTER)

    def test_death_mark_registered(self):
        spell = get_spell("death_mark")
        self.assertIsNotNone(spell)
        self.assertEqual(spell.school, skills.NECROMANCY)
        self.assertEqual(spell.min_mastery, MasteryLevel.GRANDMASTER)
        self.assertEqual(spell.mana_cost, {5: 100})

    def test_necromancy_school_has_all_spells(self):
        necro = get_spells_for_school("necromancy")
        expected = {
            "drain_life", "raise_dead", "vampiric_touch",
            "soul_harvest", "raise_lich", "death_mark",
            "raise_skeleton", "fear",
        }
        self.assertEqual(set(necro.keys()), expected)

    def test_necromancy_description_and_mechanics(self):
        """All necromancy spells should have description and mechanics."""
        for key in ["drain_life", "raise_dead", "vampiric_touch",
                     "soul_harvest", "raise_lich", "death_mark"]:
            spell = get_spell(key)
            self.assertTrue(spell.description, f"{key} missing description")
            self.assertTrue(spell.mechanics, f"{key} missing mechanics")


# ================================================================== #
#  Drain Life Execution Tests
# ================================================================== #

class TestDrainLife(EvenniaTest):
    """Test Drain Life spell execution — damage + self-heal."""

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.spell = get_spell("drain_life")
        self.char1.db.class_skill_mastery_levels = {"necromancy": 1}
        self.char1.mana = 100
        self.char1.hp = 50
        self.char1.hp_max = 100
        self.char2.hp = 100
        self.char2.hp_max = 100
        self.char2.damage_resistances = {}

    def test_drain_life_deals_damage(self):
        """Drain Life should deal cold damage to target."""
        success, result = self.spell.cast(self.char1, self.char2)
        self.assertTrue(success)
        self.assertLess(self.char2.hp, 100)

    def test_drain_life_heals_caster(self):
        """Drain Life should heal caster for damage dealt."""
        hp_before = self.char1.hp
        success, result = self.spell.cast(self.char1, self.char2)
        self.assertTrue(success)
        self.assertGreater(self.char1.hp, hp_before)

    def test_drain_life_heal_capped_at_max(self):
        """Healing should not exceed max HP."""
        self.char1.hp = 100  # Already at max
        success, result = self.spell.cast(self.char1, self.char2)
        self.assertTrue(success)
        self.assertEqual(self.char1.hp, 100)

    def test_drain_life_deducts_mana(self):
        """Should deduct mana cost (5 at tier 1)."""
        self.spell.cast(self.char1, self.char2)
        self.assertEqual(self.char1.mana, 95)

    def test_drain_life_mastery_check(self):
        """Should fail without necromancy mastery."""
        self.char1.db.class_skill_mastery_levels = {}
        success, msg = self.spell.cast(self.char1, self.char2)
        self.assertFalse(success)
        self.assertIn("mastery", msg.lower())

    def test_drain_life_multi_perspective_messages(self):
        """Should return first/second/third person messages."""
        success, result = self.spell.cast(self.char1, self.char2)
        self.assertTrue(success)
        self.assertIsInstance(result, dict)
        self.assertIn("first", result)
        self.assertIn("second", result)
        self.assertIn("third", result)

    def test_drain_life_damage_scaling_tier1(self):
        """At tier 1, should roll 2d6 (2-12 damage)."""
        with patch("world.spells.necromancy.drain_life.dice") as mock_dice:
            mock_dice.roll.return_value = 7  # fixed roll
            success, result = self.spell.cast(self.char1, self.char2)
            mock_dice.roll.assert_called_with("2d6")

    def test_drain_life_damage_scaling_tier5(self):
        """At tier 5 (GM), should roll 6d6."""
        self.char1.db.class_skill_mastery_levels = {"necromancy": 5}
        with patch("world.spells.necromancy.drain_life.dice") as mock_dice:
            mock_dice.roll.return_value = 21  # fixed roll
            success, result = self.spell.cast(self.char1, self.char2)
            mock_dice.roll.assert_called_with("6d6")

    def test_drain_life_cold_resistance_reduces_both(self):
        """Cold resistance should reduce both damage AND healing."""
        self.char2.damage_resistances = {"cold": 50}
        self.char1.hp = 50
        with patch("world.spells.necromancy.drain_life.dice") as mock_dice:
            mock_dice.roll.return_value = 10
            success, result = self.spell.cast(self.char1, self.char2)
            # 10 raw, 50% resist = 5 actual damage
            self.assertEqual(self.char2.hp, 95)
            # Caster heals for 5 (the actual damage dealt)
            self.assertEqual(self.char1.hp, 55)

    def test_drain_life_kills_target(self):
        """Should trigger death if target reaches 0 HP."""
        self.char2.hp = 1
        with patch("world.spells.necromancy.drain_life.dice") as mock_dice:
            mock_dice.roll.return_value = 10
            with patch.object(self.char2, "die") as mock_die:
                self.spell.cast(self.char1, self.char2)
                mock_die.assert_called_once_with("spell", killer=None)


# ================================================================== #
#  Soul Harvest Execution Tests
# ================================================================== #

class TestSoulHarvest(EvenniaTest):
    """Test Soul Harvest — unsafe AoE drain, caster heals total."""

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.spell = get_spell("soul_harvest")
        self.char1.db.class_skill_mastery_levels = {"necromancy": 3}
        self.char1.db.spell_cooldowns = {}
        self.char1.mana = 500
        self.char1.hp = 50
        self.char1.hp_max = 100
        self.char2.hp = 200
        self.char2.hp_max = 200
        self.char2.damage_resistances = {}

    @patch("world.spells.necromancy.soul_harvest.dice")
    def test_soul_harvest_damages_primary(self, mock_dice):
        """Primary target should take necrotic damage on failed CON save."""
        # damage roll, save DC roll, target CON save (fails)
        mock_dice.roll.side_effect = [28, 20, 1]
        self.char2.constitution = 10
        success, result = self.spell.cast(self.char1, self.char2)
        self.assertTrue(success)
        self.assertLess(self.char2.hp, 200)

    @patch("world.spells.necromancy.soul_harvest.dice")
    def test_soul_harvest_save_negates(self, mock_dice):
        """Successful CON save should negate all damage."""
        # damage roll, save DC roll (low), target CON save (high)
        mock_dice.roll.side_effect = [28, 1, 20]
        self.char2.constitution = 10
        self.spell.cast(self.char1, self.char2)
        self.assertEqual(self.char2.hp, 200)

    @patch("world.spells.necromancy.soul_harvest.dice")
    def test_soul_harvest_heals_caster(self, mock_dice):
        """Caster should heal for total damage dealt on failed saves."""
        # damage roll, save DC roll, target CON save (fails)
        mock_dice.roll.side_effect = [28, 20, 1]
        self.char2.constitution = 10
        success, result = self.spell.cast(self.char1, self.char2)
        self.assertTrue(success)
        # Started at 50, should be healed
        self.assertGreater(self.char1.hp, 50)

    @patch("world.spells.necromancy.soul_harvest.dice")
    def test_soul_harvest_heal_capped_at_max(self, mock_dice):
        """Caster heal from Soul Harvest capped at max HP."""
        self.char1.hp = 100  # Already full
        mock_dice.roll.side_effect = [28, 20, 1]
        self.char2.constitution = 10
        self.spell.cast(self.char1, self.char2)
        self.assertEqual(self.char1.hp, 100)

    def test_soul_harvest_deducts_mana(self):
        """Should deduct 28 mana at tier 3."""
        self.spell.cast(self.char1, self.char2)
        self.assertEqual(self.char1.mana, 472)

    def test_soul_harvest_returns_message_dict(self):
        """Should return first and third person messages (second is None)."""
        success, result = self.spell.cast(self.char1, self.char2)
        self.assertTrue(success)
        self.assertIn("first", result)
        self.assertIsNone(result["second"])
        self.assertIn("third", result)

    def test_soul_harvest_necrotic_resistance(self):
        """Necrotic resistance should reduce damage and therefore healing."""
        self.char2.damage_resistances = {"necrotic": 50}
        with patch("world.spells.necromancy.soul_harvest.dice") as mock_dice:
            # damage roll, save DC roll (high), target CON save (fails)
            mock_dice.roll.side_effect = [20, 20, 1]
            self.char2.constitution = 10
            self.spell.cast(self.char1, self.char2)
            # 20 raw, 50% resist = 10 actual
            self.assertEqual(self.char2.hp, 190)


# ================================================================== #
#  Necromancy vs Undead Tests
# ================================================================== #

class TestNecromancyVsUndead(EvenniaTest):
    """Necromancy drain spells should not work against undead."""

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.char1.db.class_skill_mastery_levels = {"necromancy": 3}
        self.char1.db.spell_cooldowns = {}
        self.char1.mana = 500
        self.char1.hp = 50
        self.char1.hp_max = 100
        # Tag char2 as undead
        self.char2.tags.add("undead", category="creature_type")
        self.char2.hp = 100
        self.char2.hp_max = 100
        self.char2.damage_resistances = {}

    def test_drain_life_fails_on_undead(self):
        """Drain Life should fail against undead — no damage, no heal."""
        spell = get_spell("drain_life")
        hp_before = self.char2.hp
        caster_hp_before = self.char1.hp
        success, result = spell.cast(self.char1, self.char2)
        self.assertFalse(success)
        self.assertEqual(self.char2.hp, hp_before)
        self.assertEqual(self.char1.hp, caster_hp_before)
        self.assertIn("no life force", result["first"].lower())

    def test_vampiric_touch_fails_on_undead(self):
        """Vampiric Touch should have no effect on undead."""
        spell = get_spell("vampiric_touch")
        self.char1.db.class_skill_mastery_levels = {"necromancy": 2}
        hp_before = self.char2.hp
        success, result = spell.cast(self.char1, self.char2)
        self.assertTrue(success)  # spell cast but no effect
        self.assertEqual(self.char2.hp, hp_before)
        self.assertIn("no life to drain", result["first"].lower())

    def test_soul_harvest_skips_undead_primary(self):
        """Soul Harvest on an undead primary target should drain nothing."""
        spell = get_spell("soul_harvest")
        hp_before = self.char2.hp
        success, result = spell.cast(self.char1, self.char2)
        self.assertTrue(success)
        # Undead char2 should take no damage
        self.assertEqual(self.char2.hp, hp_before)
        # Only undead — nothing to drain message
        self.assertIn("nothing", result["first"].lower())

    def test_soul_harvest_mixed_targets(self):
        """Soul Harvest should damage living secondaries but skip undead."""
        spell = get_spell("soul_harvest")
        # char2 is undead (tagged in setUp), make a living secondary
        from evennia.utils import create
        living = create.create_object(
            "typeclasses.actors.character.FCMCharacter",
            key="living_target",
            location=self.room1,
        )
        living.hp = 200
        living.hp_max = 200
        living.damage_resistances = {}
        living.constitution = 10
        # Cast on undead char2, living as secondary
        with patch("world.spells.necromancy.soul_harvest.dice") as mock_dice:
            # damage, save DC (high), living CON save (fails)
            mock_dice.roll.side_effect = [28, 20, 1]
            success, result = spell.cast(
                self.char1, self.char2, secondaries=[living],
            )
            self.assertTrue(success)
            # Living target should take damage
            self.assertLess(living.hp, 200)
            # Undead char2 should be unharmed
            self.assertEqual(self.char2.hp, 100)


# ================================================================== #
#  Vampiric Touch Tests
# ================================================================== #

class TestVampiricTouch(EvenniaTest):
    """Test Vampiric Touch spell execution."""

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.spell = get_spell("vampiric_touch")
        self.char1.db.class_skill_mastery_levels = {"necromancy": 2}
        self.char1.mana = 100
        self.char1.mana_max = 100
        self.char1.hp = 50
        self.char1.hp_max = 100
        self.char1.intelligence = 14  # +2 mod
        self.char1.db.spell_cooldowns = {}
        self.char2.hp = 200
        self.char2.hp_max = 200

    def test_registration(self):
        """Vampiric Touch should be in the registry."""
        self.assertIn("vampiric_touch", SPELL_REGISTRY)

    def test_attributes(self):
        """Vampiric Touch should have correct class attributes."""
        self.assertEqual(self.spell.name, "Vampiric Touch")
        self.assertEqual(self.spell.school, skills.NECROMANCY)
        self.assertEqual(self.spell.min_mastery, MasteryLevel.SKILLED)
        self.assertEqual(self.spell.target_type, "actor_hostile")
        self.assertEqual(self.spell.cooldown, 0)
        self.assertIn("vt", self.spell.aliases)
        self.assertIn("vamp", self.spell.aliases)

    @patch("world.spells.necromancy.vampiric_touch.dice")
    def test_touch_attack_miss(self, mock_dice):
        """Miss should deal no damage but still spend mana."""
        mock_dice.roll.return_value = 1
        start_mana = self.char1.mana
        start_hp = self.char2.hp
        success, result = self.spell.cast(self.char1, self.char2)
        self.assertTrue(success)
        self.assertEqual(self.char2.hp, start_hp)
        self.assertLess(self.char1.mana, start_mana)
        self.assertIn("misses", result["first"])

    @patch("world.spells.necromancy.vampiric_touch.dice")
    def test_touch_attack_hit_heals(self, mock_dice):
        """Hit should deal damage and heal the caster."""
        mock_dice.roll.side_effect = [20, 4]
        hp_before = self.char1.hp
        self.spell.cast(self.char1, self.char2)
        self.assertLess(self.char2.hp, 200)
        self.assertGreater(self.char1.hp, hp_before)

    @patch("world.spells.necromancy.vampiric_touch.dice")
    def test_healing_above_max_hp(self, mock_dice):
        """Caster HP should be able to exceed effective_hp_max."""
        self.char1.hp = self.char1.effective_hp_max
        mock_dice.roll.side_effect = [20, 5]
        self.spell.cast(self.char1, self.char2)
        self.assertGreater(self.char1.hp, self.char1.effective_hp_max)

    @patch("world.spells.necromancy.vampiric_touch.dice")
    def test_bonus_hp_tracking(self, mock_dice):
        """db.vampiric_bonus_hp should track HP above max."""
        self.char1.hp = self.char1.effective_hp_max
        mock_dice.roll.side_effect = [20, 5]
        self.spell.cast(self.char1, self.char2)
        bonus = self.char1.db.vampiric_bonus_hp or 0
        self.assertEqual(bonus, 5)

    def test_mana_cost_base_bracket(self):
        """At +0 bonus HP, cost should be 3% of max mana."""
        self.char1.mana_max = 100
        cost, error = self.spell._get_mana_cost(self.char1)
        self.assertIsNone(error)
        self.assertEqual(cost, 3)

    def test_mana_cost_escalation(self):
        """Higher bonus HP bracket should cost more mana."""
        self.char1.mana_max = 100
        self.char1.db.vampiric_bonus_hp = 300
        cost, error = self.spell._get_mana_cost(self.char1)
        self.assertIsNone(error)
        self.assertEqual(cost, 16)

    def test_mana_cost_hard_cap(self):
        """At +1000 bonus HP, should return error (101% cost)."""
        self.char1.db.vampiric_bonus_hp = 1000
        cost, error = self.spell._get_mana_cost(self.char1)
        self.assertIsNotNone(error)
        self.assertIn("too far", error)

    @patch("world.spells.necromancy.vampiric_touch.dice")
    def test_vampiric_effect_applied(self, mock_dice):
        """has_effect('vampiric') should be True after successful cast."""
        mock_dice.roll.side_effect = [20, 4]
        self.spell.cast(self.char1, self.char2)
        self.assertTrue(self.char1.has_effect("vampiric"))

    @patch("world.spells.necromancy.vampiric_touch.dice")
    def test_timer_expiry_hp_loss(self, mock_dice):
        """When vampiric effect removed, bonus HP should be lost (floor 1)."""
        self.char1.hp = self.char1.effective_hp_max
        mock_dice.roll.side_effect = [20, 5]
        self.spell.cast(self.char1, self.char2)
        self.assertGreater(self.char1.hp, self.char1.effective_hp_max)

        from world.spells.necromancy.vampiric_touch import remove_vampiric
        remove_vampiric(self.char1)

        self.assertLessEqual(self.char1.hp, self.char1.effective_hp_max)
        self.assertGreaterEqual(self.char1.hp, 1)
        self.assertIsNone(self.char1.db.vampiric_bonus_hp)

    @patch("world.spells.necromancy.vampiric_touch.dice")
    def test_necrotic_resistance_reduces_healing(self, mock_dice):
        """Necrotic resistance should reduce both damage and healing."""
        self.char2.damage_resistances = {"necrotic": 50}
        mock_dice.roll.side_effect = [20, 6]
        hp_before = self.char1.hp
        self.spell.cast(self.char1, self.char2)
        heal_amount = self.char1.hp - hp_before
        self.assertEqual(heal_amount, 3)

    @patch("world.spells.necromancy.vampiric_touch.dice")
    def test_damage_scaling(self, mock_dice):
        """SKILLED=1d6 range, GM=4d6 range."""
        mock_dice.roll.side_effect = [20, 4]
        self.spell.cast(self.char1, self.char2)
        tier2_damage = 200 - self.char2.hp
        self.assertGreaterEqual(tier2_damage, 1)
        self.assertLessEqual(tier2_damage, 6)

        self.char1.db.class_skill_mastery_levels = {"necromancy": 5}
        self.char2.hp = 200
        self.char1.hp = 50
        self.char1.mana = 100
        self.char1.attributes.remove("vampiric_bonus_hp")
        if self.char1.has_effect("vampiric"):
            self.char1.remove_named_effect("vampiric")
        existing = self.char1.scripts.get("vampiric_timer")
        if existing:
            existing[0].delete()
        mock_dice.roll.side_effect = [20, 14]
        self.spell.cast(self.char1, self.char2)
        tier5_damage = 200 - self.char2.hp
        self.assertGreaterEqual(tier5_damage, 4)
        self.assertLessEqual(tier5_damage, 24)

    def test_mastery_check(self):
        """BASIC mastery should not be able to cast Vampiric Touch."""
        self.char1.db.class_skill_mastery_levels = {"necromancy": 1}
        success, msg = self.spell.cast(self.char1, self.char2)
        self.assertFalse(success)
        self.assertIn("mastery", msg.lower())


# ================================================================== #
#  SLOWED Combat Mechanic Tests
# ================================================================== #

class TestSlowedMechanic(EvenniaTest):
    """Test SLOWED effect enforcement in combat_handler."""

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.char1.hp = 200
        self.char1.hp_max = 200
        self.char2.hp = 200
        self.char2.hp_max = 200

    def _start_combat(self, attacker, target):
        """Put attacker into combat against target."""
        from combat.combat_handler import CombatHandler
        from evennia.utils.create import create_script
        handler = create_script(
            CombatHandler, obj=attacker, key="combat_handler",
            autostart=False,
        )
        handler.start()
        handler.queue_action({
            "key": "attack", "target": target,
            "dt": 3, "repeat": True,
        })
        return handler

    @patch("combat.combat_utils.execute_attack")
    def test_slowed_caps_attacks_at_one(self, mock_attack):
        """SLOWED actor with multiple APR should only get 1 attack."""
        self.char1.attacks_per_round = 3
        handler = self._start_combat(self.char1, self.char2)
        self.char1.apply_named_effect(
            key="slowed",
            condition=Condition.SLOWED,
            duration=3,
            duration_type="combat_rounds",
        )
        handler.execute_next_action()
        self.assertEqual(mock_attack.call_count, 1)

    @patch("combat.combat_utils.execute_attack")
    def test_slowed_blocks_offhand(self, mock_attack):
        """SLOWED actor with off-hand weapon should only get 1 main attack."""
        self.char1.attacks_per_round = 1
        handler = self._start_combat(self.char1, self.char2)

        self.char1.apply_named_effect(
            key="slowed",
            condition=Condition.SLOWED,
            duration=3,
            duration_type="combat_rounds",
        )

        mock_weapon = MagicMock()
        mock_weapon.get_extra_attacks.return_value = 0
        mock_weapon.get_parries_per_round.return_value = 0
        mock_weapon.get_parry_advantage.return_value = False
        mock_weapon.get_offhand_attacks.return_value = 1
        mock_weapon.get_reach_counters_per_round.return_value = 0
        mock_weapon.get_stun_checks_per_round.return_value = 0
        mock_weapon.get_disarm_checks_per_round.return_value = 0

        mock_get_offhand = MagicMock(return_value=MagicMock())

        with patch("combat.combat_utils.get_weapon", return_value=mock_weapon):
            with patch("combat.combat_utils.get_offhand_weapon", mock_get_offhand):
                handler.execute_next_action()

        self.assertEqual(mock_attack.call_count, 1)
        mock_get_offhand.assert_not_called()

    @patch("combat.combat_utils.execute_attack")
    def test_slowed_per_round_message(self, mock_attack):
        """SLOWED actor should receive sluggish message each round."""
        self.char1.attacks_per_round = 1
        handler = self._start_combat(self.char1, self.char2)
        self.char1.apply_named_effect(
            key="slowed",
            condition=Condition.SLOWED,
            duration=3,
            duration_type="combat_rounds",
        )
        mock_msg = MagicMock()
        original_msg = self.char1.msg
        self.char1.msg = mock_msg
        try:
            handler.execute_next_action()
        finally:
            self.char1.msg = original_msg
        found = False
        for call in mock_msg.call_args_list:
            msg = call.args[0] if call.args else ""
            if "SLOWED" in msg and "sluggish" in msg:
                found = True
                break
        self.assertTrue(found, "SLOWED per-round message not found")
