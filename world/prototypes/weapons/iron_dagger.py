from enums.unused_for_reference.damage_type import DamageType
from enums.mastery_level import MasteryLevel

IRON_DAGGER = {
    "prototype_key": "iron_dagger",
    "typeclass": "typeclasses.items.weapons.dagger_nft_item.DaggerNFTItem",
    "key": "Iron Dagger",
    "aliases": ["dagger", "iron dagger"],
    "desc": "A sharp iron dagger. Small but deadly in skilled hands.",
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
    "speed": 0.5,
    "weight": 0.5,
    "max_durability": 5400,
}
