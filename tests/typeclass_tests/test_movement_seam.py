"""
Tests for the movement message seam — what each room is told when someone
moves between rooms, and how a caller supplies its own wording.

The vocabulary itself (verb rules, direction phrasing) is covered by
tests.utils_tests.test_movement_messages.

evennia test --settings settings tests.typeclass_tests.test_movement_seam
"""

from unittest.mock import MagicMock

from evennia.utils import create
from evennia.utils.test_resources import EvenniaTest


WALLET_A = "0xAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"


def _lines(watcher):
    """Everything said to a watcher, as plain strings."""
    said = []
    for args, kwargs in watcher.msg.call_args_list:
        payload = kwargs.get("text", args[0] if args else None)
        if isinstance(payload, tuple):
            payload = payload[0]
        if payload:
            said.append(str(payload))
    return said


class MovementSeamTest(EvenniaTest):
    """Two rooms joined north/south, with a watcher standing in each."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"
    character_typeclass = "typeclasses.actors.character.FCMCharacter"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)

        # Light both rooms. Without this, darkness is decided by the
        # real-time-derived game hour, so a watcher standing in an unlit
        # room counts as blind and every name in these assertions redacts
        # to "Someone" — making the whole suite pass or fail depending on
        # what time it is run.
        self.room1.always_lit = True
        self.room2.always_lit = True

        self.north = self._exit(self.room1, self.room2, "north")
        self.south = self._exit(self.room2, self.room1, "south")

        self.here = self._watcher("Bystander", self.room1)
        self.there = self._watcher("Watcher", self.room2)

    def _exit(self, source, destination, direction):
        ext = create.create_object(
            "typeclasses.terrain.exits.exit_vertical_aware.ExitVerticalAware",
            key=direction,
            location=source,
            destination=destination,
            nohome=True,
        )
        ext.direction = direction
        return ext

    def _watcher(self, key, room):
        watcher = create.create_object(
            self.character_typeclass, key=key, location=room, home=room
        )
        watcher.msg = MagicMock()
        return watcher

    def _walk_north(self, **kwargs):
        self.char1.move_to(
            self.room2, move_type="traverse", exit_obj=self.north, **kwargs
        )


class TestStandardWording(MovementSeamTest):
    """Wording the seam resolves for itself, with no caller involvement."""

    def test_departure_names_the_direction_travelled(self):
        self._walk_north()
        self.assertIn("Char leaves north.", _lines(self.here))

    def test_arrival_names_where_they_came_from(self):
        self._walk_north()
        self.assertIn("Char arrives from the south.", _lines(self.there))

    def test_no_room_names_appear(self):
        """Bystanders learn the direction, never the destination."""
        self._walk_north()
        for line in _lines(self.here) + _lines(self.there):
            self.assertNotIn(self.room2.key, line)

    def test_the_mover_is_not_told_about_themselves(self):
        self.char1.msg = MagicMock()
        self._walk_north()
        for line in _lines(self.char1):
            self.assertNotIn("leaves north", line)
            self.assertNotIn("arrives from", line)

    def test_flying_changes_the_verb(self):
        self.char1.room_vertical_position = 2
        self._walk_north()
        self.assertIn("Char flies north.", _lines(self.here))
        self.assertIn("Char flies in from the south.", _lines(self.there))

    def test_swimming_changes_the_verb(self):
        self.room1.max_depth = -3
        self.char1.room_vertical_position = -1
        self._walk_north()
        self.assertIn("Char swims north.", _lines(self.here))

    def test_quiet_silences_both_sides(self):
        self._walk_north(quiet=True)
        self.assertEqual(_lines(self.here), [])
        self.assertEqual(_lines(self.there), [])


class TestArrivalDirection(MovementSeamTest):
    """Which way someone came from, including when there's no way back."""

    def test_vertical_arrival_reads_as_above_or_below(self):
        """
        Also the multiply-connected case: these rooms are already joined
        north/south by setUp, so the stairs must not report the passage.
        """
        up = self._exit(self.room1, self.room2, "up")
        self._exit(self.room2, self.room1, "down")
        self.char1.move_to(self.room2, move_type="traverse", exit_obj=up)
        self.assertIn("Char arrives from below.", _lines(self.there))

    def test_asymmetric_link_uses_the_way_back_that_exists(self):
        """Out by north, back by west — the room hears the real way back."""
        self.south.delete()
        self._exit(self.room2, self.room1, "west")
        self._walk_north()
        self.assertIn("Char arrives from the west.", _lines(self.there))

    def test_one_way_exit_falls_back_to_the_opposite(self):
        """No way back to read, so invert the exit that was used."""
        self.south.delete()
        self._walk_north()
        self.assertIn("Char arrives from the south.", _lines(self.there))

    def test_no_exit_at_all_still_announces(self):
        """A directionless move says something rather than nothing."""
        self.north.delete()
        self.south.delete()
        self.char1.move_to(self.room2)
        self.assertIn("Char leaves.", _lines(self.here))
        self.assertIn("Char arrives.", _lines(self.there))


