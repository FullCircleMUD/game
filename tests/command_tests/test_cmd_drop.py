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
        self.call(CmdDrop(), "50 gold", "You aren't carrying 'gold'.")


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
        self.call(CmdDrop(), "5 wheat", "You aren't carrying 'wheat'.")


class TestCmdDropObject(EvenniaCommandTest):
    """Test dropping NFT objects (standard Evennia drop)."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.room1.always_lit = True
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
        self.call(CmdDrop(), "banana", "You aren't carrying 'banana'.")

    def test_drop_object_empty_inventory(self):
        """drop X when inventory is empty should still show the error.

        Regression test for the resolve_item_in_source short-circuit
        bug: the helper used to return None without calling
        caller.search when walk_contents produced an empty candidate
        list, which silently suppressed nofound_string and left the
        player with no error message. This test locks in the fix by
        forcing the empty-candidates path (delete the sword fixture
        first so inventory contains nothing) and asserting that the
        nofound_string still fires.
        """
        self.sword.delete()
        self.call(CmdDrop(), "banana", "You aren't carrying 'banana'.")

    # --- Dropping by touch ---
    #
    # Your own pack is found by feel, so darkness costs the time spent
    # searching rather than the action.

    def _drop_blind(self, args="sword"):
        """Call drop while sightless, returning (output, completion)."""
        self.room1.always_lit = False
        self.room1.natural_light = False
        with patch("utils.busy.delay") as mock_delay:
            out = self.call(CmdDrop(), args)
        # delay(interval, _tick, step) — the callback is bound to its step
        delayed = mock_delay.call_args[0] if mock_delay.call_args else None
        complete = (lambda: delayed[1](*delayed[2:])) if delayed else None
        return out, complete

    def _finish(self, complete):
        """Run the deferred completion, collecting what the caller hears."""
        said = []
        self.char1.msg = lambda text="", **kwargs: said.append(str(text))
        complete()
        return " ".join(said)

    def test_dropping_in_the_dark_announces_the_fumble(self):
        out, _ = self._drop_blind()
        self.assertIn("fumble blindly through your pack", out)

    def test_dropping_in_the_dark_succeeds_after_the_fumble(self):
        _, complete = self._drop_blind()
        complete()
        self.assertEqual(self.sword.location, self.room1)

    def test_nothing_is_dropped_until_the_fumble_ends(self):
        self._drop_blind()
        self.assertEqual(self.sword.location, self.char1)

    def test_a_missing_item_is_searched_for_first(self):
        """The search gives nothing away — you fumble, then find out."""
        out, complete = self._drop_blind("banana")
        self.assertIn("fumble blindly through your pack", out)
        self.assertNotIn("aren't carrying", out)
        self.assertIn("aren't carrying 'banana'", self._finish(complete))

    def test_dropping_when_sighted_does_not_fumble(self):
        result = self.call(CmdDrop(), "sword")
        self.assertNotIn("fumble", result)

    def test_dropping_is_refused_while_busy(self):
        self.char1.ndb.is_processing = True
        self.call(CmdDrop(), "sword", "You are busy.")

    def test_drop_world_anchored_nft_item(self):
        """drop should refuse to drop an WorldAnchoredNFTItem."""
        mount = create.create_object(
            "typeclasses.items.untakeables.world_anchored_nft_item.WorldAnchoredNFTItem",
            key="horse",
            nohome=True,
        )
        mount.db_location = self.char1
        mount.save(update_fields=["db_location"])
        self.char1.contents_cache.init()  # the direct write bypasses the cache
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


class TestCmdDropAmbiguousName(EvenniaCommandTest):
    """How many items one name should drop, and when to ask instead.

    Identical copies are an answer — drop one. Two different items that
    happen to share a word are a question, and dropping either without
    asking loses the player something they did not name. Neither case
    had a test, which is how the count was free to change unnoticed.
    """

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"
    databases = "__all__"  # parse_item_args queries the xrpl alias

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.room1.always_lit = True

    def _carry(self, key, worn=False):
        item = create.create_object(
            "evennia.objects.objects.DefaultObject",
            key=key,
            location=self.char1,
        )
        if worn:
            slots = self.char1.db.wearslots
            free = next(s for s, occupant in slots.items() if occupant is None)
            slots[free] = item
            self.char1.db.wearslots = slots
        return item

    def _dropped(self, *items):
        return [i for i in items if i.location == self.room1]

    def test_one_match_is_dropped(self):
        cap = self._carry("faded cap")
        self.call(CmdDrop(), "faded cap")
        self.assertEqual(self._dropped(cap), [cap])

    def test_two_identical_copies_drop_exactly_one(self):
        first = self._carry("faded cap")
        second = self._carry("faded cap")
        self.call(CmdDrop(), "faded cap")
        self.assertEqual(len(self._dropped(first, second)), 1)

    def test_two_distinct_matches_ask_which(self):
        leather = self._carry("faded cap")
        iron = self._carry("spotted cap")
        self.call(CmdDrop(), "cap", "More than one match")
        self.assertEqual(self._dropped(leather, iron), [])

    def test_exact_name_beats_a_longer_partial(self):
        plain = self._carry("faded cap")
        warding = self._carry("faded cap of warding")
        self.call(CmdDrop(), "faded cap")
        self.assertEqual(self._dropped(plain, warding), [plain])

    def test_a_count_on_an_item_is_refused(self):
        """Only fungibles stack. Every NFT carries its own token_id, so
        two caps are two things, not a pile of two."""
        caps = [self._carry("faded cap") for _ in range(3)]
        self.call(CmdDrop(), "2 faded cap")
        self.assertEqual(self._dropped(*caps), [])

    def test_all_of_an_item_is_refused_the_same_way(self):
        caps = [self._carry("faded cap") for _ in range(3)]
        self.call(CmdDrop(), "all faded cap")
        self.assertEqual(self._dropped(*caps), [])

    def test_a_refused_count_says_so_before_searching(self):
        """The refusal is about the request, so an ambiguous name or a
        name that matches nothing changes none of it."""
        self._carry("faded cap")
        self._carry("spotted cap")
        result = self.call(CmdDrop(), "2 cap")
        self.assertNotIn("More than one match", result)

    def test_a_count_still_works_on_a_fungible(self):
        """The rule is about what stacks, not about counting itself."""
        self.char1.db.resources = {1: 20}  # wheat
        with patch("blockchain.xrpl.services.resource.ResourceService.drop"):
            self.call(CmdDrop(), "5 wheat")
        self.assertEqual(self.char1.get_resource(1), 15)

    def test_a_worn_copy_is_kept_and_the_carried_one_dropped(self):
        worn = self._carry("faded cap", worn=True)
        carried = self._carry("faded cap")
        self.call(CmdDrop(), "faded cap")
        self.assertEqual(self._dropped(worn, carried), [carried])

    def test_only_a_worn_match_asks_for_removal(self):
        worn = self._carry("faded cap", worn=True)
        self.call(CmdDrop(), "faded cap", "You'll have to remove")
        self.assertEqual(self._dropped(worn), [])


class TestFungibleVersusItemName(EvenniaCommandTest):
    """Choosing between a resource and an item whose name starts with it.

    "leather" is a resource, and plenty of items are named after it. A
    player typing "leather cap" wants the cap; matching the first word
    against the resource table and discarding the rest answers "you
    don't have any Leather" and leaves the cap unreachable by the only
    name it has.

    The chain: a name that is the resource, whole or partial, is the
    resource — but only if the character actually holds some. A name
    that goes past the resource is an item name, and never falls back
    to the resource, because the extra words said what was meant.
    """

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"
    databases = "__all__"

    LEATHER = 9

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)
        self.room1.always_lit = True
        self.char1.db.gold = 0
        self.char1.db.resources = {}
        self.room1.db.gold = 0
        self.room1.db.resources = {}

    def _hold_leather(self, amount=10):
        self.char1.db.resources = {self.LEATHER: amount}

    def _carry(self, key):
        return create.create_object(
            "evennia.objects.objects.DefaultObject",
            key=key,
            location=self.char1,
        )

    @patch("blockchain.xrpl.services.resource.ResourceService.drop")
    def test_the_resource_name_drops_the_resource_when_held(self, _mock):
        self._hold_leather()
        self.call(CmdDrop(), "leather")
        self.assertEqual(self.char1.get_resource(self.LEATHER), 9)

    @patch("blockchain.xrpl.services.resource.ResourceService.drop")
    def test_a_partial_resource_name_drops_the_resource_when_held(self, _mock):
        self._hold_leather()
        self.call(CmdDrop(), "leat")
        self.assertEqual(self.char1.get_resource(self.LEATHER), 9)

    def test_the_resource_name_finds_the_item_when_no_resource_is_held(self):
        cap = self._carry("leather cap")
        self.call(CmdDrop(), "leather")
        self.assertEqual(cap.location, self.room1)

    def test_a_partial_resource_name_finds_the_item_when_none_is_held(self):
        cap = self._carry("leather cap")
        self.call(CmdDrop(), "leat")
        self.assertEqual(cap.location, self.room1)

    def test_a_longer_name_takes_the_item_over_the_held_resource(self):
        self._hold_leather()
        cap = self._carry("leather cap")
        self.call(CmdDrop(), "leather cap")
        self.assertEqual(cap.location, self.room1)
        self.assertEqual(self.char1.get_resource(self.LEATHER), 10)

    def test_a_longer_name_does_not_fall_back_to_the_resource(self):
        """No cap to find — say so, don't quietly drop leather instead."""
        self._hold_leather()
        self.call(CmdDrop(), "leather cap")
        self.assertEqual(self.char1.get_resource(self.LEATHER), 10)

    def test_two_matching_items_and_no_resource_asks_which(self):
        cap = self._carry("leather cap")
        armour = self._carry("leather armour")
        self.call(CmdDrop(), "leather", "More than one match")
        self.assertEqual(cap.location, self.char1)
        self.assertEqual(armour.location, self.char1)
