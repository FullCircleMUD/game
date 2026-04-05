"""
Tests for ItemRestrictionMixin — item usage restrictions based on class,
race, alignment, level, attributes, mastery, and remorts.

Tests cover can_use() logic, is_restricted property, multiclass edge cases,
and wear() integration.

evennia test --settings settings tests.typeclass_tests.test_item_restriction
"""

from unittest.mock import MagicMock

from evennia.utils.test_resources import EvenniaTest
from evennia.utils import create

from enums.alignment import Alignment
from typeclasses.actors.races import Race
from enums.wearslot import HumanoidWearSlot


# ── Test Helpers ──────────────────────────────────────────────────────────

def _make_item(key, location=None, **attrs):
    """Create a BaseNFTItem and set restriction attributes."""
    obj = create.create_object(
        "typeclasses.items.base_nft_item.BaseNFTItem",
        key=key,
        nohome=True,
    )
    for attr_name, value in attrs.items():
        setattr(obj.db, attr_name, value)
    # Add wearslot + no-op hooks so wear() works in integration tests
    obj.db.wearslot = HumanoidWearSlot.WIELD.value
    obj.at_wear = MagicMock()
    obj.at_remove = MagicMock()
    if location:
        obj.move_to(location, quiet=True)
    return obj


def _setup_char(char, classes=None, race=None, alignment=None,
                total_level=0, num_remorts=0, abilities=None,
                general_skills=None, class_skills=None,
                weapon_skills=None):
    """Configure character attributes for restriction tests."""
    if classes is not None:
        char.db.classes = classes
    if race is not None:
        # Store as .value string to match can_use() str() comparison
        char.race = race.value if hasattr(race, "value") else race
    if alignment is not None:
        # Map alignment enum to alignment_score so the derived property
        # returns the correct good/neutral/evil bucket
        from enums.alignment import Alignment
        _GOOD = {Alignment.LAWFUL_GOOD, Alignment.NEUTRAL_GOOD, Alignment.CHAOTIC_GOOD}
        _EVIL = {Alignment.LAWFUL_EVIL, Alignment.NEUTRAL_EVIL, Alignment.CHAOTIC_EVIL}
        if alignment in _GOOD:
            char.alignment_score = 500
        elif alignment in _EVIL:
            char.alignment_score = -500
        else:
            char.alignment_score = 0
    if total_level:
        char.total_level = total_level
    if num_remorts:
        char.num_remorts = num_remorts
    if abilities:
        for attr, value in abilities.items():
            setattr(char, attr, value)
    if general_skills is not None:
        char.db.general_skill_mastery_levels = general_skills
    if class_skills is not None:
        char.db.class_skill_mastery_levels = class_skills
    if weapon_skills is not None:
        char.db.weapon_skill_mastery_levels = weapon_skills


# ── Unrestricted (Default) ────────────────────────────────────────────────

class TestUnrestricted(EvenniaTest):
    """Unrestricted items should always pass can_use()."""

    def create_script(self):
        pass

    def test_default_passes(self):
        """Item with no restrictions should pass."""
        item = _make_item("Plain Sword")
        allowed, reason = item.can_use(self.char1)
        self.assertTrue(allowed)
        self.assertEqual(reason, "")

    def test_is_restricted_false(self):
        """is_restricted should be False when all defaults."""
        item = _make_item("Plain Sword")
        self.assertFalse(item.is_restricted)


# ── Required Classes (OR logic) ───────────────────────────────────────────

class TestRequiredClasses(EvenniaTest):
    """required_classes: character must have ANY listed class."""

    def create_script(self):
        pass

    def test_has_required_class(self):
        """Warrior with required=[warrior] should pass."""
        _setup_char(self.char1, classes={"warrior": {"level": 1}})
        item = _make_item("War Axe", required_classes=["warrior"])
        allowed, _ = item.can_use(self.char1)
        self.assertTrue(allowed)

    def test_missing_required_class(self):
        """Thief with required=[warrior] should fail."""
        _setup_char(self.char1, classes={"thief": {"level": 5}})
        item = _make_item("War Axe", required_classes=["warrior"])
        allowed, reason = item.can_use(self.char1)
        self.assertFalse(allowed)
        self.assertIn("Warrior", reason)

    def test_multiclass_one_match(self):
        """Warrior/thief with required=[warrior] should pass."""
        _setup_char(self.char1, classes={
            "warrior": {"level": 3},
            "thief": {"level": 2},
        })
        item = _make_item("War Axe", required_classes=["warrior"])
        allowed, _ = item.can_use(self.char1)
        self.assertTrue(allowed)

    def test_multiple_required_any_match(self):
        """Paladin with required=[warrior, paladin] should pass."""
        _setup_char(self.char1, classes={"paladin": {"level": 1}})
        item = _make_item("Holy Sword", required_classes=["warrior", "paladin"])
        allowed, _ = item.can_use(self.char1)
        self.assertTrue(allowed)

    def test_no_classes_at_all(self):
        """Character with no classes and required=[warrior] should fail."""
        item = _make_item("War Axe", required_classes=["warrior"])
        allowed, _ = item.can_use(self.char1)
        self.assertFalse(allowed)

    def test_is_restricted_true(self):
        """is_restricted should be True when required_classes is set."""
        item = _make_item("War Axe", required_classes=["warrior"])
        self.assertTrue(item.is_restricted)


