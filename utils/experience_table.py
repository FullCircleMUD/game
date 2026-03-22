# src/definitions/classes/experience_table.py

# Shared experience table used by all classes
# 
# DESIGN PHILOSOPHY:
# - Levels 1-10: Fast progression to get players engaged
# - Levels 11-25: Moderate pace for main gameplay
# - Levels 26-40: Steep curve for endgame dedication
#
# PROGRESSION CURVE:
# - Early levels: ~1.5x multiplier per level
# - Mid levels: ~1.3x multiplier per level  
# - Late levels: ~1.2x multiplier per level

EXPERIENCE_TABLE = {
    # Early levels - Fast progression (1-10)
    1: 0,           # Starting level
    2: 1000,        
    3: 2500,        
    4: 4500,        
    5: 7000,        
    6: 10500,       
    7: 15000,       
    8: 20500,       
    9: 27000,       
    10: 35000,      
    
    # Mid levels - Moderate pace (11-25)
    11: 45000,      
    12: 57000,      
    13: 71000,      
    14: 87000,      
    15: 105000,     # Major milestone
    16: 126000,     
    17: 150000,     
    18: 177000,     
    19: 207000,     
    20: 240000,     # Major milestone
    21: 277000,     
    22: 318000,     
    23: 363000,     
    24: 413000,     
    25: 468000,     # Major milestone
    
    # Late levels - Steep curve (26-40)
    26: 530000,     
    27: 598000,     
    28: 673000,     
    29: 756000,     
    30: 847000,     # Major milestone
    31: 947000,     
    32: 1057000,    
    33: 1178000,    
    34: 1311000,    
    35: 1457000,    # Major milestone
    36: 1617000,    
    37: 1792000,    
    38: 1983000,    
    39: 2191000,    
    40: 2417000     # Maximum level
}

def get_xp_for_next_level(current_level: int) -> int:
    """
    Get XP needed to reach the next level
    
    Args:
        current_level: Current character level
        
    Returns:
        XP needed for next level, or 0 if at max level
    """
    if current_level >= 40:
        return 0  # Already at max level
    
    return EXPERIENCE_TABLE[current_level + 1]

def get_xp_gap(level: int) -> int:
    """
    Get XP difference between this level and the previous level
    
    Args:
        level: Level to check (2-40)
        
    Returns:
        XP needed to go from previous level to this level
    """
    if level <= 1:
        return 0
    
    return EXPERIENCE_TABLE[level] - EXPERIENCE_TABLE[level - 1]

