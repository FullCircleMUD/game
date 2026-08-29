"""
Tests for NFT shop inventory matching — ``_find_inventory_item``.

This is the shared unit behind ``sell <item>`` and ``quote sell <item>``:
it turns a typed name into the single NFT the player meant, or explains
why there isn't one. Both commands wrap it in AMM pricing and deferred
threads, which are covered elsewhere — these tests exercise the matching
rules directly, with no reactor and no XRPL.

The rules under test:

* Worn copies are never candidates while an unworn copy exists.
* Ambiguity is decided on the NAME only. Two identical pairs of pants are
  not ambiguous; corduroy pants beside leather pants are.
* Within one name, a copy that can actually be sold beats one that can't
  (damaged, gem-inset). Only when no copy is sellable does the refusal
  reason surface.

NFTService is patched throughout because moving an NFT into a character
fires the mirror hooks.
"""

from unittest.mock import patch, MagicMock

from django.conf import settings

from evennia.utils import create
from evennia.utils.test_resources import EvenniaCommandTest

from blockchain.xrpl.models import NFTGameState, NFTItemType
from commands.npc_cmds.cmdset_nft_shop import _find_inventory_item


WALLET_A = "rZZZTestWalletAAAAAAAAAAAAAAAAAAAAA"

CORDUROY = "ZZZTestCorduroyPants"
CORDUROY_DELUXE = "ZZZTestCorduroyPantsDeluxe"
LEATHER = "ZZZTestLeatherPants"
DAGGER = "ZZZTestDagger"
SILK = "ZZZTestSilkPants"

WEARABLE = "typeclasses.items.wearables.wearable_nft_item.WearableNFTItem"
WEAPON = "typeclasses.items.weapons.weapon_nft_item.WeaponNFTItem"


def _messages(char):
    """All text sent to a character whose msg has been mocked."""
    return " ".join(str(call.args[0]) for call in char.msg.call_args_list if call.args)


class NFTShopMatchingTest(EvenniaCommandTest):
    """Base fixture — item types, a token counter, and item builders."""

    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)

        self.types = {
            name: NFTItemType.objects.create(
                name=name, typeclass=typeclass, tracking_token=token,
            )
            for name, typeclass, token in (
                (CORDUROY, WEARABLE, "ZZZCORD"),
                (CORDUROY_DELUXE, WEARABLE, "ZZZCORDX"),
                (LEATHER, WEARABLE, "ZZZLEATH"),
                (DAGGER, WEAPON, "ZZZDAGR"),
                (SILK, WEARABLE, "ZZZSILK"),
            )
        }
        # Everything except the silk pants is stocked by this shop.
        self.tradeable = [
            self.types[CORDUROY],
            self.types[CORDUROY_DELUXE],
            self.types[LEATHER],
            self.types[DAGGER],
        ]

        self._next_token = 9000
        self.char1.msg = MagicMock()

        patcher = patch("blockchain.xrpl.services.nft.NFTService")
        self.addCleanup(patcher.stop)
        patcher.start()

    # ── builders ─────────────────────────────────────────────────────

    def _make_item(self, key, type_name, typeclass=WEARABLE,
                   max_durability=20, durability=None, worn=False):
        """Create an NFT in char1's inventory, with its mirror row."""
        self._next_token += 1
        token_id = self._next_token

        item = create.create_object(typeclass, key=key, nohome=True)
        item.token_id = token_id
        item.max_durability = max_durability
        item.durability = max_durability if durability is None else durability
        item.move_to(self.char1, quiet=True)

        NFTGameState.objects.create(
            nftoken_id=str(token_id),
            taxon=1,
            location=NFTGameState.LOCATION_CHARACTER,
            character_key=self.char1.key,
            owner_in_game=WALLET_A,
            item_type=self.types[type_name],
        )

        if worn:
            slots = self.char1.db.wearslots
            slots[self._free_slot(slots)] = item
            self.char1.db.wearslots = slots

        return item

    def _free_slot(self, slots):
        for slot, occupant in slots.items():
            if occupant is None:
                return slot
        raise AssertionError("no free wearslot in the test fixture")

    def _find(self, term):
        return _find_inventory_item(self.char1, term, self.tradeable)


class TestWornCopiesAreNotCandidates(NFTShopMatchingTest):
    """Worn gear is still in ``contents`` — it must not win the match."""

    def test_unworn_copy_is_sold_while_an_identical_pair_is_worn(self):
        """The reported bug: three pairs, one worn, and the sale is refused."""
        worn = self._make_item("Brown Corduroy Pants", CORDUROY, worn=True)
        spare = self._make_item("Brown Corduroy Pants", CORDUROY)
        self._make_item("Brown Corduroy Pants", CORDUROY)

        item, item_type = self._find("brown corduroy pants")

        self.assertIsNotNone(item)
        self.assertIsNot(item, worn)
        self.assertEqual(item_type, self.types[CORDUROY])
        self.assertNotIn("Remove", _messages(self.char1))
        self.assertIn(item, (spare, self.char1.contents[-1]))

    def test_worn_exact_match_does_not_shadow_a_carried_partial(self):
        """An exact-named worn item must not hide a carried longer name."""
        self._make_item("Brown Corduroy Pants", CORDUROY, worn=True)
        deluxe = self._make_item(
            "Brown Corduroy Pants Deluxe", CORDUROY_DELUXE,
        )

        item, item_type = self._find("brown corduroy pants")

        self.assertIs(item, deluxe)
        self.assertEqual(item_type, self.types[CORDUROY_DELUXE])
        self.assertNotIn("Remove", _messages(self.char1))

    def test_only_copy_worn_asks_for_removal(self):
        """With nothing spare, the removal prompt is still the right answer."""
        self._make_item("Brown Corduroy Pants", CORDUROY, worn=True)

        item, item_type = self._find("brown corduroy pants")

        self.assertIsNone(item)
        self.assertIsNone(item_type)
        self.assertIn("Remove Brown Corduroy Pants", _messages(self.char1))


