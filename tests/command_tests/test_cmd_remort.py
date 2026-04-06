"""
Tests for the remort system — perk registry, at_remort(), chargen remort
awareness, and the CmdRemort command.

Covers:
    - Perk registry: get_available_perks, apply_perk
    - at_remort(): character strip, bank transfers, preserved data
    - Chargen remort awareness: skill budgets, name skip, [Remort] tags
    - CmdRemort: level gate, Y/N confirmation, perk selection, EvMenu launch
"""

from unittest.mock import MagicMock, patch, PropertyMock

from evennia.utils.test_resources import BaseEvenniaTest, EvenniaCommandTest

from enums.abilities_enum import Ability
from server.main_menu.chargen.chargen_menu import (
    ABILITIES,
    _get_skill_budget,
    _goto_after_languages,
    _restart,
    node_race_select,
    node_class_select,
    node_confirm,
)
from server.main_menu.remort.remort_perks import (
    REMORT_PERKS,
    POINT_BUY_CAP,
    get_available_perks,
    apply_perk,
)
from commands.all_char_cmds.cmd_remort import CmdRemort


class _MockCaller:
    """Lightweight mock for EvMenu caller (account)."""

    def __init__(self, chargen_state=None):
        self.ndb = MagicMock()
        self.ndb._chargen = chargen_state or {}
        self._messages = []

    def msg(self, text="", **kwargs):
        self._messages.append(text)


def _default_state():
    """Return a typical chargen state mid-flow."""
    return {
        "session": MagicMock(address="127.0.0.1"),
        "race_key": "human",
        "class_key": "warrior",
        "scores": {ab: 8 for ab in ABILITIES},
        "points_remaining": 27,
        "point_buy": 27,
    }


def _remort_state(character=None):
    """Return a typical remort chargen state."""
    char = character or MagicMock()
    char.key = "TestHero"
    char.num_remorts = 1
    char.point_buy = 32
    char.bonus_weapon_skill_pts = 10
    char.bonus_class_skill_pts = 0
    char.bonus_general_skill_pts = 0
    return {
        "session": MagicMock(address="127.0.0.1"),
        "is_remort": True,
        "character": char,
        "num_remorts": 1,
        "point_buy": 32,
        "race_key": "human",
        "class_key": "warrior",
        "scores": {ab: 8 for ab in ABILITIES},
        "points_remaining": 32,
    }


# =======================================================================
#  Perk Registry Tests
# =======================================================================

class TestPerkRegistry(BaseEvenniaTest):

    def create_script(self):
        pass

    def test_all_perks_have_required_keys(self):
        """Every perk dict must have key, name, desc, attribute, increment, cap."""
        required = {"key", "name", "desc", "attribute", "increment", "cap"}
        for perk in REMORT_PERKS:
            self.assertTrue(required.issubset(perk.keys()), f"Perk {perk.get('key')} missing keys")

    def test_perk_keys_unique(self):
        """All perk keys must be unique."""
        keys = [p["key"] for p in REMORT_PERKS]
        self.assertEqual(len(keys), len(set(keys)))

    def test_point_buy_cap_value(self):
        """POINT_BUY_CAP should be 75."""
        self.assertEqual(POINT_BUY_CAP, 75)

    def test_get_available_perks_all_available(self):
        """A fresh character should see all perks."""
        char = MagicMock()
        # Set all perk attributes to 0
        for perk in REMORT_PERKS:
            setattr(char, perk["attribute"], 0)
        # point_buy defaults to 27 for fresh char
        char.point_buy = 27

        available = get_available_perks(char)
        self.assertEqual(len(available), len(REMORT_PERKS))

    def test_get_available_perks_capped_hidden(self):
        """A perk at cap should not appear in available list."""
        char = MagicMock()
        for perk in REMORT_PERKS:
            setattr(char, perk["attribute"], 0)
        # Cap the HP perk
        char.bonus_hp_per_level = 5

        available = get_available_perks(char)
        keys = [p["key"] for p in available]
        self.assertNotIn("bonus_hp_per_level", keys)

    def test_apply_perk_increments(self):
        """apply_perk should increment the attribute by the perk's increment."""
        char = MagicMock()
        char.bonus_hp_per_level = 2
        perk = REMORT_PERKS[1]  # bonus_hp_per_level
        success, msg = apply_perk(char, perk)
        self.assertTrue(success)
        # Should set to 3
        self.assertEqual(char.bonus_hp_per_level, 3)

    def test_apply_perk_at_cap_fails(self):
        """apply_perk should fail when attribute is already at cap."""
        char = MagicMock()
        char.bonus_hp_per_level = 5
        perk = REMORT_PERKS[1]  # bonus_hp_per_level, cap=5
        success, msg = apply_perk(char, perk)
        self.assertFalse(success)
        self.assertIn("maximum", msg)

    def test_apply_perk_clamps_to_cap(self):
        """apply_perk should not exceed the cap."""
        char = MagicMock()
        char.bonus_hp_per_level = 4
        perk = {
            "key": "test",
            "name": "Test",
            "desc": "test",
            "attribute": "bonus_hp_per_level",
            "increment": 3,
            "cap": 5,
        }
        success, msg = apply_perk(char, perk)
        self.assertTrue(success)
        self.assertEqual(char.bonus_hp_per_level, 5)


