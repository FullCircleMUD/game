"""
Tests for LockableMixin — lock/unlock with keys, lockpicking via
SUBTERFUGE skill, relock timer, and can_open gate.

evennia test --settings settings tests.typeclass_tests.test_lockable
"""

from unittest.mock import patch

from evennia.utils.test_resources import EvenniaTest
from evennia.utils import create

from enums.mastery_level import MasteryLevel
from enums.skills_enum import skills


WALLET_A = "0xAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"


class LockableTestBase(EvenniaTest):

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)

    def _make_chest(self, locked=True, lock_dc=15, key_tag="test_key"):
        obj = create.create_object(
            "typeclasses.world_objects.chest.WorldChest",
            key="iron chest",
            location=self.room1,
            nohome=True,
        )
        obj.is_locked = locked
        obj.is_open = False
        obj.lock_dc = lock_dc
        obj.key_tag = key_tag
        return obj

    def _make_key(self, key_tag="test_key", location=None):
        obj = create.create_object(
            "typeclasses.world_objects.key_item.KeyItem",
            key="iron key",
            location=location or self.char1,
            nohome=True,
        )
        obj.key_tag = key_tag
        return obj


class TestUnlockWithKey(LockableTestBase):

    def test_unlock_with_matching_key(self):
        chest = self._make_chest()
        key = self._make_key()
        success, msg = chest.unlock(self.char1, key)
        self.assertTrue(success)
        self.assertFalse(chest.is_locked)
        self.assertIn("crumbles to dust", msg)

    def test_key_consumed_on_success(self):
        chest = self._make_chest()
        key = self._make_key()
        key_pk = key.pk
        chest.unlock(self.char1, key)
        from evennia.objects.models import ObjectDB
        self.assertFalse(ObjectDB.objects.filter(pk=key_pk).exists())

    def test_wrong_key_rejected(self):
        chest = self._make_chest(key_tag="chest_a")
        key = self._make_key(key_tag="chest_b")
        success, msg = chest.unlock(self.char1, key)
        self.assertFalse(success)
        self.assertIn("doesn't fit", msg)
        self.assertTrue(chest.is_locked)

    def test_unlock_already_unlocked(self):
        chest = self._make_chest(locked=False)
        key = self._make_key()
        success, msg = chest.unlock(self.char1, key)
        self.assertFalse(success)
        self.assertIn("not locked", msg)


class TestLock(LockableTestBase):

    def test_lock_when_closed_and_unlocked(self):
        chest = self._make_chest(locked=False)
        chest.is_open = False
        success, msg = chest.lock(self.char1)
        self.assertTrue(success)
        self.assertTrue(chest.is_locked)

    def test_lock_when_open_fails(self):
        chest = self._make_chest(locked=False)
        chest.is_open = True
        success, msg = chest.lock(self.char1)
        self.assertFalse(success)
        self.assertIn("close", msg)

    def test_lock_when_already_locked(self):
        chest = self._make_chest(locked=True)
        success, msg = chest.lock(self.char1)
        self.assertFalse(success)
        self.assertIn("already locked", msg)


class TestPicklock(LockableTestBase):

    def test_picklock_success_on_high_roll(self):
        chest = self._make_chest(lock_dc=10)
        self.char1.db.class_skill_mastery_levels = {
            skills.SUBTERFUGE.value: {"mastery": MasteryLevel.SKILLED.value, "classes": ["Thief"]},
        }
        with patch("utils.dice_roller.DiceRoller.roll", return_value=15):
            success, msg = chest.picklock(self.char1)
        self.assertTrue(success)
        self.assertFalse(chest.is_locked)

    def test_picklock_failure_on_low_roll(self):
        chest = self._make_chest(lock_dc=25)
        self.char1.db.class_skill_mastery_levels = {
            skills.SUBTERFUGE.value: {"mastery": MasteryLevel.BASIC.value, "classes": ["Thief"]},
        }
        with patch("utils.dice_roller.DiceRoller.roll", return_value=1):
            success, msg = chest.picklock(self.char1)
        self.assertFalse(success)
        self.assertTrue(chest.is_locked)
        self.assertIn("fail", msg)

    def test_picklock_no_skill(self):
        chest = self._make_chest()
        self.char1.db.class_skill_mastery_levels = {}
        success, msg = chest.picklock(self.char1)
        self.assertFalse(success)
        self.assertIn("skill", msg)

    def test_picklock_not_locked(self):
        chest = self._make_chest(locked=False)
        success, msg = chest.picklock(self.char1)
        self.assertFalse(success)
        self.assertIn("not locked", msg)
