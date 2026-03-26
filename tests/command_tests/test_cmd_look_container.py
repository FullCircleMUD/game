"""
Tests for ``look in <container>`` — container content inspection.
"""

from evennia.utils.test_resources import EvenniaCommandTest
from evennia.utils import create

from commands.all_char_cmds.cmd_override_look import CmdLook


class TestCmdLookInContainer(EvenniaCommandTest):

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.room1.always_lit = True

    # ------------------------------------------------------------------ #
    #  Helpers
    # ------------------------------------------------------------------ #

    def _make_container(self, key="leather backpack", location=None):
        container = create.create_object(
            "typeclasses.items.containers.container_nft_item.ContainerNFTItem",
            key=key,
            location=location or self.char1,
            nohome=True,
        )
        container.max_container_capacity_kg = 15.0
        return container

    def _make_chest(self, is_open=False):
        chest = create.create_object(
            "typeclasses.world_objects.chest.WorldChest",
            key="iron chest",
            location=self.room1,
            nohome=True,
        )
        chest.is_open = is_open
        return chest

    def _make_item(self, key="iron sword", location=None):
        return create.create_object(
            "evennia.objects.objects.DefaultObject",
            key=key,
            location=location,
            nohome=True,
        )

    # ------------------------------------------------------------------ #
    #  Tests
    # ------------------------------------------------------------------ #

    def test_look_in_container_shows_contents(self):
        """Items inside a container are listed."""
        bag = self._make_container()
        self._make_item(key="iron sword", location=bag)
        self.call(CmdLook(), "in leather backpack", "leather backpack")

    def test_look_in_empty_container(self):
        """Empty container shows 'Empty.'"""
        self._make_container()
        result = self.call(CmdLook(), "in leather backpack", "leather backpack")
        self.assertIn("Empty.", result)

    def test_look_in_closed_chest(self):
        """Closed chest cannot be inspected."""
        self._make_chest(is_open=False)
        self.call(CmdLook(), "in iron chest", "iron chest is closed.")

    def test_look_in_open_chest(self):
        """Open chest shows contents."""
        chest = self._make_chest(is_open=True)
        self._make_item(key="gold ring", location=chest)
        self.call(CmdLook(), "in iron chest", "iron chest")

    def test_look_in_not_container(self):
        """Non-container item gives error."""
        self._make_item(key="iron sword", location=self.room1)
        self.call(CmdLook(), "in iron sword", "iron sword is not a container.")

    def test_look_in_nonexistent(self):
        """Missing target gives error."""
        self.call(CmdLook(), "in nothing", "You don't see 'nothing' here.")

    def test_look_in_container_with_gold(self):
        """Container with gold shows gold line."""
        bag = self._make_container()
        bag.db.gold = 50
        result = self.call(CmdLook(), "in leather backpack", "leather backpack")
        self.assertIn("Gold", result)

    def test_look_without_in_still_works(self):
        """Plain 'look <obj>' still works (no regression)."""
        self._make_item(key="iron sword", location=self.room1)
        self.call(CmdLook(), "iron sword", "iron sword")

    def test_look_in_room_container(self):
        """Can look in a container in the room, not just inventory."""
        bag = self._make_container(location=self.room1)
        self._make_item(key="gold ring", location=bag)
        self.call(CmdLook(), "in leather backpack", "leather backpack")