# ── Excluded Classes (AND-NOT logic) ──────────────────────────────────────

class TestExcludedClasses(EvenniaTest):
    """excluded_classes: character must have NONE of the listed classes."""

    def create_script(self):
        pass

    def test_excluded_class_present(self):
        """Thief with excluded=[thief] should fail."""
        _setup_char(self.char1, classes={"thief": {"level": 1}})
        item = _make_item("Holy Mace", excluded_classes=["thief"])
        allowed, reason = item.can_use(self.char1)
        self.assertFalse(allowed)
        self.assertIn("Thief", reason)

    def test_excluded_class_absent(self):
        """Warrior with excluded=[thief] should pass."""
        _setup_char(self.char1, classes={"warrior": {"level": 1}})
        item = _make_item("Holy Mace", excluded_classes=["thief"])
        allowed, _ = item.can_use(self.char1)
        self.assertTrue(allowed)

    def test_multiclass_one_excluded(self):
        """Warrior/thief with excluded=[thief] should fail."""
        _setup_char(self.char1, classes={
            "warrior": {"level": 5},
            "thief": {"level": 1},
        })
        item = _make_item("Holy Mace", excluded_classes=["thief"])
        allowed, _ = item.can_use(self.char1)
        self.assertFalse(allowed)


# ── Combined Required + Excluded ──────────────────────────────────────────

class TestRequiredAndExcluded(EvenniaTest):
    """Exclusion vetoes even if a required class is present."""

    def create_script(self):
        pass

    def test_required_and_excluded_both_match(self):
        """Warrior/thief: required=[warrior], excluded=[thief] → fail."""
        _setup_char(self.char1, classes={
            "warrior": {"level": 5},
            "thief": {"level": 1},
        })
        item = _make_item(
            "Paladin Sword",
            required_classes=["warrior"],
            excluded_classes=["thief"],
        )
        allowed, _ = item.can_use(self.char1)
        self.assertFalse(allowed)

    def test_required_match_no_exclusion(self):
        """Pure warrior: required=[warrior], excluded=[thief] → pass."""
        _setup_char(self.char1, classes={"warrior": {"level": 5}})
        item = _make_item(
            "Paladin Sword",
            required_classes=["warrior"],
            excluded_classes=["thief"],
        )
        allowed, _ = item.can_use(self.char1)
        self.assertTrue(allowed)


# ── Min Class Levels ──────────────────────────────────────────────────────

class TestMinClassLevels(EvenniaTest):
    """min_class_levels: each listed class must be at >= level."""

    def create_script(self):
        pass

    def test_meets_class_level(self):
        """Warrior(5) with min_class_levels={warrior: 5} should pass."""
        _setup_char(self.char1, classes={"warrior": {"level": 5}})
        item = _make_item("Heavy Axe", min_class_levels={"warrior": 5})
        allowed, _ = item.can_use(self.char1)
        self.assertTrue(allowed)

    def test_below_class_level(self):
        """Warrior(3) with min_class_levels={warrior: 5} should fail."""
        _setup_char(self.char1, classes={"warrior": {"level": 3}})
        item = _make_item("Heavy Axe", min_class_levels={"warrior": 5})
        allowed, reason = item.can_use(self.char1)
        self.assertFalse(allowed)
        self.assertIn("level 5", reason)
        self.assertIn("currently level 3", reason)

    def test_missing_required_class_for_level(self):
        """Thief with min_class_levels={warrior: 5} should fail."""
        _setup_char(self.char1, classes={"thief": {"level": 10}})
        item = _make_item("Heavy Axe", min_class_levels={"warrior": 5})
        allowed, _ = item.can_use(self.char1)
        self.assertFalse(allowed)


# ── Race Restrictions ─────────────────────────────────────────────────────

