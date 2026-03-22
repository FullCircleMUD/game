from enums.unused_for_reference.damage_type import DamageType
from enums.mastery_level import MasteryLevel

IRON_MACE = {
    "prototype_key": "iron_mace",
    "typeclass": "typeclasses.items.weapons.mace_nft_item.MaceNFTItem",
    "key": "Iron Mace",
    "aliases": ["mace", "iron mace"],
    "desc": "A heavy iron mace head fixed to a wooden haft. Crushes armour with brutal efficiency.",
    "damage": {
        MasteryLevel.UNSKILLED: "1D4",
        MasteryLevel.BASIC: "1D6",
        MasteryLevel.SKILLED: "1D6+1",
        MasteryLevel.EXPERT: "1D8",
        MasteryLevel.MASTER: "1D8",
        MasteryLevel.GRANDMASTER: "1D8",
    },
    "damage_type": DamageType.BLUDGEONING,
    "weapon_type": "melee",
    "speed": 1.0,
    "weight": 2.5,
    "max_durability": 5400,
    "wear_effects": [],
}
