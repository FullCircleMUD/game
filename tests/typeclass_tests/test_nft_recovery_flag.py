"""
Tests the ``recovering`` flag on NFT object creation.

A world rebuild destroys every Evennia object row while the ownership
mirror survives untouched. Recovery rebuilds the game object for
ownership the mirror *already* records — the item has not been crafted,
deposited or spawned, it simply lost its row.

``BaseNFTItem.spawn_into()`` is the existing rebuild-from-mirror routine
and does everything needed: prototype, key, description, token binding,
metadata, and at_restore_from_metadata after the move. What it did not
have was a way to say "this is a recovery" — so the mixin booked the
arrival, calling craft_output onto a character or deposit_from_chain into
a bank. The latter also wants a tx_hash that does not exist.

The flag passes through spawn_into's **kwargs into move_to, which
forwards it to at_post_move.

evennia test --settings settings tests.typeclass_tests.test_nft_recovery_flag
"""

from unittest.mock import patch

from django.conf import settings
from evennia.utils.test_resources import EvenniaTest


TOKEN = "10101"


class NFTRecoveryFlagBase(EvenniaTest):
    databases = {"default", "xrpl"}
    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"
    character_typeclass = "typeclasses.actors.character.FCMCharacter"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        from blockchain.xrpl.models import NFTGameState, NFTItemType

        self.item_type = NFTItemType.objects.create(
            name="Recovery Test Blade",
            typeclass="typeclasses.items.base_nft_item.BaseNFTItem",
            prototype_key="",
            description="A test blade.",
            default_metadata={"durability": 42},
        )
        self.nft_row = NFTGameState.objects.create(
            nftoken_id=TOKEN,
            taxon=0,
            owner_in_game=settings.XRPL_VAULT_ADDRESS,
            location="CHARACTER",
            character_key=self.char1.key,
            item_type=self.item_type,
            metadata={"durability": 42},
        )

    def tearDown(self):
        from blockchain.xrpl.models import NFTGameState

        NFTGameState.objects.filter(nftoken_id=TOKEN).delete()
        self.item_type.delete()
        super().tearDown()


class TestRecoveringSuppressesTheMirrorWrite(NFTRecoveryFlagBase):
    """Recovery reads the mirror; it must never write to it."""

    def test_onto_a_character_books_nothing(self):
        from blockchain.xrpl.services.nft import NFTService
        from typeclasses.items.base_nft_item import BaseNFTItem

        with patch.object(NFTService, "craft_output") as craft:
            BaseNFTItem.spawn_into(TOKEN, self.char1, recovering=True)

        craft.assert_not_called()

    def test_into_a_bank_books_nothing(self):
        """deposit_from_chain would also want a tx_hash we do not have."""
        from evennia.utils.create import create_object

        from blockchain.xrpl.services.nft import NFTService
        from typeclasses.items.base_nft_item import BaseNFTItem

        bank = create_object(
            "typeclasses.accounts.account_bank.AccountBank",
            key="bank-recoverytest",
            nohome=True,
        )

        with patch.object(NFTService, "deposit_from_chain") as deposit:
            BaseNFTItem.spawn_into(TOKEN, bank, recovering=True)

        deposit.assert_not_called()

    def test_the_row_is_left_alone(self):
        from blockchain.xrpl.models import NFTGameState
        from typeclasses.items.base_nft_item import BaseNFTItem

        BaseNFTItem.spawn_into(TOKEN, self.char1, recovering=True)

        row = NFTGameState.objects.get(nftoken_id=TOKEN)
        self.assertEqual(row.location, "CHARACTER")
        self.assertEqual(row.character_key, self.char1.key)


class TestRecoveringStillRebuildsTheItem(NFTRecoveryFlagBase):
    """Suppressing the write must not suppress the rebuild."""

    def test_the_object_is_placed(self):
        from typeclasses.items.base_nft_item import BaseNFTItem

        obj = BaseNFTItem.spawn_into(TOKEN, self.char1, recovering=True)

        self.assertIsNotNone(obj)
        self.assertEqual(obj.location, self.char1)

    def test_the_token_binding_survives(self):
        from typeclasses.items.base_nft_item import BaseNFTItem

        obj = BaseNFTItem.spawn_into(TOKEN, self.char1, recovering=True)

        self.assertEqual(str(obj.token_id), TOKEN)

    def test_metadata_is_restored(self):
        """A worn weapon must not come back pristine."""
        from typeclasses.items.base_nft_item import BaseNFTItem

        obj = BaseNFTItem.spawn_into(TOKEN, self.char1, recovering=True)

        self.assertEqual(obj.attributes.get("durability"), 42)


class TestWithoutTheFlagTheMirrorIsStillWritten(NFTRecoveryFlagBase):
    """The control.

    Without it, the tests above pass just as well if spawn_into never
    wrote to the mirror in the first place.
    """

    def test_a_normal_spawn_onto_a_character_books_a_craft_output(self):
        from blockchain.xrpl.services.nft import NFTService
        from typeclasses.items.base_nft_item import BaseNFTItem

        with patch.object(NFTService, "craft_output") as craft:
            BaseNFTItem.spawn_into(TOKEN, self.char1)

        craft.assert_called_once()
