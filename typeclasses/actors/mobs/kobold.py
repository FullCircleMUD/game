"""
Kobold — cowardly pack fighter that only attacks with allies present.

Pack courage mechanic: a kobold needs at least `min_allies_to_attack`
other living kobolds in the same room to have the courage to fight.
Solo kobolds flee. Cornered kobolds (no valid exit) fight desperately.

Mid-combat check: if allies die and the kobold loses pack courage, it
attempts to flee on its next AI tick.

Designed for the Millholm Mine — L2 mobs, individually weak but
dangerous in groups of 2-3.
"""

import random

from evennia.typeclasses.attributes import AttributeProperty

from typeclasses.actors.mobs.aggressive_mob import AggressiveMob


class Kobold(AggressiveMob):
    """A small, cowardly kobold. Fights in packs, flees when alone."""

    size = AttributeProperty("small")

    # ── Stats ──
    hp = AttributeProperty(14)
    hp_max = AttributeProperty(14)
    strength = AttributeProperty(8)
    dexterity = AttributeProperty(14)
    constitution = AttributeProperty(10)
    base_armor_class = AttributeProperty(12)
    armor_class = AttributeProperty(12)
    level = AttributeProperty(2)

    # ── Combat ──
    damage_dice = AttributeProperty("1d4")
    attack_message = AttributeProperty("stabs at")
    attack_delay_min = AttributeProperty(2)
    attack_delay_max = AttributeProperty(5)

    # ── Behavior ──
    aggro_hp_threshold = AttributeProperty(0.7)  # flee early
    min_allies_to_attack = AttributeProperty(1)   # need 1+ ally

    # ── AI timing ──
    ai_tick_interval = AttributeProperty(6)
    respawn_delay = AttributeProperty(120)

    def _count_allies(self):
        """Count living kobolds in the same room (excluding self)."""
        if not self.location:
            return 0
        return sum(
            1 for obj in self.location.contents
            if isinstance(obj, Kobold) and obj != self and obj.is_alive
        )

    def _has_pack_courage(self):
        """True if enough allies present to fight."""
        return self._count_allies() >= self.min_allies_to_attack

    def _is_cornered(self):
        """True if there's no valid exit to flee through."""
        exits = self.ai.get_area_exits()
        return len(exits) == 0

    def at_new_arrival(self, arriving_obj):
        """Only aggro players if we have pack courage or are cornered."""
        if not self.is_alive or arriving_obj == self:
            return
        if self.is_low_health:
            return
        if not getattr(arriving_obj, "is_pc", False):
            return

        if self._has_pack_courage() or self._is_cornered():
            self._schedule_attack(arriving_obj)
        else:
            # Solo and not cornered — flee
            self._flee_from_threat()

    def _flee_from_threat(self):
        """Attempt to flee to an adjacent room."""
        exi = self.ai.pick_random_exit()
        if exi:
            if self.location:
                self.location.msg_contents(
                    f"{self.key} squeals in panic and flees!",
                    exclude=[self],
                )
            self.move_to(exi.destination, quiet=False)

    def ai_wander(self):
        """Pack courage check before engaging; flee if alone in combat."""
        if not self.location:
            return
        if self.is_low_health:
            self.ai.set_state("retreating")
            return

        # Mid-combat courage check — lost allies, try to flee
        in_combat = bool(self.scripts.get("combat_handler"))
        if in_combat:
            if not self._has_pack_courage() and not self._is_cornered():
                self.execute_cmd("flee")
            return

        # Not in combat — look for targets
        players = self.ai.get_targets_in_room()
        if players:
            if self._has_pack_courage() or self._is_cornered():
                self._schedule_attack(random.choice(players))
            else:
                self._flee_from_threat()
            return

        # No threats — wander
        if random.random() < 0.25:
            self.wander()
