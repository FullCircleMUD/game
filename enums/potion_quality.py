# FullCircleMUD.enums.potion_quality.py

from enum import Enum


class PotionQuality(Enum):
    """Quality tier for potions, mapped 1:1 with brewer's mastery level.

    Mastery level 1 (BASIC) produces WATERY potions, level 5
    (GRANDMASTER) produces ASCENDANT potions. The ``prefix`` property
    gives the human-readable quality word used in item names.
    """
    WATERY = 1       # BASIC mastery
    WEAK = 2         # SKILLED mastery
    STANDARD = 3     # EXPERT mastery
    POTENT = 4       # MASTER mastery
    ASCENDANT = 5    # GRANDMASTER mastery

    @property
    def prefix(self):
        """Display prefix: 'Watery', 'Weak', etc."""
        return self.name.capitalize()
