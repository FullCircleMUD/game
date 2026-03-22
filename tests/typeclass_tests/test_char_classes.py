"""
Tests for the character class system — registry, at_char_first_gaining_class,
at_gain_subsequent_level_in_class, eligibility checks, alignment gating.

evennia test --settings settings tests.typeclass_tests.test_char_classes
"""

from evennia.utils.test_resources import EvenniaTest

from enums.abilities_enum import Ability
from enums.alignment import Alignment
from typeclasses.actors.char_classes import (
    CLASS_REGISTRY,
    get_char_class,
    list_char_classes,
    get_available_char_classes,
)
from typeclasses.actors.char_classes.char_class_base import CharClassBase


# ================================================================== #
#  Registry
# ================================================================== #

class TestClassRegistry(EvenniaTest):
    """Test the auto-collecting class registry."""

    def create_script(self):
        pass

    def test_all_classes_registered(self):
        """All six classes should be in the registry."""
        self.assertIn("warrior", CLASS_REGISTRY)
        self.assertIn("thief", CLASS_REGISTRY)
        self.assertIn("mage", CLASS_REGISTRY)
        self.assertIn("cleric", CLASS_REGISTRY)
        self.assertIn("paladin", CLASS_REGISTRY)
        self.assertIn("bard", CLASS_REGISTRY)

    def test_registry_count(self):
        """Registry should have exactly 6 classes."""
        self.assertEqual(len(CLASS_REGISTRY), 6)

    def test_get_char_class_returns_instance(self):
        """get_char_class should return a CharClassBase instance."""
        warrior = get_char_class("warrior")
        self.assertIsInstance(warrior, CharClassBase)
        self.assertEqual(warrior.key, "warrior")

    def test_get_char_class_unknown(self):
        """get_char_class with unknown key returns None."""
        self.assertIsNone(get_char_class("druid"))

    def test_list_char_classes(self):
        """list_char_classes should return all keys."""
        keys = list_char_classes()
        self.assertEqual(len(keys), 6)
        self.assertIn("warrior", keys)
        self.assertIn("thief", keys)
        self.assertIn("mage", keys)
        self.assertIn("cleric", keys)
        self.assertIn("paladin", keys)
        self.assertIn("bard", keys)

    def test_get_available_char_classes_all_base(self):
        """Base classes (min_remort=0) should be available at 0 remorts."""
        available = get_available_char_classes(0)
        self.assertEqual(len(available), 4)
        self.assertNotIn("paladin", available)
        self.assertNotIn("bard", available)

    def test_get_available_char_classes_respects_min_remort(self):
        """A class with min_remort=5 should not be available at 0 remorts."""
        advanced = CharClassBase(key="test_advanced", display_name="Advanced", min_remort=5)
        CLASS_REGISTRY["test_advanced"] = advanced
        try:
            available = get_available_char_classes(0)
            self.assertNotIn("test_advanced", available)
            available = get_available_char_classes(5)
            self.assertIn("test_advanced", available)
        finally:
            del CLASS_REGISTRY["test_advanced"]


# ================================================================== #
#  char_can_take_class
# ================================================================== #

class TestCharCanTakeClass(EvenniaTest):
    """Test eligibility checks for taking a class."""

    def create_script(self):
        pass

    def test_no_restrictions_passes(self):
        """Warrior has no race/alignment restrictions — should pass."""
        warrior = get_char_class("warrior")
        self.char1.race = "human"
        self.char1.alignment = Alignment.TRUE_NEUTRAL
        self.char1.num_remorts = 0
        self.assertTrue(warrior.char_can_take_class(self.char1))

    def test_required_races_whitelist(self):
        """Only listed races should be allowed."""
        restricted = CharClassBase(
            key="test_restricted",
            display_name="Test",
            required_races=["dwarf"],
        )
        self.char1.race = "dwarf"
        self.assertTrue(restricted.char_can_take_class(self.char1))
        self.char1.race = "elf"
        self.assertFalse(restricted.char_can_take_class(self.char1))

    def test_excluded_races_blacklist(self):
        """Excluded races should be blocked."""
        restricted = CharClassBase(
            key="test_restricted",
            display_name="Test",
            excluded_races=["elf"],
        )
        self.char1.race = "human"
        self.assertTrue(restricted.char_can_take_class(self.char1))
        self.char1.race = "elf"
        self.assertFalse(restricted.char_can_take_class(self.char1))

    def test_required_alignments_whitelist(self):
        """Only listed alignments should be allowed."""
        restricted = CharClassBase(
            key="test_restricted",
            display_name="Test",
            required_alignments=[Alignment.LAWFUL_GOOD],
        )
        self.char1.race = "human"
        self.char1.alignment = Alignment.LAWFUL_GOOD
        self.assertTrue(restricted.char_can_take_class(self.char1))
        self.char1.alignment = Alignment.CHAOTIC_EVIL
        self.assertFalse(restricted.char_can_take_class(self.char1))

    def test_excluded_alignments_blacklist(self):
        """Excluded alignments should be blocked."""
        restricted = CharClassBase(
            key="test_restricted",
            display_name="Test",
            excluded_alignments=[Alignment.CHAOTIC_EVIL],
        )
        self.char1.race = "human"
        self.char1.alignment = Alignment.TRUE_NEUTRAL
        self.assertTrue(restricted.char_can_take_class(self.char1))
        self.char1.alignment = Alignment.CHAOTIC_EVIL
        self.assertFalse(restricted.char_can_take_class(self.char1))

    def test_insufficient_remorts(self):
        """Should fail if character doesn't have enough remorts."""
        restricted = CharClassBase(
            key="test_restricted",
            display_name="Test",
            min_remort=3,
        )
        self.char1.race = "human"
        self.char1.num_remorts = 2
        self.assertFalse(restricted.char_can_take_class(self.char1))
        self.char1.num_remorts = 3
        self.assertTrue(restricted.char_can_take_class(self.char1))


