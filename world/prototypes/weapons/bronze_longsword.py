from enums.unused_for_reference.damage_type import DamageType
from enums.mastery_level import MasteryLevel

BRONZE_LONGSWORD = {
    "prototype_key": "bronze_longsword",
    "typeclass": "typeclasses.items.weapons.longsword_nft_item.LongswordNFTItem",
    "key": "Bronze Longsword",
    "aliases": ["longsword", "bronze longsword"],
    "desc": "A broad bronze blade. Heavier than iron but a solid weapon.",
    "damage": {
        MasteryLevel.UNSKILLED: "1D3",
        MasteryLevel.BASIC: "1D6",
        MasteryLevel.SKILLED: "1D8",
        MasteryLevel.EXPERT: "1D10",
        MasteryLevel.MASTER: "1D10",
        MasteryLevel.GRANDMASTER: "1D10",
    },
    "damage_type": DamageType.SLASHING,
    "weapon_type": "melee",
    "speed": 1.0,
    "weight": 3.0,
    "max_durability": 3600,
    "wear_effects": [],
}
