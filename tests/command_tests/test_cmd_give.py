"""
Tests for CmdGive — verifies giving gold, resources, and objects
to another character via the overridden give command.
"""

from unittest.mock import patch

from django.conf import settings

from evennia.utils.test_resources import EvenniaCommandTest
from evennia.utils import create

from commands.all_char_cmds.cmd_override_give import CmdGive


WALLET_A = "0xAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
WALLET_B = "0xBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB"


class TestCmdGiveGold(EvenniaCommandTest):
    """Test giving gold to another character."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)
        self.account2.attributes.add("wallet_address", WALLET_B)
        self.char1.db.gold = 100
        self.char1.db.resources = {}
        self.char2.db.gold = 0
        self.char2.db.resources = {}

    def test_give_no_args(self):
        """give with no arguments should show usage."""
        self.call(CmdGive(), "", "Usage: give <item> to <target>")

    def test_give_no_target(self):
        """give with no target should show usage."""
        self.call(CmdGive(), "50 gold", "Usage: give <item> to <target>")

    @patch("blockchain.xrpl.services.gold.GoldService.transfer")
    def test_give_gold_amount(self, mock_transfer):
        """give 50 gold to Char2 should transfer gold."""
        self.call(CmdGive(), "50 gold to Char2")
        self.assertEqual(self.char1.get_gold(), 50)
        self.assertEqual(self.char2.get_gold(), 50)

    @patch("blockchain.xrpl.services.gold.GoldService.transfer")
    def test_give_all_gold(self, mock_transfer):
        """give all gold to Char2 should transfer all gold."""
        self.call(CmdGive(), "all gold to Char2")
        self.assertEqual(self.char1.get_gold(), 0)
        self.assertEqual(self.char2.get_gold(), 100)

    def test_give_gold_insufficient(self):
        """give more gold than you have should show error."""
        self.char1.db.gold = 10
        self.call(CmdGive(), "50 gold to Char2", "You only have 10")

    def test_give_gold_none(self):
        """give gold when you have none should show error."""
        self.char1.db.gold = 0
        self.call(CmdGive(), "50 gold to Char2", "You don't have any gold.")

    def test_give_to_self(self):
        """give to yourself should show error."""
        self.call(CmdGive(), "50 gold to Char", "You can't give things to yourself.")


class TestCmdGiveResource(EvenniaCommandTest):
    """Test giving resources to another character."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)
        self.account2.attributes.add("wallet_address", WALLET_B)
        self.char1.db.gold = 0
        self.char1.db.resources = {1: 20}  # 20 wheat
        self.char2.db.gold = 0
        self.char2.db.resources = {}

    @patch("blockchain.xrpl.services.resource.ResourceService.transfer")
    def test_give_resource_amount(self, mock_transfer):
        """give 5 wheat to Char2 should transfer wheat."""
        self.call(CmdGive(), "5 wheat to Char2")
        self.assertEqual(self.char1.get_resource(1), 15)
        self.assertEqual(self.char2.get_resource(1), 5)

    @patch("blockchain.xrpl.services.resource.ResourceService.transfer")
    def test_give_all_resource(self, mock_transfer):
        """give all wheat to Char2 should transfer all wheat."""
        self.call(CmdGive(), "all wheat to Char2")
        self.assertEqual(self.char1.get_resource(1), 0)
        self.assertEqual(self.char2.get_resource(1), 20)

    def test_give_resource_insufficient(self):
        """give more resource than you have should show error."""
        self.char1.db.resources = {1: 2}
        self.call(CmdGive(), "5 wheat to Char2", "You only have 2")

    def test_give_resource_none(self):
        """give resource when you have none should show error."""
        self.char1.db.resources = {}
        self.call(CmdGive(), "5 wheat to Char2", "You don't have any Wheat.")


class TestCmdGiveObject(EvenniaCommandTest):
    """Test giving NFT objects (standard Evennia give)."""

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

    def test_give_object(self):
        """give sword to Char2 should move it to Char2."""
        self.call(CmdGive(), "sword to Char2")
        self.assertIn(self.sword, self.char2.contents)

    def test_give_object_not_found(self):
        """give item you don't have should show error."""
        self.call(CmdGive(), "banana to Char2", "You aren't carrying banana.")

    def test_give_world_anchored_nft_item(self):
        """give should succeed for WorldAnchoredNFTItem (ownership transfer)."""
        mount = create.create_object(
            "typeclasses.items.untakeables.world_anchored_nft_item.WorldAnchoredNFTItem",
            key="horse",
            nohome=True,
        )
        mount.db_location = self.char1
        mount.save(update_fields=["db_location"])
        self.call(CmdGive(), "horse to Char2", "You give")
        self.assertEqual(mount.location, self.char2)


class TestCmdGiveAll(EvenniaCommandTest):
    """Test 'give all to <target>' — gives everything with confirmation."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)
        self.account2.attributes.add("wallet_address", WALLET_B)
        self.char1.db.gold = 50
        self.char1.db.resources = {1: 10}  # 10 wheat
        self.char2.db.gold = 0
        self.char2.db.resources = {}
        self.sword = create.create_object(
            "evennia.objects.objects.DefaultObject",
            key="sword",
            location=self.char1,
        )

    @patch("blockchain.xrpl.services.resource.ResourceService.transfer")
    @patch("blockchain.xrpl.services.gold.GoldService.transfer")
    def test_give_all_confirm_yes(self, mock_gold, mock_resource):
        """give all to Char2 with Y confirmation should give everything."""
        self.call(CmdGive(), "all to Char2", inputs=["y"])
        self.assertIn(self.sword, self.char2.contents)
        self.assertEqual(self.char1.get_gold(), 0)
        self.assertEqual(self.char2.get_gold(), 50)
        self.assertEqual(self.char1.get_resource(1), 0)
        self.assertEqual(self.char2.get_resource(1), 10)

    def test_give_all_confirm_no(self):
        """give all to Char2 with N confirmation should cancel."""
        self.call(CmdGive(), "all to Char2", "Give cancelled.", inputs=["n"])
        self.assertIn(self.sword, self.char1.contents)
        self.assertEqual(self.char1.get_gold(), 50)

    def test_give_all_empty_inventory(self):
        """give all with nothing to give."""
        self.sword.delete()
        self.char1.db.gold = 0
        self.char1.db.resources = {}
        self.call(CmdGive(), "all to Char2", "You aren't carrying anything.")
