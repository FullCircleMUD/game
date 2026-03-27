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

from typeclasses.actors.mobs.aggressive_mob import AggressiveMob


class KoboldChieftain(AggressiveMob):
    """A cunning kobold chieftain. Fights alone, dodges, rallies allies."""

    is_unique = AttributeProperty(True)
    size = AttributeProperty("small")

    # ── Stats ──
    hp = AttributeProperty(28)
    hp_max = AttributeProperty(28)
    strength = AttributeProperty(12)
    dexterity = AttributeProperty(14)
    constitution = AttributeProperty(12)
    base_armor_class = AttributeProperty(13)
    armor_class = AttributeProperty(13)
    level = AttributeProperty(3)

    # ── Combat ──
    damage_dice = AttributeProperty("1d6")  # +1 from STR 12
    attack_message = AttributeProperty("slashes at")
    attack_delay_min = AttributeProperty(2)
    attack_delay_max = AttributeProperty(5)

    # ── Gold loot ──
    loot_gold_max = AttributeProperty(12)

    # ── Knowledge loot ──
    scroll_loot_slots = AttributeProperty(1)
    recipe_loot_slots = AttributeProperty(1)

    # ── Behavior ──
    aggro_hp_threshold = AttributeProperty(0.3)  # fights to 30%
    max_per_room = AttributeProperty(1)

    # ── AI timing ──
    ai_tick_interval = AttributeProperty(6)
    respawn_delay = AttributeProperty(600)  # 10 minutes

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

    # ── Respawn Reset ──

    def _respawn(self):
        """Reset rally cry flag on respawn."""
        self.db.has_rallied = False
        super()._respawn()
