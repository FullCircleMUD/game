"""
Tests for exit builder helpers.

evennia test --settings settings tests.utils_tests.test_exit_helpers
"""

from evennia.utils.test_resources import EvenniaTest

from utils.exit_helpers import (
    OPPOSITES,
    connect_bidirectional_exit,
    connect_bidirectional_door_exit,
    connect_bidirectional_trapped_door_exit,
    connect_bidirectional_tripwire_exit,
    connect_oneway_loopback_exit,
)


class TestConnectBidirectionalExit(EvenniaTest):
    """Test connect_bidirectional_exit helper."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def test_creates_two_exits(self):
        """Should create exits in both directions."""
        exit_ab, exit_ba = connect_bidirectional_exit(
            self.room1, self.room2, "east"
        )
        self.assertEqual(exit_ab.location, self.room1)
        self.assertEqual(exit_ab.destination, self.room2)
        self.assertEqual(exit_ba.location, self.room2)
        self.assertEqual(exit_ba.destination, self.room1)

    def test_sets_directions(self):
        """Should set correct directions on both exits."""
        exit_ab, exit_ba = connect_bidirectional_exit(
            self.room1, self.room2, "north"
        )
        self.assertEqual(exit_ab.db.direction, "north")
        self.assertEqual(exit_ba.db.direction, "south")

    def test_default_keys_use_room_names(self):
        """Exit keys should default to destination room names."""
        exit_ab, exit_ba = connect_bidirectional_exit(
            self.room1, self.room2, "east"
        )
        self.assertEqual(exit_ab.key, self.room2.key)
        self.assertEqual(exit_ba.key, self.room1.key)

    def test_custom_descriptions(self):
        """Should use custom descriptions when provided."""
        exit_ab, exit_ba = connect_bidirectional_exit(
            self.room1, self.room2, "east",
            desc_ab="A dark tunnel", desc_ba="A bright opening",
        )
        self.assertEqual(exit_ab.key, "A dark tunnel")
        self.assertEqual(exit_ba.key, "A bright opening")


class TestConnectBidirectionalDoorExit(EvenniaTest):
    """Test connect_bidirectional_door_exit helper."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def test_creates_linked_door_pair(self):
        """Should create two linked ExitDoor objects."""
        door_ab, door_ba = connect_bidirectional_door_exit(
            self.room1, self.room2, "south", key="an oak door"
        )
        self.assertEqual(door_ab.location, self.room1)
        self.assertEqual(door_ab.destination, self.room2)
        self.assertEqual(door_ba.location, self.room2)
        self.assertEqual(door_ba.destination, self.room1)
        # Both should have the same key
        self.assertEqual(door_ab.key, "an oak door")
        self.assertEqual(door_ba.key, "an oak door")

    def test_doors_start_closed(self):
        """Doors should default to closed."""
        door_ab, door_ba = connect_bidirectional_door_exit(
            self.room1, self.room2, "south"
        )
        self.assertFalse(door_ab.is_open)
        self.assertFalse(door_ba.is_open)

    def test_locked_door(self):
        """Should create locked doors when is_locked=True."""
        door_ab, door_ba = connect_bidirectional_door_exit(
            self.room1, self.room2, "south", is_locked=True, lock_dc=20
        )
        self.assertTrue(door_ab.is_locked)
        self.assertTrue(door_ba.is_locked)
        self.assertEqual(door_ab.lock_dc, 20)

    def test_door_name(self):
        """Should set findable door_name."""
        door_ab, _ = connect_bidirectional_door_exit(
            self.room1, self.room2, "south", door_name="gate"
        )
        self.assertEqual(door_ab.door_name, "gate")


