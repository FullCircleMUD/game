"""
Tests for CmdGet — verifies picking up gold, resources, and objects
from a room via the overridden get command.
"""

from unittest.mock import patch

from django.conf import settings

from evennia.utils.test_resources import EvenniaCommandTest
from evennia.utils import create

from commands.all_char_cmds.cmd_override_get import CmdGet


WALLET_A = "0xAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
VAULT_WALLET = settings.XRPL_VAULT_ADDRESS


class TestCmdGetGold(EvenniaCommandTest):
    """Test picking up gold from a room."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)
        self.char1.db.gold = 0
        self.char1.db.resources = {}
        self.room1.db.gold = 100
        self.room1.db.resources = {}

    def test_get_no_args(self):
        """get with no arguments should show usage."""
        self.call(CmdGet(), "", "Get what?")

    @patch("blockchain.xrpl.services.gold.GoldService.pickup")
    def test_get_gold_amount(self, mock_pickup):
        """get 50 gold should move 50 gold from room to character."""
        self.call(CmdGet(), "50 gold")
        self.assertEqual(self.char1.get_gold(), 50)
        self.assertEqual(self.room1.get_gold(), 50)

    @patch("blockchain.xrpl.services.gold.GoldService.pickup")
    def test_get_all_gold(self, mock_pickup):
        """get all gold should move all gold from room to character."""
        self.call(CmdGet(), "all gold")
        self.assertEqual(self.char1.get_gold(), 100)
        self.assertEqual(self.room1.get_gold(), 0)

    def test_get_gold_insufficient(self):
        """get more gold than available should show error."""
        self.room1.db.gold = 10
        self.call(CmdGet(), "50 gold", "There's only 10")

    def test_get_gold_none_available(self):
        """get gold when room has none should show error."""
        self.room1.db.gold = 0
        self.call(CmdGet(), "50 gold", "There's no gold here.")


class TestCmdGetResource(EvenniaCommandTest):
    """Test picking up resources from a room."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)
        self.char1.db.gold = 0
        self.char1.db.resources = {}
        self.room1.db.gold = 0
        self.room1.db.resources = {1: 20}  # 20 wheat

    @patch("blockchain.xrpl.services.resource.ResourceService.pickup")
    def test_get_resource_amount(self, mock_pickup):
        """get 5 wheat should move 5 wheat from room to character."""
        self.call(CmdGet(), "5 wheat")
        self.assertEqual(self.char1.get_resource(1), 5)
        self.assertEqual(self.room1.get_resource(1), 15)

    @patch("blockchain.xrpl.services.resource.ResourceService.pickup")
    def test_get_all_resource(self, mock_pickup):
        """get all wheat should move all wheat from room to character."""
        self.call(CmdGet(), "all wheat")
        self.assertEqual(self.char1.get_resource(1), 20)
        self.assertEqual(self.room1.get_resource(1), 0)

    def test_get_resource_insufficient(self):
        """get more resource than available should show error."""
        self.room1.db.resources = {1: 2}
        self.call(CmdGet(), "5 wheat", "There's only 2")

    def test_get_resource_none_available(self):
        """get resource when room has none should show error."""
        self.room1.db.resources = {}
        self.call(CmdGet(), "5 wheat", "There's no Wheat here.")


class TestCmdGetObject(EvenniaCommandTest):
    """Test picking up NFT objects (standard Evennia get)."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.sword = create.create_object(
            "evennia.objects.objects.DefaultObject",
            key="sword",
            location=self.room1,
        )

    def test_get_object(self):
        """get sword should move it to inventory."""
        self.call(CmdGet(), "sword")
        self.assertIn(self.sword, self.char1.contents)

    def test_get_object_not_found(self):
        """get nonexistent object should show not found."""
        self.call(CmdGet(), "banana", "Could not find 'banana'.")

    def test_get_world_anchored_nft_item(self):
        """get should refuse to pick up an WorldAnchoredNFTItem."""
        mount = create.create_object(
            "typeclasses.items.untakeables.world_anchored_nft_item.WorldAnchoredNFTItem",
            key="horse",
            location=self.room1,
        )
        self.call(CmdGet(), "horse", "You can't get that.")
        self.assertEqual(mount.location, self.room1)


class TestCmdGetAll(EvenniaCommandTest):
    """Test 'get all' — picks up everything in the room."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)
        self.char1.db.gold = 0
        self.char1.db.resources = {}
        self.room1.db.gold = 50
        self.room1.db.resources = {1: 10}  # 10 wheat
        self.sword = create.create_object(
            "evennia.objects.objects.DefaultObject",
            key="sword",
            location=self.room1,
        )

    @patch("blockchain.xrpl.services.resource.ResourceService.pickup")
    @patch("blockchain.xrpl.services.gold.GoldService.pickup")
    def test_get_all(self, mock_gold, mock_resource):
        """get all should pick up objects, gold, and resources."""
        self.call(CmdGet(), "all")
        self.assertIn(self.sword, self.char1.contents)
        self.assertEqual(self.char1.get_gold(), 50)
        self.assertEqual(self.char1.get_resource(1), 10)

    def test_get_all_empty_room(self):
        """get all in empty room should show nothing message."""
        # Remove the sword and framework-created objects from the room
        self.sword.delete()
        self.obj1.delete()
        self.obj2.delete()
        self.room1.db.gold = 0
        self.room1.db.resources = {}
        self.call(CmdGet(), "all", "There's nothing here to pick up.")

    @patch("blockchain.xrpl.services.resource.ResourceService.pickup")
    @patch("blockchain.xrpl.services.gold.GoldService.pickup")
    def test_get_all_skips_exits(self, mock_gold, mock_resource):
        """get all should not pick up exits."""
        exit_obj = create.create_object(
            "evennia.objects.objects.DefaultExit",
            key="north",
            location=self.room1,
            destination=self.room2,
        )
        self.call(CmdGet(), "all")
        # Exit should remain in the room, not in inventory
        self.assertEqual(exit_obj.location, self.room1)
        self.assertNotIn(exit_obj, self.char1.contents)
        # Sword should still be picked up
        self.assertIn(self.sword, self.char1.contents)

    @patch("blockchain.xrpl.services.resource.ResourceService.pickup")
    @patch("blockchain.xrpl.services.gold.GoldService.pickup")
    def test_get_all_skips_characters(self, mock_gold, mock_resource):
        """get all should not pick up other characters."""
        other_char = create.create_object(
            "evennia.objects.objects.DefaultCharacter",
            key="bob",
        )
        other_char.move_to(self.room1, quiet=True)
        self.call(CmdGet(), "all")
        # Other character should remain in the room
        self.assertEqual(other_char.location, self.room1)
        self.assertNotIn(other_char, self.char1.contents)


