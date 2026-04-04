"""
City Watch — roaming patrol guards for Millholm town streets.

Tier 2 NPC intelligence: lore-aware with short-term rolling memory.
Same stats and loadout as MeleeGuard (level 5, 65 HP, leather armor,
shield, bronze shortsword, skilled shortsword + skilled bash) but
these mobs wander the town streets on patrol.

Patrol area defined by mob_area tag "city_watch_patrol" on street
rooms. Wandering uses CombatMob.ai_wander() (30% chance to move
per tick, area-contained by mob_area tag).

Passive — fight back when attacked, don't aggro on sight.
"""

from evennia.typeclasses.attributes import AttributeProperty

from typeclasses.actors.mob import CombatMob
from typeclasses.actors.mobs.town_guard import MeleeGuard


class CityWatch(MeleeGuard):
    """Roaming city watch guard. Same as MeleeGuard but wanders town streets."""

    room_description = AttributeProperty("patrols the streets, eyes scanning the crowd.")

    def ai_wander(self):
        """Override MeleeGuard's stationary no-op — city watch patrols."""
        CombatMob.ai_wander(self)