# ================================================================== #
#  at_char_first_gaining_class — Warrior
# ================================================================== #

class TestWarriorFirstLevel(EvenniaTest):
    """Test at_char_first_gaining_class for Warrior."""

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.warrior = get_char_class("warrior")
        # Set race baseline first (simulating race already applied)
        self.char1.hp = 10

        self.char1.hp_max = 10
        self.char1.mana = 10

        self.char1.mana_max = 10
        self.char1.move = 50

        self.char1.move_max = 50
        self.char1.general_skill_pts_available = 0
        self.char1.weapon_skill_pts_available = 0

    def test_sets_class_entry(self):
        """Should create db.classes['warrior'] with level 1."""
        self.warrior.at_char_first_gaining_class(self.char1)
        self.assertIn("warrior", self.char1.db.classes)
        self.assertEqual(self.char1.db.classes["warrior"]["level"], 1)

    def test_class_skill_points(self):
        """Warrior level 1 should grant class skill points per progression."""
        l1 = self.warrior.level_progression[1]
        self.warrior.at_char_first_gaining_class(self.char1)
        self.assertEqual(self.char1.db.classes["warrior"]["skill_pts_available"], l1["class_skill_pts"])

    def test_hp_gain(self):
        """Warrior level 1 adds HP per progression table."""
        l1 = self.warrior.level_progression[1]
        self.warrior.at_char_first_gaining_class(self.char1)
        self.assertEqual(self.char1.hp, 10 + l1["hp_gain"])
        self.assertEqual(self.char1.hp_max, 10 + l1["hp_gain"])

    def test_mana_gain(self):
        """Warrior level 1 adds mana per progression table."""
        l1 = self.warrior.level_progression[1]
        self.warrior.at_char_first_gaining_class(self.char1)
        self.assertEqual(self.char1.mana, 10 + l1["mana_gain"])
        self.assertEqual(self.char1.mana_max, 10 + l1["mana_gain"])

    def test_move_gain(self):
        """Warrior level 1 adds move per progression table."""
        l1 = self.warrior.level_progression[1]
        self.warrior.at_char_first_gaining_class(self.char1)
        self.assertEqual(self.char1.move, 50 + l1["move_gain"])
        self.assertEqual(self.char1.move_max, 50 + l1["move_gain"])

    def test_weapon_skill_points(self):
        """Warrior level 1 should grant weapon skill points per progression."""
        l1 = self.warrior.level_progression[1]
        self.warrior.at_char_first_gaining_class(self.char1)
        self.assertEqual(self.char1.weapon_skill_pts_available, l1["weapon_skill_pts"])

    def test_general_skill_points(self):
        """Warrior level 1 should grant general skill points per progression."""
        l1 = self.warrior.level_progression[1]
        self.warrior.at_char_first_gaining_class(self.char1)
        self.assertEqual(self.char1.general_skill_pts_available, l1["general_skill_pts"])


# ================================================================== #
#  at_char_first_gaining_class — Thief
# ================================================================== #

