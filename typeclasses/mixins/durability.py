"""
DurabilityMixin — adds durability tracking to any Evennia object.

Mix into equipment, doors, chests, barricades — anything that can be
damaged and eventually break. The mixin handles durability accounting
and progressive warnings; child classes define what "breaking" means
by implementing at_break().

Rules:
    max_durability = 0   → unbreakable (durability system is skipped)
    max_durability > 0   → breakable, starts at max_durability
    durability reaches 0 → at_break() fires (item is destroyed/broken)

Progressive warning system:
    25% damaged  → light warning     (fires once, on the hit that crosses)
    50% damaged  → moderate warning  (fires once)
    75% damaged  → heavy warning     (fires once)
    90%+ damaged → critical warning  (fires EVERY use to create urgency)
"""

from evennia.typeclasses.attributes import AttributeProperty


class DurabilityMixin:
    """
    Mixin that tracks durability and fires warnings/break events.

    Child classes MUST:
        1. Call at_durability_init() from at_object_creation()
        2. Override at_break() to define what happens when durability hits 0
    """

    max_durability = AttributeProperty(0)      # 0 = unbreakable
    durability = AttributeProperty(None)        # set from metadata or init
    repairable = AttributeProperty(True)        # can crafters repair this?

    def at_durability_init(self):
        """
        Initialize durability from max_durability if not already set.
        Call from at_object_creation(). Safe to call multiple times.
        """
        if self.durability is None and self.max_durability > 0:
            self.durability = self.max_durability

    def reduce_durability(self, amount=1):
        """
        Reduce durability by amount. At 0, calls at_break().

        Does nothing if max_durability == 0 (unbreakable).
        Fires progressive warnings at damage thresholds.
        """
        if self.max_durability == 0:
            return  # unbreakable

        if self.durability is None:
            self.at_durability_init()
        old_durability = self.durability
        self.durability = max(0, self.durability - amount)

        if self.durability <= 0:
            self.at_break()
            return

        # Progressive warnings based on percentage of damage taken
        old_pct_damaged = 1 - (old_durability / self.max_durability)
        new_pct_damaged = 1 - (self.durability / self.max_durability)

        # >= 90% damaged: warn EVERY use
        if new_pct_damaged >= 0.90:
            self.on_durability_warning("critical")
        # Threshold-crossing warnings (only on the hit that crosses)
        elif new_pct_damaged >= 0.75 and old_pct_damaged < 0.75:
            self.on_durability_warning("heavy")
        elif new_pct_damaged >= 0.50 and old_pct_damaged < 0.50:
            self.on_durability_warning("moderate")
        elif new_pct_damaged >= 0.25 and old_pct_damaged < 0.25:
            self.on_durability_warning("light")

    def on_durability_warning(self, severity):
        """
        Send a durability warning message.

        Override for context-specific messages (e.g. doors, chests).
        Default messages suit equipment held by a character.

        Args:
            severity: "light", "moderate", "heavy", or "critical"
        """
        msgs = {
            "light": f"|y{self.key} is showing signs of wear.|n",
            "moderate": f"|y{self.key} is moderately damaged.|n",
            "heavy": f"|r{self.key} is heavily damaged.|n",
            "critical": f"|r{self.key} is about to break!|n",
        }
        target = self.location
        if target and hasattr(target, "msg"):
            target.msg(msgs.get(severity, ""))

    def get_condition_label(self):
        """
        Coloured condition label for display commands.

        Returns empty string if unbreakable (max_durability == 0).
        """
        if self.max_durability == 0:
            return ""
        if self.durability is None:
            self.at_durability_init()
        pct = self.durability / self.max_durability
        if pct >= 1.0:
            return "|gPristine|n"
        elif pct >= 0.75:
            return "|gGood|n"
        elif pct >= 0.50:
            return "|yWorn|n"
        elif pct >= 0.25:
            return "|yDamaged|n"
        else:
            return "|rCritical|n"

    def repair_to_full(self):
        """
        Restore durability to max_durability.

        Does nothing if unbreakable (max_durability == 0).
        """
        if self.max_durability == 0:
            return
        self.durability = self.max_durability

    def at_break(self):
        """
        Called when durability reaches 0.

        Child classes MUST override to define what "breaking" means:
            - Equipment: unequip, reverse effects, delete (return NFT)
            - Door: open permanently
            - Chest: spill contents
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement at_break()"
        )
