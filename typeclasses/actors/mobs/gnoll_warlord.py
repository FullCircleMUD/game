"""
Gnoll Warlord — unique boss in the Gnoll Camp.

The toughest mob in Millholm. A massive gnoll war leader who never
retreats. Inherits Rampage from Gnoll (instant free attack on kill).
Dodges 20% of attacks. Fixed position — never wanders from camp.

Stats: L6, 75HP, 2d6+3 (STR 16), AC 16.
Designed for a party of level 5-6 players.
"""

import random

from evennia.typeclasses.attributes import AttributeProperty

from typeclasses.actors.mobs.gnoll import Gnoll


class GnollWarlord(Gnoll):
    """A massive gnoll warlord. Rampages, never retreats, dodges."""

    is_unique = AttributeProperty(True)

    # ── Stats ──
    hp = AttributeProperty(75)
    hp_max = AttributeProperty(75)
    strength = AttributeProperty(16)
    dexterity = AttributeProperty(12)
    constitution = AttributeProperty(16)
    base_armor_class = AttributeProperty(16)
    armor_class = AttributeProperty(16)
    level = AttributeProperty(6)

    # ── Combat ──
    damage_dice = AttributeProperty("2d6")  # +3 from STR 16
    attack_message = AttributeProperty("cleaves at")
    attack_delay_min = AttributeProperty(3)
    attack_delay_max = AttributeProperty(6)

    # ── Behavior ──
    aggro_hp_threshold = AttributeProperty(0.0)  # never flees
    max_per_room = AttributeProperty(1)

    # ── AI timing ──
    ai_tick_interval = AttributeProperty(8)
    respawn_delay = AttributeProperty(600)  # 10 minutes

    # ── Combat Tick — dodge 20% ──

    def at_combat_tick(self, handler):
        """80% attack as normal, 20% dodge."""
        if random.random() < 0.20:
            self.execute_cmd("dodge")

    # ── No Wander — fixed position boss ──

    def ai_wander(self):
        """Scan for players but never leave the room."""
        if not self.location:
            return
        if self.scripts.get("combat_handler"):
            return

        players = self.ai.get_targets_in_room()
        if players:
            self._schedule_attack(random.choice(players))

    # ── Never Retreat ──

    def ai_retreating(self):
        """Warlord never retreats — switch back to wander immediately."""
        self.ai.set_state("wander")

    # Rampage inherited from Gnoll — at_kill() fires instant free attack
