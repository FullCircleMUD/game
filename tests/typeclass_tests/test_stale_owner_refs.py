"""Foreign-key caches must not survive an identity-map flush.

A container's ``contents_cache`` stores primary keys and resolves them through
the idmapper on every read, so it cannot go stale. A child stores the *resolved
object* in its foreign-key cache and never looks again. That asymmetry is why
the thing holding a parent pointer is the thing holding a corpse.

``TypedObject.at_idmapper_flush`` exists to clear those caches, but looks for
them under ``_<fieldname>_cache`` — where Django kept them before 2.0. They now
live in ``_state.fields_cache``, so it clears nothing. ``BaseActor`` overrides
the hook to clear its own and its contents'.

evennia test --settings settings tests.typeclass_tests.test_stale_owner_refs
"""

from evennia.objects.models import ObjectDB
from evennia.utils import create
from evennia.utils.idmapper.models import flush_cache
from evennia.utils.test_resources import EvenniaTest

_ROOM = "typeclasses.terrain.rooms.room_base.RoomBase"
_CHAR = "typeclasses.actors.character.FCMCharacter"
_MOB = "typeclasses.actors.mob.CombatMob"
_VANILLA_OBJ = "evennia.objects.objects.DefaultObject"


class TestUpstreamStillLeaks(EvenniaTest):
    """Records the bug being worked around, so a fix upstream is noticed."""

    def create_script(self):
        pass

    def test_vanilla_object_keeps_a_stale_owner_after_flush(self):
        """If this ever fails, upstream clears fields_cache and we can drop ours."""
        room = create.create_object(_ROOM, key="Upstream Room")
        holder = create.create_object(_VANILLA_OBJ, key="holder", location=room)
        item = create.create_object(_VANILLA_OBJ, key="item", location=holder)

        item.location  # bind the foreign-key cache
        cached_before = item._state.fields_cache.get("db_location")
        self.assertIsNotNone(cached_before)

        holder.at_idmapper_flush()

        self.assertIn(
            "db_location", item._state.fields_cache,
            "upstream now clears _state.fields_cache — BaseActor's override "
            "can be removed",
        )


class TestActorClearsItsOwnPointers(EvenniaTest):
    """The half `cce8f99` covered for mobs, now on every actor."""

    def create_script(self):
        pass

    def test_character_clears_its_own_fields_cache(self):
        char = create.create_object(_CHAR, key="Owner", location=self.room1)
        char.location  # bind
        self.assertIn("db_location", char._state.fields_cache)

        char.at_idmapper_flush()

        self.assertNotIn(
            "db_location", char._state.fields_cache,
            "actor kept its own stale room reference across a flush",
        )

    def test_mob_still_clears_its_own_fields_cache(self):
        """CombatMob's override was removed in favour of BaseActor's."""
        mob = create.create_object(_MOB, key="a test mob", location=self.room1)
        mob.location
        mob.at_idmapper_flush()
        self.assertNotIn("db_location", mob._state.fields_cache)


class TestActorClearsItsContentsPointers(EvenniaTest):
    """The observed bug: equipment pinning a dead copy of its owner."""

    # at_post_puppet writes a telemetry session row on the xrpl alias.
    databases = "__all__"

    def create_script(self):
        pass

    def test_carried_items_lose_their_stale_owner_reference(self):
        char = create.create_object(_CHAR, key="Carrier", location=self.room1)
        item = create.create_object(_VANILLA_OBJ, key="a sword", location=char)

        item.location  # bind the item to this instance of the owner
        self.assertIn("db_location", item._state.fields_cache)

        char.at_idmapper_flush()

        self.assertNotIn(
            "db_location", item._state.fields_cache,
            "carried item kept pointing at the owner instance that was flushed "
            "— this is what pins a dead character in memory",
        )

    def test_item_reresolves_to_the_live_owner_after_clearing(self):
        """Clearing is only useful if the next read finds the canonical object."""
        char = create.create_object(_CHAR, key="Rebinder", location=self.room1)
        item = create.create_object(_VANILLA_OBJ, key="a lamp", location=char)

        item.location
        char.at_idmapper_flush()

        self.assertIs(
            item.location, ObjectDB.objects.get(id=char.id),
            "item did not re-resolve to the canonical owner",
        )

    def test_flush_hook_does_not_evict_anything(self):
        """Clearing, not evicting — eviction would risk duplicate instances.

        ``flush_from_cache()`` pops from ``__instance_cache__``, the dict
        ``flush_instance_cache`` is iterating when it calls this hook.
        """
        char = create.create_object(_CHAR, key="Keeper", location=self.room1)
        item = create.create_object(_VANILLA_OBJ, key="a ring", location=char)
        cache = ObjectDB.__instance_cache__

        before = set(cache.keys())
        char.at_idmapper_flush()

        self.assertEqual(
            before - set(cache.keys()), set(),
            "the hook evicted objects from the identity map",
        )
        self.assertIn(item.id, cache)

    def test_puppeting_clears_stale_owner_references(self):
        """The path that actually fires in production.

        ``evennia_shards`` evicts a character at login with
        ``flush_from_cache(force=True)``, and ``force`` short-circuits the
        ``if force or self.at_idmapper_flush()`` test — so the flush hook never
        runs on the path that replaces the instance. Verified live: tracing the
        hook across an OOC/IC cycle recorded zero calls. ``at_post_puppet`` is
        where the clearing has to happen.
        """
        # char1 comes with an account attached; at_post_puppet needs one.
        char = self.char1
        item = create.create_object(_VANILLA_OBJ, key="a torch", location=char)

        item.location  # bind
        self.assertIn("db_location", item._state.fields_cache)

        char.at_post_puppet()

        self.assertNotIn(
            "db_location", item._state.fields_cache,
            "carried item kept its stale owner across puppeting — the corpse "
            "from the previous session stays pinned",
        )

    def test_force_flush_skips_the_idmapper_hook(self):
        """Records why at_idmapper_flush alone was not enough.

        If this ever fails, upstream has changed ``flush_from_cache`` to
        consult the hook even under ``force``, and the at_post_puppet call
        may be redundant.
        """
        char = create.create_object(_CHAR, key="Forced", location=self.room1)
        calls = []
        original = type(char).at_idmapper_flush
        try:
            type(char).at_idmapper_flush = lambda s: calls.append(s.pk) or True
            char.flush_from_cache(force=True)
        finally:
            type(char).at_idmapper_flush = original
        self.assertEqual(
            calls, [],
            "force=True now consults at_idmapper_flush — re-check whether the "
            "at_post_puppet clearing is still needed",
        )

    def test_survives_a_real_flush_without_raising(self):
        """The whole point of clearing over evicting — no mutation mid-walk."""
        char = create.create_object(_CHAR, key="Flushed", location=self.room1)
        create.create_object(_VANILLA_OBJ, key="a coin", location=char)
        char.location
        flush_cache()  # must not raise RuntimeError
