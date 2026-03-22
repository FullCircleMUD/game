"""
Tests for SpellbookMixin — learn, memorise, forget, grant, revoke, cap, queries.

Uses EvenniaTest with FCMCharacter instances (auto-created by Evennia
test framework). Tests operate on the mixin methods directly.

evennia test --settings settings tests.typeclass_tests.test_spellbook
"""

import math

from evennia.utils.test_resources import EvenniaTest

from world.spells.registry import get_spell


# ================================================================== #
#  Initialization
# ================================================================== #

class TestSpellbookInit(EvenniaTest):
    """Test spellbook initialization."""

    def create_script(self):
        pass

    def test_spellbook_starts_empty(self):
        """db.spellbook should be initialized as empty dict."""
        self.char1.at_spellbook_init()
        self.assertEqual(self.char1.db.spellbook, {})

    def test_memorised_spells_starts_empty(self):
        """db.memorised_spells should be initialized as empty dict."""
        self.char1.at_spellbook_init()
        self.assertEqual(self.char1.db.memorised_spells, {})


# ================================================================== #
#  Learning
# ================================================================== #

class TestLearnSpell(EvenniaTest):
    """Test SpellbookMixin.learn_spell()."""

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.char1.db.spellbook = {}
        self.char1.db.memorised_spells = {}
        # Give mage mastery in evocation at BASIC (1)
        self.char1.db.class_skill_mastery_levels = {"evocation": 1}

    def test_learn_spell_success(self):
        """Learning a valid spell with sufficient mastery succeeds."""
        success, msg = self.char1.learn_spell("magic_missile")
        self.assertTrue(success)
        self.assertIn("Magic Missile", msg)

    def test_learn_spell_in_spellbook(self):
        """After learning, spell is in the spellbook."""
        self.char1.learn_spell("magic_missile")
        self.assertTrue(self.char1.knows_spell("magic_missile"))

    def test_learn_spell_already_known(self):
        """Learning a spell you already know should fail."""
        self.char1.learn_spell("magic_missile")
        success, msg = self.char1.learn_spell("magic_missile")
        self.assertFalse(success)
        self.assertIn("already know", msg.lower())

    def test_learn_spell_insufficient_mastery(self):
        """Learning a spell without school mastery should fail."""
        self.char1.db.class_skill_mastery_levels = {}
        success, msg = self.char1.learn_spell("magic_missile")
        self.assertFalse(success)
        self.assertIn("mastery", msg.lower())

    def test_learn_spell_unknown_spell(self):
        """Learning a nonexistent spell should fail."""
        success, msg = self.char1.learn_spell("nonexistent_spell")
        self.assertFalse(success)
        self.assertIn("doesn't exist", msg.lower())

    def test_learn_different_school(self):
        """Learning divine_healing spell with no divine mastery fails."""
        self.char1.db.class_skill_mastery_levels = {"evocation": 1}
        success, msg = self.char1.learn_spell("cure_wounds")
        self.assertFalse(success)

    def test_learn_divine_with_mastery(self):
        """Learning divine_healing spell with divine mastery succeeds."""
        self.char1.db.class_skill_mastery_levels = {"divine_healing": 1}
        success, msg = self.char1.learn_spell("cure_wounds")
        self.assertTrue(success)


# ================================================================== #
#  Knows Spell
# ================================================================== #

class TestKnowsSpell(EvenniaTest):
    """Test SpellbookMixin.knows_spell()."""

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.char1.db.spellbook = {"magic_missile": True}
        self.char1.db.memorised_spells = {}

    def test_knows_known_spell(self):
        """knows_spell returns True for a known spell."""
        self.assertTrue(self.char1.knows_spell("magic_missile"))

    def test_does_not_know_unknown_spell(self):
        """knows_spell returns False for an unknown spell."""
        self.assertFalse(self.char1.knows_spell("cure_wounds"))

    def test_does_not_know_empty_spellbook(self):
        """knows_spell returns False when spellbook is empty."""
        self.char1.db.spellbook = {}
        self.assertFalse(self.char1.knows_spell("magic_missile"))


# ================================================================== #
#  Memorisation
# ================================================================== #

