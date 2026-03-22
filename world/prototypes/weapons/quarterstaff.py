from enums.unused_for_reference.damage_type import DamageType
from enums.mastery_level import MasteryLevel

QUARTERSTAFF = {
    "prototype_key": "quarterstaff",
    "typeclass": "typeclasses.items.weapons.staff_nft_item.StaffNFTItem",
    "key": "Quarterstaff",
    "aliases": ["staff", "quarterstaff"],
    "desc": "A sturdy timber staff as tall as a man. Simple but effective in trained hands.",
    "damage": {
        MasteryLevel.UNSKILLED: "1D3",
        MasteryLevel.BASIC: "1D4",
        MasteryLevel.SKILLED: "1D6",
        MasteryLevel.EXPERT: "1D6",
        MasteryLevel.MASTER: "1D6",
        MasteryLevel.GRANDMASTER: "1D6",
    },
    "damage_type": DamageType.BLUDGEONING,
    "weapon_type": "melee",
    "speed": 0.9,
    "weight": 2.0,
    "max_durability": 2880,
    "wear_effects": [],
}
