"""
Tests for put/get container commands with prepositions.

Put requires 'in' preposition. Get supports optional 'from' preposition.
"""

from unittest.mock import patch

from evennia.utils.test_resources import EvenniaCommandTest
from evennia.utils import create

from commands.all_char_cmds.cmd_put import CmdPut
from commands.all_char_cmds.cmd_override_get import CmdGet

WALLET_A = "0xAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"


class PutGetNoPrepositionBase(EvenniaCommandTest):

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)
        # Container in inventory
        self.backpack = create.create_object(
            "typeclasses.items.containers.container_nft_item.ContainerNFTItem",
            key="leather backpack",
            location=self.char1,
            nohome=True,
        )
        self.backpack.max_container_capacity_kg = 50.0

    def _make_item(self, key="iron sword", location=None):
        return create.create_object(
            "evennia.objects.objects.DefaultObject",
            key=key,
            location=location or self.char1,
            nohome=True,
        )


# ------------------------------------------------------------------ #
#  CmdPut without "in"
# ------------------------------------------------------------------ #


class TestCmdPutPreposition(PutGetNoPrepositionBase):

    def setUp(self):
        super().setUp()
        self.room1.always_lit = True

    def test_put_with_preposition(self):
        """'put sword in backpack' works."""
        sword = self._make_item(key="iron sword", location=self.char1)
        self.call(CmdPut(), "iron sword in backpack", "You put iron sword in leather backpack.")
        self.assertEqual(sword.location, self.backpack)

    def test_put_without_preposition_shows_usage(self):
        """'put sword backpack' without 'in' shows usage error."""
        self._make_item(key="iron sword", location=self.char1)
        self.call(CmdPut(), "iron sword backpack", "Usage: put <item> in <container>")

    def test_put_single_word_shows_usage(self):
        """'put sword' with no container gives usage error."""
        self._make_item(key="iron sword", location=self.char1)
        self.call(CmdPut(), "sword", "Usage: put <item> in <container>")

    def test_put_no_args(self):
        """'put' with no args gives error."""
        self.call(CmdPut(), "", "Put what where?")

    def test_put_room_container(self):
        """'put sword in backpack' works with container in room."""
        self.backpack.move_to(self.room1, quiet=True)
        sword = self._make_item(key="iron sword", location=self.char1)
        self.call(CmdPut(), "iron sword in backpack", "You put iron sword in leather backpack.")
        self.assertEqual(sword.location, self.backpack)

    # --- Stowing by touch ---
    #
    # Both halves are found by feel: your own pack, and a container in
    # the room, which is the same chest `open` already lets you work by
    # touch. One fumble covers the whole action.

    def _darken(self):
        self.room1.always_lit = False
        self.room1.natural_light = False

    def _put_blind(self, args="iron sword in backpack"):
        """Call put while sightless, returning (output, completion)."""
        self._darken()
        with patch("utils.busy.delay") as mock_delay:
            out = self.call(CmdPut(), args)
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

    def test_putting_in_the_dark_announces_the_fumble(self):
        self._make_item(key="iron sword", location=self.char1)
        out, _ = self._put_blind()
        self.assertIn("feeling for somewhere to put it", out)

    def test_putting_in_the_dark_succeeds_after_the_fumble(self):
        sword = self._make_item(key="iron sword", location=self.char1)
        _, complete = self._put_blind()
        complete()
        self.assertEqual(sword.location, self.backpack)

    def test_a_room_container_works_the_same_way(self):
        """The same chest `open` works by touch — one behaviour, not two."""
        self.backpack.move_to(self.room1, quiet=True)
        sword = self._make_item(key="iron sword", location=self.char1)
        _, complete = self._put_blind()
        complete()
        self.assertEqual(sword.location, self.backpack)

    def test_nothing_moves_until_the_fumble_ends(self):
        sword = self._make_item(key="iron sword", location=self.char1)
        self._put_blind()
        self.assertEqual(sword.location, self.char1)

    def test_a_missing_container_is_searched_for_first(self):
        """The search gives nothing away — you fumble, then find out."""
        self._make_item(key="iron sword", location=self.char1)
        out, complete = self._put_blind("iron sword in barrel")
        self.assertIn("feeling for somewhere to put it", out)
        self.assertNotIn("don't see", out)
        self.assertIn("don't see 'barrel'", self._finish(complete))

    def test_a_blinded_character_fumbles_too(self):
        from enums.condition import Condition

        self.char1.add_condition(Condition.BLINDED)
        self._make_item(key="iron sword", location=self.char1)
        with patch("utils.busy.delay") as mock_delay:
            out = self.call(CmdPut(), "iron sword in backpack")
        self.assertIn("feeling for somewhere to put it", out)
        self.assertTrue(mock_delay.called)

    def test_darkvision_puts_normally(self):
        from enums.condition import Condition

        self._darken()
        self.char1.add_condition(Condition.DARKVISION)
        sword = self._make_item(key="iron sword", location=self.char1)
        result = self.call(CmdPut(), "iron sword in backpack")
        self.assertNotIn("feeling for somewhere", result)
        self.assertEqual(sword.location, self.backpack)

    def test_putting_when_sighted_does_not_fumble(self):
        self._make_item(key="iron sword", location=self.char1)
        result = self.call(CmdPut(), "iron sword in backpack")
        self.assertNotIn("fumble", result)

    def test_putting_is_refused_while_busy(self):
        self._make_item(key="iron sword", location=self.char1)
        self.char1.ndb.is_processing = True
        self.call(CmdPut(), "iron sword in backpack", "You are busy.")


# ------------------------------------------------------------------ #
#  CmdGet without "from"
# ------------------------------------------------------------------ #


class TestCmdGetNoPreposition(PutGetNoPrepositionBase):

    def test_get_without_preposition(self):
        """'get sword backpack' works like 'get sword from backpack'."""
        sword = self._make_item(key="iron sword", location=self.backpack)
        self.call(CmdGet(), "iron sword backpack", "You get iron sword from leather backpack.")
        self.assertEqual(sword.location, self.char1)

    def test_get_with_preposition_still_works(self):
        """'get sword from backpack' still works (no regression)."""
        sword = self._make_item(key="iron sword", location=self.backpack)
        self.call(CmdGet(), "iron sword from backpack", "You get iron sword from leather backpack.")
        self.assertEqual(sword.location, self.char1)

    def test_get_room_pickup_still_works(self):
        """'get sword' still picks up from room (no regression)."""
        sword = self._make_item(key="iron sword", location=self.room1)
        self.call(CmdGet(), "iron sword", "You pick up")
        self.assertEqual(sword.location, self.char1)

    def test_get_single_word_no_container_fallthrough(self):
        """'get sword' with no container falls through to room pickup."""
        sword = self._make_item(key="iron sword", location=self.room1)
        result = self.call(CmdGet(), "iron sword", "You pick up")
        # Confirm it didn't try container path
        self.assertNotIn("from", result.lower())

    def test_get_no_args(self):
        """'get' with no args gives error."""
        self.call(CmdGet(), "", "Get what?")
