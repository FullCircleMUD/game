"""
Wolf — predator mob that hunts rabbits AND attacks players.

Extends AggressiveMob with rabbit hunting. Players are higher priority
targets. Balanced for level 1-3 combat: a lucky level 1 can beat one,
level 2-3 handle them easily.

max_per_room = 1 prevents wolves from stacking in the same room, so
players won't get ganged up on.

When below 50% health and not in combat, retreats to the den to heal.
"""

import random

from evennia.typeclasses.attributes import AttributeProperty

from typeclasses.actors.mobs.aggressive_mob import AggressiveMob


class Wolf(AggressiveMob):
    """A grey wolf — hunts rabbits and attacks players."""

    # ── Stats ──
    hp = AttributeProperty(12)
    hp_max = AttributeProperty(12)
    strength = AttributeProperty(12)
    dexterity = AttributeProperty(13)
    constitution = AttributeProperty(12)
    base_armor_class = AttributeProperty(11)
    armor_class = AttributeProperty(11)
    level = AttributeProperty(2)

    # ── Combat ──
    damage_dice = AttributeProperty("1d4")
    attack_message = AttributeProperty("bites")
    attack_delay_min = AttributeProperty(2)
    attack_delay_max = AttributeProperty(8)

    # ── Behavior ──
    aggro_hp_threshold = AttributeProperty(0.5)
    max_per_room = AttributeProperty(1)

    # ── Loot — resource spawn service fills up to these caps ──
    loot_resources = AttributeProperty({8: 1})  # max 1 hide

    # ── AI timing ──
    ai_tick_interval = AttributeProperty(8)
    respawn_delay = AttributeProperty(120)

    # ── Area ──
    den_room_tag = AttributeProperty("woods_wolves")

    def at_object_creation(self):
        super().at_object_creation()
        self.tags.add("woods_wolves", category="mob_area")

    def at_new_arrival(self, arriving_obj):
        """Aggro players (via super) and also hunt rabbits."""
        if not self.is_alive or arriving_obj == self:
            return
        if self.is_low_health:
            return

        # Rabbits — hunt them
        from typeclasses.actors.mobs.rabbit import Rabbit
        if isinstance(arriving_obj, Rabbit) and arriving_obj.is_alive:
            self._schedule_attack(arriving_obj)
            return

        # Players — delegate to AggressiveMob
        super().at_new_arrival(arriving_obj)

    def ai_wander(self):
        """Scan for players (priority) then rabbits, then wander."""
        if not self.location:
            return
        if self.is_low_health:
            self.ai.set_state("retreating")
            return
        if self.scripts.get("combat_handler"):
            return

        # Players first (higher priority)
        players = self.ai.get_targets_in_room()
        if players:
            self._schedule_attack(random.choice(players))
            return

        # Then rabbits
        from typeclasses.actors.mobs.rabbit import Rabbit
        rabbits = [
            obj for obj in self.location.contents
            if isinstance(obj, Rabbit) and obj.is_alive
        ]
        if rabbits:
            self._schedule_attack(random.choice(rabbits))
            return

        # Otherwise wander
        if random.random() < 0.25:
            self.wander()

    def ai_retreating(self):
        """Head to the den to heal."""
        if not self.location:
            return

        den_tags = self.location.tags.get(
            category="mob_area", return_list=True
        ) or []
        if self.den_room_tag in den_tags:
            if self.hp < self.hp_max:
                self.hp = min(self.hp_max, self.hp + 2)
            if self.hp >= self.hp_max:
                self.ai.set_state("wander")
            return

        self.retreat_to_spawn()
