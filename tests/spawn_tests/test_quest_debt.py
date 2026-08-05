"""Tests for the quest debt path — shard reports, router applies.

Quest rewards redirect supply rather than adding to it: what a player is
handed is deducted from what the spawn system would otherwise place. The
budget lives on the process running the spawn service, which under sharding
is the router, while quests complete on shards — so the debt takes a bus hop.

Plain routing over roles and payloads, so no database is needed.

evennia test --settings settings tests.spawn_tests.test_quest_debt
"""

import unittest
from unittest.mock import MagicMock, patch

from blockchain.xrpl.services.spawn.quest_debt import (
    QUEST_DEBT_KIND,
    apply_quest_debt,
)
from world.quests.base_quest import FCMQuest

GET_ROLE_QUEST = "evennia_shards.get_role"
SEND_MESSAGE = "evennia_shards.send_message"
GET_SERVICE = "blockchain.xrpl.services.spawn.service.get_spawn_service"


# ================================================================== #
#  Sending — the shard side
# ================================================================== #


class TestShardSendsDebt(unittest.TestCase):

    def test_shard_sends_to_the_router(self):
        with patch(GET_ROLE_QUEST, return_value="shard"), \
                patch(SEND_MESSAGE) as mock_send:
            FCMQuest._register_quest_debt("gold", "gold", 50)
        mock_send.assert_called_once()
        self.assertEqual(mock_send.call_args[0][0], QUEST_DEBT_KIND)
        self.assertEqual(mock_send.call_args[1]["to_shard"], "router")

    def test_payload_carries_the_three_arguments(self):
        with patch(GET_ROLE_QUEST, return_value="shard"), \
                patch(SEND_MESSAGE) as mock_send:
            FCMQuest._register_quest_debt("resources", "3", 5)
        self.assertEqual(
            mock_send.call_args[0][1],
            {"category": "resources", "key": "3", "amount": 5},
        )

    def test_shard_does_not_touch_the_local_service(self):
        """A shard has no spawn service. Checking it first would discard the
        debt silently, which is what the old code did."""
        with patch(GET_ROLE_QUEST, return_value="shard"), \
                patch(SEND_MESSAGE), \
                patch(GET_SERVICE) as mock_service:
            FCMQuest._register_quest_debt("gold", "gold", 10)
        mock_service.assert_not_called()

    def test_send_failure_does_not_raise_into_the_quest(self):
        """The reward is already given; a failed send must not break
        completion."""
        with patch(GET_ROLE_QUEST, return_value="shard"), \
                patch(SEND_MESSAGE, side_effect=RuntimeError("bus down")):
            FCMQuest._register_quest_debt("gold", "gold", 10)


# ================================================================== #
#  Local application — monolith and router
# ================================================================== #


class TestLocalApplication(unittest.TestCase):

    def test_monolith_calls_the_service_directly(self):
        service = MagicMock()
        with patch(GET_ROLE_QUEST, return_value="monolith"), \
                patch(GET_SERVICE, return_value=service), \
                patch(SEND_MESSAGE) as mock_send:
            FCMQuest._register_quest_debt("gold", "gold", 50)
        service.allocate_quest_reward.assert_called_once_with(
            "gold", "gold", 50,
        )
        mock_send.assert_not_called()

    def test_router_calls_the_service_directly(self):
        """A quest completed on the router itself needs no hop."""
        service = MagicMock()
        with patch(GET_ROLE_QUEST, return_value="router"), \
                patch(GET_SERVICE, return_value=service), \
                patch(SEND_MESSAGE) as mock_send:
            FCMQuest._register_quest_debt("gold", "gold", 50)
        service.allocate_quest_reward.assert_called_once()
        mock_send.assert_not_called()

    def test_monolith_without_a_service_is_a_quiet_no_op(self):
        """Ordinary in tests and before at_server_start has run."""
        with patch(GET_ROLE_QUEST, return_value="monolith"), \
                patch(GET_SERVICE, return_value=None):
            FCMQuest._register_quest_debt("gold", "gold", 50)


# ================================================================== #
#  Receiving — the router side
# ================================================================== #


class TestApplyQuestDebt(unittest.TestCase):

    def test_applies_to_the_running_service(self):
        service = MagicMock()
        with patch(GET_SERVICE, return_value=service):
            applied = apply_quest_debt(
                {"category": "gold", "key": "gold", "amount": 50},
            )
        self.assertTrue(applied)
        service.allocate_quest_reward.assert_called_once_with(
            "gold", "gold", 50,
        )

    def test_no_service_is_reported_not_silent(self):
        """Debt landing with no service means rewards go unrepaid — the
        quiet version of this is how inflation would hide."""
        with patch(GET_SERVICE, return_value=None):
            self.assertFalse(
                apply_quest_debt(
                    {"category": "gold", "key": "gold", "amount": 50},
                ),
            )

    def test_malformed_payloads_rejected(self):
        service = MagicMock()
        with patch(GET_SERVICE, return_value=service):
            for payload in (
                None,
                {},
                {"category": "gold"},
                {"category": "gold", "key": "gold"},
                {"key": "gold", "amount": 5},
                {"category": "gold", "key": "gold", "amount": 0},
            ):
                self.assertFalse(apply_quest_debt(payload), msg=repr(payload))
        service.allocate_quest_reward.assert_not_called()

    def test_resource_key_zero_is_still_a_valid_key(self):
        """`key` may legitimately be a falsy-looking string, so the guard
        checks for None rather than truthiness."""
        service = MagicMock()
        with patch(GET_SERVICE, return_value=service):
            applied = apply_quest_debt(
                {"category": "resources", "key": "0", "amount": 3},
            )
        self.assertTrue(applied)


# ================================================================== #
#  Round trip
# ================================================================== #


class TestRoundTrip(unittest.TestCase):
    """What the shard sends is what the router applies."""

    def test_sent_payload_is_accepted_by_the_receiver(self):
        with patch(GET_ROLE_QUEST, return_value="shard"), \
                patch(SEND_MESSAGE) as mock_send:
            FCMQuest._register_quest_debt("resources", "3", 5)
        sent_payload = mock_send.call_args[0][1]

        service = MagicMock()
        with patch(GET_SERVICE, return_value=service):
            self.assertTrue(apply_quest_debt(sent_payload))
        service.allocate_quest_reward.assert_called_once_with(
            "resources", "3", 5,
        )
