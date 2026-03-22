from enum import Enum

class DamageType(Enum):
    """Types of damage weapons can deal"""
    # physical damage
    SLASHING = "slashing"      # Swords, axes
    PIERCING = "piercing"      # Daggers, arrows
    BLUDGEONING = "bludgeoning" # Maces, clubs

    
    # special damage types
    FIRE = "fire"              # Flame weapons
    COLD = "cold"              # Ice weapons
    LIGHTNING = "lightning"    # Electric weapons
    ACID = "acid"              # Acid weapons
    POISON = "poison"          # Poisoned weapons

    MAGIC = "magic"            # Magic damage

    FORCE = "force"            # Force damage, e.g., from spells or special abilities