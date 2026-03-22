from enum import Enum


class DamageType(Enum):
    """Types of damage that can be dealt to characters and objects."""

    # Physical
    SLASHING = "slashing"        # Swords, axes
    PIERCING = "piercing"        # Daggers, arrows
    BLUDGEONING = "bludgeoning"  # Maces, clubs

    # Elemental
    FIRE = "fire"
    COLD = "cold"
    LIGHTNING = "lightning"
    ACID = "acid"
    POISON = "poison"

    # Necromantic
    NECROTIC = "necrotic"

    # Divine
    RADIANT = "radiant"          # Holy/divine damage (smite, holy fire)

    # Special
    MAGIC = "magic"
    FORCE = "force"
    PSYCHIC = "psychic"          # Bard insults, mind effects
