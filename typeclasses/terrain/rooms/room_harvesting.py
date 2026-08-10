"""
Resource harvesting room — gather raw materials one at a time.

Players use type-specific commands (mine, chop, harvest, hunt, fish, forage)
to gather resources. Each action takes 3 seconds and yields 1 unit. Players
don't know how many resources remain — they just keep gathering until "nothing
left." Resource counts are replenished hourly by the UnifiedSpawnScript.

Room description changes based on resource availability:
    >abundance_threshold  → desc_abundant  ("Resources are plentiful here.")
    1..abundance_threshold → desc_scarce   ("A few resources remain here.")
    0                      → desc_depleted ("There is nothing left to gather here.")

Examples:
    Iron Mine:   mine → 1 Iron Ore (harvest_height=0)
    Forest:      chop → 1 Wood (harvest_height=0)
    Seabed:      harvest → 1 Seaweed (harvest_height=-1)
    Cave Ceiling: forage → 1 Fairy Dust (harvest_height=1)
"""

from typeclasses.terrain.rooms.room_base import RoomBase
from evennia import AttributeProperty
from commands.room_specific_cmds.harvesting.cmdset_harvesting import CmdSetHarvesting


class RoomHarvesting(RoomBase):

    # Which resource can be harvested here (resource_id from seed data)
    resource_id = AttributeProperty(1)

    # Current available count (spawn system increments this hourly)
    resource_count = AttributeProperty(0)

    # Per-room cap — how much of the resource this room can hold at once.
    # Zone builders can override via attributes= kwarg (e.g. 5 for wood,
    # which has many rooms and floods easily).
    resource_count_max = AttributeProperty(10)

    # Count above which "abundant" description is shown
    abundance_threshold = AttributeProperty(5)

    # Height at which the resource can be harvested
    # 0=ground, -1=underwater, 1=flying, etc.
    harvest_height = AttributeProperty(0)

    # Which command works here: "mine", "chop", "harvest", "hunt", "fish", "forage"
    harvest_command = AttributeProperty("harvest")

    # Three-tier room descriptions based on resource_count
    desc_abundant = AttributeProperty("Resources are plentiful here.")
    desc_scarce = AttributeProperty("A few resources remain here.")
    desc_depleted = AttributeProperty("There is nothing left to gather here.")

    # Optional tool requirement (item key string, or None)
    required_tool = AttributeProperty(None)

    # XP awarded per successful harvest (0 = no XP)
    harvest_xp = AttributeProperty(1)

    # Wilderness rooms — combat allowed by default, settable per instance
    allow_combat = AttributeProperty(True, autocreate=False)
    allow_pvp = AttributeProperty(False, autocreate=False)
    allow_death = AttributeProperty(True, autocreate=False)

    def at_object_creation(self):
        super().at_object_creation()
        self.cmdset.add(CmdSetHarvesting, persistent=True)
        # Unified spawn system: tag for target pooling. The matching
        # spawn_resources_max dict is built post-attribute-apply by
        # at_object_post_creation (Python-direct creation, e.g. tutorial,
        # test_world, tests) and again by wb_at_post_build (YAML deploys
        # via evennia-world-builder). Both populate the same single
        # Attribute row; see those methods for details.
        self.tags.add("spawn_resources", category="spawn_resources")

    def at_object_post_creation(self):
        """Derive spawn_resources_max from current attribute state.

        Evennia's standard post-creation hook. Fires after the
        ``attributes=`` kwarg of ``create_object`` has been applied, so
        under Python-direct creation (tutorial harvest rooms,
        test_world economic fixtures, tests) ``self.resource_id`` and
        ``self.resource_count_max`` already hold the caller-supplied
        values by the time we run.

        Why the dict exists at all: the unified spawn distributor reads
        ``getattr(target.db, "spawn_resources_max", None)`` generically
        across rooms and mobs to know each target's per-resource cap
        (load-bearing call in
        ``blockchain/xrpl/services/spawn/distributors/base.py``). Mobs
        and chests genuinely carry multi-key dicts (a mob can drop
        several resources at distinct caps); a harvest room has one
        resource and reshapes its scalar ``resource_id`` +
        ``resource_count_max`` into a single-entry dict so the
        distributor can treat all target types uniformly.
        """
        super().at_object_post_creation()
        self.db.spawn_resources_max = {self.resource_id: self.resource_count_max}

    def wb_at_post_build(self):
        """Hook from ``evennia-world-builder``; re-derives the spawn dict
        after the library has applied YAML attributes.

        See ``libraries/evennia-world-builder/DESIGN/post-build-hook.md``
        for the library-side contract. The hook is duck-typed and
        opt-in; the library calls it on every just-built entity at the
        end of its ``_build_one`` pass.

        Why this hook is needed in addition to ``at_object_post_creation``:
        under Python-direct creation (tutorial, test_world, tests),
        Evennia's ``at_object_post_creation`` already fires after the
        ``attributes=`` kwarg of ``create_object`` lands, so one call
        produces the correct dict. Under ``wb_build``, the library
        passes only ``desc`` via that kwarg and applies every other
        YAML attribute via ``obj.attributes.add(...)`` *after*
        ``create_object`` returns. Evennia's hook therefore fires with
        the typeclass defaults still in place (``resource_id=1``,
        ``resource_count_max=10``) and the dict would lock in as
        ``{1: 10}`` for every harvest room regardless of authored
        resource_id. ``wb_at_post_build`` fires after the library's
        ``_apply_*`` steps, so the real YAML values are in place by
        the time it runs.

        Implementation: just recall ``at_object_post_creation`` so the
        derivation logic lives in one place (the method above). For
        the rationale on why the dict exists in the first place, see
        that method's docstring.

        Idempotency: under ``wb_build`` this method causes the
        derivation to run twice (once during ``create_object`` with
        defaults, once here with real values). Both writes go to the
        single ``Attribute`` row Evennia stores for
        ``(db_key="spawn_resources_max", db_category=None)``; the
        second write replaces the value of that row, no orphan dict.
        The redundant write is invisible against the rest of the
        ``wb_build`` cost.
        """
        self.at_object_post_creation()

    def get_display_desc(self, looker, **kwargs):
        """Return tier-appropriate description based on resource count."""
        if self.is_dark(looker):
            return "|xIt is pitch black. You can't see a thing.|n"

        if self.resource_count > self.abundance_threshold:
            abundance_line = self.desc_abundant
        elif self.resource_count > 0:
            abundance_line = self.desc_scarce
        else:
            abundance_line = self.desc_depleted

        # Include weather line if applicable (matching parent behavior)
        char_height = getattr(looker, "room_vertical_position", 0)
        if char_height >= 0:
            weather_line = self._get_weather_desc_line()
            if weather_line:
                return f"{abundance_line}\n{weather_line}"

        return abundance_line
