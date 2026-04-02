"""
WearableMixin — item-side equip/unequip mechanics.

Provides wearslot assignment, data-driven wear_effects, and
at_wear/at_remove hooks that integrate with the nuclear recalculate
pattern on actors.

Composed into both NFT items (WearableNFTItem) and mob equipment
(MobWeapon, future MobWearable) so equip mechanics are defined once.
"""

from evennia.typeclasses.attributes import AttributeProperty


class WearableMixin:
    """
    Mixin providing wearslot and wear_effects for any equippable item.

    Attributes (from prototype or defaults):
        wearslot       — str or list of str, which slot(s) this item fits.
                         Uses enum values from enums.wearslot.
        wear_effects   — list of effect dicts applied on equip, reversed
                         on unequip.
    """

    # Which wearslot(s) this item can be equipped in.
    # Set by prototype. String for single-slot items ("HEAD"),
    # list for multi-slot items (["LEFT_EAR", "RIGHT_EAR"]).
    wearslot = AttributeProperty(None)

    # Data-driven effects applied on equip, reversed on unequip.
    # Each entry is a dict, e.g. {"type": "stat_bonus", "stat": "armor_class", "value": 2}
    wear_effects = AttributeProperty(default=list)

    # ================================================================== #
    #  Equip / Unequip Hooks
    # ================================================================== #

    def at_wear(self, wearer):
        """
        Called by BaseWearslotsMixin.wear() after this item is equipped.

        Condition effects are applied incrementally (ref-counted).
        Numeric stat effects are handled by nuclear recalculate — the
        item is already in wearslots when this hook fires, so
        _recalculate_stats() will see it.

        Args:
            wearer: the Evennia object wearing this item
        """
        for effect in self.wear_effects or []:
            if effect.get("type") == "condition":
                wearer.apply_effect(effect)
        wearer._recalculate_stats()

    def at_remove(self, wearer):
        """
        Called by BaseWearslotsMixin.remove() after this item is unequipped.

        Condition effects are removed incrementally (ref-counted).
        Numeric stat effects are handled by nuclear recalculate — the
        item is already out of wearslots when this hook fires.

        Args:
            wearer: the Evennia object removing this item
        """
        for effect in self.wear_effects or []:
            if effect.get("type") == "condition":
                wearer.remove_effect(effect)
        wearer._recalculate_stats()
