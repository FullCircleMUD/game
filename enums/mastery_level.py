# FullCircleMUD.enums.mastery_level.py

from enum import Enum


class MasteryLevel(Enum):
    """
    Mastery levels for all skills (weapons, class skills, general skills)
    
    Each level requires a specific point investment to achieve.
    The cost is cumulative - EXPERT costs 7 total points (not just 4).
    """
    # Simple string values - data moved to external dictionaries
    UNSKILLED = 0
    BASIC = 1
    SKILLED = 2
    EXPERT = 3
    MASTER = 4
    GRANDMASTER = 5
    
    @property
    def bonus(self) -> int:
        """Get the stat bonus for this mastery level"""
        return _MASTERY_BONUSES[self]
    
    @property
    def training_points_required(self) -> int:
        """Get training points required from previous level"""
        return _MASTERY_TRAINING_POINTS[self]


    @property
    def name(self) -> str:
        """Get the name of the mastery level"""
        return _MASTERY_REVERSE_LOOKUP[self.value]

# Mastery level stat bonuses
_MASTERY_BONUSES = {
    MasteryLevel.UNSKILLED: -2,
    MasteryLevel.BASIC: 0,
    MasteryLevel.SKILLED: 2,
    MasteryLevel.EXPERT: 4,
    MasteryLevel.MASTER: 6,
    MasteryLevel.GRANDMASTER: 8,
}

# Training points required from previous level
_MASTERY_TRAINING_POINTS = {
    MasteryLevel.UNSKILLED: 0,
    MasteryLevel.BASIC: 1,      # total 1
    MasteryLevel.SKILLED: 3,    # total 4
    MasteryLevel.EXPERT: 5,     # total 9
    MasteryLevel.MASTER: 7,     # total 16
    MasteryLevel.GRANDMASTER: 9, # total 27
}

# MASTERY LEVEL REVERSE LOOKUP
# This allows us to find the MasteryLevel enum member by its name (string)
_MASTERY_REVERSE_LOOKUP = {
    0: "UNSKILLED",
    1: "BASIC",
    2: "SKILLED",
    3: "EXPERT",
    4: "MASTER",
    5: "GRAND MASTER"
}
