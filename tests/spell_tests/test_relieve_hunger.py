"""
Tests for the Relieve Hunger divine_healing spell.

Relieve Hunger is a cleric survival utility that steps the hunger meter
up by N stages where N = mastery tier. Caster-only at BASIC/SKILLED/
EXPERT, group at MASTER/GM (mirrors shadowcloak's same-room targeting).
Does NOT create bread — the economic safety rail — and does NOT set
the hunger_free_pass_tick, same rule forage uses.

evennia test --settings settings tests.spell_tests.test_relieve_hunger
"""

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from enums.hunger_level import HungerLevel
from enums.mastery_level import MasteryLevel
from enums.skills_enum import skills
from world.spells.registry import get_spell, get_spells_for_school


_CHAR = "typeclasses.actors.character.FCMCharacter"
_ROOM = "typeclasses.terrain.rooms.room_base.RoomBase"


class TestRelieveHungerRegistry(EvenniaTest):
    """Registry + metadata shape."""

    def create_script(self):
        pass

    def test_registered(self):
        spell = get_spell("relieve_hunger")
        self.assertIsNotNone(spell)
        self.assertEqual(spell.school, skills.DIVINE_HEALING)
        self.assertEqual(spell.min_mastery, MasteryLevel.BASIC)
        self.assertEqual(spell.target_type, "none")

    def test_in_divine_healing_school(self):
        dh = get_spells_for_school("divine_healing")
        self.assertIn("relieve_hunger", dh)

    def test_mana_scales_with_tier(self):
        spell = get_spell("relieve_hunger")
        self.assertEqual(spell.mana_cost, {1: 5, 2: 8, 3: 12, 4: 16, 5: 20})

    def test_aliases_include_satiate(self):
        spell = get_spell("relieve_hunger")
        self.assertIn("satiate", spell.aliases)


class RelieveHungerTestBase(EvenniaTest):
    character_typeclass = _CHAR
    room_typeclass = _ROOM

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.spell = get_spell("relieve_hunger")
        self.char1.base_mana_max = 200
        self.char1.mana_max = 200
        self.char1.mana = 200
        self.char1.hunger_level = HungerLevel.STARVING
        self.char1.hunger_free_pass_tick = False

    def _set_tier(self, tier):
        self.char1.db.class_skill_mastery_levels = {"divine_healing": tier}


class TestRelieveHungerSoloScaling(RelieveHungerTestBase):
    """Caster-only tiers (BASIC/SKILLED/EXPERT)."""

    def test_basic_steps_hunger_up_one(self):
        self._set_tier(1)
        self.char1.hunger_level = HungerLevel.STARVING  # 1
        self.spell.cast(self.char1)
        self.assertEqual(self.char1.hunger_level, HungerLevel.FAMISHED)  # 2

    def test_skilled_steps_hunger_up_two(self):
        self._set_tier(2)
        self.char1.hunger_level = HungerLevel.STARVING  # 1
        self.spell.cast(self.char1)
        self.assertEqual(self.char1.hunger_level, HungerLevel.HUNGRY)  # 3

    def test_expert_steps_hunger_up_three(self):
        self._set_tier(3)
        self.char1.hunger_level = HungerLevel.STARVING  # 1
        self.spell.cast(self.char1)
        self.assertEqual(self.char1.hunger_level, HungerLevel.PECKISH)  # 4

    def test_starving_plus_five_caps_at_nourished(self):
        """STARVING (1) + 5 = NOURISHED (6), not overflow."""
        self._set_tier(5)
        self.char1.hunger_level = HungerLevel.STARVING
        self.spell.cast(self.char1)
        self.assertEqual(self.char1.hunger_level, HungerLevel.NOURISHED)  # 6

    def test_peckish_plus_five_caps_at_full(self):
        """PECKISH (4) + 5 = 9 → capped at FULL (8)."""
        self._set_tier(5)
        self.char1.hunger_level = HungerLevel.PECKISH  # 4
        self.spell.cast(self.char1)
        self.assertEqual(self.char1.hunger_level, HungerLevel.FULL)  # 8


class TestRelieveHungerSoloRefusal(RelieveHungerTestBase):
    """Already-full caster refunds mana."""

    def test_full_caster_refunds_mana(self):
        self._set_tier(1)
        self.char1.hunger_level = HungerLevel.FULL
        mana_before = self.char1.mana
        success, result = self.spell.cast(self.char1)
        self.assertFalse(success)
        self.assertEqual(self.char1.mana, mana_before)

    def test_full_caster_message(self):
        self._set_tier(1)
        self.char1.hunger_level = HungerLevel.FULL
        success, result = self.spell.cast(self.char1)
        self.assertIn("already full", result["first"].lower())


