"""
Tests for CmdBind — verifies binding to a cemetery sets home,
deducts gold, and handles edge cases.
"""

from unittest.mock import patch

from evennia.utils.test_resources import EvenniaCommandTest

from commands.room_specific_cmds.cemetery.cmd_bind import CmdBind


WALLET_A = "0xAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"


class TestCmdBind(EvenniaCommandTest):
    """Test the bind command."""

    room_typeclass = "typeclasses.terrain.rooms.room_cemetery.RoomCemetery"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)
        self.char1.db.gold = 10
        # Ensure char is not already bound here
        self.char1.home = None

    # ── Success ──

    @patch("blockchain.xrpl.services.gold.GoldService.sink")
    def test_bind_success(self, mock_gold):
        """Binding sets home to the cemetery room."""
        self.call(CmdBind(), "", "You bind your soul to")
        self.assertEqual(self.char1.home, self.room1)

    @patch("blockchain.xrpl.services.gold.GoldService.sink")
    def test_bind_deducts_gold(self, mock_gold):
        """Binding deducts the room's bind_cost from gold."""
        self.room1.bind_cost = 3
        self.call(CmdBind(), "", "You bind your soul to Room for 3 gold.")
        self.assertEqual(self.char1.db.gold, 7)

    @patch("blockchain.xrpl.services.gold.GoldService.sink")
    def test_bind_default_cost(self, mock_gold):
        """Default bind_cost is 1."""
        self.call(CmdBind(), "", "You bind your soul to Room for 1 gold.")
        self.assertEqual(self.char1.db.gold, 9)

    @patch("blockchain.xrpl.services.gold.GoldService.sink")
    def test_bind_free_cemetery(self, mock_gold):
        """Cemetery with bind_cost=0 is free."""
        self.room1.bind_cost = 0
        self.call(CmdBind(), "", "You bind your soul to")
        self.assertEqual(self.char1.db.gold, 10)  # unchanged
        self.assertEqual(self.char1.home, self.room1)

    # ── Already bound ──

    def test_bind_already_bound(self):
        """Binding to the same cemetery shows already-bound message."""
        self.char1.home = self.room1
        self.call(CmdBind(), "", "You are already bound to this cemetery.")

    def test_bind_already_bound_no_gold_change(self):
        """Already-bound check doesn't deduct gold."""
        self.char1.home = self.room1
        self.call(CmdBind(), "", "You are already bound")
        self.assertEqual(self.char1.db.gold, 10)

    # ── Not enough gold ──

    def test_bind_not_enough_gold(self):
        """Can't bind without enough gold."""
        self.char1.db.gold = 0
        self.call(CmdBind(), "", "You need 1 gold to bind here")

    def test_bind_not_enough_gold_no_home_change(self):
        """Failed bind doesn't change home."""
        self.char1.db.gold = 0
        self.char1.home = None
        self.call(CmdBind(), "", "You need 1 gold")
        self.assertIsNone(self.char1.home)

