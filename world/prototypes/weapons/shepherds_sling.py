from enums.unused_for_reference.damage_type import DamageType
from enums.mastery_level import MasteryLevel

SHEPHERDS_SLING = {
    "prototype_key": "shepherds_sling",
    "typeclass": "typeclasses.items.weapons.sling_nft_item.SlingNFTItem",
    "key": "Shepherd's Sling",
    "aliases": ["sling", "shepherd's sling", "shepherds sling"],
    "desc": "A leather sling imbued with arcane precision. Stones thrown from it fly straighter and hit harder.",
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
    "wear_effects": [
        {"type": "hit_bonus", "weapon_type": "sling", "value": 1},
        {"type": "damage_bonus", "weapon_type": "sling", "value": 1},
    ],
    "weight": 0.3,
    "max_durability": 1440,
}
