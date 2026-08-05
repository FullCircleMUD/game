"""Tests for spawn/dispatcher.py — routing placements to their owners.

The dispatcher is the seam between deciding and placing. In monolith it
hands the list straight to the executor; under sharding it buckets by owning
shard and sends one bus message each.

Most of this is pure data manipulation over the ``{pk: shard_id}`` the
planner already gathered, so it needs no database. The role branch is
exercised by patching ``get_role`` — the pattern already used in
``tests/server_tests/test_script_registry.py`` — which lets one monolith run
cover both roles.

evennia test --settings settings tests.spawn_tests.test_dispatcher
"""

import json
import unittest
from unittest.mock import patch

from blockchain.xrpl.services.spawn.dispatcher import (
    MESSAGE_KIND,
    dispatch,
    group_by_shard,
)

GET_ROLE = "evennia_shards.get_role"
SEND_MESSAGE = "evennia_shards.send_message"
EXECUTE = "blockchain.xrpl.services.spawn.executor.execute"


def _placement(target_pk, shard_id, amount=1, category="gold", type_key="gold"):
    return {
        "category": category,
        "type_key": type_key,
        "target_pk": target_pk,
        "amount": amount,
        "shard_id": shard_id,
    }


# ================================================================== #
#  Bucketing
# ================================================================== #


class TestGroupByShard(unittest.TestCase):

    def test_splits_by_owner(self):
        grouped = group_by_shard([
            _placement(1, "shard0"),
            _placement(2, "shard1"),
            _placement(3, "shard0"),
        ])
        self.assertEqual(set(grouped), {"shard0", "shard1"})
        self.assertEqual(len(grouped["shard0"]), 2)
        self.assertEqual(len(grouped["shard1"]), 1)

    def test_single_shard_gets_one_bucket(self):
        grouped = group_by_shard([_placement(1, "shard0"), _placement(2, "shard0")])
        self.assertEqual(list(grouped), ["shard0"])

    def test_shard_with_nothing_gets_no_bucket(self):
        """A shard with no placements must not receive an empty message."""
        grouped = group_by_shard([_placement(1, "shard0")])
        self.assertNotIn("shard1", grouped)

    def test_unrouted_placements_dropped(self):
        """No owning shard means nowhere to send it. Spawns land on
        shard-owned targets only."""
        grouped = group_by_shard([_placement(1, None), _placement(2, "shard0")])
        self.assertEqual(list(grouped), ["shard0"])
        self.assertEqual(len(grouped["shard0"]), 1)

    def test_all_unrouted_gives_nothing(self):
        self.assertEqual(group_by_shard([_placement(1, None)]), {})

    def test_empty_input(self):
        self.assertEqual(group_by_shard([]), {})


# ================================================================== #
#  Monolith — direct call, never the bus
# ================================================================== #


class TestMonolithPath(unittest.TestCase):
    """send_message() raises when to_shard == from_shard, so in monolith the
    direct call is required rather than merely faster."""

    def test_calls_executor_directly(self):
        placements = [_placement(1, None), _placement(2, None)]
        with patch(GET_ROLE, return_value="monolith"), \
                patch(EXECUTE, return_value=7) as mock_execute, \
                patch(SEND_MESSAGE) as mock_send:
            placed = dispatch(placements)
        mock_execute.assert_called_once()
        mock_send.assert_not_called()
        self.assertEqual(placed, 7)

    def test_passes_every_placement_through(self):
        placements = [_placement(1, None), _placement(2, None)]
        with patch(GET_ROLE, return_value="monolith"), \
                patch(EXECUTE, return_value=0) as mock_execute, \
                patch(SEND_MESSAGE):
            dispatch(placements)
        self.assertEqual(len(mock_execute.call_args[0][0]), 2)

    def test_strips_routing_before_executing(self):
        """The executor's contract is four fields; shard_id is routing."""
        with patch(GET_ROLE, return_value="monolith"), \
                patch(EXECUTE, return_value=0) as mock_execute, \
                patch(SEND_MESSAGE):
            dispatch([_placement(1, None)])
        forwarded = mock_execute.call_args[0][0][0]
        self.assertEqual(
            set(forwarded), {"category", "type_key", "target_pk", "amount"},
        )

    def test_unrouted_placements_still_placed_in_monolith(self):
        """shard_id is always None in monolith — it must not be read as
        'unroutable' and dropped."""
        with patch(GET_ROLE, return_value="monolith"), \
                patch(EXECUTE, return_value=3) as mock_execute, \
                patch(SEND_MESSAGE):
            placed = dispatch([_placement(1, None), _placement(2, None)])
        self.assertEqual(len(mock_execute.call_args[0][0]), 2)
        self.assertEqual(placed, 3)


# ================================================================== #
#  Sharded — one message per shard
# ================================================================== #


