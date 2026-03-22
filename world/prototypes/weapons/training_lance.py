from enums.unused_for_reference.damage_type import DamageType
from enums.mastery_level import MasteryLevel

TRAINING_LANCE = {
    "prototype_key": "training_lance",
    "typeclass": "typeclasses.items.weapons.lance_nft_item.LanceNFTItem",
    "key": "Training Lance",
    "aliases": ["lance", "training lance"],
    "desc": "A long wooden lance with a blunted tip. Used for jousting practice and mounted drills.",
    "damage": {
        MasteryLevel.UNSKILLED: "1D3",
        MasteryLevel.BASIC: "1D4",
        MasteryLevel.SKILLED: "1D6",
        MasteryLevel.EXPERT: "1D6",
        MasteryLevel.MASTER: "1D6",
        MasteryLevel.GRANDMASTER: "1D6",
    },
    "damage_type": DamageType.BLUDGEONING,
    "weapon_type": "melee",
    "speed": 1.2,
    "weight": 4.0,
    "max_durability": 1440,
    "wear_effects": [],
}
