"""
DamageResistanceMixin — damage resistance and vulnerability tracking.

Stores integer percentages in a dict keyed by damage type string:
    {"piercing": 50}   = 50% resistance to piercing
    {"fire": -25}      = 25% vulnerability to fire

Raw values are stored unclamped so that adding/removing effects never
causes drift (e.g. a dwarf's innate 20% poison resistance won't erode
when gear that pushed them past the cap is removed). The effective value
is clamped to [-75, 75] on read via get_resistance().

Sources of resistance:
    - Innate/racial: applied at character creation (e.g. Dwarf +20 poison)
    - Equipment: applied/removed via wear_effects on wearable items
    - Spells/abilities: applied via Evennia Scripts — script.at_start()
      calls apply_resistance_effect(), script.at_stop() calls
      remove_resistance_effect(). No timestamp tracking needed.

Combat system integration (TODO):
    When calculating damage in the combat system, use get_resistance()
    to obtain the capped percentage, then apply it as a multiplier:

        resistance_pct = target.get_resistance(damage_type)  # e.g. 50
        multiplier = 1 - (resistance_pct / 100)              # e.g. 0.5
        final_damage = int(raw_damage * multiplier)

    Positive resistance reduces damage. Negative (vulnerability) amplifies it:
        -25% vulnerability → multiplier = 1.25 → 25% MORE damage taken

    Damage types are defined in enums.damage_type.DamageType (SLASHING,
    PIERCING, BLUDGEONING, FIRE, COLD, LIGHTNING, ACID, POISON, MAGIC,
    FORCE). The dict keys are lowercase strings matching DamageType.value.

Designed to be mixed into any typeclass — characters, NPCs, mobs, pets,
mounts, and even destructible objects (e.g. iron bars that resist
slashing but are vulnerable to fire).

Usage:
    class FCMCharacter(DamageResistanceMixin, ...):
        ...

    class IronBars(DamageResistanceMixin, ...):
        ...
"""

from evennia.typeclasses.attributes import AttributeProperty

RESISTANCE_CAP = 75


class DamageResistanceMixin:
    """Mixin providing damage resistance/vulnerability tracking."""

    # Raw integer percentages — NOT clamped on write.
    # Zero entries are cleaned up automatically.
    damage_resistances: dict = AttributeProperty(default={})

    def get_resistance(self, damage_type):
        """
        Return the effective resistance for *damage_type*, clamped to
        [-RESISTANCE_CAP, RESISTANCE_CAP].

        Returns 0 for damage types with no entry.
        """
        raw = self.damage_resistances.get(damage_type, 0)
        return max(-RESISTANCE_CAP, min(raw, RESISTANCE_CAP))

    def apply_resistance_effect(self, effect):
        """
        Apply a damage_resistance wear effect dict.

        Expected format:
            {"type": "damage_resistance", "damage_type": "<type>", "value": <int>}

        Raw value is stored; use get_resistance() for the capped value.
        """
        dmg_type = effect["damage_type"]
        value = effect["value"]
        resistances = dict(self.damage_resistances)
        resistances[dmg_type] = resistances.get(dmg_type, 0) + value
        self.damage_resistances = {k: v for k, v in resistances.items() if v != 0}

    def remove_resistance_effect(self, effect):
        """
        Remove a damage_resistance wear effect dict.

        Reverses apply_resistance_effect().
        """
        dmg_type = effect["damage_type"]
        value = effect["value"]
        resistances = dict(self.damage_resistances)
        resistances[dmg_type] = resistances.get(dmg_type, 0) - value
        self.damage_resistances = {k: v for k, v in resistances.items() if v != 0}