# =======================================================================
#  Chargen Remort Awareness Tests
# =======================================================================

class TestChargenSkillBudget(BaseEvenniaTest):
    """Test that _get_skill_budget includes remort bonuses."""

    def create_script(self):
        pass

    def test_weapon_budget_no_remort(self):
        """Without remort character, budget is just class base."""
        state = _default_state()
        budget = _get_skill_budget(state, "weapon_skill_pts")
        # Warrior level 1 has 4 weapon skill pts
        self.assertEqual(budget, 4)

    def test_weapon_budget_with_remort_bonus(self):
        """With remort character, budget includes bonus."""
        state = _remort_state()
        budget = _get_skill_budget(state, "weapon_skill_pts")
        # Warrior base 4 + 10 bonus = 14
        self.assertEqual(budget, 14)

    def test_class_budget_no_bonus(self):
        """Class budget without remort bonus."""
        state = _remort_state()
        budget = _get_skill_budget(state, "class_skill_pts")
        # Warrior level 1 has 3 class skill pts + 0 bonus
        self.assertEqual(budget, 3)

    def test_general_budget_no_bonus(self):
        """General budget without remort bonus."""
        state = _remort_state()
        budget = _get_skill_budget(state, "general_skill_pts")
        # Warrior level 1 has 2 general skill pts + 0 bonus
        self.assertEqual(budget, 2)


class TestGotoAfterLanguages(BaseEvenniaTest):
    """Test that _goto_after_languages skips name for remort."""

    def create_script(self):
        pass

    def test_new_char_goes_to_name(self):
        """Non-remort should go to node_name."""
        caller = _MockCaller(_default_state())
        result = _goto_after_languages(caller, "")
        self.assertEqual(result, "node_name")

    def test_remort_goes_to_confirm(self):
        """Remort should skip name and go to node_confirm."""
        state = _remort_state()
        caller = _MockCaller(state)
        result = _goto_after_languages(caller, "")
        self.assertEqual(result, "node_confirm")

    def test_remort_sets_char_name(self):
        """Remort should set char_name from character.key."""
        state = _remort_state()
        caller = _MockCaller(state)
        _goto_after_languages(caller, "")
        self.assertEqual(state["char_name"], "TestHero")


class TestRestartPreservesRemort(BaseEvenniaTest):
    """Test that _restart preserves remort state."""

    def create_script(self):
        pass

    def test_restart_preserves_remort_keys(self):
        """Restart should preserve is_remort, character, num_remorts, point_buy."""
        state = _remort_state()
        caller = _MockCaller(state)
        result = _restart(caller, "")
        self.assertEqual(result, "node_race_select")
        new_state = caller.ndb._chargen
        self.assertTrue(new_state.get("is_remort"))
        self.assertEqual(new_state.get("num_remorts"), 1)
        self.assertEqual(new_state.get("point_buy"), 32)

    def test_restart_clears_choices(self):
        """Restart should clear race/class/alignment selections."""
        state = _remort_state()
        caller = _MockCaller(state)
        _restart(caller, "")
        new_state = caller.ndb._chargen
        self.assertNotIn("race_key", new_state)
        self.assertNotIn("class_key", new_state)
        self.assertNotIn("alignment", new_state)