class TestRelieveHungerNoFreePass(RelieveHungerTestBase):
    """Spell must not set hunger_free_pass_tick — bread retains its edge."""

    def test_free_pass_not_set_on_cast(self):
        self._set_tier(5)
        self.char1.hunger_level = HungerLevel.STARVING
        self.char1.hunger_free_pass_tick = False
        self.spell.cast(self.char1)
        self.assertFalse(self.char1.hunger_free_pass_tick)

    def test_free_pass_not_set_even_landing_at_full(self):
        """Even when the cast lands at FULL, free-pass stays off."""
        self._set_tier(5)
        self.char1.hunger_level = HungerLevel.PECKISH  # will cap at FULL
        self.char1.hunger_free_pass_tick = False
        self.spell.cast(self.char1)
        self.assertEqual(self.char1.hunger_level, HungerLevel.FULL)
        self.assertFalse(self.char1.hunger_free_pass_tick)


class TestRelieveHungerGroupCast(RelieveHungerTestBase):
    """MASTER/GM tiers apply to caster + same-room group members."""

    def setUp(self):
        super().setUp()
        self.follower = create_object(
            _CHAR, key="Follower", location=self.char1.location
        )
        self.follower.following = self.char1
        self.follower.hunger_level = HungerLevel.STARVING
        self.follower.hunger_free_pass_tick = False

    def test_master_feeds_caster_and_follower(self):
        self._set_tier(4)
        self.char1.hunger_level = HungerLevel.STARVING
        self.follower.hunger_level = HungerLevel.STARVING
        self.spell.cast(self.char1)
        self.assertEqual(self.char1.hunger_level, HungerLevel.CONTENT)  # 1+4
        self.assertEqual(self.follower.hunger_level, HungerLevel.CONTENT)

    def test_grandmaster_feeds_caster_and_follower(self):
        self._set_tier(5)
        self.char1.hunger_level = HungerLevel.STARVING
        self.follower.hunger_level = HungerLevel.STARVING
        self.spell.cast(self.char1)
        self.assertEqual(self.char1.hunger_level, HungerLevel.NOURISHED)  # 1+5
        self.assertEqual(self.follower.hunger_level, HungerLevel.NOURISHED)

    def test_basic_does_not_feed_follower(self):
        """BASIC is caster-only — follower stays unchanged."""
        self._set_tier(1)
        self.char1.hunger_level = HungerLevel.STARVING
        self.follower.hunger_level = HungerLevel.STARVING
        self.spell.cast(self.char1)
        self.assertEqual(self.char1.hunger_level, HungerLevel.FAMISHED)
        self.assertEqual(self.follower.hunger_level, HungerLevel.STARVING)

    def test_group_excludes_different_room(self):
        """Follower in a different room is skipped."""
        other_room = create_object(_ROOM, key="OtherRoom", nohome=True)
        self.follower.location = other_room

        self._set_tier(4)
        self.char1.hunger_level = HungerLevel.STARVING
        self.follower.hunger_level = HungerLevel.STARVING
        self.spell.cast(self.char1)
        self.assertEqual(self.char1.hunger_level, HungerLevel.CONTENT)
        self.assertEqual(self.follower.hunger_level, HungerLevel.STARVING)

    def test_group_mixed_feeds_only_hungry(self):
        """Full members are skipped but the cast still succeeds for the hungry."""
        self._set_tier(4)
        self.char1.hunger_level = HungerLevel.FULL  # caster doesn't need feeding
        self.follower.hunger_level = HungerLevel.STARVING
        success, _ = self.spell.cast(self.char1)
        self.assertTrue(success)
        self.assertEqual(self.follower.hunger_level, HungerLevel.CONTENT)

    def test_all_full_group_refunds_mana(self):
        self._set_tier(4)
        self.char1.hunger_level = HungerLevel.FULL
        self.follower.hunger_level = HungerLevel.FULL
        mana_before = self.char1.mana
        success, result = self.spell.cast(self.char1)
        self.assertFalse(success)
        self.assertEqual(self.char1.mana, mana_before)
        self.assertIn("already", result["first"].lower())
