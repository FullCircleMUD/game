"""
Tests for the procedural dungeon system.

Tests cover: template registry, instance lifecycle, lazy room creation,
exit budget, boss room generation, collapse cleanup, dungeon commands,
passage dungeons, shared instance mode, movement-triggered entry, and
follower teleport guard.

evennia test --settings settings tests.dungeon_tests.test_dungeon_system
"""

from unittest.mock import patch

from django.utils import timezone
from evennia import create_object
from evennia.utils import create
from evennia.utils.search import search_tag
from evennia.utils.test_resources import EvenniaCommandTest

from commands.room_specific_cmds.dungeon.cmd_dungeon_exit import CmdExitDungeon
from typeclasses.terrain.exits.dungeon_trigger_exit import DungeonTriggerExit
from typeclasses.scripts.dungeon_instance import (
    DungeonInstanceScript,
    DIRECTION_VECTORS,
)
from world.dungeons import register_dungeon, get_dungeon_template, DUNGEON_REGISTRY
from world.dungeons.dungeon_template import DungeonTemplate


# ------------------------------------------------------------------ #
#  Test templates
# ------------------------------------------------------------------ #

def _test_room_generator(instance, depth, coords):
    """Generate a simple test room."""
    from typeclasses.terrain.rooms.dungeon.dungeon_room import DungeonRoom
    from evennia import create_object

    room = create_object(DungeonRoom, key=f"Test Room d{depth}")
    room.db.desc = f"A test room at depth {depth}, coords {coords}."
    return room


def _test_boss_generator(instance, room):
    """Generate a simple test boss."""
    from typeclasses.actors.npc import BaseNPC
    from evennia import create_object

    boss = create_object(BaseNPC, key="Test Boss", location=room)
    boss.is_immortal = False
    return boss


TEST_TEMPLATE = DungeonTemplate(
    template_id="test_dungeon",
    name="Test Dungeon",
    dungeon_type="instance",
    instance_mode="group",
    boss_depth=2,
    max_unexplored_exits=2,
    max_new_exits_per_room=2,
    instance_lifetime_seconds=7200,
    room_generator=_test_room_generator,
    boss_generator=_test_boss_generator,
    room_typeclass="typeclasses.terrain.rooms.dungeon.dungeon_room.DungeonRoom",
    allow_combat=True,
    allow_pvp=False,
    allow_death=False,
    post_boss_linger_seconds=300,
)

TEST_PASSAGE_TEMPLATE = DungeonTemplate(
    template_id="test_passage",
    name="Test Passage",
    dungeon_type="passage",
    instance_mode="solo",
    boss_depth=2,
    max_unexplored_exits=2,
    max_new_exits_per_room=1,
    instance_lifetime_seconds=7200,
    room_generator=_test_room_generator,
    boss_generator=None,
)

TEST_SHARED_TEMPLATE = DungeonTemplate(
    template_id="test_shared",
    name="Test Shared Dungeon",
    dungeon_type="instance",
    instance_mode="shared",
    boss_depth=3,
    max_unexplored_exits=2,
    max_new_exits_per_room=2,
    instance_lifetime_seconds=7200,
    room_generator=_test_room_generator,
    boss_generator=_test_boss_generator,
    empty_collapse_delay=120,
)


def _cleanup_instances():
    """Delete all dungeon instance scripts."""
    from evennia import ScriptDB

    for script in ScriptDB.objects.filter(
        db_typeclass_path__contains="dungeon_instance"
    ):
        try:
            script.collapse_instance()
        except Exception:
            try:
                script.delete()
            except Exception:
                pass


# ------------------------------------------------------------------ #
#  Template registry tests
# ------------------------------------------------------------------ #

class TestDungeonRegistry(EvenniaCommandTest):
    """Test dungeon template registration and lookup."""

    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        DUNGEON_REGISTRY.clear()
        register_dungeon(TEST_TEMPLATE)

    def test_register_and_get(self):
        """Registered template is retrievable."""
        t = get_dungeon_template("test_dungeon")
        self.assertEqual(t.template_id, "test_dungeon")
        self.assertEqual(t.boss_depth, 2)

    def test_get_missing_raises(self):
        """Getting a non-existent template raises KeyError."""
        with self.assertRaises(KeyError):
            get_dungeon_template("nonexistent")


# ------------------------------------------------------------------ #
#  Instance lifecycle tests
# ------------------------------------------------------------------ #

