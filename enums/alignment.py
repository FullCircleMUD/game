from enum import Enum


class Alignment(Enum):
    """5-tier alignment derived from alignment_score [-1000, +1000]."""
    PURE_GOOD = "Pure Good"      # 700 to 1000
    GOOD = "Good"                # 300 to 699
    NEUTRAL = "Neutral"          # -299 to 299
    EVIL = "Evil"                # -699 to -300
    PURE_EVIL = "Pure Evil"      # -1000 to -700