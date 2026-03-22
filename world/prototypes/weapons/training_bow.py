from enums.unused_for_reference.damage_type import DamageType
from enums.mastery_level import MasteryLevel

TRAINING_BOW = {
    "prototype_key": "training_bow",
    "typeclass": "typeclasses.items.weapons.bow_nft_item.BowNFTItem",
    "key": "Training Bow",
    "aliases": ["bow", "training bow"],
    "desc": "A crude practice bow carved from a single piece of timber. Fires blunt-tipped arrows.",
    "damage": {
        MasteryLevel.UNSKILLED: "1D2",
        MasteryLevel.BASIC: "1D4",
        MasteryLevel.SKILLED: "1D4",
        MasteryLevel.EXPERT: "1D4",
        MasteryLevel.MASTER: "1D4",
        MasteryLevel.GRANDMASTER: "1D4",
    },
    "damage_type": DamageType.BLUDGEONING,
    "weapon_type": "missile",
    "speed": 1.0,
    "weight": 1.5,
    "max_durability": 2880,
}
