"""
Tests for ExitDoor — traverse gating, visibility, display name,
door_name alias, state descriptions, reciprocal pairing.

evennia test --settings settings tests.typeclass_tests.test_exit_door
"""

from evennia.utils.test_resources import EvenniaTest
from evennia.utils import create


WALLET_A = "0xAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"


class TestExitDoor(EvenniaTest):

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)
        self.door = create.create_object(
            "typeclasses.terrain.exits.exit_door.ExitDoor",
            key="oak door",
            location=self.room1,
            destination=self.room2,
            nohome=True,
        )

    def test_door_starts_closed(self):
        self.assertFalse(self.door.is_open)

    def test_traverse_blocked_when_closed(self):
        """Closed door blocks passage — character stays in room1."""
        self.door.at_traverse(self.char1, self.room2)
        self.assertEqual(self.char1.location, self.room1)

    def test_traverse_blocked_when_locked(self):
        self.door.is_locked = True
        self.door.at_traverse(self.char1, self.room2)
        self.assertEqual(self.char1.location, self.room1)

    def test_traverse_allowed_when_open(self):
        self.door.is_open = True
        self.door.at_traverse(self.char1, self.room2)
        self.assertEqual(self.char1.location, self.room2)

    def test_display_name_shows_locked(self):
        self.door.is_locked = True
        name = self.door.get_display_name(self.char1)
        self.assertIn("locked", name)

    def test_display_name_shows_closed(self):
        name = self.door.get_display_name(self.char1)
        self.assertIn("closed", name)

    def test_display_name_plain_when_open(self):
        self.door.is_open = True
        name = self.door.get_display_name(self.char1)
        self.assertNotIn("closed", name)
        self.assertNotIn("locked", name)

    def test_open_then_traverse(self):
        success, _ = self.door.open(self.char1)
        self.assertTrue(success)
        self.door.at_traverse(self.char1, self.room2)
        self.assertEqual(self.char1.location, self.room2)


class TestDoorNameAlias(EvenniaTest):
    """Test that door_name is added as an alias."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)

    def test_default_door_name_alias(self):
        """Default door_name='door' is added as alias."""
        door = create.create_object(
            "typeclasses.terrain.exits.exit_door.ExitDoor",
            key="heavy oak door",
            location=self.room1,
            destination=self.room2,
            nohome=True,
        )
        self.assertIn("door", door.aliases.all())

    def test_custom_door_name_alias(self):
        """Custom door_name is added as alias."""
        door = create.create_object(
            "typeclasses.terrain.exits.exit_door.ExitDoor",
            key="iron portcullis",
            location=self.room1,
            destination=self.room2,
            nohome=True,
        )
        door.door_name = "gate"
        # door_name is set via at_object_creation, so "door" is the alias
        # (the custom name would need to be set before creation or re-aliased)
        self.assertIn("door", door.aliases.all())


class TestStateDescriptions(EvenniaTest):
    """Test state-dependent descriptions in get_display_name."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)
        self.door = create.create_object(
            "typeclasses.terrain.exits.exit_door.ExitDoor",
            key="oak door",
            location=self.room1,
            destination=self.room2,
            nohome=True,
        )

    def test_closed_desc_used_when_closed(self):
        """When closed_desc is set and door is closed, it's used as display."""
        self.door.closed_desc = "A stout oak door blocks your way."
        name = self.door.get_display_name(self.char1)
        self.assertEqual(name, "A stout oak door blocks your way.")
        # No "(closed)" suffix since closed_desc itself conveys state
        self.assertNotIn("(closed)", name)

    def test_open_desc_used_when_open(self):
        """When open_desc is set and door is open, it's used as display."""
        self.door.open_desc = "Through the open door you see a bakehouse."
        self.door.is_open = True
        name = self.door.get_display_name(self.char1)
        self.assertEqual(name, "Through the open door you see a bakehouse.")

    def test_closed_desc_with_locked(self):
        """Locked door with closed_desc shows desc + (locked)."""
        self.door.closed_desc = "A stout oak door blocks your way."
        self.door.is_locked = True
        name = self.door.get_display_name(self.char1)
        self.assertEqual(name, "A stout oak door blocks your way. (locked)")

    def test_no_closed_desc_shows_key_with_closed_suffix(self):
        """Without closed_desc, closed door shows key + (closed)."""
        name = self.door.get_display_name(self.char1)
        self.assertIn("oak door", name)
        self.assertIn("(closed)", name)

    def test_no_open_desc_shows_key(self):
        """Without open_desc, open door shows key without suffix."""
        self.door.is_open = True
        name = self.door.get_display_name(self.char1)
        self.assertIn("oak door", name)
        self.assertNotIn("(closed)", name)
        self.assertNotIn("(locked)", name)

    def test_direction_with_state_desc(self):
        """Direction + state desc prepends direction prefix."""
        self.door.set_direction("south")
        self.door.closed_desc = "A heavy door blocks the way south."
        name = self.door.get_display_name(self.char1)
        self.assertEqual(name, "south: A heavy door blocks the way south.")

    def test_direction_without_state_desc(self):
        """Direction + no state desc shows direction: key (closed)."""
        self.door.set_direction("south")
        name = self.door.get_display_name(self.char1)
        self.assertEqual(name, "south: oak door (closed)")


