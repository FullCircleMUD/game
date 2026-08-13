"""
Tests for CmdUnlock and CmdLock commands.

evennia test --settings settings tests.command_tests.test_cmd_unlock_lock
"""

from evennia.utils.test_resources import EvenniaCommandTest
from evennia.utils import create

from commands.all_char_cmds.cmd_unlock import CmdUnlock
from commands.all_char_cmds.cmd_lock import CmdLock


WALLET_A = "0xAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"


class UnlockLockTestBase(EvenniaCommandTest):

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.room1.always_lit = True
        self.account.attributes.add("wallet_address", WALLET_A)

    def _make_chest(self, is_locked=True, key_tag="test_key"):
        chest = create.create_object(
            "typeclasses.world_objects.chest.WorldChest",
            key="iron chest",
            location=self.room1,
            nohome=True,
        )
        chest.is_locked = is_locked
        chest.is_open = False
        chest.key_tag = key_tag
        return chest

    def _make_key(self, key_tag="test_key"):
        key = create.create_object(
            "typeclasses.world_objects.key_item.KeyItem",
            key="iron key",
            location=self.char1,
            nohome=True,
        )
        key.key_tag = key_tag
        return key


class TestCmdUnlock(UnlockLockTestBase):

    def test_unlock_no_args(self):
        self.call(CmdUnlock(), "", "Unlock what?")

    def test_unlock_with_matching_key(self):
        self._make_chest()
        self._make_key()
        self.call(CmdUnlock(), "iron chest", "You use iron key to unlock iron chest.")

    def test_unlock_no_key(self):
        self._make_chest()
        self.call(CmdUnlock(), "iron chest", "You don't have a key")

    def test_unlock_wrong_key(self):
        self._make_chest(key_tag="chest_a")
        self._make_key(key_tag="chest_b")
        self.call(CmdUnlock(), "iron chest", "You don't have a key")

    def test_unlock_not_locked(self):
        self._make_chest(is_locked=False)
        self.call(CmdUnlock(), "iron chest", "iron chest is not locked.")


class TestCmdLock(UnlockLockTestBase):

    def test_lock_no_args(self):
        self.call(CmdLock(), "", "Lock what?")

    def test_lock_closed_unlocked(self):
        self._make_chest(is_locked=False)
        self.call(CmdLock(), "iron chest", "You lock iron chest.")

    def test_lock_already_locked(self):
        self._make_chest(is_locked=True)
        self.call(CmdLock(), "iron chest", "iron chest is already locked.")

    def test_lock_when_open(self):
        chest = self._make_chest(is_locked=False)
        chest.is_open = True
        self.call(CmdLock(), "iron chest", "You need to close iron chest first.")


class TestCmdLockSightless(UnlockLockTestBase):
    """
    Lining a key up with a keyhole needs eyes, so locking refuses in the
    dark rather than costing time.
    """

    def _darken(self):
        self.room1.always_lit = False
        self.room1.natural_light = False

    def test_a_dark_room_refuses_the_lock(self):
        self._make_chest(is_locked=False)
        self._darken()
        result = self.call(CmdLock(), "chest")
        self.assertIn("too dark to make out", result.lower())

    def test_the_refusal_does_not_claim_it_is_absent(self):
        """The chest is right there — 'you don't see it here' misleads."""
        self._make_chest(is_locked=False)
        self._darken()
        result = self.call(CmdLock(), "chest")
        self.assertNotIn("don't see", result.lower())

    def test_a_blinded_character_is_refused_the_same_way(self):
        from enums.condition import Condition

        self._make_chest(is_locked=False)
        self.char1.add_condition(Condition.BLINDED)
        result = self.call(CmdLock(), "chest")
        self.assertIn("too dark to make out", result.lower())

    def test_nothing_is_locked_when_refused(self):
        chest = self._make_chest(is_locked=False)
        self._darken()
        self.call(CmdLock(), "chest")
        self.assertFalse(chest.is_locked)

    def test_darkvision_locks_normally(self):
        from enums.condition import Condition

        chest = self._make_chest(is_locked=False)
        self._darken()
        self.char1.add_condition(Condition.DARKVISION)
        self.call(CmdLock(), "chest")
        self.assertTrue(chest.is_locked)


class TestCmdUnlockSightless(UnlockLockTestBase):
    """Unlocking needs eyes for the same reason locking does."""

    def _darken(self):
        self.room1.always_lit = False
        self.room1.natural_light = False

    def test_a_dark_room_refuses_the_unlock(self):
        self._make_chest(is_locked=True)
        self._make_key()
        self._darken()
        result = self.call(CmdUnlock(), "chest")
        self.assertIn("too dark to make out", result.lower())

    def test_a_blinded_character_is_refused_the_same_way(self):
        from enums.condition import Condition

        self._make_chest(is_locked=True)
        self._make_key()
        self.char1.add_condition(Condition.BLINDED)
        result = self.call(CmdUnlock(), "chest")
        self.assertIn("too dark to make out", result.lower())

    def test_nothing_is_unlocked_when_refused(self):
        chest = self._make_chest(is_locked=True)
        self._make_key()
        self._darken()
        self.call(CmdUnlock(), "chest")
        self.assertTrue(chest.is_locked)

    def test_darkvision_unlocks_normally(self):
        from enums.condition import Condition

        chest = self._make_chest(is_locked=True)
        self._make_key()
        self._darken()
        self.char1.add_condition(Condition.DARKVISION)
        self.call(CmdUnlock(), "chest")
        self.assertFalse(chest.is_locked)
