from enums.unused_for_reference.damage_type import DamageType
from enums.mastery_level import MasteryLevel

BRONZE_GREATSWORD = {
    "prototype_key": "bronze_greatsword",
    "typeclass": "typeclasses.items.weapons.greatsword_nft_item.GreatswordNFTItem",
    "key": "Bronze Greatsword",
    "aliases": ["greatsword", "bronze greatsword"],
    "desc": "A massive two-handed bronze blade. Slow but devastating.",
    "damage": {
        MasteryLevel.UNSKILLED: "1D4",
        MasteryLevel.BASIC: "1D8",
        MasteryLevel.SKILLED: "1D10",
        MasteryLevel.EXPERT: "1D12",
        MasteryLevel.MASTER: "1D12",
        MasteryLevel.GRANDMASTER: "1D12",
    },
    "damage_type": DamageType.SLASHING,
    "weapon_type": "melee",
    "two_handed": True,
    "speed": 1.2,
    "weight": 4.5,
    "max_durability": 3600,
    "wear_effects": [],
}
