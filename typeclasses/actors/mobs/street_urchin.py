"""
Street Urchin — pickpocketing thief mob for Millholm streets.

Level 3 thief with SKILLED subterfuge. Wanders the same patrol area
as the city watch. When a player enters the room, waits 10 seconds
then attempts to pickpocket 1 gold. Players learn to avoid lingering
in the same room.

Pickpocket is a simplified mob-specific behaviour (not the player
CmdPickpocket — no case requirement, fixed 1 gold target). Contested
roll: d20 + DEX mod + SUBTERFUGE bonus vs 10 + target perception.

Success: steals 1 gold, taunting message.
Failure: caught message, player can attack.
"""

import random

from evennia.typeclasses.attributes import AttributeProperty
from evennia.utils.utils import delay

from enums.mastery_level import MasteryLevel
from typeclasses.actors.mob import CombatMob
from utils.dice_roller import dice


# Subterfuge mastery bonus at SKILLED
_SUBTERFUGE_BONUS = MasteryLevel.SKILLED.bonus


class StreetUrchin(CombatMob):
    """A street urchin with quick fingers."""

    # ── Combat ──
    damage_dice = AttributeProperty("1d3")
    attack_message = AttributeProperty("kicks at")
    attack_delay_min = AttributeProperty(3)
    attack_delay_max = AttributeProperty(5)

    # ── Gold loot ──
    loot_gold_max = AttributeProperty(5)

    # ── Behavior ──
    aggro_hp_threshold = AttributeProperty(0.5)  # flees early
    max_per_room = AttributeProperty(1)

    # ── AI timing ──
    ai_tick_interval = AttributeProperty(8)
    respawn_delay = AttributeProperty(600)  # 10 minutes

    # ── Pickpocket delay ──
    _pickpocket_delay = 10  # seconds before attempting

    def at_object_creation(self):
        super().at_object_creation()
        self.base_strength = 8
        self.base_dexterity = 14
        self.base_constitution = 10
        self.base_intelligence = 12
        self.base_wisdom = 10
        self.base_charisma = 10
        self.strength = 8
        self.dexterity = 14
        self.constitution = 10
        self.intelligence = 12
        self.wisdom = 10
        self.charisma = 10
        self.base_armor_class = 10
        self.armor_class = 10
        self.base_hp_max = 12
        self.hp_max = 12
        self.hp = 12
        self.level = 3

    def at_new_arrival(self, arriving_obj):
        """When a player enters, schedule a pickpocket attempt."""
        if not getattr(arriving_obj, "is_pc", False):
            return
        if not self.is_alive:
            return
        if self.scripts.get("combat_handler"):
            return  # already fighting

        # Schedule the attempt — gives the player time to leave
        delay(self._pickpocket_delay, self._try_pickpocket, arriving_obj)

    def _try_pickpocket(self, target):
        """Attempt to steal 1 gold from a player."""
        # Safety checks — things may have changed in 10 seconds
        if not self.is_alive or not self.location:
            return
        if target.location != self.location:
            return  # player left the room
        if not getattr(target, "is_pc", False):
            return
        if getattr(target, "hp", 0) <= 0:
            return
        if self.scripts.get("combat_handler"):
            return  # got into a fight in the meantime

        # Not stupid enough to steal in front of the watch
        from typeclasses.actors.mobs.city_watch import CityWatch
        for obj in self.location.contents:
            if isinstance(obj, CityWatch) and getattr(obj, "is_alive", False):
                return

        # Check target has gold
        gold = target.get_gold() if hasattr(target, "get_gold") else 0
        if gold < 1:
            return  # nothing to steal

        # Contested roll: d20 + DEX mod + subterfuge vs 10 + perception
        dex_mod = self.get_attribute_bonus(self.dexterity)
        urchin_roll = dice.roll("1d20") + dex_mod + _SUBTERFUGE_BONUS
        target_dc = 10 + getattr(target, "effective_perception_bonus", 0)

        if urchin_roll >= target_dc:
            self._steal_success(target)
        else:
            self._steal_failure(target)

    def _steal_success(self, target):
        """Successfully pocket 1 gold."""
        if not hasattr(target, "transfer_gold_to"):
            return
        target.transfer_gold_to(self, 1)

        target.msg(
            f"|yYou feel a light tug at your belt... "
            f"{self.key} has stolen 1 gold from you!|n"
        )
        if self.location:
            self.location.msg_contents(
                f"|y{self.key} deftly lifts a coin from {target.key}'s belt!|n",
                exclude=[target],
            )

    def _steal_failure(self, target):
        """Caught! Alert the player."""
        target.msg(
            f"|r{self.key} tries to slip a hand into your coin pouch "
            f"but you catch them in the act!|n"
        )
        if self.location:
            self.location.msg_contents(
                f"|r{self.key} is caught trying to pickpocket {target.key}!|n",
                exclude=[target],
            )