class TestRaceRestrictions(EvenniaTest):
    """Race required/excluded checks."""

    def create_script(self):
        pass

    def test_required_race_match(self):
        """Dwarf with required_races=[DWARF] should pass."""
        _setup_char(self.char1, race=Race.DWARF)
        item = _make_item("Dwarven Hammer", required_races=[Race.DWARF.value])
        allowed, _ = item.can_use(self.char1)
        self.assertTrue(allowed)

    def test_required_race_no_match(self):
        """Human with required_races=[DWARF] should fail."""
        _setup_char(self.char1, race=Race.HUMAN)
        item = _make_item("Dwarven Hammer", required_races=[Race.DWARF.value])
        allowed, reason = item.can_use(self.char1)
        self.assertFalse(allowed)

    def test_excluded_race_match(self):
        """Elf with excluded_races=[ELF] should fail."""
        _setup_char(self.char1, race=Race.ELF)
        item = _make_item("Iron Shield", excluded_races=[Race.ELF.value])
        allowed, _ = item.can_use(self.char1)
        self.assertFalse(allowed)

    def test_excluded_race_no_match(self):
        """Human with excluded_races=[ELF] should pass."""
        _setup_char(self.char1, race=Race.HUMAN)
        item = _make_item("Iron Shield", excluded_races=[Race.ELF.value])
        allowed, _ = item.can_use(self.char1)
        self.assertTrue(allowed)


# ── Alignment Restrictions ────────────────────────────────────────────────

class TestAlignmentRestrictions(EvenniaTest):
    """Alignment required/excluded checks."""

    def create_script(self):
        pass

    def test_required_alignment_match(self):
        """Good character with required=[NEUTRAL_GOOD] should pass."""
        _setup_char(self.char1, alignment=Alignment.NEUTRAL_GOOD)
        item = _make_item(
            "Holy Avenger",
            required_alignments=[Alignment.NEUTRAL_GOOD.value],
        )
        allowed, _ = item.can_use(self.char1)
        self.assertTrue(allowed)

    def test_required_alignment_no_match(self):
        """Evil character with required=[NEUTRAL_GOOD] should fail."""
        _setup_char(self.char1, alignment=Alignment.NEUTRAL_EVIL)
        item = _make_item(
            "Holy Avenger",
            required_alignments=[Alignment.NEUTRAL_GOOD.value],
        )
        allowed, reason = item.can_use(self.char1)
        self.assertFalse(allowed)
        self.assertIn("alignment", reason)

    def test_excluded_alignment_match(self):
        """Evil character with excluded=[NEUTRAL_EVIL] should fail."""
        _setup_char(self.char1, alignment=Alignment.NEUTRAL_EVIL)
        item = _make_item(
            "Blessed Robe",
            excluded_alignments=[Alignment.NEUTRAL_EVIL.value],
        )
        allowed, _ = item.can_use(self.char1)
        self.assertFalse(allowed)

    def test_excluded_alignment_no_match(self):
        """Good character with excluded=[NEUTRAL_EVIL] should pass."""
        _setup_char(self.char1, alignment=Alignment.NEUTRAL_GOOD)
        item = _make_item(
            "Blessed Robe",
            excluded_alignments=[Alignment.NEUTRAL_EVIL.value],
        )
        allowed, _ = item.can_use(self.char1)
        self.assertTrue(allowed)


# ── Level and Remort ──────────────────────────────────────────────────────

class TestLevelAndRemort(EvenniaTest):
    """min_total_level and min_remorts checks."""

    def create_script(self):
        pass

    def test_meets_total_level(self):
        """Character at level 10 with min_total_level=10 should pass."""
        _setup_char(self.char1, total_level=10)
        item = _make_item("Veteran's Blade", min_total_level=10)
        allowed, _ = item.can_use(self.char1)
        self.assertTrue(allowed)

    def test_below_total_level(self):
        """Character at level 3 with min_total_level=10 should fail."""
        _setup_char(self.char1, total_level=3)
        item = _make_item("Veteran's Blade", min_total_level=10)
        allowed, reason = item.can_use(self.char1)
        self.assertFalse(allowed)
        self.assertIn("level 10", reason)

    def test_meets_remorts(self):
        """Character with 2 remorts and min_remorts=2 should pass."""
        _setup_char(self.char1, num_remorts=2)
        item = _make_item("Reborn Blade", min_remorts=2)
        allowed, _ = item.can_use(self.char1)
        self.assertTrue(allowed)

    def test_below_remorts(self):
        """Character with 0 remorts and min_remorts=1 should fail."""
        _setup_char(self.char1, num_remorts=0)
        item = _make_item("Reborn Blade", min_remorts=1)
        allowed, reason = item.can_use(self.char1)
        self.assertFalse(allowed)
        self.assertIn("remort", reason)


# ── Ability Score Restrictions ────────────────────────────────────────────

