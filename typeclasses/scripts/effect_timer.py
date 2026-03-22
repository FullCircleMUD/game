"""
EffectTimerScript — generic one-shot timer for seconds-based named effects.

Created automatically by EffectsManagerMixin._start_effect_timer() when
an effect with duration_type="seconds" is applied. On expiry, calls
remove_named_effect() on the owning actor to cleanly reverse all
stat effects, condition flags, and messaging.
"""

from evennia import DefaultScript


class EffectTimerScript(DefaultScript):
    """
    One-shot timer that removes a named effect when it fires.

    Attributes (set via db before start):
        effect_key (str): key of the named effect to remove on expiry
    """

    def at_script_creation(self):
        self.desc = "Effect timer"
        self.interval = 300  # overridden before start()
        self.start_delay = True
        self.persistent = True
        self.repeats = 1  # fire once after duration

    def at_repeat(self):
        """Timer expired — remove the named effect."""
        target = self.obj
        effect_key = self.db.effect_key
        if effect_key and hasattr(target, "remove_named_effect"):
            target.remove_named_effect(effect_key)
