"""
Tests for the Shadowcloak abjuration spell.

Tests:
    - Registry: spell registered with correct attributes
    - Solo cast: applies shadowcloaked effect to caster
    - Group cast: applies to caster + same-room followers
    - Anti-stacking: skips already-affected targets, refunds if all affected
    - Scaling: bonus and duration scale with mastery tier
    - Mastery gate: unskilled caster blocked

evennia test --settings settings tests.spell_tests.test_shadowcloak
"""

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from enums.mastery_level import MasteryLevel
from enums.skills_enum import skills
from world.spells.registry import get_spell, get_spells_for_school

_CHAR = "typeclasses.actors.character.FCMCharacter"


class TestShadowcloakRegistry(EvenniaTest):
    """Test Shadowcloak is registered correctly."""

    def create_script(self):
        pass

    def test_registered(self):
        spell = get_spell("shadowcloak")
        self.assertIsNotNone(spell)
        self.assertEqual(spell.school, skills.ABJURATION)
        self.assertEqual(spell.min_mastery, MasteryLevel.SKILLED)
        self.assertEqual(spell.target_type, "none")
        self.assertEqual(spell.mana_cost, {2: 12, 3: 15, 4: 20, 5: 24})

    def test_in_abjuration_school(self):
        abj = get_spells_for_school("abjuration")
        self.assertIn("shadowcloak", abj)

    def test_has_description_and_mechanics(self):
        spell = get_spell("shadowcloak")
        self.assertTrue(spell.description)
        self.assertTrue(spell.mechanics)


class TestShadowcloakSoloCast(EvenniaTest):
    """Test Shadowcloak when caster is solo (not in a group)."""

    character_typeclass = _CHAR

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.spell = get_spell("shadowcloak")
        self.char1.db.class_skill_mastery_levels = {"abjuration": 2}
        self.char1.mana = 100

    def test_solo_applies_effect(self):
        """Casting solo should apply shadowcloaked to caster."""
        success, result = self.spell.cast(self.char1)
        self.assertTrue(success)
        self.assertTrue(self.char1.has_effect("shadowcloaked"))

    def test_solo_increments_stealth_bonus(self):
        """Should increment stealth_bonus by the tier bonus."""
        base = self.char1.stealth_bonus
        self.spell.cast(self.char1)
        self.assertEqual(self.char1.stealth_bonus, base + 4)

    def test_solo_deducts_mana(self):
        """Should deduct mana at tier 2 cost."""
        self.spell.cast(self.char1)
        self.assertEqual(self.char1.mana, 88)

    def test_solo_message_includes_bonus_and_duration(self):
        """Cast message should include stealth bonus and duration."""
        success, result = self.spell.cast(self.char1)
        self.assertTrue(success)
        self.assertIn("+4 stealth", result["first"])
        self.assertIn("4 min", result["first"])

    def test_solo_message_says_yourself(self):
        """Solo cast message should reference wrapping self."""
        success, result = self.spell.cast(self.char1)
        self.assertIn("yourself", result["first"].lower())

    def test_solo_third_person_message(self):
        """Third person message should reference caster."""
        success, result = self.spell.cast(self.char1)
        self.assertIn(self.char1.key, result["third"])


class TestShadowcloakAntiStacking(EvenniaTest):
    """Test anti-stacking behaviour."""

    character_typeclass = _CHAR

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.spell = get_spell("shadowcloak")
        self.char1.db.class_skill_mastery_levels = {"abjuration": 2}
        self.char1.mana = 100

    def test_anti_stacking_refunds_mana(self):
        """Recasting when already affected should refund mana."""
        self.spell.cast(self.char1)
        mana_after = self.char1.mana
        success, result = self.spell.cast(self.char1)
        self.assertFalse(success)
        self.assertEqual(self.char1.mana, mana_after)

    def test_anti_stacking_message(self):
        """Should show already-affected message."""
        self.spell.cast(self.char1)
        success, result = self.spell.cast(self.char1)
        self.assertFalse(success)
        self.assertIn("already", result["first"].lower())