class TestMemoriseSpell(EvenniaTest):
    """Test SpellbookMixin.memorise_spell()."""

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.char1.db.spellbook = {"magic_missile": True, "cure_wounds": True}
        self.char1.db.memorised_spells = {}
        # Mage level 8 → floor(8/4) = 2, intelligence 14 → bonus +2, total cap = 4
        self.char1.db.classes = {"mage": {"level": 8}}
        self.char1.db.class_skill_mastery_levels = {"evocation": 1}
        self.char1.intelligence = 14
        self.char1.wisdom = 10

    def test_memorise_success(self):
        """Memorising a known spell succeeds."""
        success, msg = self.char1.memorise_spell("magic_missile")
        self.assertTrue(success)
        self.assertIn("Magic Missile", msg)

    def test_memorise_adds_to_set(self):
        """After memorising, spell is in memorised_spells."""
        self.char1.memorise_spell("magic_missile")
        self.assertTrue(self.char1.is_memorised("magic_missile"))

    def test_memorise_already_memorised(self):
        """Memorising an already-memorised spell fails."""
        self.char1.memorise_spell("magic_missile")
        success, msg = self.char1.memorise_spell("magic_missile")
        self.assertFalse(success)
        self.assertIn("already memorised", msg.lower())

    def test_memorise_unknown_spell(self):
        """Memorising a spell you don't know fails."""
        success, msg = self.char1.memorise_spell("nonexistent_spell")
        self.assertFalse(success)

    def test_memorise_cap_exceeded(self):
        """Memorising beyond the cap should fail."""
        # Cap is 4 (floor(8/4) + bonus(14) = 2+2)
        # Fill up to cap
        self.char1.db.spellbook = {
            "magic_missile": True, "cure_wounds": True,
            "spell_a": True, "spell_b": True, "spell_c": True,
        }
        self.char1.db.memorised_spells = {
            "magic_missile": True, "cure_wounds": True,
            "spell_a": True, "spell_b": True,
        }
        success, msg = self.char1.memorise_spell("spell_c")
        self.assertFalse(success)
        self.assertIn("forget one first", msg.lower())


# ================================================================== #
#  Forget
# ================================================================== #

class TestForgetSpell(EvenniaTest):
    """Test SpellbookMixin.forget_spell()."""

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.char1.db.spellbook = {"magic_missile": True}
        self.char1.db.memorised_spells = {"magic_missile": True}

    def test_forget_success(self):
        """Forgetting a memorised spell succeeds."""
        success, msg = self.char1.forget_spell("magic_missile")
        self.assertTrue(success)
        self.assertIn("Magic Missile", msg)

    def test_forget_removes_from_set(self):
        """After forgetting, spell is no longer memorised."""
        self.char1.forget_spell("magic_missile")
        self.assertFalse(self.char1.is_memorised("magic_missile"))

    def test_forget_still_known(self):
        """Forgetting does NOT remove from spellbook — only memorised."""
        self.char1.forget_spell("magic_missile")
        self.assertTrue(self.char1.knows_spell("magic_missile"))

    def test_forget_not_memorised(self):
        """Forgetting a spell that isn't memorised fails."""
        self.char1.db.memorised_spells = {}
        success, msg = self.char1.forget_spell("magic_missile")
        self.assertFalse(success)
        self.assertIn("isn't memorised", msg.lower())


# ================================================================== #
#  Is Memorised
# ================================================================== #

class TestIsMemorised(EvenniaTest):
    """Test SpellbookMixin.is_memorised()."""

    def create_script(self):
        pass

    def test_memorised_spell(self):
        """is_memorised returns True for a memorised spell."""
        self.char1.db.memorised_spells = {"magic_missile": True}
        self.assertTrue(self.char1.is_memorised("magic_missile"))

    def test_not_memorised(self):
        """is_memorised returns False for a non-memorised spell."""
        self.char1.db.memorised_spells = {}
        self.assertFalse(self.char1.is_memorised("magic_missile"))


# ================================================================== #
#  Memorisation Cap
# ================================================================== #

