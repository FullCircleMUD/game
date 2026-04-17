"""
Crow — flying pack predator.

The first flying mob in the game. Individually fragile (rabbit-tier HP)
but dangerous in packs of 3-5.  Uses PackCourageMixin for pack
fighting and FlyingMixin for innate flight.

Spawns airborne at preferred_height=1.  AggressiveMixin's
_try_match_height() handles descent to ground-level targets
automatically.  When idle (no combat, no threats) the crow re-ascends
to its preferred height.

Spawned in Millholm Woods (area_tag "woods_wolves") alongside wolves,
and in Millholm Farms abandoned farm (area_tag "abandoned_farm")
alongside rabbits.
"""

import random

from evennia.typeclasses.attributes import AttributeProperty

from enums.size import Size
from typeclasses.actors.mobs.aggressive_mob import AggressiveMob
from typeclasses.mixins.flying_mixin import FlyingMixin
from typeclasses.mixins.mob_behaviours.pack_courage_mixin import PackCourageMixin


class Crow(FlyingMixin, PackCourageMixin, AggressiveMob):
    """A black crow. Attacks in packs, flees when alone."""

    alignment_score = AttributeProperty(-30)  # slightly evil (aggressive pest)
    base_size = AttributeProperty("tiny")
    size = AttributeProperty("tiny")

    # ── Flight ──
    preferred_height = AttributeProperty(1)

    # ── Stats — fragile individually ──
    hp = AttributeProperty(4)
    base_hp_max = AttributeProperty(4)
    hp_max = AttributeProperty(4)
    base_strength = AttributeProperty(3)
    strength = AttributeProperty(3)
    base_dexterity = AttributeProperty(15)
    dexterity = AttributeProperty(15)
    base_constitution = AttributeProperty(4)
    constitution = AttributeProperty(4)
    base_armor_class = AttributeProperty(13)
    armor_class = AttributeProperty(13)
    level = AttributeProperty(1)

    # ── Combat ──
    initiative_speed = AttributeProperty(3)
    damage_dice = AttributeProperty("1d2")
    attack_message = AttributeProperty("pecks at")
    attack_delay_min = AttributeProperty(2)
    attack_delay_max = AttributeProperty(4)

    # ── Loot ──
    loot_gold_max = AttributeProperty(1)

    # ── Behavior ──
    aggro_hp_threshold = AttributeProperty(0.5)
    min_allies_to_attack = AttributeProperty(2)  # needs 2+ allies (3 total)
    flee_message = AttributeProperty("A crow caws in alarm and flaps away!")

    # ── AI timing ──
    ai_tick_interval = AttributeProperty(5)
    respawn_delay = AttributeProperty(30)

    def ai_wander(self):
        """Pack courage AI with re-ascend when idle."""
        super().ai_wander()

        # Re-ascend to preferred height when idle at ground level
        if (
            self.location
            and not self.scripts.get("combat_handler")
            and self.room_vertical_position < self.preferred_height
        ):
            self.ascend(self.preferred_height - self.room_vertical_position)
