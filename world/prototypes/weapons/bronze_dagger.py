from enums.unused_for_reference.damage_type import DamageType
from enums.mastery_level import MasteryLevel

BRONZE_DAGGER = {
    "prototype_key": "bronze_dagger",
    "typeclass": "typeclasses.items.weapons.dagger_nft_item.DaggerNFTItem",
    "key": "Bronze Dagger",
    "aliases": ["dagger", "bronze dagger"],
    "desc": "A small bronze dagger. Light and quick, with a greenish sheen.",
    "damage": {
        MasteryLevel.UNSKILLED: "1D2",
        MasteryLevel.BASIC: "1D3",
        MasteryLevel.SKILLED: "1D4",
        MasteryLevel.EXPERT: "1D4",
        MasteryLevel.MASTER: "1D4",
        MasteryLevel.GRANDMASTER: "1D4",
    },
    "damage_type": DamageType.PIERCING,
    "weapon_type": "melee",
    "speed": 0.5,
    "weight": 0.5,
    "max_durability": 3600,
    "wear_effects": [],
}