class TestMemorisationCap(EvenniaTest):
    """Test SpellbookMixin.get_memorisation_cap()."""

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.char1.db.classes = {}
        self.char1.intelligence = 10  # bonus 0
        self.char1.wisdom = 10        # bonus 0
        self.char1.extra_memory_slots = 0

    def test_mage_cap(self):
        """Mage level 8, int 14 (+2): floor(8/4) + 2 = 4."""
        self.char1.db.classes = {"mage": {"level": 8}}
        self.char1.intelligence = 14
        self.assertEqual(self.char1.get_memorisation_cap(), 4)

    def test_cleric_cap(self):
        """Cleric level 12, wis 16 (+3): floor(12/4) + 3 = 6."""
        self.char1.db.classes = {"cleric": {"level": 12}}
        self.char1.wisdom = 16
        self.assertEqual(self.char1.get_memorisation_cap(), 6)

    def test_multiclass_cap(self):
        """Mage 8 + int 14 (+2) + Cleric 4 + wis 12 (+1): 4 + 2 = 6."""
        self.char1.db.classes = {
            "mage": {"level": 8},
            "cleric": {"level": 4},
        }
        self.char1.intelligence = 14
        self.char1.wisdom = 12
        # mage: floor(8/4) + 2 = 4, cleric: floor(4/4) + 1 = 2
        self.assertEqual(self.char1.get_memorisation_cap(), 6)

    def test_equipment_bonus(self):
        """extra_memory_slots should add to cap."""
        self.char1.db.classes = {"mage": {"level": 4}}
        self.char1.intelligence = 10  # bonus 0
        self.char1.extra_memory_slots = 3
        # floor(4/4) + 0 + 3 = 4
        self.assertEqual(self.char1.get_memorisation_cap(), 4)

    def test_minimum_cap_is_1(self):
        """Cap should always be at least 1."""
        self.char1.db.classes = {}
        self.assertEqual(self.char1.get_memorisation_cap(), 1)

    def test_low_level_mage(self):
        """Mage level 1, int 10 (+0): floor(1/4) + 0 = 0 → min 1."""
        self.char1.db.classes = {"mage": {"level": 1}}
        self.char1.intelligence = 10
        self.assertEqual(self.char1.get_memorisation_cap(), 1)

    def test_high_level_mage(self):
        """Mage level 20, int 18 (+4): floor(20/4) + 4 = 9."""
        self.char1.db.classes = {"mage": {"level": 20}}
        self.char1.intelligence = 18
        self.assertEqual(self.char1.get_memorisation_cap(), 9)


# ================================================================== #
#  Queries
# ================================================================== #

class TestSpellQueries(EvenniaTest):
    """Test get_known_spells() and get_memorised_spells()."""

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.char1.db.spellbook = {"magic_missile": True, "cure_wounds": True}
        self.char1.db.memorised_spells = {"magic_missile": True}

    def test_get_known_spells_all(self):
        """get_known_spells returns all known spells."""
        known = self.char1.get_known_spells()
        self.assertIn("magic_missile", known)
        self.assertIn("cure_wounds", known)

    def test_get_known_spells_filtered(self):
        """get_known_spells with school filter returns only that school."""
        known = self.char1.get_known_spells(school="evocation")
        self.assertIn("magic_missile", known)
        self.assertNotIn("cure_wounds", known)

    def test_get_known_spells_empty(self):
        """get_known_spells returns empty dict when no spells known."""
        self.char1.db.spellbook = {}
        self.assertEqual(self.char1.get_known_spells(), {})

    def test_get_memorised_spells(self):
        """get_memorised_spells returns memorised spell instances."""
        memorised = self.char1.get_memorised_spells()
        self.assertIn("magic_missile", memorised)
        self.assertNotIn("cure_wounds", memorised)

    def test_get_memorised_spells_empty(self):
        """get_memorised_spells returns empty dict when none memorised."""
        self.char1.db.memorised_spells = {}
        self.assertEqual(self.char1.get_memorised_spells(), {})

    def test_known_spell_instances_are_spell_objects(self):
        """Returned spell values should be Spell instances with correct keys."""
        known = self.char1.get_known_spells()
        self.assertEqual(known["magic_missile"].key, "magic_missile")
        self.assertEqual(known["cure_wounds"].key, "cure_wounds")


# ================================================================== #
#  Granted Spells
# ================================================================== #

