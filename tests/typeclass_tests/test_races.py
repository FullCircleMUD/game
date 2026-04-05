"""
Tests for the race system — registry, at_taking_race, alignment gating.

evennia test --settings settings tests.typeclass_tests.test_races
"""

from evennia.utils.test_resources import EvenniaTest

from typeclasses.actors.races import (
    RACE_REGISTRY,
    get_race,
    list_races,
    get_available_races,
)
from typeclasses.actors.races.race_base import RaceBase


# ================================================================== #
#  Registry
# ================================================================== #

class TestRaceRegistry(EvenniaTest):
    """Test the auto-collecting race registry."""

    def create_script(self):
        pass

    def test_all_races_registered(self):
        """All five races should be in the registry."""
        self.assertIn("human", RACE_REGISTRY)
        self.assertIn("dwarf", RACE_REGISTRY)
        self.assertIn("elf", RACE_REGISTRY)
        self.assertIn("halfling", RACE_REGISTRY)
        self.assertIn("aasimar", RACE_REGISTRY)

    def test_registry_count(self):
        """Registry should have exactly 5 races."""
        self.assertEqual(len(RACE_REGISTRY), 5)

    def test_get_race_returns_instance(self):
        """get_race should return a RaceBase instance."""
        dwarf = get_race("dwarf")
        self.assertIsInstance(dwarf, RaceBase)
        self.assertEqual(dwarf.key, "dwarf")

    def test_get_race_unknown(self):
        """get_race with unknown key returns None."""
        self.assertIsNone(get_race("goblin"))

    def test_list_races(self):
        """list_races should return all keys."""
        keys = list_races()
        self.assertEqual(len(keys), 5)
        self.assertIn("human", keys)
        self.assertIn("dwarf", keys)
        self.assertIn("elf", keys)
        self.assertIn("halfling", keys)
        self.assertIn("aasimar", keys)

    def test_get_available_races_all_base(self):
        """All base races should be available at 0 remorts."""
        available = get_available_races(0)
        self.assertEqual(len(available), 3)

    def test_get_available_races_respects_min_remort(self):
        """A race with min_remort=5 should not be available at 0 remorts."""
        # Create a test race with high remort requirement
        advanced = RaceBase(key="test_advanced", display_name="Advanced", min_remort=5)
        # Temporarily add to registry
        RACE_REGISTRY["test_advanced"] = advanced
        try:
            available = get_available_races(0)
            self.assertNotIn("test_advanced", available)
            available = get_available_races(5)
            self.assertIn("test_advanced", available)
        finally:
            del RACE_REGISTRY["test_advanced"]


# ================================================================== #
#  at_taking_race — Human
# ================================================================== #

