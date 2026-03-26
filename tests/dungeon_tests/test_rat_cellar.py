"""
Tests for the Rat Cellar quest system.

Covers: mob stats, dungeon template, quest lifecycle, quest-gated exit,
defeat system fixes, and bartender heal.

evennia test --settings settings tests.dungeon_tests.test_rat_cellar
"""

from evennia import create_object
from evennia.utils import create
from evennia.utils.test_resources import EvenniaCommandTest

from typeclasses.scripts.dungeon_instance import DungeonInstanceScript
from world.dungeons import register_dungeon, DUNGEON_REGISTRY
from world.dungeons.dungeon_template import DungeonTemplate


# ------------------------------------------------------------------ #
#  Simple test room generator (no mobs — for isolated tests)
# ------------------------------------------------------------------ #

def _bare_room_generator(instance, depth, coords):
    """Generate a bare dungeon room without spawning mobs."""
    from typeclasses.terrain.rooms.dungeon.dungeon_room import DungeonRoom

    room = create_object(DungeonRoom, key="Test Cellar")
    room.db.desc = "A test cellar room."
    return room


_DEFEAT_TEST_TEMPLATE = DungeonTemplate(
    template_id="defeat_test",
    name="Defeat Test",
    dungeon_type="instance",
    instance_mode="solo",
    boss_depth=99,
    max_unexplored_exits=0,
    max_new_exits_per_room=0,
    instance_lifetime_seconds=1800,
    room_generator=_bare_room_generator,
    allow_combat=True,
    allow_death=False,
    defeat_destination_key=None,  # will use self.home
)


# ------------------------------------------------------------------ #
#  Mob stat tests
# ------------------------------------------------------------------ #

class TestCellarRatStats(EvenniaCommandTest):
    """Verify CellarRat mob stats."""

    databases = "__all__"

    def create_script(self):
        pass

    def test_cellar_rat_stats(self):
        from typeclasses.actors.mobs.cellar_rat import CellarRat

        rat = create_object(CellarRat, key="test rat")
        self.assertEqual(rat.hp, 4)
        self.assertEqual(rat.hp_max, 4)
        self.assertEqual(rat.level, 1)
        self.assertEqual(rat.size, "small")
        self.assertEqual(rat.damage_dice, "1d2")
        self.assertTrue(rat.is_aggressive_to_players)
        rat.delete()

    def test_rat_king_stats(self):
        from typeclasses.actors.mobs.rat_king import RatKing

        king = create_object(RatKing, key="test king")
        self.assertEqual(king.hp, 10)
        self.assertEqual(king.hp_max, 10)
        self.assertEqual(king.level, 2)
        self.assertEqual(king.size, "medium")
        self.assertEqual(king.damage_dice, "1d4")
        self.assertTrue(king.is_aggressive_to_players)
        king.delete()


# ------------------------------------------------------------------ #
#  Defeat system fix tests
# ------------------------------------------------------------------ #

class TestDefeatFixes(EvenniaCommandTest):
    """Test _defeat() combat stop and dungeon tag removal."""

    character_typeclass = "typeclasses.actors.character.FCMCharacter"
    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        DUNGEON_REGISTRY.clear()
        register_dungeon(_DEFEAT_TEST_TEMPLATE)

    def test_defeat_removes_dungeon_tag(self):
        """_defeat() should remove the dungeon_character tag."""
        # Simulate being in a dungeon by adding a tag
        self.char1.tags.add("defeat_test_123", category="dungeon_character")

        # Set up a no-death room
        self.room1.allow_death = False
        self.room1.defeat_destination = self.room2

        # Trigger defeat
        self.char1._defeat(self.room1, "combat")

        # Tag should be removed
        tag = self.char1.tags.get(category="dungeon_character")
        self.assertIsNone(tag)

    def test_defeat_teleports_to_destination(self):
        """_defeat() should teleport character to defeat_destination."""
        self.room1.allow_death = False
        self.room1.defeat_destination = self.room2

        self.char1._defeat(self.room1, "combat")

        self.assertEqual(self.char1.location, self.room2)
        self.assertEqual(self.char1.hp, 1)


# ------------------------------------------------------------------ #
#  Defeat destination resolution tests
# ------------------------------------------------------------------ #