class TestGrantSpell(EvenniaTest):
    """Test SpellbookMixin.grant_spell()."""

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.char1.db.spellbook = {}
        self.char1.db.granted_spells = {}
        self.char1.db.memorised_spells = {}

    def test_grant_spell_success(self):
        """Granting a valid spell succeeds."""
        success, msg = self.char1.grant_spell("cure_wounds")
        self.assertTrue(success)
        self.assertIn("Cure Wounds", msg)

    def test_grant_spell_in_granted(self):
        """After granting, spell is in granted_spells."""
        self.char1.grant_spell("cure_wounds")
        self.assertTrue(self.char1.is_granted("cure_wounds"))

    def test_grant_spell_knows(self):
        """After granting, knows_spell returns True."""
        self.char1.grant_spell("cure_wounds")
        self.assertTrue(self.char1.knows_spell("cure_wounds"))

    def test_grant_unknown_spell(self):
        """Granting a nonexistent spell should fail."""
        success, msg = self.char1.grant_spell("nonexistent_spell")
        self.assertFalse(success)
        self.assertIn("doesn't exist", msg.lower())

    def test_grant_already_granted(self):
        """Granting a spell that's already granted should fail."""
        self.char1.grant_spell("cure_wounds")
        success, msg = self.char1.grant_spell("cure_wounds")
        self.assertFalse(success)
        self.assertIn("already granted", msg.lower())

    def test_grant_spell_already_learned(self):
        """Granting a spell that's also learned succeeds (both dicts)."""
        self.char1.db.spellbook = {"cure_wounds": True}
        success, msg = self.char1.grant_spell("cure_wounds")
        self.assertTrue(success)
        self.assertTrue(self.char1.is_granted("cure_wounds"))
        self.assertTrue(self.char1.db.spellbook.get("cure_wounds"))


# ================================================================== #
#  Revoke Spells
# ================================================================== #

class TestRevokeSpell(EvenniaTest):
    """Test SpellbookMixin.revoke_spell() and revoke_all_granted_spells()."""

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.char1.db.spellbook = {}
        self.char1.db.granted_spells = {"cure_wounds": True}
        self.char1.db.memorised_spells = {}

    def test_revoke_spell_success(self):
        """Revoking a granted spell succeeds."""
        success, msg = self.char1.revoke_spell("cure_wounds")
        self.assertTrue(success)
        self.assertIn("revoked", msg.lower())

    def test_revoke_spell_removes_granted(self):
        """After revoking, spell is no longer granted."""
        self.char1.revoke_spell("cure_wounds")
        self.assertFalse(self.char1.is_granted("cure_wounds"))

    def test_revoke_spell_unknown(self):
        """Revoking a spell that isn't granted should fail."""
        success, msg = self.char1.revoke_spell("magic_missile")
        self.assertFalse(success)
        self.assertIn("isn't granted", msg.lower())

    def test_revoke_also_removes_memorised(self):
        """Revoking a granted+memorised spell removes from memorised too."""
        self.char1.db.memorised_spells = {"cure_wounds": True}
        self.char1.revoke_spell("cure_wounds")
        self.assertFalse(self.char1.is_memorised("cure_wounds"))

    def test_revoke_keeps_memorised_if_also_learned(self):
        """Revoking a spell that's also learned keeps it memorised."""
        self.char1.db.spellbook = {"cure_wounds": True}
        self.char1.db.memorised_spells = {"cure_wounds": True}
        self.char1.revoke_spell("cure_wounds")
        self.assertFalse(self.char1.is_granted("cure_wounds"))
        self.assertTrue(self.char1.is_memorised("cure_wounds"))
        self.assertTrue(self.char1.knows_spell("cure_wounds"))

    def test_revoke_all_granted(self):
        """revoke_all_granted_spells clears all granted spells."""
        self.char1.db.granted_spells = {
            "cure_wounds": True,
            "magic_missile": True,
        }
        self.char1.revoke_all_granted_spells()
        self.assertEqual(self.char1.db.granted_spells, {})

    def test_revoke_all_cleans_memorised(self):
        """revoke_all_granted_spells also cleans up memorised spells."""
        self.char1.db.granted_spells = {
            "cure_wounds": True,
            "magic_missile": True,
        }
        self.char1.db.memorised_spells = {
            "cure_wounds": True,
            "magic_missile": True,
        }
        self.char1.revoke_all_granted_spells()
        self.assertEqual(self.char1.db.memorised_spells, {})

    def test_revoke_all_keeps_learned_memorised(self):
        """revoke_all keeps memorised spells that are also learned."""
        self.char1.db.spellbook = {"magic_missile": True}
        self.char1.db.granted_spells = {"cure_wounds": True}
        self.char1.db.memorised_spells = {
            "magic_missile": True,
            "cure_wounds": True,
        }
        self.char1.revoke_all_granted_spells()
        self.assertTrue(self.char1.is_memorised("magic_missile"))
        self.assertFalse(self.char1.is_memorised("cure_wounds"))

    def test_revoke_all_noop_when_empty(self):
        """revoke_all_granted_spells does nothing when no granted spells."""
        self.char1.db.granted_spells = {}
        self.char1.db.memorised_spells = {"magic_missile": True}
        self.char1.db.spellbook = {"magic_missile": True}
        self.char1.revoke_all_granted_spells()
        self.assertTrue(self.char1.is_memorised("magic_missile"))


