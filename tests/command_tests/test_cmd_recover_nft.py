"""
Tests for CmdRecoverNft — role guard, orphan discovery, and the
Xaman sign/accept state machine.

get_role() is imported locally inside func() (not at module level), so
the role guard is patched at its source, evennia_shards.get_role.

evennia test --settings settings tests.command_tests.test_cmd_recover_nft
"""

from unittest import TestCase as PlainTestCase
from unittest.mock import AsyncMock, MagicMock, patch

from django.test import TestCase
from evennia.utils.test_resources import EvenniaCommandTest

from blockchain.xrpl.models import NFTGameState
from commands.account_cmds.cmd_recover_nft import (
    CmdRecoverNft,
    _accept_offer,
    _find_orphans,
    _on_accepted,
    _on_orphans_found,
    _on_poll_result,
    _on_recover_error,
    _recover_next,
)


# ══════════════════════════════════════════════════════════════════════════
#  Usage + role guard
# ══════════════════════════════════════════════════════════════════════════

@patch("evennia_shards.get_role")
class TestRecoverNftUsageAndRoleGuard(EvenniaCommandTest):

    def create_script(self):
        pass

    def test_no_args_shows_usage(self, _mock_role):
        result = self.call(CmdRecoverNft(), "", caller=self.account)
        self.assertIn("Usage: recover_nft", result)

    def test_shard_blocked(self, mock_role):
        mock_role.return_value = "shard"
        result = self.call(CmdRecoverNft(), "rSOMEWALLET", caller=self.account)
        self.assertIn("can only be run OOC on the router", result)

    def test_router_allowed(self, mock_role):
        mock_role.return_value = "router"
        with patch(
            "commands.account_cmds.cmd_recover_nft.defer_to_db_thread"
        ) as mock_defer:
            result = self.call(CmdRecoverNft(), "rSOMEWALLET", caller=self.account)
        self.assertIn("Querying wallet rSOMEWALLET for orphaned NFTs", result)
        mock_defer.assert_called_once()

    def test_monolith_allowed(self, mock_role):
        mock_role.return_value = "monolith"
        with patch(
            "commands.account_cmds.cmd_recover_nft.defer_to_db_thread"
        ) as mock_defer:
            result = self.call(CmdRecoverNft(), "rSOMEWALLET", caller=self.account)
        self.assertIn("Querying wallet rSOMEWALLET for orphaned NFTs", result)
        mock_defer.assert_called_once()


# ══════════════════════════════════════════════════════════════════════════
#  _find_orphans
# ══════════════════════════════════════════════════════════════════════════

class TestFindOrphans(TestCase):
    databases = {"default", "xrpl"}

    def _chain_nft(self, nftoken_id, uri_hex=None, taxon=0):
        return {"NFTokenID": nftoken_id, "nft_taxon": taxon, "URI": uri_hex}

    @patch("blockchain.xrpl.xrpl_tx._get_wallet_nfts_async", new_callable=AsyncMock)
    def test_nft_with_no_db_row_is_orphan(self, mock_fetch):
        mock_fetch.return_value = [self._chain_nft("A" * 64)]

        orphans = _find_orphans("rSOMEWALLET")

        self.assertEqual(len(orphans), 1)
        self.assertEqual(orphans[0]["nftoken_id"], "A" * 64)

    @patch("blockchain.xrpl.xrpl_tx._get_wallet_nfts_async", new_callable=AsyncMock)
    def test_nft_with_existing_db_row_is_not_orphan(self, mock_fetch):
        nftoken_id = "B" * 64
        NFTGameState.objects.create(
            nftoken_id=nftoken_id, uri_id=999999, taxon=0,
            owner_in_game="rSOMEWALLET", location="ACCOUNT",
            item_type=None, metadata={},
        )
        mock_fetch.return_value = [self._chain_nft(nftoken_id)]

        orphans = _find_orphans("rSOMEWALLET")

        self.assertEqual(orphans, [])

    @patch("blockchain.xrpl.xrpl_tx._get_wallet_nfts_async", new_callable=AsyncMock)
    def test_no_wallet_nfts_returns_empty(self, mock_fetch):
        mock_fetch.return_value = []

        orphans = _find_orphans("rSOMEWALLET")

        self.assertEqual(orphans, [])

    @patch("blockchain.xrpl.xrpl_tx._get_wallet_nfts_async", new_callable=AsyncMock)
    def test_multiple_orphans_all_included(self, mock_fetch):
        mock_fetch.return_value = [
            self._chain_nft("C" * 64), self._chain_nft("D" * 64),
        ]

        orphans = _find_orphans("rSOMEWALLET")

        ids = {o["nftoken_id"] for o in orphans}
        self.assertEqual(ids, {"C" * 64, "D" * 64})


