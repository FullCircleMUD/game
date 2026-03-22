from enums.unused_for_reference.damage_type import DamageType
from enums.mastery_level import MasteryLevel

IRON_SHORTSWORD = {
    "prototype_key": "iron_shortsword",
    "typeclass": "typeclasses.items.weapons.shortsword_nft_item.ShortswordNFTItem",
    "key": "Iron Shortsword",
    "aliases": ["shortsword", "iron shortsword"],
    "desc": "A well-forged iron shortsword. Quick and versatile.",
    "damage": {
        MasteryLevel.UNSKILLED: "1D4",
        MasteryLevel.BASIC: "1D6",
        MasteryLevel.SKILLED: "1D8",
        MasteryLevel.EXPERT: "1D8",
        MasteryLevel.MASTER: "1D8",
        MasteryLevel.GRANDMASTER: "1D8",
    },
    "damage_type": DamageType.SLASHING,
    "weapon_type": "melee",
    "speed": 0.8,
    "weight": 2.0,
    "max_durability": 5400,
}
