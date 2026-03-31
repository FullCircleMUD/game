"""
Tests for the spawned item cleanup utility.

Tests clear_spawned_items() which removes ephemeral spawned items
and resets mirror DB rows to RESERVE. Called via the wipe_spawns
superuser command — NOT called on server restart.

evennia test --settings settings tests.server_tests.test_spawned_cleanup
"""

from decimal import Decimal

from django.conf import settings
from evennia.objects.models import ObjectDB
from evennia.utils import create
from evennia.utils.test_resources import EvenniaTest

from blockchain.xrpl.models import NFTGameState, FungibleGameState
from commands.room_specific_cmds.bank.cmd_balance import ensure_bank
from utils.spawn_cleanup import clear_spawned_items as _clear_spawned_items


VAULT = settings.XRPL_VAULT_ADDRESS
GOLD_CODE = settings.XRPL_GOLD_CURRENCY_CODE
WALLET_A = "0xAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"


def _make_nft_state(nftoken_id, location, owner=None):
    """Create an NFTGameState row for testing."""
    kwargs = {
        "nftoken_id": str(nftoken_id),
        "taxon": 0,
        "owner_in_game": owner or VAULT,
        "location": location,
    }
    if location == NFTGameState.LOCATION_CHARACTER:
        kwargs["character_key"] = "TestChar"
    return NFTGameState.objects.create(**kwargs)


def _make_nft_object(key, location, token_id):
    """
    Create a BaseNFTItem Evennia object with chain attributes set.

    The move_to() call triggers at_post_move() which may fail silently
    if the mirror row doesn't match the expected transition. That's OK —
    the test only needs the object in the right location with the right
    attributes for the cleanup to process it.
    """
    obj = create.create_object(
        "typeclasses.items.base_nft_item.BaseNFTItem",
        key=key,
        nohome=True,
    )
    obj.token_id = token_id
    if location:
        obj.move_to(location, quiet=True)
    return obj


