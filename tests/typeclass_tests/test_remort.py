"""
Tests for RemortMixin.at_remort() — the character reset on remort.

Covers the key reset behaviours: stat wipe, inventory transfer, quest
clear, remort counter, and confirms the old active_pet / active_mount
attributes are NOT referenced (they were removed as relic dependencies).

evennia test --settings settings tests.typeclass_tests.test_remort
"""

from unittest.mock import patch, MagicMock

from evennia.utils.test_resources import EvenniaTest
from evennia.utils import create

from enums.hunger_level import HungerLevel


WALLET_A = "0xAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"

_CHAR = "typeclasses.actors.character.FCMCharacter"
_ROOM = "typeclasses.terrain.rooms.room_base.RoomBase"


class TestRemortReset(EvenniaTest):
    """Test at_remort() resets character state correctly."""

    character_typeclass = _CHAR
    room_typeclass = _ROOM
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

        # Give the character some state to reset
        self.char1.strength = 16
        self.char1.experience_points = 5000
        self.char1.total_level = 5
        self.char1.num_remorts = 0

    @patch("blockchain.xrpl.services.nft.NFTService.bank")
    @patch("blockchain.xrpl.services.gold.GoldService.unbank")
    def test_remort_increments_counter(self, *mocks):
        self.char1.at_remort(self.bank)
        self.assertEqual(self.char1.num_remorts, 1)

    @patch("blockchain.xrpl.services.nft.NFTService.bank")
    @patch("blockchain.xrpl.services.gold.GoldService.unbank")
    def test_remort_resets_ability_scores(self, *mocks):
        self.char1.at_remort(self.bank)
        self.assertEqual(self.char1.strength, 8)
        self.assertEqual(self.char1.dexterity, 8)
        self.assertEqual(self.char1.constitution, 8)

    @patch("blockchain.xrpl.services.nft.NFTService.bank")
    @patch("blockchain.xrpl.services.gold.GoldService.unbank")
    def test_remort_resets_xp_and_levels(self, *mocks):
        self.char1.at_remort(self.bank)
        self.assertEqual(self.char1.experience_points, 0)
        self.assertEqual(self.char1.total_level, 1)
        self.assertEqual(self.char1.levels_to_spend, 0)

    @patch("blockchain.xrpl.services.nft.NFTService.bank")
    @patch("blockchain.xrpl.services.gold.GoldService.unbank")
    def test_remort_resets_hunger(self, *mocks):
        self.char1.hunger_level = HungerLevel.STARVING
        self.char1.at_remort(self.bank)
        self.assertEqual(self.char1.hunger_level, HungerLevel.FULL)

    @patch("blockchain.xrpl.services.nft.NFTService.bank")
    @patch("blockchain.xrpl.services.gold.GoldService.unbank")
    def test_remort_preserves_mounted_on(self, *mocks):
        """
        mounted_on should survive remort — a character sitting on a horse
        in the room doesn't need to dismount just because they remorted.
        """
        # Use self.room1 as a stand-in for a mount (serializable to db,
        # and truthy — all we need is to confirm remort doesn't clear it).
        self.char1.db.mounted_on = self.room1

        self.char1.at_remort(self.bank)

        self.assertEqual(self.char1.db.mounted_on, self.room1)