class TestThiefFirstLevel(EvenniaTest):
    """Test at_char_first_gaining_class for Thief."""

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.thief = get_char_class("thief")
        self.char1.hp = 10

        self.char1.hp_max = 10
        self.char1.mana = 10

        self.char1.mana_max = 10
        self.char1.move = 50

        self.char1.move_max = 50
        self.char1.general_skill_pts_available = 0
        self.char1.weapon_skill_pts_available = 0

    def test_sets_class_entry(self):
        """Should create db.classes['thief'] with level 1."""
        self.thief.at_char_first_gaining_class(self.char1)
        self.assertIn("thief", self.char1.db.classes)
        self.assertEqual(self.char1.db.classes["thief"]["level"], 1)

    def test_hp_gain(self):
        """Thief level 1 adds HP per progression table."""
        l1 = self.thief.level_progression[1]
        self.thief.at_char_first_gaining_class(self.char1)
        self.assertEqual(self.char1.hp, 10 + l1["hp_gain"])

    def test_mana_gain(self):
        """Thief level 1 adds mana per progression table."""
        l1 = self.thief.level_progression[1]
        self.thief.at_char_first_gaining_class(self.char1)
        self.assertEqual(self.char1.mana, 10 + l1["mana_gain"])

    def test_move_gain(self):
        """Thief level 1 adds move per progression table."""
        l1 = self.thief.level_progression[1]
        self.thief.at_char_first_gaining_class(self.char1)
        self.assertEqual(self.char1.move, 50 + l1["move_gain"])

    def test_class_skill_points(self):
        """Thief level 1 should grant class skill points per progression."""
        l1 = self.thief.level_progression[1]
        self.thief.at_char_first_gaining_class(self.char1)
        self.assertEqual(self.char1.db.classes["thief"]["skill_pts_available"], l1["class_skill_pts"])


# ================================================================== #
#  at_gain_subsequent_level_in_class
# ================================================================== #

class TestSubsequentLevelUp(EvenniaTest):
    """Test leveling up in a class after the first level."""

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.warrior = get_char_class("warrior")
        l1 = self.warrior.level_progression[1]
        # Set up character with warrior level 1 already applied on top of race base
        self.base_hp = 10 + l1["hp_gain"]
        self.base_mana = 10 + l1["mana_gain"]
        self.base_move = 50 + l1["move_gain"]
        self.char1.hp = self.base_hp
        self.char1.hp_max = self.base_hp
        self.char1.mana = self.base_mana
        self.char1.mana_max = self.base_mana
        self.char1.move = self.base_move
        self.char1.move_max = self.base_move
        self.char1.general_skill_pts_available = l1["general_skill_pts"]
        self.char1.weapon_skill_pts_available = l1["weapon_skill_pts"]
        self.char1.levels_to_spend = 1
        self.char1.db.classes = {"warrior": {"level": 1, "skill_pts_available": l1["class_skill_pts"]}}

    def test_level_increments(self):
        """Should increment warrior level to 2."""
        self.warrior.at_gain_subsequent_level_in_class(self.char1)
        self.assertEqual(self.char1.db.classes["warrior"]["level"], 2)

    def test_hp_gain_level_2(self):
        """Warrior level 2 adds HP per progression table."""
        l2 = self.warrior.level_progression[2]
        self.warrior.at_gain_subsequent_level_in_class(self.char1)
        self.assertEqual(self.char1.hp, self.base_hp + l2["hp_gain"])
        self.assertEqual(self.char1.hp_max, self.base_hp + l2["hp_gain"])

    def test_skill_points_level_2(self):
        """Warrior level 2 adds skill points per progression table."""
        l1 = self.warrior.level_progression[1]
        l2 = self.warrior.level_progression[2]
        self.warrior.at_gain_subsequent_level_in_class(self.char1)
        self.assertEqual(self.char1.weapon_skill_pts_available, l1["weapon_skill_pts"] + l2["weapon_skill_pts"])
        self.assertEqual(self.char1.db.classes["warrior"]["skill_pts_available"], l1["class_skill_pts"] + l2["class_skill_pts"])
        self.assertEqual(self.char1.general_skill_pts_available, l1["general_skill_pts"] + l2["general_skill_pts"])

    def test_deducts_levels_to_spend(self):
        """Should deduct 1 from levels_to_spend."""
        self.warrior.at_gain_subsequent_level_in_class(self.char1)
        self.assertEqual(self.char1.levels_to_spend, 0)

    def test_fails_if_not_in_class(self):
        """Should fail gracefully if character hasn't taken the class."""
        thief = get_char_class("thief")
        thief.at_gain_subsequent_level_in_class(self.char1)
        # Should not crash — just sends a message
        self.assertNotIn("thief", self.char1.db.classes)

    def test_fails_if_no_levels_to_spend(self):
        """Should fail if character has no levels to spend."""
        self.char1.levels_to_spend = 0
        self.warrior.at_gain_subsequent_level_in_class(self.char1)
        # Level should not have changed
        self.assertEqual(self.char1.db.classes["warrior"]["level"], 1)


# ================================================================== #
#  Alignment Gating
# ================================================================== #

