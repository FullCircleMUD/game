from enums.unused_for_reference.damage_type import DamageType
from enums.mastery_level import MasteryLevel

TRAINING_DAGGER = {
    "prototype_key": "training_dagger",
    "typeclass": "typeclasses.items.weapons.dagger_nft_item.DaggerNFTItem",
    "key": "Training Dagger",
    "aliases": ["dagger", "training dagger"],
    "desc": "A blunt wooden dagger used for practice. Light and fast, but harmless.",
    "damage": {
        MasteryLevel.UNSKILLED: "1D2",
        MasteryLevel.BASIC: "1D3",
        MasteryLevel.SKILLED: "1D4",
        MasteryLevel.EXPERT: "1D4",
        MasteryLevel.MASTER: "1D4",
        MasteryLevel.GRANDMASTER: "1D4",
    },
    "damage_type": DamageType.BLUDGEONING,
    "weapon_type": "melee",
    "speed": 0.5,
    "weight": 0.5,
    "max_durability": 1440,
}
