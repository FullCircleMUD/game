from enums.unused_for_reference.damage_type import DamageType
from enums.mastery_level import MasteryLevel

BRONZE_HAND_AXE = {
    "prototype_key": "bronze_hand_axe",
    "typeclass": "typeclasses.items.weapons.axe_nft_item.AxeNFTItem",
    "key": "Bronze Hand Axe",
    "aliases": ["axe", "hand axe", "handaxe", "bronze axe"],
    "desc": "A compact bronze axe head mounted on a wooden haft.",
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
    "speed": 0.9,
    "weight": 2.0,
    "max_durability": 3600,
    "wear_effects": [],
}
