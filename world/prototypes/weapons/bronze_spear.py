from enums.unused_for_reference.damage_type import DamageType
from enums.mastery_level import MasteryLevel

BRONZE_SPEAR = {
    "prototype_key": "bronze_spear",
    "typeclass": "typeclasses.items.weapons.spear_nft_item.SpearNFTItem",
    "key": "Bronze Spear",
    "aliases": ["spear", "bronze spear"],
    "desc": "A bronze-tipped spear mounted on a wooden shaft. Good reach.",
    "damage": {
        MasteryLevel.UNSKILLED: "1D3",
        MasteryLevel.BASIC: "1D4",
        MasteryLevel.SKILLED: "1D6",
        MasteryLevel.EXPERT: "1D6",
        MasteryLevel.MASTER: "1D6",
        MasteryLevel.GRANDMASTER: "1D6",
    },
    "damage_type": DamageType.PIERCING,
    "weapon_type": "melee",
    "speed": 1.0,
    "weight": 3.0,
    "max_durability": 3600,
    "wear_effects": [],
}
