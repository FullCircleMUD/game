"""
SmashableMixin — allows objects (doors, chests) to be smashed open.

Objects with this mixin can take typed damage. When smash_hp reaches 0
the object is forced permanently open (is_open=True, is_locked=False).

Damage resistances/vulnerabilities are supported per damage type:
    100  = immune (no damage)
     50  = resistant (50% less damage)
      0  = normal
    -25  = vulnerable (25% MORE damage)

Usage (build script / prototype):
    chest.is_smashable = True
    chest.smash_hp_max = 30
    chest.smash_resistances = {
        "psychic": 100,    # immune to psychic
        "slashing": -25,   # vulnerable to slashing
    }

Combat system calls:
    damage_dealt, broke = obj.take_smash_damage(10, DamageType.SLASHING)
"""

from evennia import AttributeProperty


class SmashableMixin:
    """
    Mixin for objects that can be smashed open by dealing damage.

    Defaults to indestructible (is_smashable=False, smash_hp_max=0).
    Configure per-instance to enable.
    """

    is_smashable = AttributeProperty(False)
    smash_hp = AttributeProperty(0)
    smash_hp_max = AttributeProperty(0)
    smash_resistances = AttributeProperty(dict)

    def at_smashable_init(self):
        """Initialize smash HP. Call from at_object_creation()."""
        if self.smash_hp_max > 0:
            self.smash_hp = self.smash_hp_max

    def get_smash_resistance(self, damage_type):
        """
        Get effective resistance for a damage type.

        Args:
            damage_type: DamageType enum value or string.

        Returns:
            int: Resistance percentage clamped to [-75, 100].
                 100 = immune, negative = vulnerable.
        """
        if damage_type is None:
            return 0
        # Accept both enum and string
        key = damage_type.value if hasattr(damage_type, "value") else str(damage_type)
        resistances = self.smash_resistances or {}
        raw = resistances.get(key, 0)
        return max(-75, min(100, int(raw)))

    def take_smash_damage(self, raw_damage, damage_type=None):
        """
        Apply typed damage to this object.

        Args:
            raw_damage (int): Base damage before resistance.
            damage_type: DamageType enum or string. None = untyped.

        Returns:
            (int, bool): (damage_dealt, broke) — damage actually applied
                         and whether the object broke.
        """
        if not self.is_smashable or self.smash_hp_max <= 0:
            return (0, False)

        if self.smash_hp <= 0:
            return (0, False)  # already broken

        # Apply resistance
        if damage_type is not None:
            resistance = self.get_smash_resistance(damage_type)
            if resistance >= 100:
                return (0, False)  # immune
            multiplier = 1 - (resistance / 100)
            final_damage = max(1, int(raw_damage * multiplier))
        else:
            final_damage = max(1, raw_damage)

        self.smash_hp = max(0, self.smash_hp - final_damage)

        if self.smash_hp <= 0:
            self.at_smash_break()
            return (final_damage, True)

        return (final_damage, False)

    def at_smash_break(self):
        """
        Called when smash_hp reaches 0. Forces the object open.

        Override in subclasses for custom break behavior.
        """
        if hasattr(self, "is_locked"):
            self.is_locked = False
        if hasattr(self, "is_open"):
            self.is_open = True