class TestClassAlignmentGating(EvenniaTest):
    """Test get_valid_alignments with required/excluded lists."""

    def create_script(self):
        pass

    def test_no_restrictions_returns_all(self):
        """No alignment restrictions should return all 9 alignments."""
        cls = CharClassBase(key="test", display_name="Test")
        valid = cls.get_valid_alignments()
        self.assertEqual(len(valid), 9)

    def test_required_alignments(self):
        """Only required alignments should be returned."""
        cls = CharClassBase(
            key="test",
            display_name="Test",
            required_alignments=[Alignment.LAWFUL_GOOD, Alignment.NEUTRAL_GOOD],
        )
        valid = cls.get_valid_alignments()
        self.assertEqual(len(valid), 2)
        self.assertIn(Alignment.LAWFUL_GOOD, valid)
        self.assertIn(Alignment.NEUTRAL_GOOD, valid)

    def test_excluded_alignments(self):
        """Excluded alignments should be filtered out."""
        cls = CharClassBase(
            key="test",
            display_name="Test",
            excluded_alignments=[Alignment.CHAOTIC_EVIL, Alignment.NEUTRAL_EVIL],
        )
        valid = cls.get_valid_alignments()
        self.assertEqual(len(valid), 7)
        self.assertNotIn(Alignment.CHAOTIC_EVIL, valid)
        self.assertNotIn(Alignment.NEUTRAL_EVIL, valid)


# ================================================================== #
#  Multiclassing
# ================================================================== #

class TestMulticlass(EvenniaTest):
    """Test taking multiple classes."""

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.char1.hp = 10

        self.char1.hp_max = 10
        self.char1.mana = 10

        self.char1.mana_max = 10
        self.char1.move = 50

        self.char1.move_max = 50
        self.char1.general_skill_pts_available = 0
        self.char1.weapon_skill_pts_available = 0

    def test_can_take_second_class(self):
        """Should be able to take warrior then thief."""
        warrior = get_char_class("warrior")
        thief = get_char_class("thief")
        warrior.at_char_first_gaining_class(self.char1)
        thief.at_char_first_gaining_class(self.char1)
        self.assertIn("warrior", self.char1.db.classes)
        self.assertIn("thief", self.char1.db.classes)

    def test_multiclass_stats_stack(self):
        """HP/mana/move from both classes should stack additively."""
        warrior = get_char_class("warrior")
        thief = get_char_class("thief")
        wl1 = warrior.level_progression[1]
        tl1 = thief.level_progression[1]
        warrior.at_char_first_gaining_class(self.char1)
        thief.at_char_first_gaining_class(self.char1)
        self.assertEqual(self.char1.hp, 10 + wl1["hp_gain"] + tl1["hp_gain"])
        self.assertEqual(self.char1.mana, 10 + wl1["mana_gain"] + tl1["mana_gain"])
        self.assertEqual(self.char1.move, 50 + wl1["move_gain"] + tl1["move_gain"])


# ================================================================== #
#  Warrior data verification
# ================================================================== #

class TestWarriorData(EvenniaTest):
    """Verify warrior class data is correct."""

    def create_script(self):
        pass

    def test_prime_attribute(self):
        """Warrior prime attribute should be STR."""
        warrior = get_char_class("warrior")
        self.assertEqual(warrior.prime_attribute, Ability.STR)

    def test_multiclass_requirements(self):
        """Warrior multiclass should require STR 14 and CON 12."""
        warrior = get_char_class("warrior")
        self.assertEqual(warrior.multi_class_requirements[Ability.STR], 14)
        self.assertEqual(warrior.multi_class_requirements[Ability.CON], 12)

    def test_progression_has_40_levels(self):
        """Warrior should have progression data for levels 1-40."""
        warrior = get_char_class("warrior")
        self.assertEqual(len(warrior.level_progression), 40)
        self.assertIn(1, warrior.level_progression)
        self.assertIn(40, warrior.level_progression)


# ================================================================== #
#  Thief data verification
# ================================================================== #

class TestThiefData(EvenniaTest):
    """Verify thief class data is correct."""

    def create_script(self):
        pass

    def test_prime_attribute(self):
        """Thief prime attribute should be DEX."""
        thief = get_char_class("thief")
        self.assertEqual(thief.prime_attribute, Ability.DEX)

    def test_multiclass_requirements(self):
        """Thief multiclass should require DEX 14."""
        thief = get_char_class("thief")
        self.assertEqual(thief.multi_class_requirements[Ability.DEX], 14)

    def test_progression_has_40_levels(self):
        """Thief should have progression data for levels 1-40."""
        thief = get_char_class("thief")
        self.assertEqual(len(thief.level_progression), 40)


# ================================================================== #
#  at_char_first_gaining_class — Mage
# ================================================================== #