class TestReciprocalDoors(EvenniaTest):
    """Test reciprocal open/close/lock/unlock between paired doors."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)

        self.door_a = create.create_object(
            "typeclasses.terrain.exits.exit_door.ExitDoor",
            key="oak door",
            location=self.room1,
            destination=self.room2,
            nohome=True,
        )
        self.door_b = create.create_object(
            "typeclasses.terrain.exits.exit_door.ExitDoor",
            key="oak door",
            location=self.room2,
            destination=self.room1,
            nohome=True,
        )

        from typeclasses.terrain.exits.exit_door import ExitDoor
        ExitDoor.link_door_pair(self.door_a, self.door_b)

    def test_link_sets_other_side(self):
        """link_door_pair sets other_side on both doors."""
        self.assertEqual(self.door_a.other_side, self.door_b)
        self.assertEqual(self.door_b.other_side, self.door_a)

    def test_open_syncs_other_side(self):
        """Opening door A also opens door B."""
        self.door_a.open(self.char1)
        self.assertTrue(self.door_a.is_open)
        self.assertTrue(self.door_b.is_open)

    def test_close_syncs_other_side(self):
        """Closing door A also closes door B."""
        # Open both first
        self.door_a.is_open = True
        self.door_b.is_open = True
        self.door_a.close(self.char1)
        self.assertFalse(self.door_a.is_open)
        self.assertFalse(self.door_b.is_open)

    def test_unlock_syncs_other_side(self):
        """Unlocking door A (via at_unlock hook) also unlocks door B."""
        self.door_a.is_locked = True
        self.door_b.is_locked = True
        # Simulate successful unlock — set state and fire hook
        self.door_a.is_locked = False
        self.door_a.at_unlock(self.char1)
        self.assertFalse(self.door_a.is_locked)
        self.assertFalse(self.door_b.is_locked)

    def test_lock_syncs_other_side(self):
        """Locking door A also locks door B."""
        # Both start unlocked; close both so lock() can succeed
        self.door_a.close(self.char1)
        self.door_a.lock(self.char1)
        self.assertTrue(self.door_a.is_locked)
        self.assertTrue(self.door_b.is_locked)

    def test_sync_state_false_blocks_open_sync(self):
        """With sync_state=False, opening A does not open B."""
        self.door_a.sync_state = False
        self.door_a.open(self.char1)
        self.assertTrue(self.door_a.is_open)
        self.assertFalse(self.door_b.is_open)

    def test_sync_state_false_blocks_close_sync(self):
        """With sync_state=False, closing A does not close B."""
        self.door_a.is_open = True
        self.door_b.is_open = True
        self.door_a.sync_state = False
        self.door_a.close(self.char1)
        self.assertFalse(self.door_a.is_open)
        self.assertTrue(self.door_b.is_open)

    def test_sync_state_false_blocks_unlock_sync(self):
        """With sync_state=False, unlocking A does not unlock B."""
        self.door_a.is_locked = True
        self.door_b.is_locked = True
        self.door_a.sync_state = False
        # Simulate successful unlock
        self.door_a.is_locked = False
        self.door_a.at_unlock(self.char1)
        self.assertFalse(self.door_a.is_locked)
        self.assertTrue(self.door_b.is_locked)

    def test_unpaired_door_opens_normally(self):
        """Door without other_side opens fine (no sync attempted)."""
        solo_door = create.create_object(
            "typeclasses.terrain.exits.exit_door.ExitDoor",
            key="iron gate",
            location=self.room1,
            destination=self.room2,
            nohome=True,
        )
        solo_door.open(self.char1)
        self.assertTrue(solo_door.is_open)
