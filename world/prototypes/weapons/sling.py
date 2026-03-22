from enums.unused_for_reference.damage_type import DamageType
from enums.mastery_level import MasteryLevel

SLING = {
    "prototype_key": "sling",
    "typeclass": "typeclasses.items.weapons.sling_nft_item.SlingNFTItem",
    "key": "Sling",
    "aliases": ["sling"],
    "desc": "A simple leather sling for hurling stones. Light and easy to use.",
    "damage": {
        MasteryLevel.UNSKILLED: "1D2",
        MasteryLevel.BASIC: "1D3",
        MasteryLevel.SKILLED: "1D3",
        MasteryLevel.EXPERT: "1D3",
        MasteryLevel.MASTER: "1D3",
        MasteryLevel.GRANDMASTER: "1D3",
    },
    "damage_type": DamageType.BLUDGEONING,
    "weapon_type": "missile",
    "speed": 1.0,
    "weight": 0.3,
    "max_durability": 1440,
}
