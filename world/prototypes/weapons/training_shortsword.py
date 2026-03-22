from enums.unused_for_reference.damage_type import DamageType
from enums.mastery_level import MasteryLevel

TRAINING_SHORTSWORD = {
    "prototype_key": "training_shortsword",
    "typeclass": "typeclasses.items.weapons.shortsword_nft_item.ShortswordNFTItem",
    "key": "Training Shortsword",
    "aliases": ["shortsword", "short sword", "training shortsword"],
    "desc": "A wooden practice shortsword. Lighter than a longsword, good for one-handed drills.",
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
    "speed": 0.8,
    "weight": 1.5,
    "max_durability": 1440,
}
