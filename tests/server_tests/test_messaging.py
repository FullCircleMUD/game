"""Tests for server/conf/messaging.py and the bus startup gate.

FCMMessageHandler is the consumer half of the cross-shard message bus: the
library polls and dispatches, this decides what FCM's own kinds mean. It is
plain routing over a message object, so these need no database.

evennia test --settings settings tests.server_tests.test_messaging
"""

import unittest
from unittest.mock import MagicMock, patch

from server.conf.messaging import FCMMessageHandler
from blockchain.xrpl.services.nft_token_patch import MESSAGE_KIND as NFT_PATCH_KIND
from blockchain.xrpl.services.spawn.dispatcher import MESSAGE_KIND as SPAWN_KIND
from utils.broadcast import MESSAGE_KIND as BROADCAST_KIND

EXECUTE = "blockchain.xrpl.services.spawn.executor.execute"
APPLY_LOCAL_PATCHES = "blockchain.xrpl.services.nft_token_patch.apply_local_patches"
BROADCAST_TO_LOCAL_SESSIONS = "utils.broadcast.broadcast_to_local_sessions"
GET_ROLE = "evennia_shards.get_role"
START_BUS = "evennia_shards.start_message_bus"


def _message(kind=SPAWN_KIND, payload=None, from_shard="router"):
    message = MagicMock()
    message.kind = kind
    message.payload = payload
    message.from_shard = from_shard
    return message


# ================================================================== #
#  Routing
# ================================================================== #


class TestSpawnPlacementRouting(unittest.TestCase):

    def test_spawn_placements_reach_the_executor(self):
        placements = [{"category": "gold", "type_key": "gold",
                       "target_pk": 1, "amount": 5}]
        with patch(EXECUTE, return_value=5) as mock_execute:
            handled = FCMMessageHandler().handle(
                _message(payload={"placements": placements}),
            )
        self.assertTrue(handled)
        mock_execute.assert_called_once_with(placements)

    def test_unknown_kind_is_not_handled(self):
        """Returning False lets the library's own lifecycle decide."""
        with patch(EXECUTE) as mock_execute:
            handled = FCMMessageHandler().handle(_message(kind="not_ours"))
        self.assertFalse(handled)
        mock_execute.assert_not_called()

    def test_library_kinds_are_offered_first(self):
        """super().handle() runs before FCM's own dispatch, so the delivery
        primitives cross-shard movement relies on keep working."""
        with patch(
            "evennia_shards.MessageHandler.handle", return_value=True,
        ) as mock_super, patch(EXECUTE) as mock_execute:
            handled = FCMMessageHandler().handle(_message())
        self.assertTrue(handled)
        mock_super.assert_called_once()
        mock_execute.assert_not_called()


# ================================================================== #
#  Payload handling
# ================================================================== #


class TestPayloadHandling(unittest.TestCase):

    def test_empty_placement_list(self):
        with patch(EXECUTE, return_value=0) as mock_execute:
            handled = FCMMessageHandler().handle(
                _message(payload={"placements": []}),
            )
        self.assertTrue(handled)
        mock_execute.assert_called_once_with([])

    def test_missing_placements_key(self):
        with patch(EXECUTE, return_value=0) as mock_execute:
            handled = FCMMessageHandler().handle(_message(payload={}))
        self.assertTrue(handled)
        mock_execute.assert_called_once_with([])

    def test_null_payload(self):
        with patch(EXECUTE, return_value=0) as mock_execute:
            handled = FCMMessageHandler().handle(_message(payload=None))
        self.assertTrue(handled)
        mock_execute.assert_called_once_with([])


# ================================================================== #
#  Never retry
# ================================================================== #


class TestNeverRetries(unittest.TestCase):
    """The return value tells the bus whether to retry, not whether the work
    succeeded. Re-running placements risks double-placing when a target has
    been looted since, so the message is always consumed."""

    def test_consumed_even_when_nothing_was_placed(self):
        with patch(EXECUTE, return_value=0):
            handled = FCMMessageHandler().handle(
                _message(payload={"placements": [{"bad": "entry"}]}),
            )
        self.assertTrue(handled)

    def test_consumed_when_only_some_placements_land(self):
        with patch(EXECUTE, return_value=2):
            handled = FCMMessageHandler().handle(
                _message(payload={"placements": [1, 2, 3]}),
            )
        self.assertTrue(handled)


