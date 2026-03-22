from enums.unused_for_reference.damage_type import DamageType
from enums.mastery_level import MasteryLevel

IRON_HAMMER = {
    "prototype_key": "iron_hammer",
    "typeclass": "typeclasses.items.weapons.hammer_nft_item.HammerNFTItem",
    "key": "Iron Hammer",
    "aliases": ["hammer", "iron hammer"],
    "desc": "A solid iron hammer head mounted on a wooden haft. Delivers devastating blows.",
    "damage": {
        MasteryLevel.UNSKILLED: "1D4+1",
        MasteryLevel.BASIC: "1D6+1",
        MasteryLevel.SKILLED: "1D8",
        MasteryLevel.EXPERT: "1D8+1",
        MasteryLevel.MASTER: "1D10",
        MasteryLevel.GRANDMASTER: "1D10",
    },
    "damage_type": DamageType.BLUDGEONING,
    "weapon_type": "melee",
    "speed": 1.1,
    "weight": 3.5,
    "max_durability": 5400,
    "wear_effects": [],
}
