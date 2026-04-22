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
    allow_death = AttributeProperty(False, autocreate=False)

    def at_object_creation(self):
        super().at_object_creation()
        self.cmdset.add(CmdSetHarvesting, persistent=True)
        # Unified spawn system: tag for target pooling. The matching
        # spawn_resources_max dict is built in at_object_post_creation,
        # because at this point the attributes= kwarg from create_object()
        # has not yet been applied — self.resource_id still returns the
        # AttributeProperty default (1), not the zone-builder value.
        self.tags.add("spawn_resources", category="spawn_resources")

    def at_object_post_creation(self):
        super().at_object_post_creation()
        # Fires after the attributes= kwarg has been applied, so
        # self.resource_id and self.resource_count_max hold the
        # zone-builder-supplied values.
        self.db.spawn_resources_max = {self.resource_id: self.resource_count_max}

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