# ══════════════════════════════════════════════════════════════════════════
#  _accept_offer
# ══════════════════════════════════════════════════════════════════════════

class TestAcceptOffer(PlainTestCase):

    def _meta_with_offer(self, ledger_index="OFFER123"):
        return {
            "AffectedNodes": [
                {"CreatedNode": {"LedgerEntryType": "NFTokenOffer", "LedgerIndex": ledger_index}},
                {"ModifiedNode": {"LedgerEntryType": "NFTokenPage"}},
            ]
        }

    @patch("blockchain.xrpl.xrpl_tx.accept_nft_sell_offer")
    @patch("blockchain.xrpl.xrpl_tx.get_transaction")
    def test_extracts_offer_id_and_accepts(self, mock_get_tx, mock_accept):
        mock_get_tx.return_value = {"meta": self._meta_with_offer("OFFER123")}
        mock_accept.return_value = "ACCEPT_TX_HASH"

        result = _accept_offer("TX_HASH")

        mock_accept.assert_called_once_with("OFFER123")
        self.assertEqual(result, "ACCEPT_TX_HASH")

    @patch("blockchain.xrpl.xrpl_tx.accept_nft_sell_offer")
    @patch("blockchain.xrpl.xrpl_tx.get_transaction")
    def test_falls_back_to_metadata_key(self, mock_get_tx, mock_accept):
        """Some tx result shapes use 'metaData' instead of 'meta'."""
        mock_get_tx.return_value = {"metaData": self._meta_with_offer("OFFER456")}
        mock_accept.return_value = "ACCEPT_TX_HASH"

        _accept_offer("TX_HASH")

        mock_accept.assert_called_once_with("OFFER456")

    @patch("blockchain.xrpl.xrpl_tx.accept_nft_sell_offer")
    @patch("blockchain.xrpl.xrpl_tx.get_transaction")
    def test_missing_offer_id_raises(self, mock_get_tx, mock_accept):
        mock_get_tx.return_value = {"meta": {"AffectedNodes": []}}

        with self.assertRaises(ValueError):
            _accept_offer("TX_HASH")

        mock_accept.assert_not_called()


# ══════════════════════════════════════════════════════════════════════════
#  Display/state-machine callbacks — direct calls, no thread plumbing
# ══════════════════════════════════════════════════════════════════════════

class TestOnOrphansFound(PlainTestCase):

    def test_no_orphans_shows_all_clear(self):
        caller = MagicMock()
        caller.sessions.count.return_value = 1
        _on_orphans_found(caller, "rWALLET", [])
        msgs = " ".join(c.args[0] for c in caller.msg.call_args_list)
        self.assertIn("No orphaned NFTs found", msgs)

    def test_disconnected_caller_is_noop(self):
        caller = MagicMock()
        caller.sessions.count.return_value = 0
        _on_orphans_found(caller, "rWALLET", [{"nftoken_id": "A" * 64, "game_id": 1}])
        caller.msg.assert_not_called()

    @patch("commands.account_cmds.cmd_recover_nft._recover_next")
    def test_orphans_found_starts_recovery(self, mock_next):
        caller = MagicMock()
        caller.sessions.count.return_value = 1
        orphans = [{"nftoken_id": "A" * 64, "game_id": 5, "taxon": 0}]

        _on_orphans_found(caller, "rWALLET", orphans)

        mock_next.assert_called_once_with(caller, "rWALLET", orphans, 0)
        msgs = " ".join(c.args[0] for c in caller.msg.call_args_list)
        self.assertIn("Orphaned NFTs (1)", msgs)


