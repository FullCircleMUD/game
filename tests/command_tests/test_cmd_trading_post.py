"""
Tests for the Trading Post bulletin board system.

Tests browsing, posting (with gold fee), removing listings,
auto-expiry filtering, and message length limits.
"""

from datetime import timedelta
from unittest.mock import patch

from django.utils import timezone

from evennia.utils.test_resources import EvenniaCommandTest

from blockchain.xrpl.models import BulletinListing
from commands.room_specific_cmds.trading_post.cmd_trading_post import (
    CmdBrowse,
    CmdPost,
    CmdRemoveListing,
    POSTING_FEE,
)

_ROOM = "typeclasses.terrain.rooms.room_base.RoomBase"
_CHAR = "typeclasses.actors.character.FCMCharacter"


class TestBrowseListings(EvenniaCommandTest):
    """Tests for browsing the Trading Post."""

    room_typeclass = _ROOM
    character_typeclass = _CHAR
    databases = "__all__"

    def create_script(self):
        pass

    def _create_listing(self, name="TestChar", listing_type="WTS", message="Selling stuff", days=7):
        return BulletinListing.objects.create(
            account_id=1,
            character_name=name,
            listing_type=listing_type,
            message=message,
            expires_at=timezone.now() + timedelta(days=days),
        )

    def test_empty_board(self):
        """Empty board shows appropriate message."""
        self.call(CmdBrowse(), "", "The Trading Post has no active listings.")

    def test_browse_shows_listings(self):
        """Browse shows active listings."""
        self._create_listing(message="Enchanted Sword 500g")
        self.call(CmdBrowse(), "", "=== Trading Post ===", caller=self.char1)

    def test_expired_listings_hidden(self):
        """Expired listings don't show up in browse."""
        self._create_listing(days=-1)  # Already expired
        self.call(CmdBrowse(), "", "The Trading Post has no active listings.")

    def test_pagination(self):
        """Multiple pages work correctly."""
        for i in range(25):
            self._create_listing(message=f"Item {i}")
        # Page 1 should show trading post header
        self.call(CmdBrowse(), "", "=== Trading Post ===", caller=self.char1)
        # Page 2
        self.call(CmdBrowse(), "2", "=== Trading Post ===", caller=self.char1)


class TestPostListing(EvenniaCommandTest):
    """Tests for posting listings to the Trading Post."""

    room_typeclass = _ROOM
    character_typeclass = _CHAR
    databases = "__all__"

    def create_script(self):
        pass

    def test_post_wts(self):
        """Can post a Want to Sell listing."""
        self.char1.db.gold = 100
        with patch.object(self.char1, "return_gold_to_sink"):
            self.call(CmdPost(), "WTS Enchanted Sword 500g", "Listing posted", caller=self.char1)
        self.assertEqual(BulletinListing.objects.count(), 1)
        listing = BulletinListing.objects.first()
        self.assertEqual(listing.listing_type, "WTS")
        self.assertEqual(listing.message, "Enchanted Sword 500g")

    def test_post_wtb(self):
        """Can post a Want to Buy listing."""
        self.char1.db.gold = 100
        with patch.object(self.char1, "return_gold_to_sink"):
            self.call(CmdPost(), "WTB Diamond, paying 200g", "Listing posted", caller=self.char1)
        listing = BulletinListing.objects.first()
        self.assertEqual(listing.listing_type, "WTB")

    def test_post_deducts_gold(self):
        """Posting deducts the gold fee."""
        self.char1.db.gold = 100
        with patch.object(self.char1, "return_gold_to_sink") as mock_sink:
            self.call(CmdPost(), "WTS Sword 50g", caller=self.char1)
            mock_sink.assert_called_once_with(POSTING_FEE)

    def test_post_insufficient_gold(self):
        """Cannot post without enough gold."""
        self.char1.db.gold = 0
        self.call(CmdPost(), "WTS Sword 50g", "Posting a listing costs", caller=self.char1)
        self.assertEqual(BulletinListing.objects.count(), 0)

    def test_post_invalid_type(self):
        """Must use WTS or WTB."""
        self.char1.db.gold = 100
        self.call(CmdPost(), "SELL Sword 50g", "Listing type must be WTS", caller=self.char1)

    def test_post_no_message(self):
        """Must provide a message."""
        self.char1.db.gold = 100
        self.call(CmdPost(), "WTS", "Usage: post", caller=self.char1)

    def test_post_message_too_long(self):
        """Message cannot exceed 200 characters."""
        self.char1.db.gold = 100
        long_msg = "x" * 201
        self.call(CmdPost(), f"WTS {long_msg}", "Message too long", caller=self.char1)


class TestRemoveListing(EvenniaCommandTest):
    """Tests for removing listings."""

    room_typeclass = _ROOM
    character_typeclass = _CHAR
    databases = "__all__"

    def create_script(self):
        pass

    def _create_listing(self, account_id=1, name="TestChar"):
        return BulletinListing.objects.create(
            account_id=account_id,
            character_name=name,
            listing_type="WTS",
            message="Test item",
            expires_at=timezone.now() + timedelta(days=7),
        )

    def test_remove_own_listing(self):
        """Can remove your own listing."""
        listing = self._create_listing(
            account_id=self.char1.account.id if self.char1.account else 1,
        )
        self.call(CmdRemoveListing(), str(listing.id), f"Listing #{listing.id} removed", caller=self.char1)
        self.assertEqual(BulletinListing.objects.count(), 0)

    def test_remove_nonexistent(self):
        """Removing nonexistent listing shows error."""
        self.call(CmdRemoveListing(), "9999", "No listing #9999", caller=self.char1)

    def test_remove_others_listing(self):
        """Cannot remove another player's listing."""
        listing = self._create_listing(account_id=999)
        self.call(CmdRemoveListing(), str(listing.id), "You can only remove your own", caller=self.char1)
        self.assertEqual(BulletinListing.objects.count(), 1)
