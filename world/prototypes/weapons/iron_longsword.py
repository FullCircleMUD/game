from enums.unused_for_reference.damage_type import DamageType
from enums.mastery_level import MasteryLevel

IRON_LONGSWORD = {
    "prototype_key": "iron_longsword",
    "typeclass": "typeclasses.items.weapons.longsword_nft_item.LongswordNFTItem",
    "key": "Iron Longsword",
    "aliases": ["sword", "longsword", "iron"],
    "desc": "A sturdy iron blade, forged by a competent smith.",
    "damage": {
        MasteryLevel.UNSKILLED: "1D4",
        MasteryLevel.BASIC: "1D8",
        MasteryLevel.SKILLED: "1D10",
        MasteryLevel.EXPERT: "2D6",
        MasteryLevel.MASTER: "2D8",
        MasteryLevel.GRANDMASTER: "2D8",
    },
    "damage_type": DamageType.SLASHING,
    "weapon_type": "melee",
    "speed": 1.0,
    "weight": 3.0,
    "max_durability": 5400,
}
