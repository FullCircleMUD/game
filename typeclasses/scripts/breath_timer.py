"""
Breath timer — per-character script that tracks air while underwater.

Started when a character goes underwater (room_vertical_position < 0)
without WATER_BREATHING. Ticks every 2 seconds with countdown messages.
After breath runs out, deals periodic drowning damage.

Duration: 20 + (CON modifier * 5) seconds, minimum 10 seconds.
"""

from evennia import DefaultScript


BREATH_TICK_SECONDS = 2


class BreathTimerScript(DefaultScript):
    """
    Attached to a single character. Tracks remaining breath underwater.
    """

    def at_script_creation(self):
        self.key = "breath_timer"
        self.desc = "Underwater breath countdown"
        self.interval = BREATH_TICK_SECONDS
        self.persistent = False
        self.start_delay = False
        self.repeats = 0  # repeat until stopped

    def at_start(self, **kwargs):
        self.ndb.elapsed = 0

    def _get_breath_duration(self):
        """Total breath time in seconds based on character's CON."""
        char = self.obj
        if hasattr(char, "constitution") and hasattr(char, "get_attribute_bonus"):
            con_mod = char.get_attribute_bonus(char.constitution)
        else:
            con_mod = 0
        return max(10, 20 + con_mod * 5)

    def at_repeat(self):
        char = self.obj
        if not char or not char.pk:
            self.stop()
            return

        # Safety: if character surfaced or gained WATER_BREATHING, stop
        if char.room_vertical_position >= 0:
            self.stop()
            return

        from enums.condition import Condition
        if char.has_condition(Condition.WATER_BREATHING):
            self.stop()
            return

        self.ndb.elapsed = (self.ndb.elapsed or 0) + BREATH_TICK_SECONDS
        total_breath = self._get_breath_duration()
        remaining = total_breath - self.ndb.elapsed

        if remaining > 0:
            char.msg(f"|gYou have {remaining} seconds of air remaining...|n")
        else:
            # Drowning damage: ~5% of max HP per tick
            raw_damage = max(1, char.effective_hp_max // 20)
            damage = char.take_damage(
                raw_damage, cause="drowning", ignore_resistance=True
            )
            char.msg(
                f"|rYou are drowning! You take |w{damage}|r damage.|n"
            )
            if char.hp <= 0:
                self.stop()
