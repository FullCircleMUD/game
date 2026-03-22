from enums.unused_for_reference.damage_type import DamageType
from enums.mastery_level import MasteryLevel

BRONZE_RAPIER = {
    "prototype_key": "bronze_rapier",
    "typeclass": "typeclasses.items.weapons.rapier_nft_item.RapierNFTItem",
    "key": "Bronze Rapier",
    "aliases": ["rapier", "bronze rapier"],
    "desc": "A thin bronze thrusting blade. Fast and precise, favouring dexterity over brute strength.",
    "damage": {
        MasteryLevel.UNSKILLED: "1D3",
        MasteryLevel.BASIC: "1D4+1",
        MasteryLevel.SKILLED: "1D6",
        MasteryLevel.EXPERT: "1D6+1",
        MasteryLevel.MASTER: "1D8",
        MasteryLevel.GRANDMASTER: "1D8",
    },
    "damage_type": DamageType.PIERCING,
    "weapon_type": "melee",
    "speed": 0.7,
    "weight": 1.5,
    "max_durability": 3600,
    "wear_effects": [],
}