class TestDefeatDestinationResolution(EvenniaCommandTest):
    """Test that dungeon instances resolve defeat_destination_key."""

    character_typeclass = "typeclasses.actors.character.FCMCharacter"
    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        DUNGEON_REGISTRY.clear()

        # Create a named room to serve as defeat destination
        self.inn_room = create_object(
            "typeclasses.terrain.rooms.room_base.RoomBase",
            key="Test Inn Room",
        )

        # Template that references the inn by key
        self._template = DungeonTemplate(
            template_id="dest_test",
            name="Dest Test",
            dungeon_type="instance",
            instance_mode="solo",
            boss_depth=99,
            max_unexplored_exits=0,
            max_new_exits_per_room=0,
            instance_lifetime_seconds=1800,
            room_generator=_bare_room_generator,
            allow_combat=True,
            allow_death=False,
            defeat_destination_key="Test Inn Room",
        )
        register_dungeon(self._template)

    def tearDown(self):
        if self.inn_room and self.inn_room.pk:
            self.inn_room.delete()
        super().tearDown()

    def test_defeat_destination_resolved(self):
        """start_dungeon should set defeat_destination from template key."""
        instance = create.create_script(
            DungeonInstanceScript,
            key="dest_test_1",
            autostart=False,
        )
        instance.template_id = "dest_test"
        instance.instance_key = "dest_test_1"
        instance.entrance_room_id = self.room1.id
        instance.start()

        try:
            instance.start_dungeon([self.char1])

            dungeon_room = self.char1.location
            self.assertEqual(dungeon_room.defeat_destination, self.inn_room)
        finally:
            instance.collapse_instance()


# ------------------------------------------------------------------ #
#  Quest-gated exit tests
# ------------------------------------------------------------------ #

class TestConditionalDungeonExit(EvenniaCommandTest):
    """Test ConditionalDungeonExit quest gating routing behavior."""

    character_typeclass = "typeclasses.actors.character.FCMCharacter"
    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        DUNGEON_REGISTRY.clear()

        # Re-register explicitly (cached import won't re-run module-level code)
        from world.dungeons.templates.rat_cellar import RAT_CELLAR
        register_dungeon(RAT_CELLAR)

        # Create fallback room (permanent cellar)
        self.fallback_room = create_object(
            "typeclasses.terrain.rooms.room_base.RoomBase",
            key="Permanent Cellar",
        )

    def tearDown(self):
        # Clean up dungeon instances
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
        if self.fallback_room and self.fallback_room.pk:
            self.fallback_room.delete()
        super().tearDown()

    def test_completed_quest_routes_to_fallback(self):
        """When quest is completed, exit should route to fallback room."""
        from typeclasses.terrain.exits.conditional_dungeon_exit import (
            ConditionalDungeonExit,
        )
        from world.quests.rat_cellar import RatCellarQuest

        # Complete the quest (set status directly to avoid blockchain gold reward)
        quest = self.char1.quests.add(RatCellarQuest)
        quest.status = "completed"

        # Create the exit
        trigger = create_object(
            ConditionalDungeonExit,
            key="south",
            location=self.room1,
            destination=self.room1,
        )
        trigger.dungeon_template_id = "rat_cellar"
        trigger.condition_type = "quest_active"
        trigger.condition_key = "rat_cellar"
        trigger.alternate_destination_id = self.fallback_room.id

        # Traverse
        trigger.at_traverse(self.char1, self.room1)

        # Should be in the fallback room (permanent cellar)
        self.assertEqual(self.char1.location, self.fallback_room)

    def test_no_quest_routes_to_fallback(self):
        """When quest not accepted, exit should route to fallback room."""
        from typeclasses.terrain.exits.conditional_dungeon_exit import (
            ConditionalDungeonExit,
        )

        trigger = create_object(
            ConditionalDungeonExit,
            key="south",
            location=self.room1,
            destination=self.room1,
        )
        trigger.dungeon_template_id = "rat_cellar"
        trigger.condition_type = "quest_active"
        trigger.condition_key = "rat_cellar"
        trigger.alternate_destination_id = self.fallback_room.id

        trigger.at_traverse(self.char1, self.room1)

        # Quest should NOT be auto-accepted
        self.assertFalse(self.char1.quests.has("rat_cellar"))

        # Character should be in the fallback room (ordinary cellar)
        self.assertEqual(self.char1.location, self.fallback_room)

    def test_active_quest_enters_dungeon(self):
        """When quest is active, exit should create dungeon instance."""
        from typeclasses.terrain.exits.conditional_dungeon_exit import (
            ConditionalDungeonExit,
        )
        from world.quests.rat_cellar import RatCellarQuest

        # Accept the quest first
        self.char1.quests.add(RatCellarQuest)

        trigger = create_object(
            ConditionalDungeonExit,
            key="south",
            location=self.room1,
            destination=self.room1,
        )
        trigger.dungeon_template_id = "rat_cellar"
        trigger.condition_type = "quest_active"
        trigger.condition_key = "rat_cellar"
        trigger.alternate_destination_id = self.fallback_room.id

        trigger.at_traverse(self.char1, self.room1)

        # Character should be in a dungeon room (not room1 or fallback)
        self.assertNotEqual(self.char1.location, self.room1)
        self.assertNotEqual(self.char1.location, self.fallback_room)
        self.assertEqual(self.char1.location.key, "Dank Cellar")