# ================================================================== #
#  nft_token_patch_sweep routing
# ================================================================== #


class TestNftTokenPatchSweepRouting(unittest.TestCase):
    """The router sends this trigger after sync_nfts updates the mirror —
    payload carries no data, this shard just checks its own objects."""

    def test_sweep_trigger_reaches_apply_local_patches(self):
        with patch(APPLY_LOCAL_PATCHES, return_value=2) as mock_apply:
            handled = FCMMessageHandler().handle(
                _message(kind=NFT_PATCH_KIND, payload={}),
            )
        self.assertTrue(handled)
        mock_apply.assert_called_once()

    def test_null_payload_does_not_raise(self):
        with patch(APPLY_LOCAL_PATCHES, return_value=0) as mock_apply:
            handled = FCMMessageHandler().handle(
                _message(kind=NFT_PATCH_KIND, payload=None),
            )
        self.assertTrue(handled)
        mock_apply.assert_called_once()

    def test_always_consumed_even_with_nothing_patched(self):
        """Re-running the sweep is harmless — an object already holding a
        real token_id is skipped, so a duplicate message finds nothing."""
        with patch(APPLY_LOCAL_PATCHES, return_value=0):
            handled = FCMMessageHandler().handle(
                _message(kind=NFT_PATCH_KIND, payload={}),
            )
        self.assertTrue(handled)


# ================================================================== #
#  broadcast_to_shard routing
# ================================================================== #


class TestBroadcastRouting(unittest.TestCase):

    def test_broadcast_reaches_local_sessions(self):
        with patch(BROADCAST_TO_LOCAL_SESSIONS, return_value=3) as mock_broadcast:
            handled = FCMMessageHandler().handle(
                _message(
                    kind=BROADCAST_KIND,
                    payload={"caller_name": "Tim", "message": "hello shard"},
                ),
            )
        self.assertTrue(handled)
        mock_broadcast.assert_called_once_with("Tim", "hello shard")

    def test_missing_caller_name_defaults_to_admin(self):
        with patch(BROADCAST_TO_LOCAL_SESSIONS, return_value=0) as mock_broadcast:
            handled = FCMMessageHandler().handle(
                _message(kind=BROADCAST_KIND, payload={"message": "hi"}),
            )
        self.assertTrue(handled)
        mock_broadcast.assert_called_once_with("Admin", "hi")

    def test_null_payload_does_not_raise(self):
        with patch(BROADCAST_TO_LOCAL_SESSIONS, return_value=0) as mock_broadcast:
            handled = FCMMessageHandler().handle(
                _message(kind=BROADCAST_KIND, payload=None),
            )
        self.assertTrue(handled)
        mock_broadcast.assert_called_once_with("Admin", "")


# ================================================================== #
#  Startup gate
# ================================================================== #


class TestBusStartupGate(unittest.TestCase):
    """One of only two calls the shards library asks a consumer to make.
    FCM had never made it, so nothing addressed to a process was processed."""

    def _start(self):
        from server.conf.at_server_startstop import _start_message_bus

        _start_message_bus()

    def test_not_started_in_monolith(self):
        """Nothing to poll for — a process cannot message itself, and
        send_message() refuses same-shard delivery."""
        with patch(GET_ROLE, return_value="monolith"), \
                patch(START_BUS) as mock_start:
            self._start()
        mock_start.assert_not_called()

    def test_started_on_a_shard(self):
        with patch(GET_ROLE, return_value="shard"), \
                patch(START_BUS) as mock_start:
            self._start()
        mock_start.assert_called_once()

    def test_started_on_the_router(self):
        with patch(GET_ROLE, return_value="router"), \
                patch(START_BUS) as mock_start:
            self._start()
        mock_start.assert_called_once()

    def test_started_with_the_fcm_handler(self):
        """Passing the subclass is what routes spawn_placements; the bare
        call would only get the library's own kinds."""
        with patch(GET_ROLE, return_value="shard"), \
                patch(START_BUS) as mock_start:
            self._start()
        handler = mock_start.call_args[0][0]
        self.assertIsInstance(handler, FCMMessageHandler)
