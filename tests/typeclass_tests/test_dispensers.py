"""
Tests for the test-only dispensers and gold button.

Covers the three behavioural differences from the production shopkeepers:

- Free — get_buy_price/get_sell_price return 0, and buying charges nothing.
- Unfiltered stock — the NFT dispenser lists item types with no
  tracking_token, which NFTShopkeeperNPC deliberately hides. This is the
  behaviour the dispensers exist for, so it is tested by contrast against
  the parent rather than in isolation.
- No selling back — execute_sell refuses instead of destroying the item.

Plus TestGoldButton, which funds the gold side so a tester can use a real
AMM-priced shop.

evennia test --settings settings tests.typeclass_tests.test_dispensers
"""

from unittest.mock import MagicMock

from django.conf import settings
from evennia import create_object
from evennia.utils.test_resources import EvenniaCommandTest

from blockchain.xrpl.models import NFTGameState, NFTItemType
from typeclasses.actors.npcs.nft_shopkeeper import NFTShopkeeperNPC
from typeclasses.actors.npcs.resource_shopkeeper import ResourceShopkeeperNPC
from typeclasses.actors.npcs.test_dispenser import (
    TestNFTDispenser,
    TestResourceDispenser,
)
from typeclasses.world_objects.test_gold_button import TestGoldButton

TRADEABLE = "ZZZTestTradeableSword"
UNTRADEABLE = "ZZZTestUntradeableRecipe"


def _messages(char):
    """All text sent to a character whose msg has been mocked."""
    return " ".join(str(call.args[0]) for call in char.msg.call_args_list if call.args)


def _make_item_types():
    """One priceable item type and one without a tracking_token."""
    tradeable = NFTItemType.objects.create(
        name=TRADEABLE,
        typeclass="typeclasses.items.base_nft_item.BaseNFTItem",
        tracking_token="ZZZTRACK",
    )
    untradeable = NFTItemType.objects.create(
        name=UNTRADEABLE,
        typeclass="typeclasses.items.base_nft_item.BaseNFTItem",
        tracking_token=None,
    )
    return tradeable, untradeable


# ══════════════════════════════════════════════════════════════════════════
#  TestNFTDispenser
# ══════════════════════════════════════════════════════════════════════════


class TestNFTDispenserListing(EvenniaCommandTest):
    """The dispenser lists what the parent hides.

    This is the load-bearing difference: free pricing alone would still
    leave every recipe and spell scroll invisible, because they are
    excluded by tradeability rather than by cost.
    """

    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        _make_item_types()
        self.stock = [TRADEABLE, UNTRADEABLE]
        self.shop = create_object(
            NFTShopkeeperNPC, key="RealShop", location=self.room1,
        )
        self.shop.inventory = self.stock
        self.dispenser = create_object(
            TestNFTDispenser, key="Dispenser", location=self.room1,
        )
        self.dispenser.inventory = self.stock

    def tearDown(self):
        for obj in (self.shop, self.dispenser):
            if obj and obj.pk:
                obj.delete()
        super().tearDown()

    def test_parent_hides_untradeable(self):
        names = {row["name"] for row in self.shop.list_inventory()}
        self.assertEqual(names, {TRADEABLE})

    def test_dispenser_lists_untradeable(self):
        names = {row["name"] for row in self.dispenser.list_inventory()}
        self.assertEqual(names, {TRADEABLE, UNTRADEABLE})

    def test_get_tradeable_types_also_unfiltered(self):
        """Command-side counterpart must agree with list_inventory."""
        names = set(
            self.dispenser.get_tradeable_types().values_list("name", flat=True)
        )
        self.assertEqual(names, {TRADEABLE, UNTRADEABLE})

    def test_unstocked_types_still_excluded(self):
        """Unfiltered does not mean unrestricted — stock still governs."""
        self.dispenser.inventory = [UNTRADEABLE]
        names = {row["name"] for row in self.dispenser.list_inventory()}
        self.assertEqual(names, {UNTRADEABLE})


