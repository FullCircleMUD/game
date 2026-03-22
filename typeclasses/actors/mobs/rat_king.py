"""
RatKing — mini-boss for the Harvest Moon cellar quest.

Tougher than regular cellar rats. Engages on a longer delay so the
smaller rats hit first. On death, fires quest completion event and
triggers the dungeon instance boss-defeated timer.
"""

import random

from evennia.typeclasses.attributes import AttributeProperty
from evennia.utils.utils import delay

from typeclasses.actors.mob import CombatMob


class RatKing(CombatMob):
    """An enormous rat king — boss of the cellar infestation."""

    size = AttributeProperty("medium")

    # ── Stats — level 2 mini-boss ──
    hp = AttributeProperty(15)
    hp_max = AttributeProperty(15)
    strength = AttributeProperty(10)
    dexterity = AttributeProperty(12)
    constitution = AttributeProperty(12)
    base_armor_class = AttributeProperty(11)
    armor_class = AttributeProperty(11)
    level = AttributeProperty(2)

    # ── Combat ──
    damage_dice = AttributeProperty("1d4")
    attack_message = AttributeProperty("savagely bites")
    attack_delay_min = AttributeProperty(5)
    attack_delay_max = AttributeProperty(8)

    # ── Behavior ──
    is_aggressive_to_players = AttributeProperty(True)
    ai_tick_interval = AttributeProperty(5)
    respawn_delay = AttributeProperty(0)  # dungeon mob, no respawn

    def at_new_arrival(self, arriving_obj):
        """Attack players on sight after a longer delay than regular rats."""
        if not self.is_alive or arriving_obj == self:
            return
        if getattr(arriving_obj, "is_pc", False):
            attack_delay = random.uniform(
                self.attack_delay_min, self.attack_delay_max
            )
            delay(attack_delay, self._initiate_attack, arriving_obj)

    def _initiate_attack(self, target):
        """Start combat if target is still valid."""
        if not self.is_alive or not self.location:
            return
        if not target.pk or target.location != self.location:
            return
        if getattr(target, "hp", 1) <= 0:
            return
        self.mob_attack(target)

    # ── AI States ──

    def ai_wander(self):
        """Seek players in room. No wandering (dungeon mob)."""
        if not self.location or not self.is_alive:
            return
        if self.scripts.get("combat_handler"):
            return
        players = self.ai.get_targets_in_room()
        if players:
            target = random.choice(players)
            attack_delay = random.uniform(
                self.attack_delay_min, self.attack_delay_max
            )
            delay(attack_delay, self._initiate_attack, target)

    # ── Death — fire quest completion ──

    def die(self, cause="unknown", killer=None):
        """On death, fire quest completion for characters in the instance."""
        room = self.location
        super().die(cause, killer=killer)

        if not room:
            return

        # Find the dungeon instance via the room's tag
        instance_tag = room.tags.get(category="dungeon_room")
        if not instance_tag:
            return

        from evennia import ScriptDB

        try:
            instance = ScriptDB.objects.get(db_key=instance_tag)
        except ScriptDB.DoesNotExist:
            return

        # Notify all characters in the instance
        for char in instance.get_characters():
            char.msg("|gThe Rat King has been slain! The cellar falls quiet.|n")
            if hasattr(char, "quests"):
                char.quests.check_progress(
                    "boss_killed",
                    quest_keys=["rat_cellar"],
                    source=self,
                )

        # Start post-boss collapse timer
        instance.on_boss_defeated()
