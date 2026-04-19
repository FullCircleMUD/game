"""
Tests for QuitDrop — abandoned pack left when a player quits.

evennia test --settings settings tests.typeclass_tests.test_quit_drop
"""

from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.world_objects.quit_drop import QuitDrop


class TestQuitDrop(EvenniaTest):

    databases = "__all__"

    def create_script(self):
        pass

    def test_display_name(self):
        """QuitDrop should show owner's name in display."""
        qd = create_object(QuitDrop, key="quit_drop", location=self.room1, nohome=True)
        qd.owner_name = "Bob"
        self.assertEqual(qd.get_display_name(), "Bob's abandoned pack")

    def test_display_desc(self):
        """QuitDrop should show a description mentioning the owner."""
        qd = create_object(QuitDrop, key="quit_drop", location=self.room1, nohome=True)
        qd.owner_name = "Bob"
        desc = qd.get_display_desc(self.char1)
        self.assertIn("Bob", desc)
        self.assertIn("abandoned", desc)

    def test_can_loot_owner(self):
        """Owner can always loot their quit drop."""
        qd = create_object(QuitDrop, key="quit_drop", location=self.room1, nohome=True)
        qd.owner_character_key = self.char1.key
        qd.is_unlocked = False
        self.assertTrue(qd.can_loot(self.char1))

    def test_can_loot_non_owner_locked(self):
        """Non-owner cannot loot while locked."""
        qd = create_object(QuitDrop, key="quit_drop", location=self.room1, nohome=True)
        qd.owner_character_key = self.char1.key
        qd.is_unlocked = False
        self.assertFalse(qd.can_loot(self.char2))

    def test_can_loot_non_owner_unlocked(self):
        """Non-owner can loot after unlock."""
        qd = create_object(QuitDrop, key="quit_drop", location=self.room1, nohome=True)
        qd.owner_character_key = self.char1.key
        qd.is_unlocked = True
        self.assertTrue(qd.can_loot(self.char2))

    def test_despawn_scatters_items(self):
        """Despawn should move NFT items to the room, not delete them."""
        from typeclasses.items.base_nft_item import BaseNFTItem

        qd = create_object(QuitDrop, key="quit_drop", location=self.room1, nohome=True)
        qd.owner_name = "Bob"

        # Create a test item inside the quit drop
        item = create_object(BaseNFTItem, key="test_sword", location=qd, nohome=True)

        qd.despawn()

        # Item should now be in the room, not deleted
        self.assertEqual(item.location, self.room1)
        # QuitDrop should be deleted
        self.assertFalse(qd.pk)

    def test_despawn_empty_crumbles(self):
        """Despawn with no items should show crumble message."""
        qd = create_object(QuitDrop, key="quit_drop", location=self.room1, nohome=True)
        qd.owner_name = "Bob"

        qd.despawn()

        self.assertFalse(qd.pk)
