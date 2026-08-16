"""
Tests for the knowledge grant engine (world/grants.py).

Covers both providers — spells granted by class, recipes granted by skill —
plus the properties the engine relies on being safe to call from chargen,
the trainer, and every login: idempotence and additive-only behaviour.

Expected sets are derived from the registries rather than hardcoded, so
adding a spell or recipe to the game doesn't break these tests.

evennia test --settings settings tests.world_tests.test_grants
"""

from evennia.utils.test_resources import EvenniaTest

from enums.mastery_level import MasteryLevel
from enums.skills_enum import skills
from world.grants import (
    AUTO_GRANT_RECIPE_SKILLS,
    format_gains,
    get_skill_mastery,
    grant_recipes,
    grant_spells,
    reconcile_grants,
)
from world.recipes import get_recipes_for_skill
from world.spells.registry import get_spells_for_school

HEALING = skills.DIVINE_HEALING.value
DOMINION = skills.DIVINE_DOMINION.value


def _spells_up_to(school, mastery):
    """Spell keys in a school at or below a mastery tier."""
    return {
        key
        for key, spell in get_spells_for_school(school).items()
        if spell.min_mastery.value <= mastery
    }


def _recipes_up_to(skill, mastery):
    """Recipe keys for a skill at or below a mastery tier."""
    return {
        key
        for key, recipe in get_recipes_for_skill(skill).items()
        if recipe["min_mastery"].value <= mastery
    }


class GrantTestBase(EvenniaTest):

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.char1.db.spellbook = {}
        self.char1.db.granted_spells = {}
        self.char1.db.recipe_book = {}
        self.char1.db.granted_recipes = {}
        self.char1.db.general_skill_mastery_levels = {}

    def make_cleric(self, **schools):
        """Give char1 the cleric class with the given school masteries."""
        self.char1.db.classes = {"cleric": {"level": 1}}
        self.char1.db.class_skill_mastery_levels = {
            school: {"mastery": mastery, "classes": ["cleric"]}
            for school, mastery in schools.items()
        }
        return self.char1

    def make_mage(self, enchanting=0):
        """Give char1 the mage class at the given enchanting mastery."""
        self.char1.db.classes = {"mage": {"level": 1}}
        self.char1.db.class_skill_mastery_levels = {
            skills.ENCHANTING.value: {
                "mastery": enchanting,
                "classes": ["mage"],
            }
        }
        return self.char1


# ================================================================== #
#  Spells — granted by class
# ================================================================== #