class TestCmdGetVaultWallet(EvenniaCommandTest):
    """Test that vault-wallet characters get a clean error instead of crash."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        # Set wallet to the vault address (superuser dev scenario)
        self.account.attributes.add("wallet_address", VAULT_WALLET)
        self.char1.db.gold = 0
        self.char1.db.resources = {}
        self.room1.db.gold = 50
        self.room1.db.resources = {1: 10}

    def test_get_gold_vault_wallet_skips(self):
        """Picking up gold with vault wallet should show dev message, not crash."""
        self.call(CmdGet(), "50 gold", "[Dev] Gold transfer skipped")
        # Gold should NOT move — transfer was blocked
        self.assertEqual(self.char1.get_gold(), 0)
        self.assertEqual(self.room1.get_gold(), 50)

    def test_get_resource_vault_wallet_skips(self):
        """Picking up resource with vault wallet should show dev message, not crash."""
        self.call(CmdGet(), "5 wheat", "[Dev] Resource transfer skipped")
        # Resource should NOT move — transfer was blocked
        self.assertEqual(self.char1.get_resource(1), 0)
        self.assertEqual(self.room1.get_resource(1), 10)

    def test_get_all_vault_wallet_skips_fungibles(self):
        """get all with vault wallet should pick up objects but skip fungibles."""
        sword = create.create_object(
            "evennia.objects.objects.DefaultObject",
            key="sword",
            location=self.room1,
        )
        self.call(CmdGet(), "all")
        # Object should be picked up
        self.assertIn(sword, self.char1.contents)
        # Fungibles should NOT move
        self.assertEqual(self.char1.get_gold(), 0)
        self.assertEqual(self.room1.get_gold(), 50)


class TestCmdGetContainerAmbiguity(EvenniaCommandTest):
    """Test that multi-word item names aren't misread as container syntax."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)
        self.char1.db.gold = 0
        self.char1.db.resources = {}

        # A container named "Backpack" in the room
        self.backpack = create.create_object(
            "typeclasses.items.containers.container_nft_item.ContainerNFTItem",
            key="Backpack",
            location=self.room1,
            nohome=True,
        )
        self.backpack.is_open = True

        # An item whose name ends with the container's name
        self.leather_backpack = create.create_object(
            "evennia.objects.objects.DefaultObject",
            key="Leather Backpack",
            location=self.room1,
        )

        # An item inside the container
        self.sword = create.create_object(
            "evennia.objects.objects.DefaultObject",
            key="Sword",
            location=self.backpack,
        )

    def test_get_multiword_item_not_parsed_as_container(self):
        """'get leather backpack' should pick up the item, not try to get
        'leather' from 'backpack'."""
        self.call(CmdGet(), "leather backpack")
        self.assertIn(self.leather_backpack, self.char1.contents)

    def test_get_from_container_explicit(self):
        """'get sword from backpack' should get the sword from inside the
        backpack using the explicit 'from' preposition."""
        result = self.call(CmdGet(), "sword from backpack")
        self.assertIn(self.sword, self.char1.contents)

    def test_get_from_container_shorthand_f(self):
        """'get sword f backpack' should work as shorthand for 'from'."""
        result = self.call(CmdGet(), "sword f backpack")
        self.assertIn(self.sword, self.char1.contents)

    def test_get_container_fallback_when_no_direct_match(self):
        """If no item matches the full name, fall back to container split.
        'get sword backpack' should get sword from backpack when there's
        no item called 'sword backpack'."""
        result = self.call(CmdGet(), "sword backpack")
        self.assertIn(self.sword, self.char1.contents)
