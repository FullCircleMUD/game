"""
PackCourageMixin — pack-fighting behavior for mobs.

Mobs with this mixin only attack when enough allies of the **same type**
are in the room.  Solo mobs flee.  Cornered mobs (no valid exit) fight
regardless of pack size.  Mid-combat, if allies die and courage is lost
the mob attempts to flee.

`_count_allies()` uses `self.__class__` so a Kobold counts other Kobolds,
a Crow counts other Crows, etc. — no cross-species courage.

Usage:
    class Kobold(PackCourageMixin, AggressiveMob):
        min_allies_to_attack = AttributeProperty(1)
        flee_message = AttributeProperty("{name} squeals in panic and flees!")
"""

import random

from evennia.typeclasses.attributes import AttributeProperty


class PackCourageMixin:
    """Fights only when enough allies of the same type are present."""

    min_allies_to_attack = AttributeProperty(1)
    flee_message = AttributeProperty("{name} panics and flees!")

    # ── Pack helpers ──

    def _count_allies(self):
        """Count living mobs of the same class in the room (excl self)."""
        if not self.location:
            return 0
        my_class = self.__class__
        return sum(
            1 for obj in self.location.contents
            if isinstance(obj, my_class) and obj != self and obj.is_alive
        )

    def _has_pack_courage(self):
        """True if enough allies present to fight."""
        return self._count_allies() >= self.min_allies_to_attack

    def _is_cornered(self):
        """True if there's no valid exit to flee through."""
        exits = self.ai.get_area_exits()
        return len(exits) == 0

    # ── Aggro gate ──

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
            self._flee_from_threat()

    def _flee_from_threat(self):
        """Flee to an adjacent room with a flavoured message."""
        exi = self.ai.pick_random_exit()
        if exi:
            if self.location:
                msg = self.flee_message.format(name=self.key)
                self.location.msg_contents(msg, exclude=[self])
            self.move_to(exi.destination, quiet=False)

    # ── AI wander override ──

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
