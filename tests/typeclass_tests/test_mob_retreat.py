"""
Tests for Mob.retreat_to_spawn — the move itself, and the combat cleanup
that has to travel with it.

Retreating is the one way out of a fight that isn't death or fleeing, so
it carries the same obligation flee_from_combat does: end the retreating
mob's combat without ending anyone else's.

evennia test --settings settings tests.typeclass_tests.test_mob_retreat
"""

from evennia.utils import create
from evennia.utils.test_resources import EvenniaTest


class TestRetreatToSpawnMove(EvenniaTest):
    """Where the mob lands, and when it refuses to go."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.wolf = create.create_object(
            "typeclasses.actors.mobs.wolf.Wolf",
            key="a grey wolf",
            location=self.room1,
        )
        self.wolf.is_alive = True
        self.wolf.hp = 5
        self.wolf.spawn_room_id = self.room2.id

    def test_moves_to_spawn_room(self):
        self.wolf.retreat_to_spawn()
        self.assertEqual(self.wolf.location, self.room2)

    def test_no_spawn_room_id_stays_put(self):
        self.wolf.spawn_room_id = None
        self.wolf.retreat_to_spawn()
        self.assertEqual(self.wolf.location, self.room1)

    def test_already_at_spawn_stays_put(self):
        self.wolf.spawn_room_id = self.room1.id
        self.wolf.retreat_to_spawn()
        self.assertEqual(self.wolf.location, self.room1)

    def test_deleted_spawn_room_stays_put(self):
        gone = create.create_object(self.room_typeclass, key="gone")
        gone_id = gone.id
        gone.delete()
        self.wolf.spawn_room_id = gone_id
        self.wolf.retreat_to_spawn()
        self.assertEqual(self.wolf.location, self.room1)


class TestRetreatEndsCombat(EvenniaTest):
    """Retreating takes the combat handler with it."""

    character_typeclass = "typeclasses.actors.character.FCMCharacter"
    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.room1.allow_combat = True
        self.char1.hp = 50
        self.char1.hp_max = 50

        self.wolf = self._create_wolf("a grey wolf")
        self.wolf.spawn_room_id = self.room2.id

        from combat.combat_utils import enter_combat
        enter_combat(self.wolf, self.char1)

    def _create_wolf(self, key):
        wolf = create.create_object(
            "typeclasses.actors.mobs.wolf.Wolf", key=key, location=self.room1,
        )
        wolf.is_alive = True
        wolf.hp = 5
        return wolf

    def _in_combat(self, obj):
        return bool(obj.scripts.get("combat_handler"))

    def test_setup_puts_both_in_combat(self):
        """Guard — the rest of this class means nothing if this fails."""
        self.assertTrue(self._in_combat(self.wolf))
        self.assertTrue(self._in_combat(self.char1))

    def test_retreat_deletes_own_handler(self):
        self.wolf.retreat_to_spawn()
        self.assertFalse(self._in_combat(self.wolf))

    def test_retreat_clears_fighting_position(self):
        self.wolf.retreat_to_spawn()
        self.assertEqual(self.wolf.position, "standing")

    def test_lone_enemy_leaves_combat_too(self):
        """Nobody left to fight, so the player's combat ends as well."""
        self.wolf.retreat_to_spawn()
        self.assertFalse(self._in_combat(self.char1))

    def test_other_combatants_keep_fighting(self):
        """A wider brawl carries on without the mob that ran."""
        from combat.combat_utils import enter_combat
        second = self._create_wolf("a second grey wolf")
        enter_combat(second, self.char1)

        self.wolf.retreat_to_spawn()

        self.assertFalse(self._in_combat(self.wolf))
        self.assertTrue(self._in_combat(second))
        self.assertTrue(self._in_combat(self.char1))

    def test_retreat_outside_combat_is_harmless(self):
        """Most retreats happen with no fight running at all."""
        self.wolf.scripts.get("combat_handler")[0].stop_combat()
        self.wolf.retreat_to_spawn()
        self.assertEqual(self.wolf.location, self.room2)


class TestWolfAiRetreating(EvenniaTest):
    """The wolf state that calls retreat_to_spawn."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.wolf = create.create_object(
            "typeclasses.actors.mobs.wolf.Wolf",
            key="a grey wolf",
            location=self.room1,
        )
        self.wolf.is_alive = True
        self.wolf.hp = 5
        self.wolf.spawn_room_id = self.room2.id

    def _make_den(self, room):
        room.tags.add(self.wolf.den_room_tag, category="mob_area")

    def test_heals_while_at_the_den(self):
        self._make_den(self.room1)
        self.wolf.ai_retreating()
        self.assertEqual(self.wolf.location, self.room1)
        self.assertEqual(self.wolf.hp, 7)

    def test_returns_to_wander_when_healed(self):
        self._make_den(self.room1)
        self.wolf.hp = self.wolf.hp_max
        self.wolf.ai_retreating()
        self.assertEqual(self.wolf.ai.get_state(), "wander")

    def test_heads_for_the_den_when_away_from_it(self):
        self.wolf.ai_retreating()
        self.assertEqual(self.wolf.location, self.room2)
