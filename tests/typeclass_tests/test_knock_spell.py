"""
Tests for the Knock spell — magical lock defeat.

Knock duck-types on ``hasattr(target, "is_locked")`` so it works on
ExitDoor, WorldChest, TrapChest, and any future LockableMixin subclass
without special-case branching. The DC ceiling is deterministic per
mastery tier (no roll); failure modes are explicit.

evennia test --settings settings tests.typeclass_tests.test_knock_spell
"""

from unittest.mock import MagicMock, patch

from evennia.utils.test_resources import EvenniaTest
from evennia.utils import create

from enums.mastery_level import MasteryLevel
from world.spells.conjuration.knock import Knock


def _set_conjuration_mastery(char, level):
    """Install conjuration mastery on a character at the given tier."""
    if not char.db.class_skill_mastery_levels:
        char.db.class_skill_mastery_levels = {}
    char.db.class_skill_mastery_levels["conjuration"] = {
        "mastery": level,
        "classes": ["mage"],
    }


def _create_chest(room, lock_dc=10, locked=True):
    chest = create.create_object(
        "typeclasses.world_objects.chest.WorldChest",
        key="iron chest",
        location=room,
    )
    chest.lock_dc = lock_dc
    chest.is_locked = locked
    return chest


class TestKnockSpellBase(EvenniaTest):
    """Base setup — char1 is a SKILLED conjuration mage by default."""

    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        _set_conjuration_mastery(self.char1, MasteryLevel.SKILLED.value)
        self.char1.mana = 100
        self.char1.mana_max = 100
        self.spell = Knock()


class TestKnockBasicSuccess(TestKnockSpellBase):

    def test_unlocks_chest_within_tier(self):
        chest = _create_chest(self.room1, lock_dc=10, locked=True)
        success, result = self.spell._execute(self.char1, chest)
        self.assertTrue(success)
        self.assertFalse(chest.is_locked)
        self.assertIn("first", result)

    def test_returns_message_dict_on_success(self):
        chest = _create_chest(self.room1, lock_dc=10, locked=True)
        _, result = self.spell._execute(self.char1, chest)
        # second is None for item targets
        self.assertIsNone(result["second"])
        self.assertIn("third", result)

    def test_calls_at_unlock_hook(self):
        chest = _create_chest(self.room1, lock_dc=10, locked=True)
        with patch.object(type(chest), "at_unlock") as mock_at_unlock:
            self.spell._execute(self.char1, chest)
            mock_at_unlock.assert_called_once_with(self.char1)

    def test_opens_target_after_unlocking(self):
        chest = _create_chest(self.room1, lock_dc=10, locked=True)
        # Chests start closed
        self.assertFalse(chest.is_open)
        success, result = self.spell._execute(self.char1, chest)
        self.assertTrue(success)
        self.assertTrue(chest.is_open)
        # Success message reflects the open state
        self.assertIn("swings open", result["first"])


class TestKnockTierGating(TestKnockSpellBase):

    def test_skilled_rejects_lock_dc_above_15(self):
        chest = _create_chest(self.room1, lock_dc=16, locked=True)
        success, result = self.spell._execute(self.char1, chest)
        self.assertFalse(success)
        self.assertTrue(chest.is_locked)
        # Result is a string (caster-only failure message)
        self.assertIn("resists", result.lower())

    def test_skilled_accepts_lock_dc_15(self):
        chest = _create_chest(self.room1, lock_dc=15, locked=True)
        success, _ = self.spell._execute(self.char1, chest)
        self.assertTrue(success)

    def test_expert_accepts_lock_dc_20(self):
        _set_conjuration_mastery(self.char1, MasteryLevel.EXPERT.value)
        chest = _create_chest(self.room1, lock_dc=20, locked=True)
        success, _ = self.spell._execute(self.char1, chest)
        self.assertTrue(success)

    def test_expert_rejects_lock_dc_21(self):
        _set_conjuration_mastery(self.char1, MasteryLevel.EXPERT.value)
        chest = _create_chest(self.room1, lock_dc=21, locked=True)
        success, _ = self.spell._execute(self.char1, chest)
        self.assertFalse(success)

    def test_master_accepts_lock_dc_25(self):
        _set_conjuration_mastery(self.char1, MasteryLevel.MASTER.value)
        chest = _create_chest(self.room1, lock_dc=25, locked=True)
        success, _ = self.spell._execute(self.char1, chest)
        self.assertTrue(success)

    def test_grandmaster_accepts_any_dc(self):
        _set_conjuration_mastery(self.char1, MasteryLevel.GRANDMASTER.value)
        chest = _create_chest(self.room1, lock_dc=999, locked=True)
        success, _ = self.spell._execute(self.char1, chest)
        self.assertTrue(success)


class TestKnockFailureModes(TestKnockSpellBase):

    def test_already_unlocked_target_rejected(self):
        chest = _create_chest(self.room1, lock_dc=10, locked=False)
        success, result = self.spell._execute(self.char1, chest)
        self.assertFalse(success)
        self.assertIn("not locked", result.lower())

    def test_non_lockable_target_rejected(self):
        # Plain BaseNFTItem has no is_locked attribute
        item = create.create_object(
            "typeclasses.items.base_nft_item.BaseNFTItem",
            key="random thing",
            location=self.room1,
        )
        success, result = self.spell._execute(self.char1, item)
        self.assertFalse(success)
        self.assertIn("cannot be magically unlocked", result.lower())

    def test_already_open_target_still_succeeds_if_locked(self):
        """Edge case: a locked-but-open object should still unlock cleanly."""
        chest = _create_chest(self.room1, lock_dc=10, locked=True)
        chest.is_open = True
        success, result = self.spell._execute(self.char1, chest)
        self.assertTrue(success)
        self.assertFalse(chest.is_locked)
        # No "swings open" since it was already open
        self.assertNotIn("swings open", result["first"])


class TestKnockDuckTyping(TestKnockSpellBase):
    """Verify Knock works on different LockableMixin subclasses."""

    def test_works_on_world_chest(self):
        chest = _create_chest(self.room1, lock_dc=10, locked=True)
        success, _ = self.spell._execute(self.char1, chest)
        self.assertTrue(success)

    def test_works_on_trap_chest(self):
        """TrapChest inherits LockableMixin via WorldChest — Knock should fire."""
        from typeclasses.world_objects.trap_chest import TrapChest
        chest = create.create_object(TrapChest, key="trapped chest", location=self.room1)
        chest.lock_dc = 10
        chest.is_locked = True
        chest.is_trapped = False  # no trap effect to confuse the test
        success, _ = self.spell._execute(self.char1, chest)
        self.assertTrue(success)
        self.assertFalse(chest.is_locked)


class TestKnockRelockTimer(TestKnockSpellBase):
    """Knock should suppress any pending auto-relock timer."""

    def test_cancels_relock_timer_on_success(self):
        chest = _create_chest(self.room1, lock_dc=10, locked=True)
        # Mock the script delete path — we don't want to spin up a real
        # RelockTimerScript in tests. Knock tries to delete the script
        # by key; we just verify it doesn't crash and that the chest
        # ends up unlocked.
        with patch.object(chest.scripts, "delete") as mock_delete:
            self.spell._execute(self.char1, chest)
            mock_delete.assert_called_with("relock_timer")