class TestHumanRace(EvenniaTest):
    """Test at_taking_race for Human — the baseline race."""

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.race = get_race("human")

    def test_sets_race(self):
        """Should set character.race to 'human'."""
        self.race.at_taking_race(self.char1)
        self.assertEqual(self.char1.race, "human")

    def test_sets_hp(self):
        """Human starting HP should be 10."""
        self.race.at_taking_race(self.char1)
        self.assertEqual(self.char1.hp, 10)
        self.assertEqual(self.char1.hp_max, 10)

    def test_sets_mana(self):
        """Human starting mana should be 10."""
        self.race.at_taking_race(self.char1)
        self.assertEqual(self.char1.mana, 10)
        self.assertEqual(self.char1.mana_max, 10)

    def test_sets_move(self):
        """Human starting move should be 100."""
        self.race.at_taking_race(self.char1)
        self.assertEqual(self.char1.move, 100)
        self.assertEqual(self.char1.move_max, 100)

    def test_no_ability_bonuses(self):
        """Human should have no ability score changes."""
        # Record base stats before
        orig_str = self.char1.base_strength
        orig_dex = self.char1.base_dexterity
        orig_con = self.char1.base_constitution
        orig_int = self.char1.base_intelligence
        orig_wis = self.char1.base_wisdom
        orig_cha = self.char1.base_charisma
        self.race.at_taking_race(self.char1)
        self.assertEqual(self.char1.base_strength, orig_str)
        self.assertEqual(self.char1.base_dexterity, orig_dex)
        self.assertEqual(self.char1.base_constitution, orig_con)
        self.assertEqual(self.char1.base_intelligence, orig_int)
        self.assertEqual(self.char1.base_wisdom, orig_wis)
        self.assertEqual(self.char1.base_charisma, orig_cha)

    def test_no_conditions(self):
        """Human should have no racial conditions."""
        self.race.at_taking_race(self.char1)
        self.assertFalse(self.char1.has_condition("darkvision"))

    def test_languages_common_only(self):
        """Human should only know Common."""
        self.race.at_taking_race(self.char1)
        self.assertIn("common", self.char1.db.languages)
        self.assertEqual(len(self.char1.db.languages), 1)

    def test_no_weapon_proficiencies(self):
        """Human should have no racial weapon proficiencies."""
        self.race.at_taking_race(self.char1)
        weapons = self.char1.db.weapon_skill_mastery_levels or {}
        self.assertEqual(len(weapons), 0)

    def test_base_armor_class(self):
        """Human base AC should be 10."""
        self.race.at_taking_race(self.char1)
        self.assertEqual(self.char1.base_armor_class, 10)
        self.assertEqual(self.char1.armor_class, 10)


# ================================================================== #
#  at_taking_race — Dwarf
# ================================================================== #

class TestDwarfRace(EvenniaTest):
    """Test at_taking_race for Dwarf — stat bonuses, conditions, resistances."""

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.race = get_race("dwarf")

    def test_sets_race(self):
        """Should set character.race to 'dwarf'."""
        self.race.at_taking_race(self.char1)
        self.assertEqual(self.char1.race, "dwarf")

    def test_sets_hp(self):
        """Dwarf starting HP should be 14."""
        self.race.at_taking_race(self.char1)
        self.assertEqual(self.char1.hp, 14)
        self.assertEqual(self.char1.hp_max, 14)

    def test_sets_mana(self):
        """Dwarf starting mana should be 6."""
        self.race.at_taking_race(self.char1)
        self.assertEqual(self.char1.mana, 6)

    def test_sets_move(self):
        """Dwarf starting move should be 80."""
        self.race.at_taking_race(self.char1)
        self.assertEqual(self.char1.move, 80)

    def test_constitution_bonus_base(self):
        """Dwarf should get +2 to base_constitution."""
        orig = self.char1.base_constitution
        self.race.at_taking_race(self.char1)
        self.assertEqual(self.char1.base_constitution, orig + 2)

    def test_constitution_bonus_current(self):
        """Dwarf should get +2 to constitution (current)."""
        orig = self.char1.constitution
        self.race.at_taking_race(self.char1)
        self.assertEqual(self.char1.constitution, orig + 2)

    def test_dexterity_penalty_base(self):
        """Dwarf should get -1 to base_dexterity."""
        orig = self.char1.base_dexterity
        self.race.at_taking_race(self.char1)
        self.assertEqual(self.char1.base_dexterity, orig - 1)

    def test_dexterity_penalty_current(self):
        """Dwarf should get -1 to dexterity (current)."""
        orig = self.char1.dexterity
        self.race.at_taking_race(self.char1)
        self.assertEqual(self.char1.dexterity, orig - 1)

    def test_has_darkvision(self):
        """Dwarf should gain darkvision condition."""
        self.race.at_taking_race(self.char1)
        self.assertTrue(self.char1.has_condition("darkvision"))

    def test_poison_resistance(self):
        """Dwarf should have 30% poison resistance."""
        self.race.at_taking_race(self.char1)
        self.assertEqual(self.char1.get_resistance("poison"), 30)

    def test_languages_include_dwarven(self):
        """Dwarf should know Dwarven and Common."""
        self.race.at_taking_race(self.char1)
        self.assertIn("common", self.char1.db.languages)
        self.assertIn("dwarven", self.char1.db.languages)
        self.assertEqual(len(self.char1.db.languages), 2)

    def test_weapon_proficiency_battleaxe(self):
        """Dwarf should have BASIC mastery in battleaxe."""
        self.race.at_taking_race(self.char1)
        self.assertEqual(self.char1.db.weapon_skill_mastery_levels.get("battleaxe"), 1)

    def test_weapon_proficiency_hammer(self):
        """Dwarf should have BASIC mastery in hammer."""
        self.race.at_taking_race(self.char1)
        self.assertEqual(self.char1.db.weapon_skill_mastery_levels.get("hammer"), 1)