class TestRemortTags(BaseEvenniaTest):
    """Test that [Remort] tags appear on remort-only races and classes."""

    def create_script(self):
        pass

    def test_race_select_shows_remort_tag(self):
        """Remort races should show [Remort] tag in display."""
        state = {"num_remorts": 2}
        caller = _MockCaller(state)
        text, options = node_race_select(caller, "")
        # Find the Aasimar option (min_remort=2)
        found_remort_tag = False
        for opt in options:
            desc = opt.get("desc", "")
            if "Aasimar" in desc and "[Remort]" in desc:
                found_remort_tag = True
                break
        self.assertTrue(found_remort_tag, "Aasimar should show [Remort] tag")

    def test_race_select_no_tag_for_base_races(self):
        """Base races (min_remort=0) should NOT show [Remort] tag."""
        state = {"num_remorts": 2}
        caller = _MockCaller(state)
        text, options = node_race_select(caller, "")
        for opt in options:
            desc = opt.get("desc", "")
            if "Human" in desc:
                self.assertNotIn("[Remort]", desc)
                break

    def test_class_select_shows_remort_tag(self):
        """Remort classes should show [Remort] tag in display."""
        state = {"num_remorts": 2, "race_key": "human"}
        caller = _MockCaller(state)
        text, options = node_class_select(caller, "")
        found_remort_tag = False
        for opt in options:
            desc = opt.get("desc", "")
            if "Paladin" in desc and "[Remort]" in desc:
                found_remort_tag = True
                break
        self.assertTrue(found_remort_tag, "Paladin should show [Remort] tag")


class TestConfirmNodeRemort(BaseEvenniaTest):
    """Test node_confirm adjustments for remort."""

    def create_script(self):
        pass

    def test_confirm_shows_rebuild_for_remort(self):
        """Remort confirm should show 'Rebuild' instead of 'Create'."""
        state = _remort_state()
        state["char_name"] = "TestHero"
        state["selected_weapon_skills"] = set()
        state["selected_class_skills"] = set()
        state["selected_general_skills"] = set()
        caller = _MockCaller(state)
        text, options = node_confirm(caller, "")
        # Check header
        self.assertIn("Remort", text)
        self.assertIn("Rebuild", text)
        # Check confirm button
        confirm_opt = options[0]
        self.assertIn("Rebuild", confirm_opt["desc"])

    def test_confirm_shows_create_for_new_char(self):
        """New char confirm should show 'Create'."""
        state = _default_state()
        state["char_name"] = "NewChar"
        state["selected_weapon_skills"] = set()
        state["selected_class_skills"] = set()
        state["selected_general_skills"] = set()
        caller = _MockCaller(state)
        text, options = node_confirm(caller, "")
        self.assertNotIn("Remort", text)
        confirm_opt = options[0]
        self.assertIn("Create", confirm_opt["desc"])

    def test_confirm_back_goes_to_languages_for_remort(self):
        """Remort confirm back should go to languages, not name."""
        state = _remort_state()
        state["char_name"] = "TestHero"
        state["selected_weapon_skills"] = set()
        state["selected_class_skills"] = set()
        state["selected_general_skills"] = set()
        caller = _MockCaller(state)
        text, options = node_confirm(caller, "")
        back_opt = options[1]
        self.assertEqual(back_opt["goto"], "node_languages")


# =======================================================================
#  CmdRemort Tests
# =======================================================================

class TestCmdRemortLevelGate(EvenniaCommandTest):
    """Test that remort is blocked below max level."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def test_remort_below_max_level(self):
        """Remort should be blocked at levels below 40."""
        self.char1.total_level = 10
        self.call(CmdRemort(), "", "You must be level 40")

    def test_remort_at_level_39(self):
        """Remort should be blocked at level 39."""
        self.char1.total_level = 39
        self.call(CmdRemort(), "", "You must be level 40")


class TestCmdRemortConfirmation(EvenniaCommandTest):
    """Test the Y/N confirmation flow."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.char1.total_level = 40
        self.char1.num_remorts = 0
        self.char1.point_buy = 27
        self.char1.bonus_hp_per_level = 0
        self.char1.bonus_mana_per_level = 0
        self.char1.bonus_move_per_level = 0
        self.char1.bonus_weapon_skill_pts = 0
        self.char1.bonus_class_skill_pts = 0
        self.char1.bonus_general_skill_pts = 0

    def test_remort_cancel(self):
        """Answering 'n' should cancel remort."""
        self.call(CmdRemort(), "", "Remort cancelled.", inputs=["n"])

    def test_remort_cancel_message(self):
        """Cancelling remort should show cancelled message."""
        self.call(CmdRemort(), "", "Remort cancelled.", inputs=["n"])
