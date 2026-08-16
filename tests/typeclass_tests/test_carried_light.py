"""
Tests for carried light lighting the room.

Light is a property of the room, not of the person holding it. A torch
in a hand lights the place for everyone standing there, exactly as a
dropped one does — otherwise four players in a dungeon with one lantern
between them leave three in the dark.

evennia test --settings settings tests.typeclass_tests.test_carried_light
"""

from evennia.utils.test_resources import EvenniaTest
from evennia.utils import create


class CarriedLightTest(EvenniaTest):
    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"
    character_typeclass = "typeclasses.actors.character.FCMCharacter"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.room1.always_lit = False
        self.room1.natural_light = False

    def _torch(self, location, lit=True):
        torch = create.create_object(
            "typeclasses.items.holdables.torch_nft_item.TorchNFTItem",
            key="torch",
            location=location,
            nohome=True,
        )
        torch.is_lit = lit
        return torch

    # ── The room is the unit of light ─────────────────────────────

    def test_an_empty_dark_room_is_dark(self):
        self.assertTrue(self.room1.is_dark(self.char1))

    def test_a_dropped_torch_lights_the_room(self):
        self._torch(self.room1)
        self.assertFalse(self.room1.is_dark(self.char1))

    def test_a_carried_torch_lights_the_room_for_its_bearer(self):
        self._torch(self.char1)
        self.assertFalse(self.room1.is_dark(self.char1))

    def test_a_carried_torch_lights_the_room_for_everyone_else(self):
        """The point of the change — one lantern between four."""
        self._torch(self.char1)
        self.assertFalse(self.room1.is_dark(self.char2))

    def test_an_unlit_torch_lights_nothing(self):
        self._torch(self.char1, lit=False)
        self.assertTrue(self.room1.is_dark(self.char2))

    def test_a_torch_carried_elsewhere_lights_nothing(self):
        """char2 and their torch are in room2."""
        self.char2.location = self.room2
        self._torch(self.char2)
        self.assertTrue(self.room1.is_dark(self.char1))

    # ── What the one-level, p_living gate excludes ────────────────

    def test_a_torch_shut_in_a_container_lights_nothing(self):
        chest = create.create_object(
            "typeclasses.world_objects.base_world_item.WorldItem",
            key="chest",
            location=self.room1,
            nohome=True,
        )
        self._torch(chest)
        self.assertTrue(self.room1.is_dark(self.char1))

    def test_a_torch_on_a_corpse_lights_nothing_until_looted(self):
        """A body has contents but no hp, so p_living excludes it."""
        self.char2.hp = 0
        self._torch(self.char2)
        self.assertTrue(self.room1.is_dark(self.char1))

    def test_looting_that_torch_lights_the_room(self):
        self.char2.hp = 0
        torch = self._torch(self.char2)
        self.assertTrue(self.room1.is_dark(self.char1))
        torch.location = self.char1
        self.assertFalse(self.room1.is_dark(self.char1))