class TestShadowcloakScaling(EvenniaTest):
    """Test bonus and duration scaling across tiers."""

    character_typeclass = _CHAR

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.spell = get_spell("shadowcloak")
        self.char1.mana = 200

    def test_skilled_bonus(self):
        """SKILLED tier should give +4 stealth."""
        self.char1.db.class_skill_mastery_levels = {"abjuration": 2}
        base = self.char1.stealth_bonus
        self.spell.cast(self.char1)
        self.assertEqual(self.char1.stealth_bonus, base + 4)

    def test_expert_bonus(self):
        """EXPERT tier should give +6 stealth."""
        self.char1.db.class_skill_mastery_levels = {"abjuration": 3}
        base = self.char1.stealth_bonus
        self.spell.cast(self.char1)
        self.assertEqual(self.char1.stealth_bonus, base + 6)

    def test_master_bonus(self):
        """MASTER tier should give +8 stealth."""
        self.char1.db.class_skill_mastery_levels = {"abjuration": 4}
        base = self.char1.stealth_bonus
        self.spell.cast(self.char1)
        self.assertEqual(self.char1.stealth_bonus, base + 8)

    def test_grandmaster_bonus(self):
        """GRANDMASTER tier should give +10 stealth."""
        self.char1.db.class_skill_mastery_levels = {"abjuration": 5}
        base = self.char1.stealth_bonus
        self.spell.cast(self.char1)
        self.assertEqual(self.char1.stealth_bonus, base + 10)

    def test_mana_scaling(self):
        """Mana costs should match tier scaling."""
        expected = {2: 12, 3: 15, 4: 20, 5: 24}
        for tier, cost in expected.items():
            self.char1.db.class_skill_mastery_levels = {"abjuration": tier}
            self.char1.mana = 200
            if self.char1.has_effect("shadowcloaked"):
                self.char1.remove_named_effect("shadowcloaked")
            self.spell.cast(self.char1)
            self.assertEqual(self.char1.mana, 200 - cost,
                             f"Tier {tier} mana cost mismatch")


class TestShadowcloakMasteryGate(EvenniaTest):
    """Test mastery requirements."""

    character_typeclass = _CHAR

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.spell = get_spell("shadowcloak")
        self.char1.mana = 100

    def test_no_mastery_blocked(self):
        """Should fail without abjuration mastery."""
        self.char1.db.class_skill_mastery_levels = {}
        success, msg = self.spell.cast(self.char1)
        self.assertFalse(success)

    def test_basic_mastery_blocked(self):
        """BASIC mastery should be insufficient for SKILLED spell."""
        self.char1.db.class_skill_mastery_levels = {"abjuration": 1}
        success, msg = self.spell.cast(self.char1)
        self.assertFalse(success)


class TestShadowcloakGroupCast(EvenniaTest):
    """Test group targeting behaviour."""

    character_typeclass = _CHAR

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.spell = get_spell("shadowcloak")
        self.char1.db.class_skill_mastery_levels = {"abjuration": 2}
        self.char1.mana = 100
        # Create a follower in the same room
        self.follower = create_object(_CHAR, key="Follower", location=self.char1.location)
        self.follower.following = self.char1

    def test_group_applies_to_caster(self):
        """Group cast should apply to caster."""
        self.spell.cast(self.char1)
        self.assertTrue(self.char1.has_effect("shadowcloaked"))

    def test_group_applies_to_follower(self):
        """Group cast should apply to follower."""
        self.spell.cast(self.char1)
        self.assertTrue(self.follower.has_effect("shadowcloaked"))

    def test_group_follower_gets_bonus(self):
        """Follower should get stealth bonus."""
        base = self.follower.stealth_bonus
        self.spell.cast(self.char1)
        self.assertEqual(self.follower.stealth_bonus, base + 4)

    def test_group_message_mentions_allies(self):
        """Group cast message should mention allies."""
        success, result = self.spell.cast(self.char1)
        self.assertIn("group", result["first"].lower())
        self.assertIn("1 ally", result["first"])

    def test_group_excludes_different_room(self):
        """Follower in a different room should not be affected."""
        other_room = create_object(
            "typeclasses.terrain.rooms.room_base.RoomBase", key="OtherRoom"
        )
        self.follower.location = other_room
        self.spell.cast(self.char1)
        self.assertTrue(self.char1.has_effect("shadowcloaked"))
        self.assertFalse(self.follower.has_effect("shadowcloaked"))

    def test_group_partial_anti_stacking(self):
        """Already-affected group members should be skipped."""
        # Pre-apply effect to follower
        from enums.named_effect import NamedEffect
        ne = NamedEffect.SHADOWCLOAKED
        self.follower.apply_named_effect(
            key=ne.value,
            source=self.char1,
            effects=[{"type": "stat_bonus", "stat": "stealth_bonus", "value": 4}],
            duration=240,
            duration_type="seconds",
            messages={
                "start": ne.get_start_message(),
                "end": ne.get_end_message(),
                "start_third": ne.get_start_message_third_person("{name}"),
                "end_third": ne.get_end_message_third_person("{name}"),
            },
        )
        # Cast — should still apply to caster, skip follower
        success, result = self.spell.cast(self.char1)
        self.assertTrue(success)
        self.assertTrue(self.char1.has_effect("shadowcloaked"))

    def test_caster_following_someone_gets_group(self):
        """Caster who is following someone should also get group targeting."""
        leader = create_object(_CHAR, key="Leader", location=self.char1.location)
        self.char1.following = leader
        self.follower.following = self.char1
        self.spell.cast(self.char1)
        # All three should be affected
        self.assertTrue(leader.has_effect("shadowcloaked"))
        self.assertTrue(self.char1.has_effect("shadowcloaked"))
        self.assertTrue(self.follower.has_effect("shadowcloaked"))