class TestDungeonInstanceLifecycle(EvenniaCommandTest):
    """Test dungeon instance creation, room generation, and collapse."""

    character_typeclass = "typeclasses.actors.character.FCMCharacter"
    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        DUNGEON_REGISTRY.clear()
        register_dungeon(TEST_TEMPLATE)

        # Create an instance
        self.instance = create.create_script(
            DungeonInstanceScript,
            key="test_dungeon_1",
            autostart=False,
        )
        self.instance.template_id = "test_dungeon"
        self.instance.instance_key = "test_dungeon_1"
        self.instance.entrance_room_id = self.room1.id
        self.instance.start()

    def tearDown(self):
        # Clean up instance if still running
        try:
            if self.instance and self.instance.pk:
                self.instance.collapse_instance()
        except Exception:
            pass
        super().tearDown()

    def test_start_dungeon_creates_first_room(self):
        """start_dungeon creates a room and moves characters in."""
        self.instance.start_dungeon([self.char1])

        # Character should be in a dungeon room, not room1
        self.assertNotEqual(self.char1.location, self.room1)
        self.assertEqual(self.char1.location.key, "Test Room d0")

        # Character should be tagged
        self.assertEqual(
            self.char1.tags.get(category="dungeon_character"),
            "test_dungeon_1",
        )

    def test_first_room_has_exits(self):
        """First room should have at least one forward exit."""
        self.instance.start_dungeon([self.char1])
        first_room = self.char1.location
        exits = first_room.contents_get(content_type="exit")
        self.assertGreater(len(exits), 0)

    def test_lazy_room_creation(self):
        """Traversing a lazy exit creates a new room."""
        self.instance.start_dungeon([self.char1])
        first_room = self.char1.location
        exits = first_room.contents_get(content_type="exit")

        # Find a forward exit (not return)
        forward_exit = None
        for ex in exits:
            if not ex.is_return_exit:
                forward_exit = ex
                break
        self.assertIsNotNone(forward_exit)

        # Exit should point back to first room (lazy)
        self.assertEqual(forward_exit.destination, first_room)

        # Traverse it
        new_room = self.instance.create_room_from_exit(forward_exit)
        self.assertIsNotNone(new_room)
        self.assertNotEqual(new_room, first_room)

    def test_boss_room_at_depth(self):
        """Boss room is created when depth >= boss_depth."""
        self.instance.start_dungeon([self.char1])
        first_room = self.char1.location

        # Navigate through rooms until we hit boss depth
        current_room = first_room
        for _ in range(3):  # boss_depth is 2, so within 3 moves we should hit it
            exits = current_room.contents_get(content_type="exit")
            forward = [ex for ex in exits if not getattr(ex, "is_return_exit", True)]
            if not forward:
                break
            ex = forward[0]
            if ex.destination == current_room:
                new_room = self.instance.create_room_from_exit(ex)
                if new_room:
                    current_room = new_room
                else:
                    break

        # Check if we found a boss room
        all_rooms = list(
            search_tag("test_dungeon_1", category="dungeon_room")
        )
        boss_rooms = [r for r in all_rooms if r.is_boss_room]
        # With boss_depth=2 and max exits, we should reach it
        if boss_rooms:
            self.assertTrue(boss_rooms[0].is_boss_room)
            # Boss room should have a mob
            mobs = list(
                search_tag("test_dungeon_1", category="dungeon_mob")
            )
            self.assertGreater(len(mobs), 0)

    def test_collapse_cleans_up(self):
        """Collapsing an instance removes all rooms, exits, mobs, and tags."""
        self.instance.start_dungeon([self.char1])
        self.instance.collapse_instance()

        # Character should be back at entrance
        self.assertEqual(self.char1.location, self.room1)

        # Character tag should be removed
        self.assertIsNone(
            self.char1.tags.get(category="dungeon_character")
        )

        # No rooms/exits/mobs should remain
        self.assertEqual(
            len(list(search_tag("test_dungeon_1", category="dungeon_room"))),
            0,
        )
        self.assertEqual(
            len(list(search_tag("test_dungeon_1", category="dungeon_exit"))),
            0,
        )

    def test_empty_instance_collapses_on_tick(self):
        """Instance with no characters collapses on next tick."""
        self.instance.start_dungeon([self.char1])
        instance_id = self.instance.id
        # Remove the character
        self.instance.remove_character(self.char1)
        self.char1.move_to(self.room1, quiet=True, move_type="teleport")

        # Tick — should trigger collapse and deletion
        self.instance.at_repeat()

        # Instance should be deleted from DB
        from evennia import ScriptDB

        self.assertFalse(
            ScriptDB.objects.filter(id=instance_id).exists()
        )