class TestNFTDispenserPricing(EvenniaCommandTest):
    """Everything is free, including the types the parent cannot price."""

    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        _make_item_types()
        self.dispenser = create_object(
            TestNFTDispenser, key="Dispenser", location=self.room1,
        )
        self.dispenser.inventory = [TRADEABLE, UNTRADEABLE]

    def tearDown(self):
        if self.dispenser and self.dispenser.pk:
            self.dispenser.delete()
        super().tearDown()

    def test_buy_price_is_zero(self):
        self.assertEqual(self.dispenser.get_buy_price(TRADEABLE), 0)

    def test_buy_price_is_zero_for_unpriceable_type(self):
        """No AMM pool exists for this type — it must still not raise."""
        self.assertEqual(self.dispenser.get_buy_price(UNTRADEABLE), 0)

    def test_sell_price_is_zero(self):
        self.assertEqual(self.dispenser.get_sell_price(TRADEABLE), 0)

    def test_quote_hint_advertises_free(self):
        self.assertIn("free", self.dispenser.quote_hint().lower())


class TestNFTDispenserBuy(EvenniaCommandTest):
    """Buying dispenses the item, charges nothing, and moves the mirror."""

    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        _make_item_types()
        self.dispenser = create_object(
            TestNFTDispenser, key="Dispenser", location=self.room1,
        )
        self.dispenser.inventory = [UNTRADEABLE]
        self.char1.msg = MagicMock()
        # The mirror writes owner_in_game from the character's account
        # wallet, and the model rejects a null owner on a non-ONCHAIN
        # token. Real players always have one; the test fixture does not,
        # so give char1 a wallet or craft_output trips the constraint.
        self.char1.account.attributes.add("wallet_address", "rZZZTestWallet00000000000000000001")
        # assign_item_type claims the first blank RESERVE token ordered by
        # nftoken_id, so any other blank token in the test DB would be
        # picked ahead of ours and the assertions would inspect the wrong
        # row. Clear the table first and make this the only candidate.
        NFTGameState.objects.all().delete()
        self.token = NFTGameState.objects.create(
            nftoken_id="ZZZTESTTOKEN0001",
            taxon=1,
            location=NFTGameState.LOCATION_RESERVE,
            # owner_in_game must be set — the model constrains it to null
            # only for ONCHAIN tokens.
            owner_in_game=settings.XRPL_VAULT_ADDRESS,
            item_type=None,
        )

    def tearDown(self):
        if self.dispenser and self.dispenser.pk:
            self.dispenser.delete()
        super().tearDown()

    def _quote(self, item_key=UNTRADEABLE):
        return {"item_key": item_key, "qty": 1, "gold_price": 0}

    def test_buy_charges_no_gold(self):
        before = self.char1.get_gold()
        self.dispenser.execute_buy(self.char1, self._quote())
        self.assertEqual(self.char1.get_gold(), before)

    def test_buy_assigns_the_item_type(self):
        self.dispenser.execute_buy(self.char1, self._quote())
        self.token.refresh_from_db()
        self.assertIsNotNone(self.token.item_type)
        self.assertEqual(self.token.item_type.name, UNTRADEABLE)

    def test_buy_moves_mirror_to_character(self):
        """Possession must be mirrored even though no payment happened."""
        self.dispenser.execute_buy(self.char1, self._quote())
        self.token.refresh_from_db()
        self.assertEqual(
            self.token.location, NFTGameState.LOCATION_CHARACTER,
        )

    def test_buy_puts_the_object_in_inventory(self):
        self.dispenser.execute_buy(self.char1, self._quote())
        keys = [obj.key for obj in self.char1.contents]
        self.assertIn(UNTRADEABLE, keys)

    def test_unknown_item_type_is_reported_not_raised(self):
        """A typo in a machine's YAML stock list must not traceback."""
        self.dispenser.execute_buy(self.char1, self._quote("ZZZNoSuchThing"))
        self.assertIn("UNKNOWN PRODUCT CODE", _messages(self.char1))

    def test_exhausted_pool_is_reported_not_raised(self):
        """The blank-token reserve is finite; running dry must be graceful."""
        NFTGameState.objects.all().delete()
        self.dispenser.execute_buy(self.char1, self._quote())
        self.assertIn("SOLD OUT", _messages(self.char1))

    def test_buy_rejects_non_singleton(self):
        with self.assertRaises(AssertionError):
            self.dispenser.execute_buy(
                self.char1, {"item_key": UNTRADEABLE, "qty": 2, "gold_price": 0},
            )


