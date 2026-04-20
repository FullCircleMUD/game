"""
Tests for the quaff command.

evennia test --settings settings tests.command_tests.test_cmd_quaff
"""

from unittest.mock import patch

from evennia.utils.test_resources import EvenniaCommandTest
from evennia.utils import create

from commands.all_char_cmds.cmd_quaff import CmdQuaff


class TestCmdQuaff(EvenniaCommandTest):
    """Test the quaff command."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.room1.always_lit = True
        self.potion = create.create_object(
            "typeclasses.items.consumables.potion_nft_item.PotionNFTItem",
            key="Healing Potion",
            location=self.char1,
            nohome=True,
        )
        self.potion.potion_effects = [
            {"type": "heal", "dice": "2d4+2"},
        ]
        # Give char1 some damage to heal
        self.char1.hp = 10
        self.char1.hp_max = 50

    def test_no_args(self):
        """Quaff with no args shows usage."""
        self.call(CmdQuaff(), "", "Quaff what?")

    def test_quaff_potion(self):
        """Quaffing a potion should consume it."""
        self.call(CmdQuaff(), "healing potion")
        # Potion should be consumed (removed from inventory)
        from typeclasses.items.consumables.potion_nft_item import PotionNFTItem
        potions = [o for o in self.char1.contents if isinstance(o, PotionNFTItem)]
        self.assertEqual(len(potions), 0)

    def test_quaff_not_found(self):
        """Quaffing something not in inventory shows error."""
        self.call(CmdQuaff(), "banana", "You aren't carrying 'banana'.")

    def test_quaff_non_potion(self):
        """Quaffing a non-potion item shows type error."""
        sword = create.create_object(
            "evennia.objects.objects.DefaultObject",
            key="sword",
            location=self.char1,
        )
        self.call(CmdQuaff(), "sword", "sword is not a potion.")

    def test_quaff_in_darkness(self):
        """Quaffing in darkness should fail."""
        self.room1.always_lit = False
        self.room1.natural_light = False
        self.call(CmdQuaff(), "healing potion", "It's too dark to see anything.")