# ================================================================== #
#  at_taking_race — Elf
# ================================================================== #

class TestElfRace(EvenniaTest):
    """Test at_taking_race for Elf — stat bonuses, conditions."""

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.race = get_race("elf")

    def test_sets_race(self):
        """Should set character.race to 'elf'."""
        self.race.at_taking_race(self.char1)
        self.assertEqual(self.char1.race, "elf")

    def test_sets_hp(self):
        """Elf starting HP should be 8."""
        self.race.at_taking_race(self.char1)
        self.assertEqual(self.char1.hp, 8)

    def test_sets_mana(self):
        """Elf starting mana should be 14."""
        self.race.at_taking_race(self.char1)
        self.assertEqual(self.char1.mana, 14)

    def test_sets_move(self):
        """Elf starting move should be 100."""
        self.race.at_taking_race(self.char1)
        self.assertEqual(self.char1.move, 100)

    def test_dexterity_bonus(self):
        """Elf should get +1 to dexterity (both base and current)."""
        orig_base = self.char1.base_dexterity
        orig_curr = self.char1.dexterity
        self.race.at_taking_race(self.char1)
        self.assertEqual(self.char1.base_dexterity, orig_base + 1)
        self.assertEqual(self.char1.dexterity, orig_curr + 1)

    def test_intelligence_bonus(self):
        """Elf should get +1 to intelligence (both base and current)."""
        orig_base = self.char1.base_intelligence
        orig_curr = self.char1.intelligence
        self.race.at_taking_race(self.char1)
        self.assertEqual(self.char1.base_intelligence, orig_base + 1)
        self.assertEqual(self.char1.intelligence, orig_curr + 1)

    def test_constitution_penalty(self):
        """Elf should get -1 to constitution (both base and current)."""
        orig_base = self.char1.base_constitution
        orig_curr = self.char1.constitution
        self.race.at_taking_race(self.char1)
        self.assertEqual(self.char1.base_constitution, orig_base - 1)
        self.assertEqual(self.char1.constitution, orig_curr - 1)

    def test_has_darkvision(self):
        """Elf should gain darkvision condition."""
        self.race.at_taking_race(self.char1)
        self.assertTrue(self.char1.has_condition("darkvision"))

    def test_no_damage_resistance(self):
        """Elf should have no damage resistances."""
        self.race.at_taking_race(self.char1)
        self.assertEqual(self.char1.get_resistance("poison"), 0)

    def test_languages_include_elfish(self):
        """Elf should know Elfish and Common."""
        self.race.at_taking_race(self.char1)
        self.assertIn("common", self.char1.db.languages)
        self.assertIn("elfish", self.char1.db.languages)
        self.assertEqual(len(self.char1.db.languages), 2)


# ================================================================== #
#  Alignment Gating
# ================================================================== #