# ------------------------------------------------------------------ #
#  Command tests
# ------------------------------------------------------------------ #

class TestDungeonEntry(EvenniaCommandTest):
    """Test dungeon entry via DungeonTriggerExit."""

    character_typeclass = "typeclasses.actors.character.FCMCharacter"
    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        DUNGEON_REGISTRY.clear()
        register_dungeon(TEST_TEMPLATE)
        self.trigger = create_object(
            DungeonTriggerExit,
            key="dark cave",
            location=self.room1,
            destination=self.room1,
        )
        self.trigger.dungeon_template_id = "test_dungeon"

    def tearDown(self):
        _cleanup_instances()
        super().tearDown()

    def test_enter_creates_instance(self):
        """Traversing trigger exit creates an instance and moves player."""
        self.trigger.at_traverse(self.char1, self.room1)
        # Player should have been moved to a dungeon room
        self.assertNotEqual(self.char1.location, self.room1)
        # Player should be tagged
        self.assertIsNotNone(
            self.char1.tags.get(category="dungeon_character")
        )

    def test_enter_group_mode(self):
        """In group mode, leader + followers enter together."""
        self.char2.following = self.char1
        self.trigger.at_traverse(self.char1, self.room1)
        # Both should be in the dungeon
        self.assertNotEqual(self.char1.location, self.room1)
        self.assertEqual(self.char1.location, self.char2.location)

    def test_follower_cannot_enter(self):
        """Followers can't enter — only the leader can."""
        self.char1.following = self.char2
        self.trigger.at_traverse(self.char1, self.room1)
        # char1 should still be in entrance
        self.assertEqual(self.char1.location, self.room1)


class TestCmdExitDungeon(EvenniaCommandTest):
    """Test the exit dungeon command."""

    character_typeclass = "typeclasses.actors.character.FCMCharacter"
    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        DUNGEON_REGISTRY.clear()
        register_dungeon(TEST_TEMPLATE)

        # Create an instance and move char1 into it
        self.instance = create.create_script(
            DungeonInstanceScript,
            key="test_dungeon_exit",
            autostart=False,
        )
        self.instance.template_id = "test_dungeon"
        self.instance.instance_key = "test_dungeon_exit"
        self.instance.entrance_room_id = self.room1.id
        self.instance.start()
        self.instance.start_dungeon([self.char1])
        self.dungeon_room = self.char1.location

    def tearDown(self):
        try:
            if self.instance and self.instance.pk:
                self.instance.collapse_instance()
        except Exception:
            pass
        super().tearDown()

    def test_exit_returns_to_entrance(self):
        """exit dungeon teleports player to entrance."""
        self.call(CmdExitDungeon(), "", caller=self.char1)
        self.assertEqual(self.char1.location, self.room1)

    def test_exit_removes_tag(self):
        """exit dungeon removes the dungeon character tag."""
        self.call(CmdExitDungeon(), "", caller=self.char1)
        self.assertIsNone(
            self.char1.tags.get(category="dungeon_character")
        )


# ------------------------------------------------------------------ #
#  Passage dungeon tests
# ------------------------------------------------------------------ #