class TestMinAttributes(EvenniaTest):
    """min_attributes: each ability score must meet minimum."""

    def create_script(self):
        pass

    def test_meets_all_attributes(self):
        """Character meeting all attribute requirements should pass."""
        _setup_char(self.char1, abilities={"strength": 16, "dexterity": 14})
        item = _make_item(
            "Heavy Bow",
            min_attributes={"strength": 14, "dexterity": 12},
        )
        allowed, _ = item.can_use(self.char1)
        self.assertTrue(allowed)

    def test_fails_one_attribute(self):
        """Character failing one attribute requirement should fail."""
        _setup_char(self.char1, abilities={"strength": 10, "dexterity": 14})
        item = _make_item(
            "Heavy Bow",
            min_attributes={"strength": 14, "dexterity": 12},
        )
        allowed, reason = item.can_use(self.char1)
        self.assertFalse(allowed)
        self.assertIn("strength", reason)
        self.assertIn("14", reason)


# ── Skill Mastery Restrictions ────────────────────────────────────────────

class TestMinMastery(EvenniaTest):
    """min_mastery: skill mastery must meet minimum across all skill dicts."""

    def create_script(self):
        pass

    def test_general_skill_meets(self):
        """Character with general skill at required level should pass."""
        _setup_char(self.char1, general_skills={"blacksmith": 3})
        item = _make_item("Master Tongs", min_mastery={"blacksmith": 3})
        allowed, _ = item.can_use(self.char1)
        self.assertTrue(allowed)

    def test_weapon_skill_meets(self):
        """Character with weapon skill at required level should pass."""
        _setup_char(self.char1, weapon_skills={"longsword": 2})
        item = _make_item("Fine Longsword", min_mastery={"longsword": 2})
        allowed, _ = item.can_use(self.char1)
        self.assertTrue(allowed)

    def test_class_skill_meets(self):
        """Character with class skill at required level should pass."""
        _setup_char(self.char1, class_skills={"stab": 4})
        item = _make_item("Shadow Dagger", min_mastery={"stab": 4})
        allowed, _ = item.can_use(self.char1)
        self.assertTrue(allowed)

    def test_skill_too_low(self):
        """Character with skill below required level should fail."""
        _setup_char(self.char1, weapon_skills={"longsword": 1})
        item = _make_item("Fine Longsword", min_mastery={"longsword": 3})
        allowed, reason = item.can_use(self.char1)
        self.assertFalse(allowed)
        self.assertIn("longsword", reason)

    def test_missing_skill(self):
        """Character with no mastery in required skill should fail."""
        item = _make_item("Fine Longsword", min_mastery={"longsword": 1})
        allowed, _ = item.can_use(self.char1)
        self.assertFalse(allowed)


# ── Multiple Restrictions Combined ────────────────────────────────────────

class TestCombinedRestrictions(EvenniaTest):
    """Multiple restriction types combined on one item."""

    def create_script(self):
        pass

    def test_all_pass(self):
        """Character meeting all restrictions should pass."""
        _setup_char(
            self.char1,
            classes={"warrior": {"level": 5}},
            race=Race.HUMAN,
            alignment=Alignment.LAWFUL_GOOD,
            total_level=5,
            abilities={"strength": 14},
        )
        item = _make_item(
            "Holy Greatsword",
            required_classes=["warrior"],
            required_races=[Race.HUMAN.value, Race.DWARF.value],
            required_alignments=[Alignment.LAWFUL_GOOD.value, Alignment.NEUTRAL_GOOD.value],
            min_total_level=5,
            min_attributes={"strength": 14},
        )
        allowed, _ = item.can_use(self.char1)
        self.assertTrue(allowed)

    def test_first_failure_short_circuits(self):
        """Should fail on first restriction not met (class check first)."""
        _setup_char(
            self.char1,
            classes={"thief": {"level": 5}},
            race=Race.HUMAN,
            total_level=5,
        )
        item = _make_item(
            "Holy Greatsword",
            required_classes=["warrior"],
            min_total_level=5,
        )
        allowed, reason = item.can_use(self.char1)
        self.assertFalse(allowed)
        self.assertIn("Warrior", reason)


# ── Wear Integration ──────────────────────────────────────────────────────

class TestWearIntegration(EvenniaTest):
    """Test can_use() integration with the wear() validation chain."""

    def create_script(self):
        pass

    def test_restricted_item_rejected(self):
        """wear() should reject item that fails can_use()."""
        item = _make_item(
            "War Axe",
            location=self.char1,
            required_classes=["warrior"],
        )
        success, reason = self.char1.wear(item)
        self.assertFalse(success)
        self.assertIn("Warrior", reason)

    def test_unrestricted_item_wearable(self):
        """wear() should allow unrestricted item."""
        item = _make_item("Plain Sword", location=self.char1)
        success, _ = self.char1.wear(item)
        self.assertTrue(success)

    def test_restricted_item_passes_when_qualified(self):
        """wear() should allow restricted item when character qualifies."""
        _setup_char(self.char1, classes={"warrior": {"level": 1}})
        item = _make_item(
            "War Axe",
            location=self.char1,
            required_classes=["warrior"],
        )
        success, _ = self.char1.wear(item)
        self.assertTrue(success)
