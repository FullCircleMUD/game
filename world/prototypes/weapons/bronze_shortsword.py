from enums.unused_for_reference.damage_type import DamageType
from enums.mastery_level import MasteryLevel

BRONZE_SHORTSWORD = {
    "prototype_key": "bronze_shortsword",
    "typeclass": "typeclasses.items.weapons.shortsword_nft_item.ShortswordNFTItem",
    "key": "Bronze Shortsword",
    "aliases": ["shortsword", "bronze shortsword"],
    "desc": "A sturdy bronze shortsword. Quick and reliable.",
    "damage": {
        MasteryLevel.UNSKILLED: "1D3",
        MasteryLevel.BASIC: "1D4",
        MasteryLevel.SKILLED: "1D6",
        MasteryLevel.EXPERT: "1D6",
        MasteryLevel.MASTER: "1D6",
        MasteryLevel.GRANDMASTER: "1D6",
    },
    "damage_type": DamageType.SLASHING,
    "weapon_type": "melee",
    "speed": 0.8,
    "weight": 2.0,
    "max_durability": 3600,
    "wear_effects": [],
}
