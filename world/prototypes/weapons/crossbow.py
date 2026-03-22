from enums.unused_for_reference.damage_type import DamageType
from enums.mastery_level import MasteryLevel

CROSSBOW = {
    "prototype_key": "crossbow",
    "typeclass": "typeclasses.items.weapons.crossbow_nft_item.CrossbowNFTItem",
    "key": "Crossbow",
    "aliases": ["crossbow"],
    "desc": "A mechanical crossbow with an iron prod and timber stock. High damage, slow to reload.",
    "damage": {
        MasteryLevel.UNSKILLED: "1D4",
        MasteryLevel.BASIC: "1D6",
        MasteryLevel.SKILLED: "1D8",
        MasteryLevel.EXPERT: "1D8",
        MasteryLevel.MASTER: "1D8",
        MasteryLevel.GRANDMASTER: "1D8",
    },
    "damage_type": DamageType.PIERCING,
    "weapon_type": "missile",
    "speed": 1.4,
    "weight": 3.5,
    "max_durability": 5400,
    "wear_effects": [],
}