class TestMageFirstLevel(EvenniaTest):
    """Test at_char_first_gaining_class for Mage."""

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.mage = get_char_class("mage")
        self.char1.hp = 10
        self.char1.hp_max = 10
        self.char1.mana = 10
        self.char1.mana_max = 10
        self.char1.move = 50
        self.char1.move_max = 50
        self.char1.general_skill_pts_available = 0
        self.char1.weapon_skill_pts_available = 0

    def test_sets_class_entry(self):
        """Should create db.classes['mage'] with level 1."""
        self.mage.at_char_first_gaining_class(self.char1)
        self.assertIn("mage", self.char1.db.classes)
        self.assertEqual(self.char1.db.classes["mage"]["level"], 1)

    def test_hp_gain(self):
        """Mage level 1 adds HP per progression table."""
        l1 = self.mage.level_progression[1]
        self.mage.at_char_first_gaining_class(self.char1)
        self.assertEqual(self.char1.hp, 10 + l1["hp_gain"])
        self.assertEqual(self.char1.hp_max, 10 + l1["hp_gain"])

    def test_mana_gain(self):
        """Mage level 1 adds mana per progression table."""
        l1 = self.mage.level_progression[1]
        self.mage.at_char_first_gaining_class(self.char1)
        self.assertEqual(self.char1.mana, 10 + l1["mana_gain"])
        self.assertEqual(self.char1.mana_max, 10 + l1["mana_gain"])

    def test_move_gain(self):
        """Mage level 1 adds move per progression table."""
        l1 = self.mage.level_progression[1]
        self.mage.at_char_first_gaining_class(self.char1)
        self.assertEqual(self.char1.move, 50 + l1["move_gain"])
        self.assertEqual(self.char1.move_max, 50 + l1["move_gain"])

    def test_class_skill_points(self):
        """Mage level 1 should grant class skill points per progression."""
        l1 = self.mage.level_progression[1]
        self.mage.at_char_first_gaining_class(self.char1)
        self.assertEqual(self.char1.db.classes["mage"]["skill_pts_available"], l1["class_skill_pts"])

    def test_weapon_skill_points(self):
        """Mage level 1 should grant weapon skill points per progression."""
        l1 = self.mage.level_progression[1]
        self.mage.at_char_first_gaining_class(self.char1)
        self.assertEqual(self.char1.weapon_skill_pts_available, l1["weapon_skill_pts"])

    def test_general_skill_points(self):
        """Mage level 1 should grant general skill points per progression."""
        l1 = self.mage.level_progression[1]
        self.mage.at_char_first_gaining_class(self.char1)
        self.assertEqual(self.char1.general_skill_pts_available, l1["general_skill_pts"])


# ================================================================== #
#  Mage data verification
# ================================================================== #

class TestMageData(EvenniaTest):
    """Verify mage class data is correct."""

    def create_script(self):
        pass

    def test_prime_attribute(self):
        """Mage prime attribute should be INT."""
        mage = get_char_class("mage")
        self.assertEqual(mage.prime_attribute, Ability.INT)

    def test_multiclass_requirements(self):
        """Mage multiclass should require INT 14."""
        mage = get_char_class("mage")
        self.assertEqual(mage.multi_class_requirements[Ability.INT], 14)
        self.assertEqual(len(mage.multi_class_requirements), 1)

    def test_progression_has_40_levels(self):
        """Mage should have progression data for levels 1-40."""
        mage = get_char_class("mage")
        self.assertEqual(len(mage.level_progression), 40)
        self.assertIn(1, mage.level_progression)
        self.assertIn(40, mage.level_progression)

    def test_no_race_restrictions(self):
        """Mage should have no race restrictions."""
        mage = get_char_class("mage")
        self.assertEqual(len(mage.required_races), 0)
        self.assertEqual(len(mage.excluded_races), 0)

    def test_no_alignment_restrictions(self):
        """Mage should have no alignment restrictions."""
        mage = get_char_class("mage")
        self.assertEqual(len(mage.required_alignments), 0)
        self.assertEqual(len(mage.excluded_alignments), 0)

    def test_available_at_zero_remorts(self):
        """Mage should be available without any remorts."""
        mage = get_char_class("mage")
        self.assertEqual(mage.min_remort, 0)


# ================================================================== #
#  at_char_first_gaining_class — Cleric
# ================================================================== #

