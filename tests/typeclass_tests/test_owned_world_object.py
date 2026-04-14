"""
Tests for OwnedWorldObjectMixin — set_world_location flattens the room
reference and persists it to NFTGameState.metadata via the mirror layer.

NFTService.update_metadata itself is covered by xrpl_tests.test_nft_service;
here we only verify the typeclass-side plumbing (flattening + mirror call).
"""

from unittest.mock import patch

from django.conf import settings

from evennia.utils.test_resources import EvenniaTest
from evennia.utils import create


VAULT = settings.XRPL_VAULT_ADDRESS
TOKEN_ID = 777
WALLET_A = "0xAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"


class TestOwnedWorldObjectPersistence(EvenniaTest):
    """Verify set_world_location flattens the room and patches mirror metadata."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)

    def _make_ship(self, with_token=True):
        """Create a ShipNFTItem without triggering at_post_move side effects."""
        # Patch out NFTService calls during creation so we don't need a real
        # mirror row. The at_post_move hook on ShipNFTItem will try to set
        # an initial world_location — we want the create itself to be inert
        # and then drive set_world_location ourselves under a fresh mock.
        with patch(
            "blockchain.xrpl.services.nft.NFTService.update_metadata"
        ), patch(
            "blockchain.xrpl.services.nft.NFTService.craft_output"
        ), patch(
            "blockchain.xrpl.services.nft.NFTService.spawn"
        ):
            ship = create.create_object(
                "typeclasses.items.untakeables.ship_nft_item.ShipNFTItem",
                key="The Grey Widow",
                nohome=True,
            )
            if with_token:
                ship.token_id = TOKEN_ID
        return ship

    @patch("blockchain.xrpl.services.nft.NFTService.update_metadata")
    def test_set_world_location_flattens_and_persists(self, mock_update):
        ship = self._make_ship()
        ship.set_world_location(self.room1)

        self.assertIs(ship.db.world_location, self.room1)
        mock_update.assert_called_once_with(
            TOKEN_ID,
            {
                "world_location_dbref": self.room1.id,
                "world_location_name": self.room1.key,
            },
        )

    @patch("blockchain.xrpl.services.nft.NFTService.update_metadata")
    def test_set_world_location_none_clears_both_fields(self, mock_update):
        ship = self._make_ship()
        ship.set_world_location(None)

        self.assertIsNone(ship.db.world_location)
        mock_update.assert_called_once_with(
            TOKEN_ID,
            {
                "world_location_dbref": None,
                "world_location_name": None,
            },
        )

    @patch("blockchain.xrpl.services.nft.NFTService.update_metadata")
    def test_persist_noop_before_token_assigned(self, mock_update):
        """
        During at_object_creation / early at_post_move the NFT may not yet
        have a token_id. persist_metadata must silently no-op rather than
        blowing up, because set_world_location is called from
        ship_nft_item.at_post_move at first-spawn time.
        """
        ship = self._make_ship(with_token=False)
        ship.token_id = None

        ship.set_world_location(self.room1)

        mock_update.assert_not_called()

    @patch(
        "blockchain.xrpl.services.nft.NFTService.update_metadata",
        side_effect=RuntimeError("mirror row missing"),
    )
    def test_persist_errors_are_swallowed(self, mock_update):
        """
        Metadata persistence is best-effort — a mirror write failure must
        not crash gameplay (e.g. mid-voyage). The error path is logged via
        _log_error but doesn't propagate.
        """
        ship = self._make_ship()
        try:
            ship.set_world_location(self.room1)
        except RuntimeError:
            self.fail("set_world_location must not propagate mirror errors")

        self.assertIs(ship.db.world_location, self.room1)
        mock_update.assert_called_once()