class TestParties(MovementSeamTest):
    """A group is one event, so the room hears one line."""

    def setUp(self):
        super().setUp()
        self.follower = self._watcher("Tagalong", self.room1)
        self.follower.following = self.char1

    def test_leader_with_followers_announces_as_a_party(self):
        self._walk_north()
        self.assertIn("Char's party leaves north.", _lines(self.here))
        self.assertIn("Char's party arrives from the south.", _lines(self.there))

    def test_party_keeps_the_leader_verb(self):
        """A mixed group reads as one line, but not a wrong one."""
        self.char1.room_vertical_position = 2
        self._walk_north()
        self.assertIn("Char's party flies north.", _lines(self.here))

    def test_a_leader_alone_is_not_a_party(self):
        self.follower.following = None
        self._walk_north()
        self.assertIn("Char leaves north.", _lines(self.here))

    def test_followers_do_not_announce_themselves(self):
        """One party line per room, not one line per follower."""
        self._walk_north()
        arrivals = [ln for ln in _lines(self.there) if "arrives" in ln]
        self.assertEqual(len(arrivals), 1)

    def test_follower_is_told_which_way_they_went(self):
        self._walk_north()
        self.assertIn("You follow Char north.", _lines(self.follower))


class TestCallerSuppliedWording(MovementSeamTest):
    """A direct caller passes its own text through the same machinery."""

    def test_msg_from_replaces_the_departure_line(self):
        self._walk_north(msg_from="{name} bolts {direction} in a panic!")
        self.assertIn("Char bolts north in a panic!", _lines(self.here))

    def test_msg_to_replaces_the_arrival_line(self):
        self._walk_north(msg_to="{name} stumbles in {direction}.")
        self.assertIn("Char stumbles in from the south.", _lines(self.there))

    def test_each_side_can_differ(self):
        """The problem a single msg= could not solve."""
        self._walk_north(msg_from="{name} bolts!", msg_to="{name} stumbles in.")
        self.assertIn("Char bolts!", _lines(self.here))
        self.assertIn("Char stumbles in.", _lines(self.there))

    def test_override_replaces_the_party_form_too(self):
        follower = self._watcher("Tagalong", self.room1)
        follower.following = self.char1
        self._walk_north(msg_from="{name} bolts {direction}!")
        self.assertIn("Char bolts north!", _lines(self.here))

    def test_caller_placeholders_are_merged(self):
        guard = self._watcher("Guard", self.room1)
        self._walk_north(
            msg_mapping={"pursuer": guard},
            msg_from="{name} flees {direction}, {pursuer} close behind!",
        )
        self.assertIn("Char flees north, Guard close behind!", _lines(self.here))

    def test_caller_cannot_rebind_the_mover(self):
        """{name} stays the mover, so per-recipient resolution survives."""
        self._walk_north(
            msg_mapping={"name": "Somebody Else"},
            msg_from="{name} leaves {direction}.",
        )
        self.assertIn("Char leaves north.", _lines(self.here))

    def test_a_quiet_caller_is_still_silent_with_text(self):
        """Passing text does not opt out of suppression."""
        self._walk_north(quiet=True, msg_from="{name} bolts!")
        self.assertEqual(_lines(self.here), [])


class TestDoorsDoNotDuplicate(MovementSeamTest):
    """A door announces itself, never the movement."""

    def test_traversing_a_door_produces_one_line_per_room(self):
        door = create.create_object(
            "typeclasses.terrain.exits.exit_door.ExitDoor",
            key="a wooden door",
            location=self.room1,
            destination=self.room2,
            nohome=True,
        )
        door.direction = "north"
        door.is_open = True

        door.at_traverse(self.char1, self.room2)

        departures = [ln for ln in _lines(self.here) if "Char" in ln]
        arrivals = [ln for ln in _lines(self.there) if "Char" in ln]
        self.assertEqual(departures, ["Char leaves north."])
        self.assertEqual(arrivals, ["Char arrives from the south."])

    def test_door_name_never_appears_in_a_movement_line(self):
        door = create.create_object(
            "typeclasses.terrain.exits.exit_door.ExitDoor",
            key="a sturdy wooden door",
            location=self.room1,
            destination=self.room2,
            nohome=True,
        )
        door.direction = "north"
        door.is_open = True

        door.at_traverse(self.char1, self.room2)

        for line in _lines(self.here) + _lines(self.there):
            self.assertNotIn("wooden door", line)