class TestAlignmentGating(EvenniaTest):
    """Test get_valid_alignments with required/excluded lists."""

    def create_script(self):
        pass

    def test_no_restrictions(self):
        """No alignment restrictions should return (None, None) range."""
        race = RaceBase(key="test", display_name="Test")
        min_s, max_s = race.get_valid_alignment_range()
        self.assertIsNone(min_s)
        self.assertIsNone(max_s)

    def test_min_alignment_range(self):
        """min_alignment_score should be returned in range."""
        race = RaceBase(key="test", display_name="Test", min_alignment_score=300)
        min_s, max_s = race.get_valid_alignment_range()
        self.assertEqual(min_s, 300)
        self.assertIsNone(max_s)

    def test_max_alignment_range(self):
        """max_alignment_score should be returned in range."""
        race = RaceBase(key="test", display_name="Test", max_alignment_score=-300)
        min_s, max_s = race.get_valid_alignment_range()
        self.assertIsNone(min_s)
        self.assertEqual(max_s, -300)


# ================================================================== #
#  Base Armor Class
# ================================================================== #

class TestBaseArmorClass(EvenniaTest):
    """Test base armor class application."""

    def create_script(self):
        pass

    def test_default_ac(self):
        """Default base AC of 10 should be applied."""
        race = RaceBase(key="test", display_name="Test")
        race.at_taking_race(self.char1)
        self.assertEqual(self.char1.base_armor_class, 10)
        self.assertEqual(self.char1.armor_class, 10)

    def test_custom_ac(self):
        """Non-default base AC should be applied."""
        race = RaceBase(key="test_shell", display_name="Turtle Folk", base_armor_class=12)
        race.at_taking_race(self.char1)
        self.assertEqual(self.char1.base_armor_class, 12)
        self.assertEqual(self.char1.armor_class, 12)


# ================================================================== #
#  at_taking_race — Halfling
# ================================================================== #

class TestHalflingRace(EvenniaTest):
    """Test at_taking_race for Halfling — small, nimble, remort race."""

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.race = get_race("halfling")

    def test_sets_race(self):
        """Should set character.race to 'halfling'."""
        self.race.at_taking_race(self.char1)
        self.assertEqual(self.char1.race, "halfling")

    def test_sets_hp(self):
        """Halfling starting HP should be 8."""
        self.race.at_taking_race(self.char1)
        self.assertEqual(self.char1.hp, 8)
        self.assertEqual(self.char1.hp_max, 8)

    def test_sets_mana(self):
        """Halfling starting mana should be 10."""
        self.race.at_taking_race(self.char1)
        self.assertEqual(self.char1.mana, 10)
        self.assertEqual(self.char1.mana_max, 10)

    def test_sets_move(self):
        """Halfling starting move should be 80."""
        self.race.at_taking_race(self.char1)
        self.assertEqual(self.char1.move, 80)
        self.assertEqual(self.char1.move_max, 80)

    def test_dexterity_bonus(self):
        """Halfling should get +2 to dexterity (both base and current)."""
        orig_base = self.char1.base_dexterity
        orig_curr = self.char1.dexterity
        self.race.at_taking_race(self.char1)
        self.assertEqual(self.char1.base_dexterity, orig_base + 2)
        self.assertEqual(self.char1.dexterity, orig_curr + 2)

    def test_strength_penalty(self):
        """Halfling should get -1 to strength (both base and current)."""
        orig_base = self.char1.base_strength
        orig_curr = self.char1.strength
        self.race.at_taking_race(self.char1)
        self.assertEqual(self.char1.base_strength, orig_base - 1)
        self.assertEqual(self.char1.strength, orig_curr - 1)

    def test_no_darkvision(self):
        """Halfling should NOT have darkvision."""
        self.race.at_taking_race(self.char1)
        self.assertFalse(self.char1.has_condition("darkvision"))

    def test_languages_include_halfling(self):
        """Halfling should know Halfling and Common."""
        self.race.at_taking_race(self.char1)
        self.assertIn("common", self.char1.db.languages)
        self.assertIn("halfling", self.char1.db.languages)
        self.assertEqual(len(self.char1.db.languages), 2)

    def test_weapon_proficiency_sling(self):
        """Halfling should have BASIC mastery in sling."""
        self.race.at_taking_race(self.char1)
        self.assertEqual(self.char1.db.weapon_skill_mastery_levels.get("sling"), 1)

    def test_min_remort(self):
        """Halfling should require 1 remort."""
        self.assertEqual(self.race.min_remort, 1)

    def test_base_armor_class(self):
        """Halfling base AC should be 10."""
        self.race.at_taking_race(self.char1)
        self.assertEqual(self.char1.base_armor_class, 10)
        self.assertEqual(self.char1.armor_class, 10)


