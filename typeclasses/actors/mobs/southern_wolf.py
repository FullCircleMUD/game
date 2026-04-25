"""
Southern Wolves — pack-hunting predators of the southern forest quadrants.

A pack is one Direwolf alpha plus three SouthernWolf followers. Followers
use MobFollowableMixin with squad_leader_typeclass=Direwolf, mirroring the
south-gate guard squad pattern. When a follower lands in the same room as
a living alpha, ai_idle() locks it onto the alpha and Evennia's follow
chain keeps the pack moving as a unit when the alpha wanders.

Naming note: this Direwolf (lowercase 'w') is distinct from the legacy
DireWolf in dire_wolf.py (used only by test fixtures). They are separate
typeclasses with different stats and behavior.

Per-quadrant den_room_tag is set via the spawn rule's `attrs` field — each
of the four quadrants (NE/NW/SE/SW) has its own den room tagged in
world/game_world/zones/millholm/southern.py.
"""

from evennia.typeclasses.attributes import AttributeProperty

from enums.damage_type import DamageType
from enums.size import Size
from typeclasses.actors.mobs.aggressive_mob import AggressiveMob
from typeclasses.mixins.mob_behaviours.mob_followable_mixin import MobFollowableMixin


class Direwolf(AggressiveMob):
    """Pack alpha — leads a pack of southern wolves."""

    base_size = AttributeProperty(Size.LARGE.value)
    size = AttributeProperty(Size.LARGE.value)
    room_description = AttributeProperty(
        "stands head and shoulders above its kin, scarred muzzle low, amber eyes hard."
    )

    # ── Stats ──
    hp = AttributeProperty(35)
    base_hp_max = AttributeProperty(35)
    hp_max = AttributeProperty(35)
    base_strength = AttributeProperty(16)
    strength = AttributeProperty(16)
    base_dexterity = AttributeProperty(14)
    dexterity = AttributeProperty(14)
    base_constitution = AttributeProperty(14)
    constitution = AttributeProperty(14)
    base_armor_class = AttributeProperty(13)
    armor_class = AttributeProperty(13)
    level = AttributeProperty(6)

    # ── Combat ──
    initiative_speed = AttributeProperty(1)
    damage_dice = AttributeProperty("1d8+1")
    damage_type = AttributeProperty(DamageType.PIERCING)
    attack_message = AttributeProperty("savagely bites")
    attack_delay_min = AttributeProperty(2)
    attack_delay_max = AttributeProperty(6)

    # ── Loot ──
    loot_resources = AttributeProperty({8: 1})  # 1 hide
    loot_gold_max = AttributeProperty(5)

    # ── Behavior ──
    aggro_hp_threshold = AttributeProperty(0.5)
    max_per_room = AttributeProperty(1)

    # ── AI timing ──
    ai_tick_interval = AttributeProperty(6)

    # ── Retreat — set per-quadrant via spawn-rule attrs ──
    den_room_tag = AttributeProperty(None)

    def ai_retreating(self):
        """Heal when on a den-tagged room; otherwise teleport to spawn room."""
        if not self.location:
            return

        den_tags = self.location.tags.get(
            category="mob_area", return_list=True
        ) or []
        if self.den_room_tag and self.den_room_tag in den_tags:
            if self.hp < self.hp_max:
                self.hp = min(self.hp_max, self.hp + 3)
            if self.hp >= self.hp_max:
                self.ai.set_state("wander")
            return

        self.retreat_to_spawn()


class SouthernWolf(MobFollowableMixin, AggressiveMob):
    """Pack member — follows the Direwolf alpha when one is in the room."""

    squad_leader_typeclass = Direwolf

    room_description = AttributeProperty(
        "moves with the easy confidence of a pack hunter, ears pricked for the alpha's signal."
    )

    # ── Stats ──
    hp = AttributeProperty(18)
    base_hp_max = AttributeProperty(18)
    hp_max = AttributeProperty(18)
    base_strength = AttributeProperty(13)
    strength = AttributeProperty(13)
    base_dexterity = AttributeProperty(15)
    dexterity = AttributeProperty(15)
    base_constitution = AttributeProperty(12)
    constitution = AttributeProperty(12)
    base_armor_class = AttributeProperty(11)
    armor_class = AttributeProperty(11)
    level = AttributeProperty(4)

    # ── Combat ──
    initiative_speed = AttributeProperty(2)
    damage_dice = AttributeProperty("1d6")
    damage_type = AttributeProperty(DamageType.PIERCING)
    attack_message = AttributeProperty("bites")
    attack_delay_min = AttributeProperty(2)
    attack_delay_max = AttributeProperty(7)

    # ── Loot ──
    loot_resources = AttributeProperty({8: 1})  # 1 hide
    loot_gold_max = AttributeProperty(3)

    # ── Behavior ──
    aggro_hp_threshold = AttributeProperty(0.5)
    max_per_room = AttributeProperty(4)  # whole pack can stack in one room

    # ── AI timing ──
    ai_tick_interval = AttributeProperty(7)

    # ── Retreat — set per-quadrant via spawn-rule attrs ──
    den_room_tag = AttributeProperty(None)

    def ai_retreating(self):
        """Heal when on a den-tagged room; otherwise teleport to spawn room."""
        if not self.location:
            return

        den_tags = self.location.tags.get(
            category="mob_area", return_list=True
        ) or []
        if self.den_room_tag and self.den_room_tag in den_tags:
            if self.hp < self.hp_max:
                self.hp = min(self.hp_max, self.hp + 2)
            if self.hp >= self.hp_max:
                self.ai.set_state("wander")
            return

        self.retreat_to_spawn()


class SouthernWolfFatLoad(SouthernWolf):
    """Loot variant — drops animal fat instead of hide."""

    loot_resources = AttributeProperty({45: 1})  # 1 animal fat, no hide