class TestNameDecidesAmbiguity(NFTShopMatchingTest):
    """Ambiguity is a question about the name, nothing else."""

    def test_two_identical_copies_are_not_ambiguous(self):
        """Functionally identical pants — sell either one, don't ask."""
        self._make_item("Brown Corduroy Pants", CORDUROY)
        self._make_item("Brown Corduroy Pants", CORDUROY)

        item, item_type = self._find("brown corduroy pants")

        self.assertIsNotNone(item)
        self.assertEqual(item_type, self.types[CORDUROY])
        self.assertNotIn("more specific", _messages(self.char1))

    def test_two_different_names_are_ambiguous(self):
        """'pants' matching two distinct items must ask which."""
        self._make_item("Brown Corduroy Pants", CORDUROY)
        self._make_item("Black Leather Pants", LEATHER)

        item, item_type = self._find("pants")

        self.assertIsNone(item)
        self.assertIsNone(item_type)
        self.assertIn("more specific", _messages(self.char1))

    def test_exact_name_wins_over_a_longer_partial_match(self):
        """Typing the full name of one item is never ambiguous."""
        plain = self._make_item("Brown Corduroy Pants", CORDUROY)
        self._make_item("Brown Corduroy Pants Deluxe", CORDUROY_DELUXE)

        item, item_type = self._find("brown corduroy pants")

        self.assertIs(item, plain)
        self.assertEqual(item_type, self.types[CORDUROY])
        self.assertNotIn("more specific", _messages(self.char1))

    def test_nothing_matching_the_name_says_so(self):
        self._make_item("Brown Corduroy Pants", CORDUROY)

        item, item_type = self._find("velvet cloak")

        self.assertIsNone(item)
        self.assertIsNone(item_type)
        self.assertIn("velvet cloak", _messages(self.char1))


class TestSellableCopyPreferred(NFTShopMatchingTest):
    """Same name, different condition — take the one that can be sold."""

    def test_damaged_copy_skipped_in_favour_of_the_pristine_one(self):
        """The damaged pair is first in inventory; the sale must not stall."""
        self._make_item("Brown Corduroy Pants", CORDUROY, durability=4)
        pristine = self._make_item("Brown Corduroy Pants", CORDUROY)

        item, item_type = self._find("brown corduroy pants")

        self.assertIs(item, pristine)
        self.assertEqual(item_type, self.types[CORDUROY])
        self.assertNotIn("damaged goods", _messages(self.char1))

    def test_every_copy_damaged_reports_the_damage(self):
        self._make_item("Brown Corduroy Pants", CORDUROY, durability=4)
        self._make_item("Brown Corduroy Pants", CORDUROY, durability=11)

        item, item_type = self._find("brown corduroy pants")

        self.assertIsNone(item)
        self.assertIsNone(item_type)
        self.assertIn("damaged goods", _messages(self.char1))

    def test_gem_inset_copy_skipped_in_favour_of_the_plain_one(self):
        inset = self._make_item("Training Dagger", DAGGER, typeclass=WEAPON)
        inset.is_inset = True
        plain = self._make_item("Training Dagger", DAGGER, typeclass=WEAPON)

        item, item_type = self._find("training dagger")

        self.assertIs(item, plain)
        self.assertEqual(item_type, self.types[DAGGER])
        self.assertNotIn("gem inset", _messages(self.char1))

    def test_only_copy_gem_inset_reports_the_inset(self):
        inset = self._make_item("Training Dagger", DAGGER, typeclass=WEAPON)
        inset.is_inset = True

        item, item_type = self._find("training dagger")

        self.assertIsNone(item)
        self.assertIsNone(item_type)
        self.assertIn("gem inset", _messages(self.char1))

    def test_worn_and_damaged_together_prefers_the_clean_spare(self):
        """Both filters at once — the one good pair still gets sold."""
        self._make_item("Brown Corduroy Pants", CORDUROY, worn=True)
        self._make_item("Brown Corduroy Pants", CORDUROY, durability=2)
        good = self._make_item("Brown Corduroy Pants", CORDUROY)

        item, _item_type = self._find("brown corduroy pants")

        self.assertIs(item, good)


class TestShopRefusals(NFTShopMatchingTest):
    """Refusals that belong to the shop, not the item's condition."""

    def test_type_this_shop_does_not_stock_is_refused(self):
        self._make_item("White Silk Pants", SILK)

        item, item_type = self._find("white silk pants")

        self.assertIsNone(item)
        self.assertIsNone(item_type)
        self.assertIn(SILK, _messages(self.char1))

    def test_item_without_a_mirror_row_is_refused(self):
        orphan = create.create_object(WEARABLE, key="Ghost Pants", nohome=True)
        orphan.token_id = 99999
        orphan.move_to(self.char1, quiet=True)

        item, item_type = self._find("ghost pants")

        self.assertIsNone(item)
        self.assertIsNone(item_type)
        self.assertIn("blockchain record", _messages(self.char1))
