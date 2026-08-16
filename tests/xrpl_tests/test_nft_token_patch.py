"""
Tests for blockchain/xrpl/services/nft_token_patch.py.

get_role()/send_message() are imported locally inside dispatch_patch_sweep()
(not at module level), so they're patched at their source, evennia_shards.*.

evennia test --settings settings tests.xrpl_tests.test_nft_token_patch
"""

from unittest.mock import patch

from django.test import TestCase, override_settings
from evennia.utils import create

from blockchain.xrpl.models import NFTGameState
from blockchain.xrpl.services.nft_token_patch import (
    MESSAGE_KIND,
    apply_local_patches,
    dispatch_patch_sweep,
)


def _make_item(key, token_id):
    obj = create.create_object(
        "typeclasses.items.base_nft_item.BaseNFTItem",
        key=key, nohome=True,
    )
    obj.token_id = token_id
    return obj


# ══════════════════════════════════════════════════════════════════════════
#  dispatch_patch_sweep
# ══════════════════════════════════════════════════════════════════════════

class TestDispatchPatchSweep(TestCase):

    @patch("blockchain.xrpl.services.nft_token_patch.apply_local_patches")
    @patch("evennia_shards.get_role")
    def test_monolith_runs_sweep_locally(self, mock_role, mock_apply):
        mock_role.return_value = "monolith"
        mock_apply.return_value = 3

        result = dispatch_patch_sweep()

        self.assertEqual(result, 3)
        mock_apply.assert_called_once()

    @override_settings(SHARD_URLS={"shard0": "url0", "shard1": "url1"})
    @patch("evennia_shards.send_message")
    @patch("evennia_shards.get_role")
    def test_sharded_broadcasts_trigger_to_every_shard(self, mock_role, mock_send):
        mock_role.return_value = "router"

        result = dispatch_patch_sweep()

        self.assertIsNone(result)
        self.assertEqual(mock_send.call_count, 2)
        called_shards = {c.kwargs.get("to_shard") for c in mock_send.call_args_list}
        self.assertEqual(called_shards, {"shard0", "shard1"})
        for c in mock_send.call_args_list:
            self.assertEqual(c.args[0], MESSAGE_KIND)
            self.assertEqual(c.args[1], {})

    @override_settings(SHARD_URLS={"shard0": "url0", "shard1": "url1"})
    @patch("evennia_shards.send_message")
    @patch("evennia_shards.get_role")
    def test_one_shard_failure_does_not_stop_the_others(self, mock_role, mock_send):
        mock_role.return_value = "router"
        mock_send.side_effect = [Exception("boom"), None]

        result = dispatch_patch_sweep()

        self.assertIsNone(result)
        self.assertEqual(mock_send.call_count, 2)

    @override_settings(SHARD_URLS={})
    @patch("evennia_shards.send_message")
    @patch("evennia_shards.get_role")
    def test_no_shards_configured_sends_nothing(self, mock_role, mock_send):
        mock_role.return_value = "router"

        result = dispatch_patch_sweep()

        self.assertIsNone(result)
        mock_send.assert_not_called()


# ══════════════════════════════════════════════════════════════════════════
#  apply_local_patches
# ══════════════════════════════════════════════════════════════════════════

class TestApplyLocalPatches(TestCase):
    databases = {"default", "xrpl"}

    def test_placeholder_patched_when_mirror_has_real_id(self):
        NFTGameState.objects.create(
            nftoken_id="X" * 64, uri_id=2001, taxon=0,
            owner_in_game="rVAULT", location="ACCOUNT",
            item_type=None, metadata={},
        )
        obj = _make_item("Sword", token_id="2001")

        patched = apply_local_patches()

        self.assertEqual(patched, 1)
        obj_reloaded = type(obj).objects.get(id=obj.id)
        self.assertEqual(obj_reloaded.token_id, "X" * 64)

    def test_already_real_id_is_not_repatched(self):
        _make_item("Sword", token_id="Y" * 64)

        patched = apply_local_patches()

        self.assertEqual(patched, 0)

    def test_no_matching_mirror_row_skipped(self):
        _make_item("Sword", token_id="9999")

        patched = apply_local_patches()

        self.assertEqual(patched, 0)

    def test_mirror_row_still_placeholder_skipped(self):
        """Mirror row exists for this uri_id but hasn't itself been
        patched with a real NFToken ID yet — nothing to copy over."""
        NFTGameState.objects.create(
            nftoken_id="2002", uri_id=2002, taxon=0,
            owner_in_game="rVAULT", location="ACCOUNT",
            item_type=None, metadata={},
        )
        _make_item("Sword", token_id="2002")

        patched = apply_local_patches()

        self.assertEqual(patched, 0)

    def test_non_numeric_token_id_skipped_without_raising(self):
        _make_item("Weird Item", token_id="not-a-number")

        try:
            patched = apply_local_patches()
        except Exception as exc:
            self.fail(f"apply_local_patches raised on non-numeric token_id: {exc}")

        self.assertEqual(patched, 0)

    def test_none_token_id_skipped(self):
        _make_item("Blank Item", token_id=None)

        patched = apply_local_patches()

        self.assertEqual(patched, 0)

    def test_non_nft_item_with_same_attribute_name_excluded(self):
        """isinstance(obj, BaseNFTItem) guard — a plain object that
        happens to carry a 'token_id' attribute must not be touched."""
        NFTGameState.objects.create(
            nftoken_id="Z" * 64, uri_id=2003, taxon=0,
            owner_in_game="rVAULT", location="ACCOUNT",
            item_type=None, metadata={},
        )
        plain = create.create_object(
            "evennia.objects.objects.DefaultObject", key="Plain", nohome=True,
        )
        plain.attributes.add("token_id", "2003")

        patched = apply_local_patches()

        self.assertEqual(patched, 0)
        plain_reloaded = type(plain).objects.get(id=plain.id)
        self.assertEqual(plain_reloaded.attributes.get("token_id"), "2003")

    def test_multiple_eligible_items_all_patched(self):
        NFTGameState.objects.create(
            nftoken_id="A" * 64, uri_id=2004, taxon=0,
            owner_in_game="rVAULT", location="ACCOUNT",
            item_type=None, metadata={},
        )
        NFTGameState.objects.create(
            nftoken_id="B" * 64, uri_id=2005, taxon=0,
            owner_in_game="rVAULT", location="ACCOUNT",
            item_type=None, metadata={},
        )
        _make_item("Sword A", token_id="2004")
        _make_item("Sword B", token_id="2005")

        patched = apply_local_patches()

        self.assertEqual(patched, 2)
