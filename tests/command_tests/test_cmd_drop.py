"""
Tests for CmdDrop — verifies dropping gold, resources, and objects
from inventory via the overridden drop command.
"""

from unittest.mock import patch

from django.conf import settings

from evennia.utils.test_resources import EvenniaCommandTest
from evennia.utils import create

from commands.all_char_cmds.cmd_override_drop import CmdDrop


WALLET_A = "0xAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"


class TestCmdDropGold(EvenniaCommandTest):
    """Test dropping gold into a room."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)
        self.char1.db.gold = 100
        self.char1.db.resources = {}
        self.room1.db.gold = 0
        self.room1.db.resources = {}

    def test_drop_no_args(self):
        """drop with no arguments should show usage."""
        self.call(CmdDrop(), "", "Drop what?")

    @patch("blockchain.xrpl.services.gold.GoldService.drop")
    def test_drop_gold_amount(self, mock_drop):
        """drop 50 gold should move 50 gold from character to room."""
        self.call(CmdDrop(), "50 gold")
        self.assertEqual(self.char1.get_gold(), 50)
        self.assertEqual(self.room1.get_gold(), 50)

    @patch("blockchain.xrpl.services.gold.GoldService.drop")
    def test_drop_all_gold(self, mock_drop):
        """drop all gold should move all gold from character to room."""
        self.call(CmdDrop(), "all gold")
        self.assertEqual(self.char1.get_gold(), 0)
        self.assertEqual(self.room1.get_gold(), 100)

    def test_drop_gold_insufficient(self):
        """drop more gold than you have should show error."""
        self.char1.db.gold = 10
        self.call(CmdDrop(), "50 gold", "You only have 10")

    def test_drop_gold_none(self):
        """drop gold when you have none should show error."""
        self.char1.db.gold = 0
        self.call(CmdDrop(), "50 gold", "You don't have any gold.")


class TestCmdDropResource(EvenniaCommandTest):
    """Test dropping resources into a room."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)
        self.char1.db.gold = 0
        self.char1.db.resources = {1: 20}  # 20 wheat
        self.room1.db.gold = 0
        self.room1.db.resources = {}

    @patch("blockchain.xrpl.services.resource.ResourceService.drop")
    def test_drop_resource_amount(self, mock_drop):
        """drop 5 wheat should move 5 wheat from character to room."""
        self.call(CmdDrop(), "5 wheat")
        self.assertEqual(self.char1.get_resource(1), 15)
        self.assertEqual(self.room1.get_resource(1), 5)

    @patch("blockchain.xrpl.services.resource.ResourceService.drop")
    def test_drop_all_resource(self, mock_drop):
        """drop all wheat should move all wheat from character to room."""
        self.call(CmdDrop(), "all wheat")
        self.assertEqual(self.char1.get_resource(1), 0)
        self.assertEqual(self.room1.get_resource(1), 20)

    def test_drop_resource_insufficient(self):
        """drop more resource than you have should show error."""
        self.char1.db.resources = {1: 2}
        self.call(CmdDrop(), "5 wheat", "You only have 2")

    def test_drop_resource_none(self):
        """drop resource when you have none should show error."""
        self.char1.db.resources = {}
        self.call(CmdDrop(), "5 wheat", "You don't have any Wheat.")


class TestCmdDropObject(EvenniaCommandTest):
    """Test dropping NFT objects (standard Evennia drop)."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.sword = create.create_object(
            "evennia.objects.objects.DefaultObject",
            key="sword",
            location=self.char1,
        )

    def test_drop_object(self):
        """drop sword should move it to room."""
        self.call(CmdDrop(), "sword")
        self.assertEqual(self.sword.location, self.room1)

    def test_drop_object_not_found(self):
        """drop item you don't have should show error."""
        self.call(CmdDrop(), "banana", "You aren't carrying banana.")

    def test_drop_untakeable_nft_item(self):
        """drop should refuse to drop an UntakeableNFTItem."""
        mount = create.create_object(
            "typeclasses.items.untakeables.untakeable_nft_item.UntakeableNFTItem",
            key="horse",
            nohome=True,
        )
        mount.db_location = self.char1
        mount.save(update_fields=["db_location"])
        self.call(CmdDrop(), "horse", "You can't drop")
        self.assertEqual(mount.location, self.char1)


class TestCmdDropAll(EvenniaCommandTest):
    """Test 'drop all' — drops everything with confirmation."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)
        self.char1.db.gold = 50
        self.char1.db.resources = {1: 10}  # 10 wheat
        self.room1.db.gold = 0
        self.room1.db.resources = {}
        self.sword = create.create_object(
            "evennia.objects.objects.DefaultObject",
            key="sword",
            location=self.char1,
        )

    @patch("blockchain.xrpl.services.resource.ResourceService.drop")
    @patch("blockchain.xrpl.services.gold.GoldService.drop")
    def test_drop_all_confirm_yes(self, mock_gold, mock_resource):
        """drop all with Y confirmation should drop everything."""
        self.call(CmdDrop(), "all", inputs=["y"])
        self.assertEqual(self.sword.location, self.room1)
        self.assertEqual(self.char1.get_gold(), 0)
        self.assertEqual(self.char1.get_resource(1), 0)

    def test_drop_all_confirm_no(self):
        """drop all with N confirmation should cancel."""
        self.call(CmdDrop(), "all", "Drop cancelled.", inputs=["n"])
        self.assertIn(self.sword, self.char1.contents)
        self.assertEqual(self.char1.get_gold(), 50)

    def test_drop_all_empty_inventory(self):
        """drop all with nothing to drop."""
        self.sword.delete()
        self.char1.db.gold = 0
        self.char1.db.resources = {}
        self.call(CmdDrop(), "all", "You aren't carrying anything.")