class TestNFTDispenserSell(EvenniaCommandTest):
    """Dispensers vend only."""

    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        _make_item_types()
        self.dispenser = create_object(
            TestNFTDispenser, key="Dispenser", location=self.room1,
        )
        self.dispenser.inventory = [TRADEABLE]
        self.char1.msg = MagicMock()

    def tearDown(self):
        if self.dispenser and self.dispenser.pk:
            self.dispenser.delete()
        super().tearDown()

    def test_sell_refuses_without_paying(self):
        before = self.char1.get_gold()
        self.dispenser.execute_sell(
            self.char1, {"item_key": TRADEABLE, "qty": 1, "gold_price": 0},
        )
        self.assertEqual(self.char1.get_gold(), before)
        self.assertIn("no coin slot", _messages(self.char1))


# ══════════════════════════════════════════════════════════════════════════
#  TestResourceDispenser
# ══════════════════════════════════════════════════════════════════════════


class TestResourceDispenserBasics(EvenniaCommandTest):
    """Free pricing, and no listing override (the parent never filtered)."""

    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.dispenser = create_object(
            TestResourceDispenser, key="ResDispenser", location=self.room1,
        )
        self.dispenser.inventory = [1]
        self.char1.msg = MagicMock()

    def tearDown(self):
        if self.dispenser and self.dispenser.pk:
            self.dispenser.delete()
        super().tearDown()

    def test_buy_price_is_zero(self):
        self.assertEqual(self.dispenser.get_buy_price(1, 10), 0)

    def test_sell_price_is_zero(self):
        self.assertEqual(self.dispenser.get_sell_price(1, 10), 0)

    def test_quote_hint_advertises_free(self):
        self.assertIn("free", self.dispenser.quote_hint().lower())

    def test_listing_is_inherited_not_overridden(self):
        """The parent needs no filter lift — every resource has a pool."""
        self.assertIs(
            type(self.dispenser).list_inventory,
            ResourceShopkeeperNPC.list_inventory,
        )

    def test_sell_refuses_without_paying(self):
        before = self.char1.get_gold()
        self.dispenser.execute_sell(
            self.char1, {"item_key": 1, "qty": 1, "gold_price": 0},
        )
        self.assertEqual(self.char1.get_gold(), before)
        self.assertIn("no coin slot", _messages(self.char1))


# ══════════════════════════════════════════════════════════════════════════
#  TestGoldButton
# ══════════════════════════════════════════════════════════════════════════


class TestGoldButtonBasics(EvenniaCommandTest):
    """Pays out through the encapsulated reserve route."""

    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.button = create_object(
            TestGoldButton, key="Big Gold Button", location=self.room1,
        )

    def tearDown(self):
        if self.button and self.button.pk:
            self.button.delete()
        super().tearDown()

    def test_default_payout_is_1000(self):
        self.assertEqual(self.button.gold_amount, 1000)

    def test_payout_is_yaml_overridable(self):
        self.button.gold_amount = 5
        self.assertEqual(self.button.gold_amount, 5)

    def test_has_press_cmdset(self):
        self.assertTrue(
            any(
                cs.key == "GoldButtonCmdSet"
                for cs in self.button.cmdset.all()
            )
        )
