"""
End-to-end ship banking tests — deposit, withdraw, cross-character transfer.

Verifies:
  - A ship can be deposited from a character's inventory into the account bank.
  - A ship can be withdrawn back to the same or a different character.
  - db.world_location survives the round-trip via Evennia attributes (and
    via mirror metadata after the metadata persistence wiring).
  - Multiple characters of the same account can hand a ship to each other
    asynchronously through the bank.
"""

from unittest.mock import patch

from evennia.utils.test_resources import EvenniaCommandTest
from evennia.utils import create

from commands.room_specific_cmds.bank.cmd_deposit import CmdDeposit
from commands.room_specific_cmds.bank.cmd_withdraw import CmdWithdraw
from commands.room_specific_cmds.bank.cmd_balance import CmdBalance


WALLET_A = "0xAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"


class ShipBankingTestBase(EvenniaCommandTest):
    """Common setup: account with a bank, a character, a built ship at room1."""

    room_typeclass = "typeclasses.terrain.rooms.room_bank.RoomBank"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)
        self.bank = create.create_object(
            "typeclasses.accounts.account_bank.AccountBank",
            key=f"bank-{self.account.key}",
            nohome=True,
        )
        self.bank.wallet_address = WALLET_A
        self.account.db.bank = self.bank

        # Stand up a ship in char1's contents with a real berth location.
        # Patch update_metadata so set_world_location doesn't try to write
        # to a non-existent mirror row.
        with patch("blockchain.xrpl.services.nft.NFTService.update_metadata"):
            self.ship = create.create_object(
                "typeclasses.items.untakeables.ship_nft_item.ShipNFTItem",
                key="The Grey Widow",
                nohome=True,
            )
            self.ship.token_id = 4242
            self.ship.db.ship_tier = 1  # Cog
            self.ship.set_world_location(self.room2)  # berthed at room2
        self.ship.db_location = self.char1
        self.ship.save(update_fields=["db_location"])


class TestShipBankingRoundTrip(ShipBankingTestBase):
    """char1 deposits a ship and withdraws it again — location preserved."""

    @patch("blockchain.xrpl.services.nft.NFTService.bank")
    @patch("blockchain.xrpl.services.nft.NFTService.unbank")
    def test_deposit_then_withdraw_preserves_world_location(
        self, mock_unbank, mock_bank
    ):
        # 1. Deposit
        result = self.call(CmdDeposit(), "Grey Widow")
        self.assertIn("deposit", result.lower())
        self.assertEqual(self.ship.location, self.bank)
        self.assertEqual(self.ship.db.world_location, self.room2)

        # 2. Balance shows it under Ships with berth info
        balance = self.call(CmdBalance(), "")
        self.assertIn("Ships", balance)
        self.assertIn("The Grey Widow", balance)
        self.assertIn("berthed at", balance)
        self.assertIn(self.room2.key, balance)

        # 3. Withdraw back
        result = self.call(CmdWithdraw(), str(self.ship.id))
        self.assertIn("withdraw", result.lower())
        self.assertEqual(self.ship.location, self.char1)
        # world_location survived the round-trip
        self.assertEqual(self.ship.db.world_location, self.room2)

    @patch("blockchain.xrpl.services.nft.NFTService.bank")
    @patch("blockchain.xrpl.services.nft.NFTService.unbank")
    def test_deposit_by_dbref(self, mock_unbank, mock_bank):
        """Ships should also deposit via `dep #<dbref>` (the token-id form
        in cmd_deposit actually matches obj.id / Evennia dbref)."""
        result = self.call(CmdDeposit(), f"#{self.ship.id}")
        self.assertEqual(self.ship.location, self.bank)


class TestShipCrossCharacterTransfer(ShipBankingTestBase):
    """char1 deposits, sibling char (same account) withdraws — ownership transfers."""

    def setUp(self):
        super().setUp()
        # EvenniaCommandTest puts self.char2 on self.account2 (a different
        # account), so it doesn't share self.account.db.bank. Create a
        # sibling character on the SAME account to exercise the real
        # cross-character-via-shared-bank flow.
        self.char_sibling = create.create_object(
            "typeclasses.actors.character.FCMCharacter",
            key="Sibling",
            location=self.room1,
            home=self.room1,
        )
        self.char_sibling.account = self.account

    @patch("blockchain.xrpl.services.nft.NFTService.bank")
    @patch("blockchain.xrpl.services.nft.NFTService.unbank")
    def test_char1_deposit_sibling_withdraw(self, mock_unbank, mock_bank):
        # char1 deposits
        self.call(CmdDeposit(), "Grey Widow")
        self.assertEqual(self.ship.location, self.bank)

        # Sibling character (same account) withdraws
        result = self.call(
            CmdWithdraw(), str(self.ship.id), caller=self.char_sibling
        )
        self.assertIn("withdraw", result.lower())
        self.assertEqual(self.ship.location, self.char_sibling)
        # Berth location intact — sibling must travel to room2 to sail it
        self.assertEqual(self.ship.db.world_location, self.room2)
