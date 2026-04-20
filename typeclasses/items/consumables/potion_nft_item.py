"""
PotionNFTItem — consumable NFT that applies effects when drunk.

Two modes:
  - Instant (duration=0): restore HP/mana/move, capped at max.
  - Timed (duration>0): apply stat_bonus/condition effects via
    EffectsManagerMixin.apply_named_effect() with seconds-based timer.

Anti-stacking: uses named effect system's built-in has_effect() check.
If the effect is already active, the potion is NOT consumed (saved).
Anti-stacking is by stat (e.g. "potion_strength"), not by potion name —
any two STR potions share the same key and can't stack.

Hierarchy:
    BaseNFTItem
    └── ConsumableNFTItem
        └── PotionNFTItem   ← this class
"""

from evennia import AttributeProperty

from typeclasses.items.consumables.consumable_nft_item import ConsumableNFTItem
from utils.dice_roller import dice as dice_roller


class PotionNFTItem(ConsumableNFTItem):
    """A consumable potion NFT that applies effects when consumed."""

    potion_effects = AttributeProperty(default=list)
    duration = AttributeProperty(default=0)  # 0 = instant, >0 = seconds
    named_effect_key = AttributeProperty(default="")
    mastery_tier = AttributeProperty(default=1)  # PotionQuality enum value

    def at_object_creation(self):
        super().at_object_creation()
        self.tags.add("potion", category="item_type")

    def at_consume(self, consumer):
        """
        Apply potion effects to the consumer.

        Instant effects (restore) are applied directly.
        Timed effects (stat_bonus, condition) go through the named effect
        system for lifecycle management and anti-stacking.

        Returns:
            (bool, str) — (success, message)
        """
        if not self.potion_effects:
            return (False, "This potion seems to have no effect.")

        # ── Anti-stacking check (before consuming) ──────────────
        effect_key = self.named_effect_key
        if self.duration > 0 and effect_key:
            if consumer.has_effect(effect_key):
                return (False, "You are already under this effect.")

        messages = []

        # ── Instant effects (restore) — always apply ────────────
        for effect in self.potion_effects:
            if effect["type"] == "restore":
                self._apply_restore(consumer, effect, messages)

        # ── Timed effects via named effect system ───────────────
        if self.duration > 0 and effect_key:
            condition = None
            stat_effects = []
            for effect in self.potion_effects:
                if effect["type"] == "condition":
                    condition = effect["condition"]
                elif effect["type"] != "restore":
                    stat_effects.append(effect)

            consumer.apply_named_effect(
                key=effect_key,
                effects=stat_effects,
                condition=condition,
                duration=self.duration,
                messages={
                    "end": f"|rThe effects of {self.key} wear off.|n",
                    "end_third": "The potion effects on {name} fade.",
                },
            )

            minutes = self.duration // 60
            if minutes > 0:
                messages.append(f"The effects will last {minutes} minutes.")
            else:
                messages.append(
                    f"The effects will last {self.duration} seconds."
                )

        detail = " ".join(messages)
        return (
            True,
            f"|gYou drink {self.get_display_name(consumer)}.|n {detail}".strip(),
        )

    def _apply_restore(self, consumer, effect, messages):
        """Apply an instant restoration effect, capped at the effective max."""
        stat = effect["stat"]

        # Support dice strings: {"dice": "2d4+1"} or fixed int: {"value": 20}
        if "dice" in effect:
            value = dice_roller.roll(effect["dice"])
        else:
            value = effect["value"]

        # Map stat names to their max properties
        max_map = {
            "hp": "effective_hp_max",
            "mana": "mana_max",
            "move": "move_max",
        }

        current = getattr(consumer, stat, None)
        if current is None:
            return

        max_prop = max_map.get(stat)
        if max_prop:
            cap = getattr(consumer, max_prop, current + value)
            new_val = min(current + value, cap)
        else:
            new_val = current + value

        restored = new_val - current
        if restored > 0:
            setattr(consumer, stat, new_val)
            messages.append(f"You recover {restored} {stat}.")
        else:
            messages.append(f"Your {stat} is already full.")