# ================================================================== #
#  at_taking_race — Aasimar
# ================================================================== #

class TestAasimarRace(EvenniaTest):
    """Test at_taking_race for Aasimar — celestial-touched, remort race."""

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.race = get_race("aasimar")

    def test_sets_race(self):
        """Should set character.race to 'aasimar'."""
        self.race.at_taking_race(self.char1)
        self.assertEqual(self.char1.race, "aasimar")

    def test_sets_hp(self):
        """Aasimar starting HP should be 12."""
        self.race.at_taking_race(self.char1)
        self.assertEqual(self.char1.hp, 12)
        self.assertEqual(self.char1.hp_max, 12)

    def test_sets_mana(self):
        """Aasimar starting mana should be 14."""
        self.race.at_taking_race(self.char1)
        self.assertEqual(self.char1.mana, 14)
        self.assertEqual(self.char1.mana_max, 14)

    def test_sets_move(self):
        """Aasimar starting move should be 100."""
        self.race.at_taking_race(self.char1)
        self.assertEqual(self.char1.move, 100)
        self.assertEqual(self.char1.move_max, 100)

    def test_wisdom_bonus(self):
        """Aasimar should get +1 to wisdom (both base and current)."""
        orig_base = self.char1.base_wisdom
        orig_curr = self.char1.wisdom
        self.race.at_taking_race(self.char1)
        self.assertEqual(self.char1.base_wisdom, orig_base + 1)
        self.assertEqual(self.char1.wisdom, orig_curr + 1)

    def test_charisma_bonus(self):
        """Aasimar should get +1 to charisma (both base and current)."""
        orig_base = self.char1.base_charisma
        orig_curr = self.char1.charisma
        self.race.at_taking_race(self.char1)
        self.assertEqual(self.char1.base_charisma, orig_base + 1)
        self.assertEqual(self.char1.charisma, orig_curr + 1)

    def test_has_darkvision(self):
        """Aasimar should gain darkvision condition."""
        self.race.at_taking_race(self.char1)
        self.assertTrue(self.char1.has_condition("darkvision"))

    def test_necrotic_resistance(self):
        """Aasimar should have 25% necrotic resistance."""
        self.race.at_taking_race(self.char1)
        self.assertEqual(self.char1.get_resistance("necrotic"), 25)

    def test_languages_include_celestial(self):
        """Aasimar should know Celestial and Common."""
        self.race.at_taking_race(self.char1)
        self.assertIn("common", self.char1.db.languages)
        self.assertIn("celestial", self.char1.db.languages)
        self.assertEqual(len(self.char1.db.languages), 2)

    def test_no_weapon_proficiencies(self):
        """Aasimar should have no racial weapon proficiencies."""
        self.race.at_taking_race(self.char1)
        weapons = self.char1.db.weapon_skill_mastery_levels or {}
        self.assertEqual(len(weapons), 0)

    def test_min_remort(self):
        """Aasimar should require 2 remorts."""
        self.assertEqual(self.race.min_remort, 2)

    def test_base_armor_class(self):
        """Aasimar base AC should be 10."""
        self.race.at_taking_race(self.char1)
        self.assertEqual(self.char1.base_armor_class, 10)
        self.assertEqual(self.char1.armor_class, 10)