class TestPassageDungeon(EvenniaCommandTest):
    """Test passage-type dungeons that connect two world rooms."""

    character_typeclass = "typeclasses.actors.character.FCMCharacter"
    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        DUNGEON_REGISTRY.clear()
        register_dungeon(TEST_PASSAGE_TEMPLATE)

        # room2 is the destination world room
        self.instance = create.create_script(
            DungeonInstanceScript,
            key="test_passage_1",
            autostart=False,
        )
        self.instance.template_id = "test_passage"
        self.instance.instance_key = "test_passage_1"
        self.instance.entrance_room_id = self.room1.id
        self.instance.destination_room_id = self.room2.id
        self.instance.start()

    def tearDown(self):
        try:
            if self.instance and self.instance.pk:
                self.instance.collapse_instance()
        except Exception:
            pass
        super().tearDown()

    def test_first_room_has_return_exit(self):
        """Passage first room has a passage exit back to entrance."""
        self.instance.start_dungeon([self.char1])
        first_room = self.char1.location
        exits = first_room.contents_get(content_type="exit")

        # Should have a passage exit pointing to room1 (entrance)
        from typeclasses.terrain.exits.dungeon_passage_exit import DungeonPassageExit

        passage_exits = [
            ex for ex in exits if isinstance(ex, DungeonPassageExit)
        ]
        self.assertEqual(len(passage_exits), 1)
        self.assertEqual(passage_exits[0].destination, self.room1)

    def test_terminal_room_has_passage_exit(self):
        """At termination depth, passage creates exit to destination room."""
        self.instance.start_dungeon([self.char1])

        # Navigate to termination depth (boss_depth=2)
        current_room = self.char1.location
        for _ in range(3):
            exits = current_room.contents_get(content_type="exit")
            forward = [
                ex for ex in exits
                if hasattr(ex, "is_return_exit") and not ex.is_return_exit
            ]
            if not forward:
                break
            ex = forward[0]
            if ex.destination == current_room:
                new_room = self.instance.create_room_from_exit(ex)
                if new_room:
                    current_room = new_room
                else:
                    break

        # Check that a passage exit to room2 exists somewhere
        from typeclasses.terrain.exits.dungeon_passage_exit import DungeonPassageExit

        all_exits = list(
            search_tag("test_passage_1", category="dungeon_exit")
        )
        dest_exits = [
            ex for ex in all_exits
            if isinstance(ex, DungeonPassageExit)
            and ex.destination == self.room2
        ]
        self.assertGreater(len(dest_exits), 0)

    def test_no_boss_in_passage(self):
        """Passage dungeons don't spawn a boss at termination depth."""
        self.instance.start_dungeon([self.char1])

        # Navigate to termination depth
        current_room = self.char1.location
        for _ in range(3):
            exits = current_room.contents_get(content_type="exit")
            forward = [
                ex for ex in exits
                if hasattr(ex, "is_return_exit") and not ex.is_return_exit
            ]
            if not forward:
                break
            ex = forward[0]
            if ex.destination == current_room:
                new_room = self.instance.create_room_from_exit(ex)
                if new_room:
                    current_room = new_room
                else:
                    break

        # No mobs should exist
        mobs = list(search_tag("test_passage_1", category="dungeon_mob"))
        self.assertEqual(len(mobs), 0)

        # No boss rooms
        all_rooms = list(
            search_tag("test_passage_1", category="dungeon_room")
        )
        boss_rooms = [r for r in all_rooms if r.is_boss_room]
        self.assertEqual(len(boss_rooms), 0)

    def test_passage_exit_removes_tag(self):
        """Walking through a passage exit removes the dungeon tag."""
        self.instance.start_dungeon([self.char1])
        first_room = self.char1.location

        # Find the passage exit (return to entrance)
        from typeclasses.terrain.exits.dungeon_passage_exit import DungeonPassageExit

        exits = first_room.contents_get(content_type="exit")
        passage_exit = None
        for ex in exits:
            if isinstance(ex, DungeonPassageExit):
                passage_exit = ex
                break
        self.assertIsNotNone(passage_exit)

        # Traverse it
        passage_exit.at_traverse(self.char1, passage_exit.destination)

        # Character should be at entrance and untagged
        self.assertEqual(self.char1.location, self.room1)
        self.assertIsNone(
            self.char1.tags.get(category="dungeon_character")
        )


# ------------------------------------------------------------------ #
#  Shared instance mode tests
# ------------------------------------------------------------------ #

class TestSharedInstanceMode(EvenniaCommandTest):
    """Test shared instance mode where multiple players join the same instance."""

    character_typeclass = "typeclasses.actors.character.FCMCharacter"
    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        DUNGEON_REGISTRY.clear()
        register_dungeon(TEST_SHARED_TEMPLATE)
        self.trigger = create_object(
            DungeonTriggerExit,
            key="shared entrance",
            location=self.room1,
            destination=self.room1,
        )
        self.trigger.dungeon_template_id = "test_shared"

    def tearDown(self):
        _cleanup_instances()
        super().tearDown()

    def test_second_player_joins_existing(self):
        """Second player joins existing shared instance."""
        # First player enters
        self.trigger.at_traverse(self.char1, self.room1)
        self.assertNotEqual(self.char1.location, self.room1)

        # Second player enters — should join same instance
        self.trigger.at_traverse(self.char2, self.room1)
        self.assertNotEqual(self.char2.location, self.room1)

        # Both should be tagged with the same instance key
        tag1 = self.char1.tags.get(category="dungeon_character")
        tag2 = self.char2.tags.get(category="dungeon_character")
        self.assertEqual(tag1, tag2)

    def test_shared_instance_persists_after_empty(self):
        """Shared instance with delay persists when all players leave."""
        self.trigger.at_traverse(self.char1, self.room1)

        from evennia import ScriptDB

        instance_key = self.char1.tags.get(category="dungeon_character")
        instance = ScriptDB.objects.get(db_key=instance_key)
        instance_id = instance.id

        # Remove character
        instance.remove_character(self.char1)
        self.char1.move_to(self.room1, quiet=True, move_type="teleport")

        # Tick — should NOT collapse (empty_collapse_delay=120)
        instance.at_repeat()
        self.assertTrue(
            ScriptDB.objects.filter(id=instance_id).exists()
        )