class TestClericFirstLevel(EvenniaTest):
    """Test at_char_first_gaining_class for Cleric."""

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.cleric = get_char_class("cleric")
        self.char1.hp = 10
        self.char1.hp_max = 10
        self.char1.mana = 10
        self.char1.mana_max = 10
        self.char1.move = 50
        self.char1.move_max = 50
        self.char1.general_skill_pts_available = 0
        self.char1.weapon_skill_pts_available = 0

    def test_sets_class_entry(self):
        """Should create db.classes['cleric'] with level 1."""
        self.cleric.at_char_first_gaining_class(self.char1)
        self.assertIn("cleric", self.char1.db.classes)
        self.assertEqual(self.char1.db.classes["cleric"]["level"], 1)

    def test_hp_gain(self):
        """Cleric level 1 adds HP per progression table."""
        l1 = self.cleric.level_progression[1]
        self.cleric.at_char_first_gaining_class(self.char1)
        self.assertEqual(self.char1.hp, 10 + l1["hp_gain"])
        self.assertEqual(self.char1.hp_max, 10 + l1["hp_gain"])

    def test_mana_gain(self):
        """Cleric level 1 adds mana per progression table."""
        l1 = self.cleric.level_progression[1]
        self.cleric.at_char_first_gaining_class(self.char1)
        self.assertEqual(self.char1.mana, 10 + l1["mana_gain"])
        self.assertEqual(self.char1.mana_max, 10 + l1["mana_gain"])

    def test_move_gain(self):
        """Cleric level 1 adds move per progression table."""
        l1 = self.cleric.level_progression[1]
        self.cleric.at_char_first_gaining_class(self.char1)
        self.assertEqual(self.char1.move, 50 + l1["move_gain"])
        self.assertEqual(self.char1.move_max, 50 + l1["move_gain"])

    def test_class_skill_points(self):
        """Cleric level 1 should grant class skill points per progression."""
        l1 = self.cleric.level_progression[1]
        self.cleric.at_char_first_gaining_class(self.char1)
        self.assertEqual(self.char1.db.classes["cleric"]["skill_pts_available"], l1["class_skill_pts"])

    def test_weapon_skill_points(self):
        """Cleric level 1 should grant weapon skill points per progression."""
        l1 = self.cleric.level_progression[1]
        self.cleric.at_char_first_gaining_class(self.char1)
        self.assertEqual(self.char1.weapon_skill_pts_available, l1["weapon_skill_pts"])

    def test_general_skill_points(self):
        """Cleric level 1 should grant general skill points per progression."""
        l1 = self.cleric.level_progression[1]
        self.cleric.at_char_first_gaining_class(self.char1)
        self.assertEqual(self.char1.general_skill_pts_available, l1["general_skill_pts"])


# ================================================================== #
#  Cleric data verification
# ================================================================== #

class TestClericData(EvenniaTest):
    """Verify cleric class data is correct."""

    def create_script(self):
        pass

    def test_prime_attribute(self):
        """Cleric prime attribute should be WIS."""
        cleric = get_char_class("cleric")
        self.assertEqual(cleric.prime_attribute, Ability.WIS)

    def test_multiclass_requirements(self):
        """Cleric multiclass should require WIS 14."""
        cleric = get_char_class("cleric")
        self.assertEqual(cleric.multi_class_requirements[Ability.WIS], 14)
        self.assertEqual(len(cleric.multi_class_requirements), 1)

    def test_progression_has_40_levels(self):
        """Cleric should have progression data for levels 1-40."""
        cleric = get_char_class("cleric")
        self.assertEqual(len(cleric.level_progression), 40)
        self.assertIn(1, cleric.level_progression)
        self.assertIn(40, cleric.level_progression)

    def test_no_race_restrictions(self):
        """Cleric should have no race restrictions."""
        cleric = get_char_class("cleric")
        self.assertEqual(len(cleric.required_races), 0)
        self.assertEqual(len(cleric.excluded_races), 0)

    def test_evil_alignments_excluded(self):
        """Cleric should exclude all three evil alignments."""
        cleric = get_char_class("cleric")
        self.assertEqual(len(cleric.excluded_alignments), 3)
        self.assertIn(Alignment.LAWFUL_EVIL, cleric.excluded_alignments)
        self.assertIn(Alignment.NEUTRAL_EVIL, cleric.excluded_alignments)
        self.assertIn(Alignment.CHAOTIC_EVIL, cleric.excluded_alignments)

    def test_valid_alignments_excludes_evil(self):
        """get_valid_alignments should return 6 non-evil alignments."""
        cleric = get_char_class("cleric")
        valid = cleric.get_valid_alignments()
        self.assertEqual(len(valid), 6)
        self.assertNotIn(Alignment.LAWFUL_EVIL, valid)
        self.assertNotIn(Alignment.NEUTRAL_EVIL, valid)
        self.assertNotIn(Alignment.CHAOTIC_EVIL, valid)

    def test_available_at_zero_remorts(self):
        """Cleric should be available without any remorts."""
        cleric = get_char_class("cleric")
        self.assertEqual(cleric.min_remort, 0)


# ================================================================== #
#  Paladin data verification
# ================================================================== #