# ================================================================== #
#  Knows Spell — Granted Integration
# ================================================================== #

class TestKnowsSpellGranted(EvenniaTest):
    """Test knows_spell() checks both learned and granted."""

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.char1.db.spellbook = {"magic_missile": True}
        self.char1.db.granted_spells = {"cure_wounds": True}
        self.char1.db.memorised_spells = {}

    def test_knows_learned_spell(self):
        """knows_spell returns True for a learned spell."""
        self.assertTrue(self.char1.knows_spell("magic_missile"))

    def test_knows_granted_spell(self):
        """knows_spell returns True for a granted spell."""
        self.assertTrue(self.char1.knows_spell("cure_wounds"))

    def test_does_not_know_neither(self):
        """knows_spell returns False for a spell in neither dict."""
        self.assertFalse(self.char1.knows_spell("nonexistent"))

    def test_get_known_spells_unions_both(self):
        """get_known_spells returns spells from both dicts."""
        known = self.char1.get_known_spells()
        self.assertIn("magic_missile", known)
        self.assertIn("cure_wounds", known)
        self.assertEqual(len(known), 2)

    def test_get_known_spells_with_school_filter(self):
        """get_known_spells with school filter works across both dicts."""
        known = self.char1.get_known_spells(school="divine_healing")
        self.assertIn("cure_wounds", known)
        self.assertNotIn("magic_missile", known)


# ================================================================== #
#  Memorise/Forget Granted Spells
# ================================================================== #

class TestMemoriseGrantedSpell(EvenniaTest):
    """Test that granted spells can be memorised and forgotten normally."""

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.char1.db.spellbook = {}
        self.char1.db.granted_spells = {"cure_wounds": True}
        self.char1.db.memorised_spells = {}
        self.char1.db.classes = {"cleric": {"level": 8}}
        self.char1.wisdom = 14
        self.char1.intelligence = 10

    def test_memorise_granted_spell(self):
        """A granted spell can be memorised normally."""
        success, msg = self.char1.memorise_spell("cure_wounds")
        self.assertTrue(success)
        self.assertTrue(self.char1.is_memorised("cure_wounds"))

    def test_forget_granted_spell_keeps_granted(self):
        """Forgetting a granted spell removes from memorised but stays granted."""
        self.char1.memorise_spell("cure_wounds")
        self.char1.forget_spell("cure_wounds")
        self.assertFalse(self.char1.is_memorised("cure_wounds"))
        self.assertTrue(self.char1.is_granted("cure_wounds"))
        self.assertTrue(self.char1.knows_spell("cure_wounds"))


# ================================================================== #
#  Initialization — Granted
# ================================================================== #

class TestSpellbookInitGranted(EvenniaTest):
    """Test that at_spellbook_init initializes granted_spells."""

    def create_script(self):
        pass

    def test_granted_spells_starts_empty(self):
        """db.granted_spells should be initialized as empty dict."""
        self.char1.at_spellbook_init()
        self.assertEqual(self.char1.db.granted_spells, {})