class TestConnectBidirectionalTrappedDoorExit(EvenniaTest):
    """Test connect_bidirectional_trapped_door_exit helper."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def test_trap_on_ab_side(self):
        """Default trap_side='ab' should trap the A→B door."""
        door_ab, door_ba = connect_bidirectional_trapped_door_exit(
            self.room1, self.room2, "west",
            trap_find_dc=12, trap_damage_dice="2d6",
            trap_description="a poison needle",
        )
        # A→B side is trapped
        self.assertTrue(door_ab.is_trapped)
        self.assertTrue(door_ab.trap_armed)
        self.assertEqual(door_ab.trap_find_dc, 12)
        self.assertEqual(door_ab.trap_damage_dice, "2d6")
        # B→A side is safe
        self.assertFalse(getattr(door_ba, "is_trapped", False))

    def test_trap_on_ba_side(self):
        """trap_side='ba' should trap the B→A door."""
        door_ab, door_ba = connect_bidirectional_trapped_door_exit(
            self.room1, self.room2, "west",
            trap_side="ba", trap_find_dc=10,
        )
        self.assertFalse(getattr(door_ab, "is_trapped", False))
        self.assertTrue(door_ba.is_trapped)
        self.assertEqual(door_ba.trap_find_dc, 10)

    def test_trap_effect_key(self):
        """Should set named effect on the trapped door."""
        door_ab, _ = connect_bidirectional_trapped_door_exit(
            self.room1, self.room2, "west",
            trap_effect_key="poisoned",
            trap_effect_duration=3,
            trap_effect_duration_type="combat_rounds",
        )
        self.assertEqual(door_ab.trap_effect_key, "poisoned")
        self.assertEqual(door_ab.trap_effect_duration, 3)


class TestConnectBidirectionalTripwireExit(EvenniaTest):
    """Test connect_bidirectional_tripwire_exit helper."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def test_creates_bidirectional_exits(self):
        """Should create exits in both directions."""
        exit_ab, exit_ba = connect_bidirectional_tripwire_exit(
            self.room1, self.room2, "north",
            trap_find_dc=10,
        )
        self.assertEqual(exit_ab.location, self.room1)
        self.assertEqual(exit_ab.destination, self.room2)
        self.assertEqual(exit_ba.location, self.room2)
        self.assertEqual(exit_ba.destination, self.room1)

    def test_trap_on_ab_side_only(self):
        """Default trap_side='ab' traps A→B, B→A is a plain exit."""
        exit_ab, exit_ba = connect_bidirectional_tripwire_exit(
            self.room1, self.room2, "north",
            trap_find_dc=14, trap_damage_dice="1d8",
            trap_description="a nearly invisible wire",
        )
        # A→B is the tripwire
        self.assertTrue(exit_ab.is_trapped)
        self.assertTrue(exit_ab.trap_armed)
        self.assertEqual(exit_ab.trap_find_dc, 14)
        self.assertEqual(exit_ab.trap_damage_dice, "1d8")
        self.assertEqual(exit_ab.trap_description, "a nearly invisible wire")
        # B→A is plain
        self.assertFalse(getattr(exit_ba, "is_trapped", False))

    def test_trap_on_ba_side(self):
        """trap_side='ba' should trap B→A instead."""
        exit_ab, exit_ba = connect_bidirectional_tripwire_exit(
            self.room1, self.room2, "north",
            trap_side="ba", trap_find_dc=12,
        )
        self.assertFalse(getattr(exit_ab, "is_trapped", False))
        self.assertTrue(exit_ba.is_trapped)

    def test_default_keys_use_room_names(self):
        """Exit keys should default to destination room names."""
        exit_ab, exit_ba = connect_bidirectional_tripwire_exit(
            self.room1, self.room2, "east",
        )
        self.assertEqual(exit_ab.key, self.room2.key)
        self.assertEqual(exit_ba.key, self.room1.key)

    def test_one_shot_default(self):
        """Tripwire should default to one-shot."""
        exit_ab, _ = connect_bidirectional_tripwire_exit(
            self.room1, self.room2, "north",
        )
        self.assertTrue(exit_ab.trap_one_shot)


class TestConnectOnewayLoopbackExit(EvenniaTest):
    """Test connect_oneway_loopback_exit helper."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def test_loops_back_to_same_room(self):
        """Exit destination should be the same as its location."""
        exit_obj = connect_oneway_loopback_exit(self.room1, "west")
        self.assertEqual(exit_obj.location, self.room1)
        self.assertEqual(exit_obj.destination, self.room1)

    def test_sets_direction(self):
        """Should set the correct direction."""
        exit_obj = connect_oneway_loopback_exit(self.room1, "south")
        self.assertEqual(exit_obj.db.direction, "south")

    def test_default_key_uses_room_name(self):
        """Key should default to room's name."""
        exit_obj = connect_oneway_loopback_exit(self.room1, "west")
        self.assertEqual(exit_obj.key, self.room1.key)

    def test_custom_key(self):
        """Should use custom key when provided."""
        exit_obj = connect_oneway_loopback_exit(
            self.room1, "west", key="Dense Forest"
        )
        self.assertEqual(exit_obj.key, "Dense Forest")

    def test_only_creates_one_exit(self):
        """Should only create one exit, not a pair."""
        before = len([
            obj for obj in self.room1.exits
        ])
        connect_oneway_loopback_exit(self.room1, "west")
        after = len([
            obj for obj in self.room1.exits
        ])
        self.assertEqual(after - before, 1)


class TestOpposites(EvenniaTest):
    """Test the OPPOSITES direction mapping."""

    def create_script(self):
        pass

    def test_all_cardinal_directions(self):
        self.assertEqual(OPPOSITES["north"], "south")
        self.assertEqual(OPPOSITES["south"], "north")
        self.assertEqual(OPPOSITES["east"], "west")
        self.assertEqual(OPPOSITES["west"], "east")

    def test_diagonal_directions(self):
        self.assertEqual(OPPOSITES["northeast"], "southwest")
        self.assertEqual(OPPOSITES["northwest"], "southeast")

    def test_vertical_directions(self):
        self.assertEqual(OPPOSITES["up"], "down")
        self.assertEqual(OPPOSITES["down"], "up")

    def test_in_out(self):
        self.assertEqual(OPPOSITES["in"], "out")
        self.assertEqual(OPPOSITES["out"], "in")
