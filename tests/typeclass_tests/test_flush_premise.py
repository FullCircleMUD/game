"""
Foreign-key caches surviving an Evennia identity-map flush.

Evennia flushes its identity map on a timer. An object that survives the flush —
a mob does, because its AI ticker holds it — keeps its own reference to the room
it is standing in, while the rest of the game gets a rebuilt room object. Its
next move then removes it from the discarded copy's contents cache, leaving the
rebuilt room listing a mob that is not in it.

``TypedObject.at_idmapper_flush`` means to prevent exactly this by clearing
foreign-key caches, but it looks for them under ``_<fieldname>_cache`` — where
Django kept them before 2.0. They now live in ``_state.fields_cache``, so it
clears nothing. ``CombatMob`` overrides the hook to clear them for real.

evennia test --settings settings tests.typeclass_tests.test_flush_premise
"""

from evennia.objects.models import ObjectDB
from evennia.utils import create
from evennia.utils.idmapper.models import flush_cache
from evennia.utils.test_resources import EvenniaTest

_ROOM = "typeclasses.terrain.rooms.room_base.RoomBase"
_VANILLA_OBJ = "evennia.objects.objects.DefaultObject"
_MOB = "typeclasses.actors.mob.CombatMob"


class TestForeignKeyCacheAcrossFlush(EvenniaTest):

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.a = create.create_object(_ROOM, key="room A")
        self.b = create.create_object(_ROOM, key="room B")

    def _stale_entries(self, room):
        return set(room.contents_cache._pkcache) - set(
            ObjectDB.objects.filter(db_location=room).values_list("id", flat=True)
        )

    def _move_across_flush(self, mover):
        """Flush, then move *mover* without re-fetching it, as a ticked mob does."""
        mover.location  # populate the mover's own reference to room A
        flush_cache()
        fresh_a = ObjectDB.objects.get(id=self.a.id)
        fresh_b = ObjectDB.objects.get(id=self.b.id)
        list(fresh_a.contents)  # something looks in A, building its cache
        mover.move_to(fresh_b)
        return fresh_a

    def test_evennia_leaves_a_stale_entry(self):
        """Upstream behaviour, recorded deliberately.

        A plain Evennia object still holds the discarded room and removes
        itself from that copy. Assert the bug rather than skip it — if a future
        Evennia fixes the field name, this fails and tells us the override can
        go.
        """
        mover = create.create_object(_VANILLA_OBJ, key="vanilla", location=self.a)
        fresh_a = self._move_across_flush(mover)
        self.assertEqual(
            self._stale_entries(fresh_a), {mover.id},
            "upstream appears to have fixed the foreign-key cache clearing — "
            "check whether CombatMob.at_idmapper_flush is still needed",
        )

    def test_mob_override_leaves_no_stale_entry(self):
        """The override drops the reference, so the removal lands correctly."""
        mob = create.create_object(_MOB, key="a test mob", location=self.a)
        fresh_a = self._move_across_flush(mob)
        self.assertEqual(
            self._stale_entries(fresh_a), set(),
            "room A kept an entry for a mob that left",
        )