class TestPaladinData(EvenniaTest):
    """Verify paladin class data is correct."""

    def create_script(self):
        pass

    def test_prime_attribute(self):
        """Paladin prime attribute should be CHA."""
        paladin = get_char_class("paladin")
        self.assertEqual(paladin.prime_attribute, Ability.CHA)

    def test_multiclass_requirements(self):
        """Paladin multiclass should require STR 14 and CHA 14."""
        paladin = get_char_class("paladin")
        self.assertEqual(paladin.multi_class_requirements[Ability.STR], 14)
        self.assertEqual(paladin.multi_class_requirements[Ability.CHA], 14)
        self.assertEqual(len(paladin.multi_class_requirements), 2)

    def test_progression_has_40_levels(self):
        """Paladin should have progression data for levels 1-40."""
        paladin = get_char_class("paladin")
        self.assertEqual(len(paladin.level_progression), 40)
        self.assertIn(1, paladin.level_progression)
        self.assertIn(40, paladin.level_progression)

    def test_no_race_restrictions(self):
        """Paladin should have no race restrictions."""
        paladin = get_char_class("paladin")
        self.assertEqual(len(paladin.required_races), 0)
        self.assertEqual(len(paladin.excluded_races), 0)

    def test_evil_alignments_excluded(self):
        """Paladin should exclude all three evil alignments."""
        paladin = get_char_class("paladin")
        self.assertEqual(len(paladin.excluded_alignments), 3)
        self.assertIn(Alignment.LAWFUL_EVIL, paladin.excluded_alignments)
        self.assertIn(Alignment.NEUTRAL_EVIL, paladin.excluded_alignments)
        self.assertIn(Alignment.CHAOTIC_EVIL, paladin.excluded_alignments)

    def test_valid_alignments_excludes_evil(self):
        """get_valid_alignments should return 6 non-evil alignments."""
        paladin = get_char_class("paladin")
        valid = paladin.get_valid_alignments()
        self.assertEqual(len(valid), 6)

    def test_requires_one_remort(self):
        """Paladin should require 1 remort."""
        paladin = get_char_class("paladin")
        self.assertEqual(paladin.min_remort, 1)

    def test_grants_spells(self):
        """Paladin should grant spells."""
        paladin = get_char_class("paladin")
        self.assertTrue(paladin.grants_spells)


# ================================================================== #
#  at_char_first_gaining_class — Paladin
# ================================================================== #

class TestPaladinFirstLevel(EvenniaTest):
    """Test at_char_first_gaining_class for Paladin."""

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.paladin = get_char_class("paladin")
        self.char1.hp = 10
        self.char1.hp_max = 10
        self.char1.mana = 10
        self.char1.mana_max = 10
        self.char1.move = 50
        self.char1.move_max = 50
        self.char1.general_skill_pts_available = 0
        self.char1.weapon_skill_pts_available = 0

    def test_sets_class_entry(self):
        """Should create db.classes['paladin'] with level 1."""
        self.paladin.at_char_first_gaining_class(self.char1)
        self.assertIn("paladin", self.char1.db.classes)
        self.assertEqual(self.char1.db.classes["paladin"]["level"], 1)

    def test_hp_gain(self):
        """Paladin level 1 adds HP per progression table."""
        l1 = self.paladin.level_progression[1]
        self.paladin.at_char_first_gaining_class(self.char1)
        self.assertEqual(self.char1.hp, 10 + l1["hp_gain"])
        self.assertEqual(self.char1.hp_max, 10 + l1["hp_gain"])

    def test_mana_gain(self):
        """Paladin level 1 adds mana per progression table."""
        l1 = self.paladin.level_progression[1]
        self.paladin.at_char_first_gaining_class(self.char1)
        self.assertEqual(self.char1.mana, 10 + l1["mana_gain"])
        self.assertEqual(self.char1.mana_max, 10 + l1["mana_gain"])

    def test_move_gain(self):
        """Paladin level 1 adds move per progression table."""
        l1 = self.paladin.level_progression[1]
        self.paladin.at_char_first_gaining_class(self.char1)
        self.assertEqual(self.char1.move, 50 + l1["move_gain"])
        self.assertEqual(self.char1.move_max, 50 + l1["move_gain"])

    def test_class_skill_points(self):
        """Paladin level 1 should grant class skill points per progression."""
        l1 = self.paladin.level_progression[1]
        self.paladin.at_char_first_gaining_class(self.char1)
        self.assertEqual(self.char1.db.classes["paladin"]["skill_pts_available"], l1["class_skill_pts"])

    def test_weapon_skill_points(self):
        """Paladin level 1 should grant weapon skill points per progression."""
        l1 = self.paladin.level_progression[1]
        self.paladin.at_char_first_gaining_class(self.char1)
        self.assertEqual(self.char1.weapon_skill_pts_available, l1["weapon_skill_pts"])

    def test_general_skill_points(self):
        """Paladin level 1 should grant general skill points per progression."""
        l1 = self.paladin.level_progression[1]
        self.paladin.at_char_first_gaining_class(self.char1)
        self.assertEqual(self.char1.general_skill_pts_available, l1["general_skill_pts"])


