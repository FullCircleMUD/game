"""
Raven flock — 8 ravens perched in the Raven Tree room.

Peaceful by default. Attacking any raven pulls the entire flock into
combat via the follow-chain group mechanic used by the town guards:
followers auto-acquire the RavenFlockLeader via MobFollowableMixin,
and combat_utils.enter_combat() then pulls the leader's entire group
onto the defender's side when one is attacked.

The leader is structurally distinct (different typeclass) but visually
identical — same key, same desc — so players cannot single it out.

Loot variants share the same key/desc as the base raven so players
can't tell what's about to drop. Distribution is set in the spawn JSON
(1 leader + 5 base + 1 scroll + 1 recipe = 6 raven loads with gold,
1 scroll, 1 recipe).
"""

from evennia.typeclasses.attributes import AttributeProperty

from enums.damage_type import DamageType
from enums.size import Size
from typeclasses.actors.mob import CombatMob
from typeclasses.mixins.flying_mixin import FlyingMixin
from typeclasses.mixins.mob_behaviours.mob_followable_mixin import MobFollowableMixin


def _set_raven_stats(mob):
    """Shared stats for RavenFlockLeader + Raven. Identical on purpose."""
    mob.base_hp_max = 12
    mob.hp_max = 12
    mob.hp = 12
    mob.base_strength = 5
    mob.strength = 5
    mob.base_dexterity = 16
    mob.dexterity = 16
    mob.base_constitution = 10
    mob.constitution = 10
    mob.base_armor_class = 13
    mob.armor_class = 13
    mob.level = 3


class RavenFlockLeader(FlyingMixin, CombatMob):
    """Flock leader — other ravens follow this typeclass."""

    base_size = AttributeProperty(Size.SMALL.value)
    size = AttributeProperty(Size.SMALL.value)
    preferred_height = AttributeProperty(1)
    room_description = AttributeProperty(
        "perches motionless among the black branches, watching."
    )

    initiative_speed = AttributeProperty(3)
    damage_dice = AttributeProperty("1d4+1")
    damage_type = AttributeProperty(DamageType.PIERCING)
    attack_message = AttributeProperty("stabs at")
    attack_delay_min = AttributeProperty(2)
    attack_delay_max = AttributeProperty(4)

    loot_gold_max = AttributeProperty(3)

    max_per_room = AttributeProperty(0)
    ai_tick_interval = AttributeProperty(10)

    def at_object_creation(self):
        super().at_object_creation()
        _set_raven_stats(self)


class Raven(MobFollowableMixin, FlyingMixin, CombatMob):
    """Flock member — auto-acquires RavenFlockLeader on idle ticks."""

    squad_leader_typeclass = RavenFlockLeader

    base_size = AttributeProperty(Size.SMALL.value)
    size = AttributeProperty(Size.SMALL.value)
    preferred_height = AttributeProperty(1)
    room_description = AttributeProperty(
        "perches motionless among the black branches, watching."
    )

    initiative_speed = AttributeProperty(3)
    damage_dice = AttributeProperty("1d4+1")
    damage_type = AttributeProperty(DamageType.PIERCING)
    attack_message = AttributeProperty("stabs at")
    attack_delay_min = AttributeProperty(2)
    attack_delay_max = AttributeProperty(4)

    loot_gold_max = AttributeProperty(3)

    max_per_room = AttributeProperty(0)
    ai_tick_interval = AttributeProperty(10)

    def at_object_creation(self):
        super().at_object_creation()
        _set_raven_stats(self)


class RavenScrollLoad(Raven):
    """Loot variant — drops a skilled-tier scroll instead of gold."""

    loot_gold_max = AttributeProperty(0)
    spawn_scrolls_max = AttributeProperty({"skilled": 1})


class RavenRecipeLoad(Raven):
    """Loot variant — drops a skilled-tier recipe instead of gold."""

    loot_gold_max = AttributeProperty(0)
    spawn_recipes_max = AttributeProperty({"skilled": 1})