# ------------------------------------------------------------------ #
#  Quest completion tests
# ------------------------------------------------------------------ #

class TestRatCellarQuest(EvenniaCommandTest):
    """Test RatCellarQuest lifecycle."""

    character_typeclass = "typeclasses.actors.character.FCMCharacter"
    databases = "__all__"

    def create_script(self):
        pass

    def test_boss_killed_completes_quest(self):
        """Quest completes on boss_killed event."""
        from unittest.mock import patch

        from world.quests.rat_cellar import RatCellarQuest

        quest = self.char1.quests.add(RatCellarQuest)
        self.assertFalse(quest.is_completed)

        # Mock rewards to avoid blockchain DB dependency
        with patch.object(self.char1, "receive_gold_from_reserve"), \
             patch.object(self.char1, "receive_resource_from_reserve"):
            self.char1.quests.check_progress(
                "boss_killed",
                quest_keys=["rat_cellar"],
            )

        quest = self.char1.quests.get("rat_cellar")
        self.assertTrue(quest.is_completed)

    def test_quest_not_repeatable(self):
        """Completed quest cannot be re-accepted."""
        from world.quests.rat_cellar import RatCellarQuest

        quest = self.char1.quests.add(RatCellarQuest)
        quest.status = "completed"  # avoid blockchain gold reward

        can_accept, reason = RatCellarQuest.can_accept(self.char1)
        self.assertFalse(can_accept)


# ------------------------------------------------------------------ #
#  Inn heal tests
# ------------------------------------------------------------------ #

class TestInnHealOnDefeat(EvenniaCommandTest):
    """Test bartender heal when defeated player arrives at inn."""

    character_typeclass = "typeclasses.actors.character.FCMCharacter"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.inn = create_object(
            "typeclasses.terrain.rooms.room_inn.RoomInn",
            key="Test Inn",
        )

    def tearDown(self):
        if self.inn and self.inn.pk:
            self.inn.delete()
        super().tearDown()

    def test_heal_on_defeat_arrival(self):
        """Player with active rat quest and HP=1 gets healed at inn."""
        from world.quests.rat_cellar import RatCellarQuest

        self.char1.quests.add(RatCellarQuest)
        self.char1.hp = 1

        # Move to inn (triggers at_object_receive)
        self.char1.move_to(self.inn, quiet=True)

        # Should be fully healed
        self.assertEqual(self.char1.hp, self.char1.effective_hp_max)

    def test_no_heal_when_quest_complete(self):
        """Player with completed quest should NOT get healed."""
        from world.quests.rat_cellar import RatCellarQuest

        quest = self.char1.quests.add(RatCellarQuest)
        quest.status = "completed"  # avoid blockchain gold reward
        self.char1.hp = 1

        self.char1.move_to(self.inn, quiet=True)

        # Should still be at 1 HP
        self.assertEqual(self.char1.hp, 1)

    def test_no_heal_when_full_hp(self):
        """Player with full HP should NOT trigger the heal."""
        from world.quests.rat_cellar import RatCellarQuest

        self.char1.quests.add(RatCellarQuest)
        original_hp = self.char1.hp

        self.char1.move_to(self.inn, quiet=True)

        # HP unchanged
        self.assertEqual(self.char1.hp, original_hp)
