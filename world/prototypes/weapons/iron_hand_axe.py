from enums.unused_for_reference.damage_type import DamageType
from enums.mastery_level import MasteryLevel

IRON_HAND_AXE = {
    "prototype_key": "iron_hand_axe",
    "typeclass": "typeclasses.items.weapons.axe_nft_item.AxeNFTItem",
    "key": "Iron Hand Axe",
    "aliases": ["axe", "hand axe", "handaxe", "iron axe"],
    "desc": "A compact iron axe. Good for chopping more than just wood.",
    "damage": {
        MasteryLevel.UNSKILLED: "1D4",
        MasteryLevel.BASIC: "1D6",
        MasteryLevel.SKILLED: "1D6",
        MasteryLevel.EXPERT: "1D8",
        MasteryLevel.MASTER: "1D8",
        MasteryLevel.GRANDMASTER: "1D8",
    },
    "damage_type": DamageType.SLASHING,
    "weapon_type": "melee",
    "speed": 0.9,
    "weight": 2.0,
    "max_durability": 5400,
}