class TestRecoverNext(PlainTestCase):

    def test_index_past_end_shows_complete(self):
        caller = MagicMock()
        caller.sessions.count.return_value = 1
        _recover_next(caller, "rWALLET", [], 0)
        msgs = " ".join(c.args[0] for c in caller.msg.call_args_list)
        self.assertIn("Recovery Complete", msgs)

    def test_disconnected_caller_is_noop(self):
        caller = MagicMock()
        caller.sessions.count.return_value = 0
        _recover_next(caller, "rWALLET", [{"nftoken_id": "A" * 64}], 0)
        caller.msg.assert_not_called()

    @patch("commands.account_cmds.cmd_recover_nft.defer_to_db_thread")
    def test_dispatches_sell_offer_creation_for_current_index(self, mock_defer):
        caller = MagicMock()
        caller.sessions.count.return_value = 1
        orphans = [{"nftoken_id": "A" * 64, "game_id": None, "taxon": 0}]

        _recover_next(caller, "rWALLET", orphans, 0)

        mock_defer.assert_called_once()
        args = mock_defer.call_args[0]
        self.assertEqual(args[1], "A" * 64)


class TestOnPollResult(PlainTestCase):

    def _base_kwargs(self):
        return dict(
            caller=MagicMock(), wallet="rWALLET", orphans=[{"nftoken_id": "A" * 64}],
            index=0, nftoken_id="A" * 64, uuid="UUID1", attempt=0,
        )

    @patch("commands.account_cmds.cmd_recover_nft._recover_next")
    def test_expired_skips_to_next(self, mock_next):
        kw = self._base_kwargs()
        kw["caller"].sessions.count.return_value = 1
        _on_poll_result(**kw, status={"expired": True, "resolved": False, "signed": False})
        mock_next.assert_called_once_with(kw["caller"], "rWALLET", kw["orphans"], 1)

    @patch("commands.account_cmds.cmd_recover_nft.delay")
    def test_not_resolved_reschedules_poll(self, mock_delay):
        kw = self._base_kwargs()
        kw["caller"].sessions.count.return_value = 1
        _on_poll_result(**kw, status={"expired": False, "resolved": False, "signed": False})
        mock_delay.assert_called_once()
        args = mock_delay.call_args[0]
        self.assertEqual(args[0], 2)
        # last positional arg to delay(...) is the new attempt count
        self.assertEqual(args[-1], 1)

    @patch("commands.account_cmds.cmd_recover_nft._recover_next")
    def test_resolved_but_not_signed_is_rejected(self, mock_next):
        kw = self._base_kwargs()
        kw["caller"].sessions.count.return_value = 1
        _on_poll_result(**kw, status={"expired": False, "resolved": True, "signed": False})
        mock_next.assert_called_once_with(kw["caller"], "rWALLET", kw["orphans"], 1)

    @patch("commands.account_cmds.cmd_recover_nft.defer_to_db_thread")
    def test_signed_dispatches_accept(self, mock_defer):
        kw = self._base_kwargs()
        kw["caller"].sessions.count.return_value = 1
        _on_poll_result(
            **kw,
            status={"expired": False, "resolved": True, "signed": True, "tx_hash": "TXH"},
        )
        mock_defer.assert_called_once()
        args = mock_defer.call_args[0]
        self.assertEqual(args[1], "TXH")


class TestOnAcceptedAndError(PlainTestCase):

    @patch("commands.account_cmds.cmd_recover_nft._recover_next")
    def test_on_accepted_advances_to_next(self, mock_next):
        caller = MagicMock()
        caller.sessions.count.return_value = 1
        _on_accepted(caller, "rWALLET", [{"nftoken_id": "A" * 64}], 0, "A" * 64, "ACCEPTHASH")
        mock_next.assert_called_once_with(caller, "rWALLET", [{"nftoken_id": "A" * 64}], 1)
        msgs = " ".join(c.args[0] for c in caller.msg.call_args_list)
        self.assertIn("recovered to vault", msgs)

    @patch("commands.account_cmds.cmd_recover_nft._recover_next")
    def test_on_recover_error_skips_to_next(self, mock_next):
        caller = MagicMock()
        caller.sessions.count.return_value = 1
        failure = MagicMock()
        failure.getErrorMessage.return_value = "boom"
        _on_recover_error(caller, "rWALLET", [{"nftoken_id": "A" * 64}], 0, failure)
        mock_next.assert_called_once_with(caller, "rWALLET", [{"nftoken_id": "A" * 64}], 1)
        msgs = " ".join(c.args[0] for c in caller.msg.call_args_list)
        self.assertIn("boom", msgs)