# ================================================================== #
#  Bard data verification
# ================================================================== #

class TestBardData(EvenniaTest):
    """Verify bard class data is correct."""

    def create_script(self):
        pass

    def test_prime_attribute(self):
        """Bard prime attribute should be CHA."""
        bard = get_char_class("bard")
        self.assertEqual(bard.prime_attribute, Ability.CHA)

    def test_multiclass_requirements(self):
        """Bard multiclass should require CHA 14."""
        bard = get_char_class("bard")
        self.assertEqual(bard.multi_class_requirements[Ability.CHA], 14)
        self.assertEqual(len(bard.multi_class_requirements), 1)

    def test_progression_has_40_levels(self):
        """Bard should have progression data for levels 1-40."""
        bard = get_char_class("bard")
        self.assertEqual(len(bard.level_progression), 40)
        self.assertIn(1, bard.level_progression)
        self.assertIn(40, bard.level_progression)

    def test_no_race_restrictions(self):
        """Bard should have no race restrictions."""
        bard = get_char_class("bard")
        self.assertEqual(len(bard.required_races), 0)
        self.assertEqual(len(bard.excluded_races), 0)

    def test_no_alignment_restrictions(self):
        """Bard should have no alignment restrictions."""
        bard = get_char_class("bard")
        self.assertEqual(len(bard.required_alignments), 0)
        self.assertEqual(len(bard.excluded_alignments), 0)

    def test_requires_two_remorts(self):
        """Bard should require 2 remorts."""
        bard = get_char_class("bard")
        self.assertEqual(bard.min_remort, 2)


# ================================================================== #
#  at_char_first_gaining_class — Bard
# ================================================================== #

class TestBardFirstLevel(EvenniaTest):
    """Test at_char_first_gaining_class for Bard."""

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.bard = get_char_class("bard")
        self.char1.hp = 10
        self.char1.hp_max = 10
        self.char1.mana = 10
        self.char1.mana_max = 10
        self.char1.move = 50
        self.char1.move_max = 50
        self.char1.general_skill_pts_available = 0
        self.char1.weapon_skill_pts_available = 0

    def test_sets_class_entry(self):
        """Should create db.classes['bard'] with level 1."""
        self.bard.at_char_first_gaining_class(self.char1)
        self.assertIn("bard", self.char1.db.classes)
        self.assertEqual(self.char1.db.classes["bard"]["level"], 1)

    def test_hp_gain(self):
        """Bard level 1 adds HP per progression table."""
        l1 = self.bard.level_progression[1]
        self.bard.at_char_first_gaining_class(self.char1)
        self.assertEqual(self.char1.hp, 10 + l1["hp_gain"])
        self.assertEqual(self.char1.hp_max, 10 + l1["hp_gain"])

    def test_mana_gain(self):
        """Bard level 1 adds mana per progression table."""
        l1 = self.bard.level_progression[1]
        self.bard.at_char_first_gaining_class(self.char1)
        self.assertEqual(self.char1.mana, 10 + l1["mana_gain"])
        self.assertEqual(self.char1.mana_max, 10 + l1["mana_gain"])

    def test_move_gain(self):
        """Bard level 1 adds move per progression table."""
        l1 = self.bard.level_progression[1]
        self.bard.at_char_first_gaining_class(self.char1)
        self.assertEqual(self.char1.move, 50 + l1["move_gain"])
        self.assertEqual(self.char1.move_max, 50 + l1["move_gain"])

    def test_class_skill_points(self):
        """Bard level 1 should grant class skill points per progression."""
        l1 = self.bard.level_progression[1]
        self.bard.at_char_first_gaining_class(self.char1)
        self.assertEqual(self.char1.db.classes["bard"]["skill_pts_available"], l1["class_skill_pts"])

    def test_weapon_skill_points(self):
        """Bard level 1 should grant weapon skill points per progression."""
        l1 = self.bard.level_progression[1]
        self.bard.at_char_first_gaining_class(self.char1)
        self.assertEqual(self.char1.weapon_skill_pts_available, l1["weapon_skill_pts"])

    def test_general_skill_points(self):
        """Bard level 1 should grant general skill points per progression."""
        l1 = self.bard.level_progression[1]
        self.bard.at_char_first_gaining_class(self.char1)
        self.assertEqual(self.char1.general_skill_pts_available, l1["general_skill_pts"])
