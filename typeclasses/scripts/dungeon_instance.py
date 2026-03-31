"""
DungeonInstanceScript — the core orchestrator for a single dungeon instance.

Manages the lifecycle of a procedural dungeon: room creation, exit budget,
boss spawning (instance type) or passage exit (passage type), character
tracking, and instance collapse/cleanup.

Supports two dungeon types:
    "instance" — terminates with a boss room (dead-end).
    "passage"  — terminates with an exit to a destination world room.

Supports three instance modes:
    "solo"   — one instance per player.
    "group"  — leader + followers share one instance.
    "shared" — one instance per entrance, anyone can join.

Each instance is tied to a DungeonTemplate and tracks its own xy_grid,
rooms, exits, mobs, and characters via Evennia tags.
"""

import random

from django.utils import timezone
from evennia import AttributeProperty, DefaultScript, ScriptDB, create_object
from evennia.utils.search import search_tag

from utils.exit_helpers import OPPOSITES
from world.dungeons import get_dungeon_template


# Direction vectors for compass directions
DIRECTION_VECTORS = {
    "north": (0, 1),
    "south": (0, -1),
    "east": (1, 0),
    "west": (-1, 0),
}


class DungeonInstanceScript(DefaultScript):
    """
    Manages a single procedural dungeon instance.

    State machine: active → collapsing → done
    """

    template_id = AttributeProperty(None)
    instance_key = AttributeProperty(None)
    entrance_room_id = AttributeProperty(None)
    entrance_direction = AttributeProperty(None)  # direction player entered from
    destination_room_id = AttributeProperty(None)  # passage endpoint
    state = AttributeProperty("active")
    boss_defeated = AttributeProperty(False)
    created_at = AttributeProperty(None)
    emptied_at = AttributeProperty(None)  # when last player left

    def at_script_creation(self):
        self.interval = 60  # tick every minute
        self.persistent = True
        self.start_delay = True
        self.repeats = 0  # forever

    def at_start(self, **kwargs):
        if not self.created_at:
            self.created_at = timezone.now()

    # ------------------------------------------------------------------ #
    #  Template access
    # ------------------------------------------------------------------ #

    @property
    def template(self):
        return get_dungeon_template(self.template_id)

    @property
    def entrance_room(self):
        from evennia import ObjectDB

        if not self.entrance_room_id:
            return None
        try:
            return ObjectDB.objects.get(id=self.entrance_room_id)
        except ObjectDB.DoesNotExist:
            return None

    # ------------------------------------------------------------------ #
    #  Character management
    # ------------------------------------------------------------------ #

    def add_characters(self, characters):
        """Tag multiple characters for this instance."""
        for char in characters:
            char.tags.add(self.instance_key, category="dungeon_character")
        self.emptied_at = None

    def add_character(self, char):
        """Tag a single character joining this instance (shared mode)."""
        char.tags.add(self.instance_key, category="dungeon_character")
        self.emptied_at = None

    def remove_character(self, char):
        """Remove a character from this instance."""
        char.tags.remove(self.instance_key, category="dungeon_character")

    def get_characters(self):
        """Get all characters tagged for this instance."""
        return list(search_tag(self.instance_key, category="dungeon_character"))

    # ------------------------------------------------------------------ #
    #  Room property helper
    # ------------------------------------------------------------------ #

    def _set_room_properties(self, room, template):
        """Apply standard template properties to a dungeon room."""
        room.allow_combat = template.allow_combat
        room.allow_pvp = template.allow_pvp
        room.allow_death = template.allow_death
        if template.defeat_destination_key:
            from evennia import search_object

            dest_matches = search_object(
                template.defeat_destination_key, exact=True
            )
            if dest_matches:
                room.defeat_destination = dest_matches[0]

        # Terrain and lighting — makes dungeon rooms consistent with world rooms
        if hasattr(room, "set_terrain"):
            room.set_terrain(template.terrain_type)
        if template.always_lit:
            room.always_lit = True

    # ------------------------------------------------------------------ #
    #  Instance initialisation — create first room and move players in
    # ------------------------------------------------------------------ #

    def start_dungeon(self, characters):
        """
        Create the first room and move all characters into it.

        Called by ProceduralDungeonMixin.enter_dungeon() after collecting
        the group.
        """
        self.add_characters(characters)

        template = self.template

        # Create first room at origin (0, 0)
        first_room = template.room_generator(self, 0, (0, 0))
        first_room.tags.add(self.instance_key, category="dungeon_room")
        first_room.dungeon_instance_id = self.id
        first_room.xy_coords = (0, 0)
        self._set_room_properties(first_room, template)

        # Store in grid
        self.db.xy_grid = {(0, 0): first_room.id}
        self.db.unvisited_exits = []

        # Return exit from room (0,0) back to the entrance
        return_dir = None
        if self.entrance_room_id:
            entrance = self.entrance_room
            if entrance:
                # Use the opposite of the entry direction for the return
                return_dir = OPPOSITES.get(self.entrance_direction, "out") \
                    if self.entrance_direction else "out"
                self._create_passage_exit(first_room, entrance, return_dir)

        # Create initial exits from the first room, excluding the return direction
        exclude = {return_dir} if return_dir else set()
        self._create_forward_exits(first_room, (0, 0), exclude_directions=exclude)

        # Move characters in
        for char in characters:
            char.move_to(first_room, quiet=True, move_type="teleport")

    # ------------------------------------------------------------------ #
    #  Room creation (called by DungeonExit.at_traverse)
    # ------------------------------------------------------------------ #

    def create_room_from_exit(self, exit_obj):
        """
        Create the destination room for a lazy exit.

        Calculates coordinates from the exit's direction, checks depth,
        and either creates a normal room, boss room, or passage endpoint.

        Returns the new room, or None if creation fails.
        """
        template = self.template
        source_coords = exit_obj.location.xy_coords
        dx, dy = DIRECTION_VECTORS.get(exit_obj.direction, (0, 0))
        new_coords = (source_coords[0] + dx, source_coords[1] + dy)

        # Check if a room already exists at these coords
        grid = dict(self.db.xy_grid or {})
        if new_coords in grid:
            from evennia import ObjectDB

            try:
                return ObjectDB.objects.get(id=grid[new_coords])
            except ObjectDB.DoesNotExist:
                pass

        depth = abs(new_coords[0]) + abs(new_coords[1])

        # Determine if this room is at termination depth
        is_terminal = depth >= template.boss_depth

        # Create the room
        new_room = template.room_generator(self, depth, new_coords)
        new_room.tags.add(self.instance_key, category="dungeon_room")
        new_room.dungeon_instance_id = self.id
        new_room.xy_coords = new_coords
        self._set_room_properties(new_room, template)

        # Store in grid
        grid[new_coords] = new_room.id
        self.db.xy_grid = grid

        # Remove traversed exit from unvisited list
        unvisited = list(self.db.unvisited_exits or [])
        if exit_obj.id in unvisited:
            unvisited.remove(exit_obj.id)
        self.db.unvisited_exits = unvisited

        # Create return exit back to source room
        opposite = OPPOSITES.get(exit_obj.direction, "back")
        self._create_exit(
            new_room, exit_obj.location, opposite, is_return=True
        )

        # Terminal room — fork on dungeon type
        if is_terminal:
            if template.dungeon_type == "passage":
                # Passage: create exit to destination world room
                self._create_terminal_passage_exit(new_room)
            else:
                # Instance: spawn boss (dead-end, no forward exits)
                new_room.is_boss_room = True
                if template.boss_generator:
                    boss = template.boss_generator(self, new_room)
                    if boss:
                        boss.tags.add(self.instance_key, category="dungeon_mob")
        else:
            # Exclude the return direction to avoid duplicate exits
            self._create_forward_exits(
                new_room, new_coords, exclude_directions={opposite}
            )

        return new_room

    # ------------------------------------------------------------------ #
    #  Exit creation helpers
    # ------------------------------------------------------------------ #

    def _create_forward_exits(self, room, coords, exclude_directions=None):
        """Create 1-N forward exits from a room, respecting exit budget.

        Args:
            room: The room to create exits in.
            coords: (x, y) coordinates of the room.
            exclude_directions: set of directions to skip (e.g. the return
                exit direction, to avoid duplicate exits in the same direction).
        """
        template = self.template
        unvisited = list(self.db.unvisited_exits or [])
        grid = dict(self.db.xy_grid or {})
        exclude = exclude_directions or set()

        # Available directions that don't loop back to existing rooms
        # and aren't excluded (e.g. the return exit direction)
        available = []
        for direction, (dx, dy) in DIRECTION_VECTORS.items():
            if direction in exclude:
                continue
            target_coords = (coords[0] + dx, coords[1] + dy)
            if target_coords not in grid:
                available.append(direction)

        if not available:
            return

        # How many new exits can we create?
        budget = template.max_unexplored_exits - len(unvisited)
        if budget <= 0:
            return

        num_exits = min(
            random.randint(1, template.max_new_exits_per_room),
            len(available),
            budget,
        )
        # Always create at least 1 exit if budget allows
        num_exits = max(1, num_exits)

        chosen = random.sample(available, num_exits)

        for direction in chosen:
            exit_obj = self._create_exit(room, room, direction, is_return=False)
            unvisited.append(exit_obj.id)

        self.db.unvisited_exits = unvisited

    def _create_exit(self, source, destination, direction, is_return=False):
        """Create a single DungeonExit with direction aliases."""
        from typeclasses.terrain.exits.dungeon_exit import DungeonExit

        exit_obj = create_object(
            DungeonExit,
            key=direction,
            location=source,
            destination=destination,
        )
        exit_obj.dungeon_instance_id = self.id
        exit_obj.set_direction(direction)
        exit_obj.is_return_exit = is_return
        exit_obj.tags.add(self.instance_key, category="dungeon_exit")
        return exit_obj

    def _create_passage_exit(self, source_room, destination_room,
                             direction="out"):
        """Create a DungeonPassageExit from a dungeon room to a world room."""
        from typeclasses.terrain.exits.dungeon_passage_exit import DungeonPassageExit

        passage_exit = create_object(
            DungeonPassageExit,
            key=destination_room.key,
            location=source_room,
            destination=destination_room,
        )
        passage_exit.dungeon_instance_id = self.id
        passage_exit.set_direction(direction)
        passage_exit.tags.add(self.instance_key, category="dungeon_exit")
        return passage_exit

    def _create_terminal_passage_exit(self, terminal_room, direction="out"):
        """Create the exit from the final passage room to the destination."""
        from evennia import ObjectDB

        if not self.destination_room_id:
            return
        try:
            dest_room = ObjectDB.objects.get(id=self.destination_room_id)
        except ObjectDB.DoesNotExist:
            return
        self._create_passage_exit(terminal_room, dest_room, direction)

    # ------------------------------------------------------------------ #
    #  Boss defeated
    # ------------------------------------------------------------------ #

    def on_boss_defeated(self):
        """
        Called when the boss is killed.

        Sets the boss_defeated flag for quest/progression checks.
        Does NOT trigger collapse — the instance persists until the
        player leaves naturally (walk out, recall, etc.).
        """
        self.boss_defeated = True

    # ------------------------------------------------------------------ #
    #  Collapse / cleanup
    # ------------------------------------------------------------------ #

    def collapse_instance(self):
        """
        Clean up the dungeon instance and destroy all dungeon objects.

        If any characters are still inside (AFK, disconnected, or safety
        timeout), silently teleports them to the entrance. Returns
        fungibles to reserve and deletes all tagged rooms/exits/mobs.
        """
        if self.state == "done":
            return

        self.state = "collapsing"
        entrance = self.entrance_room

        # Silently evacuate any remaining characters (safety net only)
        for char in self.get_characters():
            if entrance:
                char.move_to(entrance, quiet=True, move_type="teleport")
            self.remove_character(char)

        # Delete mobs
        for mob in search_tag(self.instance_key, category="dungeon_mob"):
            mob.delete()

        # Delete exits (before rooms, since exits reference rooms)
        for exit_obj in search_tag(self.instance_key, category="dungeon_exit"):
            exit_obj.delete()

        # Return fungibles to reserve, then delete rooms
        for room in search_tag(self.instance_key, category="dungeon_room"):
            gold = room.get_gold()
            if gold > 0:
                room.return_gold_to_reserve(gold)
            for rid, amt in list(room.get_all_resources().items()):
                if amt > 0:
                    room.return_resource_to_reserve(rid, amt)
            room.delete()

        self.state = "done"
        self.stop()
        self.delete()

    # ------------------------------------------------------------------ #
    #  Periodic tick
    # ------------------------------------------------------------------ #

    def at_repeat(self):
        """Check timers and collapse conditions."""
        if self.state == "done":
            self.stop()
            return

        now = timezone.now()
        template = self.template

        # Instance lifetime expired? (skipped if persistent_until_empty)
        if not template.persistent_until_empty and self.created_at:
            elapsed = (now - self.created_at).total_seconds()
            if elapsed >= template.instance_lifetime_seconds:
                self.collapse_instance()
                return

        # All characters left? Collapse (with optional delay).
        if not self.get_characters():
            if template.empty_collapse_delay > 0:
                if not self.emptied_at:
                    self.emptied_at = now
                elapsed = (now - self.emptied_at).total_seconds()
                if elapsed >= template.empty_collapse_delay:
                    self.collapse_instance()
            else:
                self.collapse_instance()
            return

        # Characters present — reset empty timer
        self.emptied_at = None
