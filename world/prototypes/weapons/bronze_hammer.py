from enums.unused_for_reference.damage_type import DamageType
from enums.mastery_level import MasteryLevel

BRONZE_HAMMER = {
    "prototype_key": "bronze_hammer",
    "typeclass": "typeclasses.items.weapons.hammer_nft_item.HammerNFTItem",
    "key": "Bronze Hammer",
    "aliases": ["hammer", "bronze hammer"],
    "desc": "A solid bronze hammer head mounted on a wooden haft. Delivers devastating blows.",
    "damage": {
        MasteryLevel.UNSKILLED: "1D4",
        MasteryLevel.BASIC: "1D6",
        MasteryLevel.SKILLED: "1D8",
        MasteryLevel.EXPERT: "1D8",
        MasteryLevel.MASTER: "1D8",
        MasteryLevel.GRANDMASTER: "1D8",
    },
    "damage_type": DamageType.BLUDGEONING,
    "weapon_type": "melee",
    "speed": 1.1,
    "weight": 3.5,
    "max_durability": 3600,
    "wear_effects": [],
}
