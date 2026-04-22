"""
Kobold Chieftain — unique mini-boss in the Kobold Warren.

A cunning kobold leader who fights alone (no pack courage). Fixed
position in the warren — never wanders. Dodges 20% of attacks via
at_combat_tick(). Emits a rally cry when first wounded below 50% HP.

Stats: L3, 28HP, 1d6+1 (STR 12), AC 13.
Designed for a solo L3 or a pair of L2s.
"""

import random

from evennia.typeclasses.attributes import AttributeProperty

from enums.mastery_level import MasteryLevel
from enums.size import Size
from typeclasses.actors.mobs.aggressive_mob import AggressiveMob
from typeclasses.items.mob_items.mob_item import MobItem
from typeclasses.mixins.mob_abilities.weapon_mastery import WeaponMasteryMixin
from typeclasses.mixins.wearslots.humanoid_wearslots import HumanoidWearslotsMixin


class KoboldChieftain(WeaponMasteryMixin, HumanoidWearslotsMixin, AggressiveMob):
    """A cunning kobold chieftain. Fights alone, dodges, rallies allies.

    Club + wooden shield. SKILLED club mastery gives stagger chance.
    """

    is_unique = AttributeProperty(False)
    base_size = AttributeProperty(Size.SMALL.value)
    size = AttributeProperty(Size.SMALL.value)
    default_weapon_masteries = {"club": MasteryLevel.SKILLED.value}
    room_description = AttributeProperty(
        "squats atop a heap of bones, tapping a heavy club against a battered shield."
    )

    # ── Stats ──
    hp = AttributeProperty(28)
    base_hp_max = AttributeProperty(28)
    hp_max = AttributeProperty(28)
    base_strength = AttributeProperty(12)
    strength = AttributeProperty(12)
    base_dexterity = AttributeProperty(14)
    dexterity = AttributeProperty(14)
    base_constitution = AttributeProperty(12)
    constitution = AttributeProperty(12)
    base_armor_class = AttributeProperty(13)
    armor_class = AttributeProperty(13)
    level = AttributeProperty(3)

    # ── Combat ──
    initiative_speed = AttributeProperty(1)
    damage_dice = AttributeProperty("1d6")  # +1 from STR 12
    attack_message = AttributeProperty("slashes at")
    attack_delay_min = AttributeProperty(2)
    attack_delay_max = AttributeProperty(5)

    # ── Gold loot ──
    loot_gold_max = AttributeProperty(6)

    # ── Knowledge loot ──
    spawn_scrolls_max = AttributeProperty({"skilled": 1})

    # ── Behavior ──
    aggro_hp_threshold = AttributeProperty(0.3)  # fights to 30%
    max_per_room = AttributeProperty(1)

    # ── AI timing ──
    ai_tick_interval = AttributeProperty(6)
    respawn_delay = AttributeProperty(600)  # 10 minutes

    def at_object_creation(self):
        super().at_object_creation()
        weapon = MobItem.spawn_mob_item("club", location=self)
        if weapon:
            self.wear(weapon)
        shield = MobItem.spawn_mob_item("wooden_shield", location=self)
        if shield:
            self.wear(shield)

    # ── Combat Tick — dodge 20% + rally cry ──

    def at_combat_tick(self, handler):
        """80% attack as normal, 20% dodge. Rally cry on first drop below 50%."""
        # Rally cry — one-time war cry when first wounded below 50%
        if (not self.db.has_rallied and self.hp_fraction < 0.5):
            self.db.has_rallied = True
            if self.location:
                self.location.msg_contents(
                    f"|y{self.key} lets out a shrill war cry that echoes "
                    f"through the tunnels!|n",
                    from_obj=self,
                )

        if random.random() < 0.20:
            self.execute_cmd("dodge")

    # ── No Wander — fixed position boss ──

    def ai_wander(self):
        """Scan for players but never leave the room."""
        if not self.location:
            return
        if self.is_low_health:
            self.ai.set_state("retreating")
            return
        if self.scripts.get("combat_handler"):
            return

        players = self.ai.get_targets_in_room()
        if players:
            self._schedule_attack(random.choice(players))

    # ── Retreat — fight to 30% then cower ──

    def ai_retreating(self):
        """Cower in place when badly wounded (no escape for a boss)."""
        if not self.location:
            return
        if self.hp_fraction >= self.aggro_hp_threshold:
            self.ai.set_state("wander")
            return
        # Boss doesn't flee — just stops being aggressive until healed


def reset_chieftain_state(mob):
    """Post-spawn hook: reset rally-cry flag on a JSON-spawned chieftain."""
    mob.db.has_rallied = False