class TestClearSpawnedItems(EvenniaTest):
    """Test the _clear_spawned_items() cleanup function."""

    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)

    # ============================================================== #
    #  Primary sweep — NFT Evennia object deletion
    # ============================================================== #

    def test_nft_in_room_deleted(self):
        """NFT in a room should be deleted and mirror reset to RESERVE."""
        mirror = _make_nft_state(10100, NFTGameState.LOCATION_SPAWNED)
        item = _make_nft_object("Spawned Sword", self.room1, token_id=10100)
        item_pk = item.pk

        _clear_spawned_items()

        # Evennia object should be gone
        self.assertFalse(ObjectDB.objects.filter(pk=item_pk).exists())
        # Mirror row should be back in RESERVE with identity wiped
        mirror.refresh_from_db()
        self.assertEqual(mirror.location, NFTGameState.LOCATION_RESERVE)
        self.assertIsNone(mirror.item_type)
        self.assertEqual(mirror.metadata, {})

    def test_nft_on_character_preserved(self):
        """NFT on a character should NOT be deleted."""
        mirror = _make_nft_state(
            10101, NFTGameState.LOCATION_CHARACTER, owner=WALLET_A,
        )
        mirror.character_key = self.char1.key
        mirror.save()

        item = _make_nft_object("Player Sword", self.char1, token_id=10101)
        item_pk = item.pk

        _clear_spawned_items()

        # Object should still exist on the character
        self.assertTrue(ObjectDB.objects.filter(pk=item_pk).exists())
        self.assertEqual(item.location, self.char1)
        # Mirror should be unchanged
        mirror.refresh_from_db()
        self.assertEqual(mirror.location, NFTGameState.LOCATION_CHARACTER)

    def test_nft_in_bank_preserved(self):
        """NFT in an account bank should NOT be deleted."""
        bank = ensure_bank(self.account)
        mirror = _make_nft_state(
            10102, NFTGameState.LOCATION_ACCOUNT, owner=WALLET_A,
        )

        item = _make_nft_object("Banked Shield", bank, token_id=10102)
        item_pk = item.pk

        _clear_spawned_items()

        # Object should still exist in the bank
        self.assertTrue(ObjectDB.objects.filter(pk=item_pk).exists())
        self.assertEqual(item.location, bank)
        # Mirror should be unchanged
        mirror.refresh_from_db()
        self.assertEqual(mirror.location, NFTGameState.LOCATION_ACCOUNT)

    def test_nft_with_no_location_deleted(self):
        """NFT with no location (orphaned) should be deleted."""
        mirror = _make_nft_state(10103, NFTGameState.LOCATION_SPAWNED)
        item = _make_nft_object("Orphaned Item", None, token_id=10103)
        item_pk = item.pk

        _clear_spawned_items()

        self.assertFalse(ObjectDB.objects.filter(pk=item_pk).exists())

    # ============================================================== #
    #  Secondary sweep — orphaned NFT mirror rows
    # ============================================================== #

    def test_orphaned_nft_mirror_reset(self):
        """SPAWNED mirror row with no Evennia object resets to RESERVE."""
        # Create a mirror row with no corresponding Evennia object —
        # simulates a crash where the object was lost
        mirror = _make_nft_state(10104, NFTGameState.LOCATION_SPAWNED)

        _clear_spawned_items()

        mirror.refresh_from_db()
        self.assertEqual(mirror.location, NFTGameState.LOCATION_RESERVE)
        self.assertIsNone(mirror.item_type)
        self.assertEqual(mirror.metadata, {})

    # ============================================================== #
    #  Secondary sweep — orphaned gold/resource rows
    # ============================================================== #

    def test_spawned_gold_reset(self):
        """SPAWNED gold row should be returned to RESERVE."""
        # Record initial reserve balance (seed data may have created one)
        initial_reserve = Decimal(0)
        try:
            row = FungibleGameState.objects.get(
                wallet_address=VAULT,
                currency_code=GOLD_CODE,
                location=FungibleGameState.LOCATION_RESERVE,
            )
            initial_reserve = row.balance
        except FungibleGameState.DoesNotExist:
            pass

        # Create SPAWNED gold (e.g. gold placed on a mob that was never looted)
        FungibleGameState.objects.create(
            wallet_address=VAULT,
            currency_code=GOLD_CODE,
            location=FungibleGameState.LOCATION_SPAWNED,
            balance=Decimal(500),
        )

        _clear_spawned_items()

        # SPAWNED row should be gone
        self.assertFalse(
            FungibleGameState.objects.filter(
                location=FungibleGameState.LOCATION_SPAWNED,
                currency_code=GOLD_CODE,
            ).exists()
        )
        # RESERVE should have gained the 500
        reserve = FungibleGameState.objects.get(
            wallet_address=VAULT,
            currency_code=GOLD_CODE,
            location=FungibleGameState.LOCATION_RESERVE,
        )
        self.assertEqual(reserve.balance, initial_reserve + Decimal(500))

    def test_spawned_resource_reset(self):
        """SPAWNED resource rows should be returned to RESERVE."""
        # Use "FCMWheat" as the test resource currency code
        # (matches resource_id=1 in currency_cache seed data)
        wheat_code = "FCMWheat"

        initial_reserve = Decimal(0)
        try:
            row = FungibleGameState.objects.get(
                wallet_address=VAULT,
                currency_code=wheat_code,
                location=FungibleGameState.LOCATION_RESERVE,
            )
            initial_reserve = row.balance
        except FungibleGameState.DoesNotExist:
            pass

        # Create SPAWNED wheat (e.g. wheat on a harvest node never collected)
        FungibleGameState.objects.create(
            wallet_address=VAULT,
            currency_code=wheat_code,
            location=FungibleGameState.LOCATION_SPAWNED,
            balance=Decimal(100),
        )

        _clear_spawned_items()

        # SPAWNED row should be gone
        self.assertFalse(
            FungibleGameState.objects.filter(
                location=FungibleGameState.LOCATION_SPAWNED,
                currency_code=wheat_code,
            ).exists()
        )
        # RESERVE should have gained the 100
        reserve = FungibleGameState.objects.get(
            wallet_address=VAULT,
            currency_code=wheat_code,
            location=FungibleGameState.LOCATION_RESERVE,
        )
        self.assertEqual(reserve.balance, initial_reserve + Decimal(100))

    # ============================================================== #
    #  Edge cases
    # ============================================================== #

    def test_no_spawned_items_no_errors(self):
        """Cleanup with nothing spawned should complete without errors."""
        _clear_spawned_items()

    def test_multiple_nft_types_cleared(self):
        """Multiple NFT objects in rooms are all deleted."""
        m1 = _make_nft_state(10110, NFTGameState.LOCATION_SPAWNED)
        m2 = _make_nft_state(10111, NFTGameState.LOCATION_SPAWNED)
        i1 = _make_nft_object("Sword", self.room1, token_id=10110)
        i2 = _make_nft_object("Shield", self.room1, token_id=10111)
        pk1, pk2 = i1.pk, i2.pk

        _clear_spawned_items()

        self.assertFalse(ObjectDB.objects.filter(pk=pk1).exists())
        self.assertFalse(ObjectDB.objects.filter(pk=pk2).exists())
        m1.refresh_from_db()
        m2.refresh_from_db()
        self.assertEqual(m1.location, NFTGameState.LOCATION_RESERVE)
        self.assertEqual(m2.location, NFTGameState.LOCATION_RESERVE)