class TestShardedPath(unittest.TestCase):

    def test_one_message_per_shard(self):
        placements = [
            _placement(1, "shard0"),
            _placement(2, "shard1"),
            _placement(3, "shard0"),
        ]
        with patch(GET_ROLE, return_value="router"), \
                patch(SEND_MESSAGE) as mock_send, \
                patch(EXECUTE) as mock_execute:
            dispatch(placements)
        self.assertEqual(mock_send.call_count, 2)
        mock_execute.assert_not_called()

    def test_message_addressed_to_owning_shard(self):
        with patch(GET_ROLE, return_value="router"), \
                patch(SEND_MESSAGE) as mock_send:
            dispatch([_placement(1, "shard1")])
        _, kwargs = mock_send.call_args
        self.assertEqual(kwargs["to_shard"], "shard1")

    def test_message_kind(self):
        with patch(GET_ROLE, return_value="router"), \
                patch(SEND_MESSAGE) as mock_send:
            dispatch([_placement(1, "shard0")])
        self.assertEqual(mock_send.call_args[0][0], MESSAGE_KIND)

    def test_payload_carries_that_shards_placements_only(self):
        with patch(GET_ROLE, return_value="router"), \
                patch(SEND_MESSAGE) as mock_send:
            dispatch([
                _placement(1, "shard0"),
                _placement(2, "shard1"),
                _placement(3, "shard0"),
            ])
        by_shard = {
            call.kwargs["to_shard"]: call.args[1]
            for call in mock_send.call_args_list
        }
        self.assertEqual(len(by_shard["shard0"]["placements"]), 2)
        self.assertEqual(len(by_shard["shard1"]["placements"]), 1)
        self.assertEqual(
            by_shard["shard1"]["placements"][0]["target_pk"], 2,
        )

    def test_payload_strips_routing_field(self):
        with patch(GET_ROLE, return_value="router"), \
                patch(SEND_MESSAGE) as mock_send:
            dispatch([_placement(1, "shard0")])
        entry = mock_send.call_args[0][1]["placements"][0]
        self.assertEqual(
            set(entry), {"category", "type_key", "target_pk", "amount"},
        )

    def test_payload_is_json_serialisable(self):
        """It goes into a JSONB column."""
        with patch(GET_ROLE, return_value="router"), \
                patch(SEND_MESSAGE) as mock_send:
            dispatch([_placement(1, "shard0"), _placement(2, "shard0")])
        payload = mock_send.call_args[0][1]
        self.assertEqual(json.loads(json.dumps(payload)), payload)

    def test_returns_zero_because_nothing_is_placed_locally(self):
        with patch(GET_ROLE, return_value="router"), \
                patch(SEND_MESSAGE):
            self.assertEqual(dispatch([_placement(1, "shard0")]), 0)

    def test_mixed_categories_travel_together(self):
        """Entries are self-describing, so one message can carry several
        items for the same shard."""
        with patch(GET_ROLE, return_value="router"), \
                patch(SEND_MESSAGE) as mock_send:
            dispatch([
                _placement(1, "shard0", category="gold", type_key="gold"),
                _placement(2, "shard0", category="resources", type_key=1),
            ])
        self.assertEqual(mock_send.call_count, 1)
        entries = mock_send.call_args[0][1]["placements"]
        self.assertEqual(
            {entry["category"] for entry in entries}, {"gold", "resources"},
        )


# ================================================================== #
#  Failure isolation
# ================================================================== #


class TestDispatchFailures(unittest.TestCase):

    def test_one_shard_failing_does_not_stop_the_others(self):
        """A shard that cannot be reached misses this tick. The others
        still get theirs — the router does not retry or re-bank."""
        def _fail_shard0(kind, payload, to_shard=None, **kwargs):
            if to_shard == "shard0":
                raise RuntimeError("undeliverable")

        with patch(GET_ROLE, return_value="router"), \
                patch(SEND_MESSAGE, side_effect=_fail_shard0) as mock_send:
            dispatch([_placement(1, "shard0"), _placement(2, "shard1")])
        self.assertEqual(mock_send.call_count, 2)

    def test_send_failure_does_not_raise(self):
        with patch(GET_ROLE, return_value="router"), \
                patch(SEND_MESSAGE, side_effect=RuntimeError("boom")):
            self.assertEqual(dispatch([_placement(1, "shard0")]), 0)


# ================================================================== #
#  Nothing to do
# ================================================================== #


class TestEmptyDispatch(unittest.TestCase):

    def test_empty_list_sends_nothing(self):
        with patch(GET_ROLE, return_value="router"), \
                patch(SEND_MESSAGE) as mock_send:
            self.assertEqual(dispatch([]), 0)
        mock_send.assert_not_called()

    def test_empty_list_does_not_call_executor(self):
        with patch(GET_ROLE, return_value="monolith"), \
                patch(EXECUTE) as mock_execute:
            self.assertEqual(dispatch([]), 0)
        mock_execute.assert_not_called()
