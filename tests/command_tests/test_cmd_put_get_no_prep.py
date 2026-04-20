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