class TestGrantSpells(GrantTestBase):

    def test_basic_mastery_grants_basic_spells(self):
        char = self.make_cleric(**{HEALING: MasteryLevel.BASIC.value})
        gained = grant_spells(char)
        self.assertEqual(
            set(gained), _spells_up_to(HEALING, MasteryLevel.BASIC.value)
        )

    def test_skilled_mastery_grants_the_skilled_spell(self):
        """The bug this engine exists to fix — a new tier hands over its spells."""
        char = self.make_cleric(**{HEALING: MasteryLevel.BASIC.value})
        grant_spells(char)
        basic = set(char.db.granted_spells)

        char.db.class_skill_mastery_levels = {
            HEALING: {"mastery": MasteryLevel.SKILLED.value, "classes": ["cleric"]}
        }
        gained = grant_spells(char)

        expected = _spells_up_to(HEALING, MasteryLevel.SKILLED.value)
        self.assertEqual(set(char.db.granted_spells), expected)
        self.assertEqual(set(gained), expected - basic)
        self.assertTrue(gained, "SKILLED should have added at least one spell")

    def test_does_not_grant_above_current_mastery(self):
        char = self.make_cleric(**{HEALING: MasteryLevel.BASIC.value})
        grant_spells(char)
        granted = set(char.db.granted_spells)
        for key, spell in get_spells_for_school(HEALING).items():
            if spell.min_mastery.value > MasteryLevel.BASIC.value:
                self.assertNotIn(key, granted)

    def test_multiple_schools(self):
        char = self.make_cleric(**{
            HEALING: MasteryLevel.BASIC.value,
            DOMINION: MasteryLevel.SKILLED.value,
        })
        grant_spells(char)
        self.assertEqual(
            set(char.db.granted_spells),
            _spells_up_to(HEALING, MasteryLevel.BASIC.value)
            | _spells_up_to(DOMINION, MasteryLevel.SKILLED.value),
        )

    def test_unskilled_school_grants_nothing(self):
        char = self.make_cleric(**{HEALING: MasteryLevel.UNSKILLED.value})
        self.assertEqual(grant_spells(char), [])
        self.assertFalse(char.db.granted_spells)

    def test_non_granting_class_gets_nothing(self):
        """A mage learns spells from scrolls — mastery grants them nothing."""
        char = self.char1
        char.db.classes = {"mage": {"level": 1}}
        char.db.class_skill_mastery_levels = {
            skills.EVOCATION.value: {
                "mastery": MasteryLevel.EXPERT.value,
                "classes": ["mage"],
            }
        }
        self.assertEqual(grant_spells(char), [])
        self.assertFalse(char.db.granted_spells)

    def test_classless_character_gets_nothing(self):
        char = self.char1
        char.db.classes = {}
        char.db.class_skill_mastery_levels = {
            HEALING: {"mastery": MasteryLevel.MASTER.value, "classes": []}
        }
        self.assertEqual(grant_spells(char), [])

    def test_already_learned_spell_is_not_regranted(self):
        """A spell in the permanent spellbook isn't duplicated into grants."""
        char = self.make_cleric(**{HEALING: MasteryLevel.BASIC.value})
        known = sorted(_spells_up_to(HEALING, MasteryLevel.BASIC.value))[0]
        char.db.spellbook = {known: True}

        gained = grant_spells(char)
        self.assertNotIn(known, gained)
        self.assertNotIn(known, char.db.granted_spells)
        self.assertTrue(char.knows_spell(known))

    def test_idempotent(self):
        char = self.make_cleric(**{HEALING: MasteryLevel.SKILLED.value})
        first = grant_spells(char)
        self.assertTrue(first)
        self.assertEqual(grant_spells(char), [])
        self.assertEqual(set(char.db.granted_spells), set(first))

    def test_additive_only_when_mastery_drops(self):
        """Reconcile never removes — remort clears the store instead."""
        char = self.make_cleric(**{HEALING: MasteryLevel.SKILLED.value})
        grant_spells(char)
        granted = set(char.db.granted_spells)

        char.db.class_skill_mastery_levels = {
            HEALING: {"mastery": MasteryLevel.BASIC.value, "classes": ["cleric"]}
        }
        self.assertEqual(grant_spells(char), [])
        self.assertEqual(set(char.db.granted_spells), granted)

    def test_bare_int_mastery_entry_is_tolerated(self):
        """A legacy int entry must not crash a login."""
        char = self.make_cleric(**{HEALING: MasteryLevel.BASIC.value})
        char.db.class_skill_mastery_levels = {HEALING: MasteryLevel.BASIC.value}
        self.assertEqual(
            set(grant_spells(char)),
            _spells_up_to(HEALING, MasteryLevel.BASIC.value),
        )


# ================================================================== #
#  Recipes — granted by skill
# ================================================================== #

