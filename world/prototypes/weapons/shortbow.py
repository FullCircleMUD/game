from enums.unused_for_reference.damage_type import DamageType
from enums.mastery_level import MasteryLevel

SHORTBOW = {
    "prototype_key": "shortbow",
    "typeclass": "typeclasses.items.weapons.bow_nft_item.BowNFTItem",
    "key": "Shortbow",
    "aliases": ["bow", "shortbow", "short bow"],
    "desc": "A compact timber bow with good draw strength. Light and quick to fire.",
    "damage": {
        MasteryLevel.UNSKILLED: "1D3",
        MasteryLevel.BASIC: "1D4",
        MasteryLevel.SKILLED: "1D6",
        MasteryLevel.EXPERT: "1D6",
        MasteryLevel.MASTER: "1D6",
        MasteryLevel.GRANDMASTER: "1D6",
    },
    "damage_type": DamageType.PIERCING,
    "weapon_type": "missile",
    "speed": 1.0,
    "weight": 1.5,
    "max_durability": 2880,
    "wear_effects": [],
}
