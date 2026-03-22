from enums.unused_for_reference.damage_type import DamageType
from enums.mastery_level import MasteryLevel

TRAINING_LONGSWORD = {
    "prototype_key": "training_longsword",
    "typeclass": "typeclasses.items.weapons.longsword_nft_item.LongswordNFTItem",
    "key": "Training Longsword",
    "aliases": ["sword", "longsword", "training", "practice"],
    "desc": "A wooden practice sword. Won't cut much, but it'll bruise.",
    "damage": {
        MasteryLevel.UNSKILLED: "1D2",
        MasteryLevel.BASIC: "1D4",
        MasteryLevel.SKILLED: "1D6",
        MasteryLevel.EXPERT: "1D6",
        MasteryLevel.MASTER: "1D6",
        MasteryLevel.GRANDMASTER: "1D6",
    },
    "damage_type": DamageType.BLUDGEONING,
    "weapon_type": "melee",
    "speed": 1.0,
    "weight": 2.0,
    "max_durability": 1440,
}
