"""
Tests that an item's shard stamp follows it into and out of the bank.

The bank belongs to the account, not to a shard — its own row is stamped
``"*"``. Items were never given the same treatment: an item kept the
shard it was created on for life, and nothing in the deposit or withdraw
path changed it.

With one populated shard that is invisible. With two it is a silent
disappearance: Fred banks something on shard0, Lancelot withdraws it on
shard1, and the row still says shard0 while every query shard1 runs
filters ``shard_id IN ('shard1', '*')``. No error — the item is just not
there.

The stamp is changed with ``qs.update`` rather than ``save()``, because
the shards library flags an assignment to the tenant column and the next
``save()`` raises. That is the library's own technique, borrowed from
evennia_shards.handoff.cross_shard_move.

evennia test --settings settings tests.typeclass_tests.test_nft_shard_follows
"""

from unittest.mock import patch

from evennia.utils.test_resources import EvenniaTest

from evennia_shards import ROLE_MONOLITH, ROLE_SHARD


class ShardFollowsBase(EvenniaTest):
    databases = {"default", "xrpl"}
    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"
    character_typeclass = "typeclasses.actors.character.FCMCharacter"

    def create_script(self):
        pass

    def _item(self):
        from evennia.utils.create import create_object

        obj = create_object(
            "typeclasses.items.base_nft_item.BaseNFTItem",
            key="Shard Test Blade",
            nohome=True,
        )
        obj.token_id = "SHARDFOLLOWTOKEN"
        return obj

    def _bank(self):
        from evennia.utils.create import create_object

        return create_object(
            "typeclasses.accounts.account_bank.AccountBank",
            key="bank-shardtest",
            nohome=True,
        )


class TestStampTargets(ShardFollowsBase):
    """Which stamp each destination implies."""

    def test_banking_makes_it_global(self):
        item = self._item()
        bank = self._bank()

        with patch("evennia_shards.get_role", return_value=ROLE_SHARD), \
                patch.object(type(item), "_restamp_pks") as restamp:
            item._follow_shard(None, "ACCOUNT", bank, bank)

        _, target, _containers = restamp.call_args[0]
        self.assertEqual(target, "*")

    def test_withdrawing_takes_the_holders_shard(self):
        """Lancelot on shard1 withdraws what Fred banked on shard0."""
        item = self._item()

        with patch("evennia_shards.get_role", return_value=ROLE_SHARD), \
                patch.object(type(item), "_restamp_pks") as restamp:
            item._follow_shard(None, "CHARACTER", self._holder("shard1"), None)

        _, target, _containers = restamp.call_args[0]
        self.assertEqual(target, "shard1")

    def test_no_change_when_already_correct(self):
        """A move within one shard must not touch the stamp."""
        item = self._item()
        object.__setattr__(item, "shard_id", "shard0")

        with patch("evennia_shards.get_role", return_value=ROLE_SHARD), \
                patch.object(type(item), "_restamp_pks") as restamp:
            item._follow_shard(None, "CHARACTER", self._holder("shard0"), None)

        restamp.assert_not_called()

    def test_monolith_does_nothing(self):
        """No shard_id column exists there."""
        item = self._item()

        with patch("evennia_shards.get_role", return_value=ROLE_MONOLITH), \
                patch.object(type(item), "_restamp_pks") as restamp:
            item._follow_shard(None, "ACCOUNT", self._bank(), None)

        restamp.assert_not_called()

    @staticmethod
    def _holder(shard_id):
        holder = type("_Holder", (), {})()
        holder.shard_id = shard_id
        return holder


class TestContentsRideAlong(ShardFollowsBase):
    """A container is banked with everything in it."""

    def test_container_contents_are_restamped_too(self):
        item = self._item()
        inner = self._item()
        inner.key = "Inner Blade"

        with patch.object(
            type(item), "is_container", True, create=True
        ), patch.object(
            type(item), "contents", [inner]
        ), patch("evennia_shards.get_role", return_value=ROLE_SHARD), \
                patch.object(type(item), "_restamp_pks") as restamp:
            item._follow_shard(None, "ACCOUNT", self._bank(), None)

        pks, _target, _containers = restamp.call_args[0]
        self.assertIn(item.pk, pks)
        self.assertIn(inner.pk, pks)

# The mechanism itself — _restamp_pks — has no unit test, and cannot have
# one in this environment. It needs the shard_id column, which exists only
# when evennia_shards is installed; the default test settings are monolith,
# where the column is absent, and the suite does not boot under
# settings_shard0 (Evennia's own create_account fails in setUp).
#
# It is verified live instead: bank an item, check the row reads "*",
# withdraw it, check the row reads the character's shard. Noted here so the
# gap is visible rather than assumed covered.
