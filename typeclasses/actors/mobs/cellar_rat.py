"""
CellarRat — weak aggressive mob for the Harvest Moon cellar quest.

Small, fast, low HP. Attacks players on sight after a short delay.
Designed as dungeon instance mobs — no wander or respawn needed.
"""

from evennia.typeclasses.attributes import AttributeProperty

from typeclasses.actors.mobs.aggressive_mob import AggressiveMob


class CellarRat(AggressiveMob):
    """A large cellar rat. Aggressive but weak."""

    size = AttributeProperty("small")

    # ── Stats — level 1, fragile ──
    hp = AttributeProperty(4)
    hp_max = AttributeProperty(4)
    strength = AttributeProperty(4)
    dexterity = AttributeProperty(14)
    constitution = AttributeProperty(8)
    base_armor_class = AttributeProperty(10)
    armor_class = AttributeProperty(10)
    level = AttributeProperty(1)

    # ── Combat ──
    damage_dice = AttributeProperty("1d2")
    attack_message = AttributeProperty("bites")
    attack_delay_min = AttributeProperty(2)
    attack_delay_max = AttributeProperty(4)

    # ── Behavior ──
    ai_tick_interval = AttributeProperty(5)
    respawn_delay = AttributeProperty(0)  # dungeon mob, no respawn

    # ── AI States ──

    def ai_wander(self):
        """Seek players in room. No wandering (dungeon mob)."""
        if not self.location or not self.is_alive:
            return
        if self.scripts.get("combat_handler"):
            return
        players = self.ai.get_targets_in_room()
        if players:
            import random
            self._schedule_attack(random.choice(players))