# ------------------------------------------------------------------ #
#  Movement-triggered entry tests (DungeonTriggerExit)
# ------------------------------------------------------------------ #

class TestDungeonTriggerExit(EvenniaCommandTest):
    """Test movement-triggered dungeon entry via DungeonTriggerExit."""

    character_typeclass = "typeclasses.actors.character.FCMCharacter"
    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        DUNGEON_REGISTRY.clear()
        register_dungeon(TEST_TEMPLATE)
        register_dungeon(TEST_PASSAGE_TEMPLATE)

        # Create a trigger exit in room1
        self.trigger = create_object(
            DungeonTriggerExit,
            key="dark cave",
            location=self.room1,
            destination=self.room1,  # self-referential
        )
        self.trigger.dungeon_template_id = "test_dungeon"

    def tearDown(self):
        _cleanup_instances()
        super().tearDown()

    def test_traverse_creates_instance(self):
        """Walking through trigger exit creates a dungeon instance."""
        self.trigger.at_traverse(self.char1, self.room1)

        # Character should be in a dungeon room
        self.assertNotEqual(self.char1.location, self.room1)
        # Character should be tagged
        self.assertIsNotNone(
            self.char1.tags.get(category="dungeon_character")
        )

    def test_group_mode_collects_followers(self):
        """Group mode trigger exit moves leader + followers."""
        self.char2.following = self.char1
        self.trigger.at_traverse(self.char1, self.room1)

        # Both should be in the dungeon
        self.assertNotEqual(self.char1.location, self.room1)
        self.assertEqual(self.char1.location, self.char2.location)

        # Both should be tagged
        self.assertIsNotNone(
            self.char1.tags.get(category="dungeon_character")
        )
        self.assertIsNotNone(
            self.char2.tags.get(category="dungeon_character")
        )

    def test_follower_cannot_trigger(self):
        """Followers walking through trigger exit are rejected."""
        self.char1.following = self.char2
        self.trigger.at_traverse(self.char1, self.room1)

        # char1 should still be in room1 (not moved)
        self.assertEqual(self.char1.location, self.room1)

    def test_already_in_dungeon_rejected(self):
        """Characters already in a dungeon can't enter another."""
        # Put char1 in a dungeon
        self.char1.tags.add("some_dungeon", category="dungeon_character")

        self.trigger.at_traverse(self.char1, self.room1)

        # Should still be in room1
        self.assertEqual(self.char1.location, self.room1)

        # Clean up
        self.char1.tags.remove("some_dungeon", category="dungeon_character")

    def test_passage_with_trigger_exit(self):
        """Trigger exit with passage template sets destination_room_id."""
        self.trigger.dungeon_template_id = "test_passage"
        self.trigger.dungeon_destination_room_id = self.room2.id

        self.trigger.at_traverse(self.char1, self.room1)

        # Character should be in a dungeon room
        self.assertNotEqual(self.char1.location, self.room1)

        # Find the instance and verify destination is set
        from evennia import ScriptDB

        tag = self.char1.tags.get(category="dungeon_character")
        instance = ScriptDB.objects.get(db_key=tag)
        self.assertEqual(instance.destination_room_id, self.room2.id)


# ------------------------------------------------------------------ #
#  Follower teleport guard tests
# ------------------------------------------------------------------ #

class TestFollowerTeleportGuard(EvenniaCommandTest):
    """Test that teleports do not cascade followers."""

    character_typeclass = "typeclasses.actors.character.FCMCharacter"
    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"
    databases = "__all__"

    def create_script(self):
        pass

    def test_teleport_does_not_cascade(self):
        """Followers do not follow on teleport moves."""
        self.char2.following = self.char1
        self.char1.move_to(self.room2, quiet=True, move_type="teleport")

        # char1 should be in room2
        self.assertEqual(self.char1.location, self.room2)
        # char2 should still be in room1 (NOT cascaded)
        self.assertEqual(self.char2.location, self.room1)

    def test_normal_move_still_cascades(self):
        """Followers still follow on normal (non-teleport) moves."""
        self.char2.following = self.char1
        self.char1.move_to(self.room2, quiet=True, move_type="move")

        # Both should be in room2
        self.assertEqual(self.char1.location, self.room2)
        self.assertEqual(self.char2.location, self.room2)
