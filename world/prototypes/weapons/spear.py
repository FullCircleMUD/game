from enums.unused_for_reference.damage_type import DamageType
from enums.mastery_level import MasteryLevel

SPEAR = {
    "prototype_key": "spear",
    "typeclass": "typeclasses.items.weapons.spear_nft_item.SpearNFTItem",
    "key": "Spear",
    "aliases": ["spear"],
    "desc": "An iron-tipped spear mounted on a wooden shaft. Good reach and piercing damage.",
    "damage": {
        MasteryLevel.UNSKILLED: "1D4",
        MasteryLevel.BASIC: "1D6",
        MasteryLevel.SKILLED: "1D8",
        MasteryLevel.EXPERT: "1D8",
        MasteryLevel.MASTER: "1D8",
        MasteryLevel.GRANDMASTER: "1D8",
    },
    "damage_type": DamageType.PIERCING,
    "weapon_type": "melee",
    "speed": 1.0,
    "weight": 3.0,
    "max_durability": 5400,
}