class TestGrantRecipes(GrantTestBase):

    def test_enchanting_is_the_auto_granting_craft(self):
        self.assertIn(skills.ENCHANTING, AUTO_GRANT_RECIPE_SKILLS)

    def test_basic_mastery_grants_basic_recipes(self):
        char = self.make_mage(enchanting=MasteryLevel.BASIC.value)
        gained = grant_recipes(char)
        self.assertEqual(
            set(gained),
            _recipes_up_to(skills.ENCHANTING, MasteryLevel.BASIC.value),
        )

    def test_higher_mastery_grants_more(self):
        char = self.make_mage(enchanting=MasteryLevel.BASIC.value)
        grant_recipes(char)
        basic = set(char.db.granted_recipes)

        char.db.class_skill_mastery_levels = {
            skills.ENCHANTING.value: {
                "mastery": MasteryLevel.EXPERT.value,
                "classes": ["mage"],
            }
        }
        grant_recipes(char)
        expert = set(char.db.granted_recipes)
        self.assertTrue(basic < expert, "EXPERT should be a strict superset of BASIC")

    def test_no_enchanting_mastery_grants_nothing(self):
        char = self.make_mage(enchanting=MasteryLevel.UNSKILLED.value)
        self.assertEqual(grant_recipes(char), [])

    def test_granted_recipes_are_known(self):
        char = self.make_mage(enchanting=MasteryLevel.BASIC.value)
        gained = grant_recipes(char)
        for key in gained:
            self.assertTrue(char.knows_recipe(key))
        self.assertLessEqual(set(gained), set(char.get_known_recipes()))

    def test_scroll_based_craft_is_not_granted(self):
        """Blacksmithing mastery hands out nothing — those use scrolls."""
        char = self.char1
        char.db.classes = {}
        char.db.general_skill_mastery_levels = {
            skills.BLACKSMITH.value: MasteryLevel.MASTER.value
        }
        self.assertEqual(grant_recipes(char), [])
        self.assertFalse(char.db.granted_recipes)

    def test_idempotent(self):
        char = self.make_mage(enchanting=MasteryLevel.SKILLED.value)
        first = grant_recipes(char)
        self.assertTrue(first)
        self.assertEqual(grant_recipes(char), [])


# ================================================================== #
#  Mastery lookup
# ================================================================== #

class TestGetSkillMastery(GrantTestBase):

    def test_reads_class_skill_pool(self):
        char = self.make_cleric(**{HEALING: MasteryLevel.EXPERT.value})
        self.assertEqual(
            get_skill_mastery(char, skills.DIVINE_HEALING),
            MasteryLevel.EXPERT.value,
        )

    def test_reads_general_skill_pool(self):
        char = self.char1
        char.db.general_skill_mastery_levels = {
            skills.BLACKSMITH.value: MasteryLevel.SKILLED.value
        }
        self.assertEqual(
            get_skill_mastery(char, skills.BLACKSMITH),
            MasteryLevel.SKILLED.value,
        )

    def test_absent_skill_is_zero(self):
        char = self.make_cleric()
        self.assertEqual(get_skill_mastery(char, skills.DIVINE_HEALING), 0)


# ================================================================== #
#  The combined entry point
# ================================================================== #

class TestReconcileGrants(GrantTestBase):

    def test_returns_both_kinds(self):
        char = self.make_cleric(**{HEALING: MasteryLevel.BASIC.value})
        gained = reconcile_grants(char)
        self.assertEqual(set(gained), {"spells", "recipes"})
        self.assertTrue(gained["spells"])
        self.assertEqual(gained["recipes"], [])

    def test_idempotent(self):
        char = self.make_cleric(**{HEALING: MasteryLevel.BASIC.value})
        reconcile_grants(char)
        self.assertEqual(
            reconcile_grants(char), {"spells": [], "recipes": []}
        )

    def test_format_gains_names_the_spell(self):
        char = self.make_cleric(**{HEALING: MasteryLevel.BASIC.value})
        lines = format_gains(reconcile_grants(char))
        self.assertEqual(len(lines), len(char.db.granted_spells))
        self.assertTrue(all("You have gained the spell" in ln for ln in lines))

    def test_format_gains_empty_when_nothing_gained(self):
        char = self.make_cleric()
        self.assertEqual(format_gains(reconcile_grants(char)), [])
