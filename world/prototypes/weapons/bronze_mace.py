from enums.unused_for_reference.damage_type import DamageType
from enums.mastery_level import MasteryLevel

BRONZE_MACE = {
    "prototype_key": "bronze_mace",
    "typeclass": "typeclasses.items.weapons.mace_nft_item.MaceNFTItem",
    "key": "Bronze Mace",
    "aliases": ["mace", "bronze mace"],
    "desc": "A heavy bronze mace head fixed to a wooden haft. Crushes armour effectively.",
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
    "speed": 1.0,
    "weight": 2.5,
    "max_durability": 3600,
    "wear_effects": [],
}
