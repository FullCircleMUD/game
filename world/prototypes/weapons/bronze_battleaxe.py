from enums.unused_for_reference.damage_type import DamageType
from enums.mastery_level import MasteryLevel

BRONZE_BATTLEAXE = {
    "prototype_key": "bronze_battleaxe",
    "typeclass": "typeclasses.items.weapons.battleaxe_nft_item.BattleaxeNFTItem",
    "key": "Bronze Battleaxe",
    "aliases": ["battleaxe", "battle axe", "bronze battleaxe"],
    "desc": "A large two-handed bronze axe head mounted on a wooden haft. Heavy hits, slow recovery.",
    "damage": {
        MasteryLevel.UNSKILLED: "1D4",
        MasteryLevel.BASIC: "1D6+1",
        MasteryLevel.SKILLED: "1D8+1",
        MasteryLevel.EXPERT: "1D10",
        MasteryLevel.MASTER: "1D10+1",
        MasteryLevel.GRANDMASTER: "1D12",
    },
    "damage_type": DamageType.SLASHING,
    "weapon_type": "melee",
    "two_handed": True,
    "speed": 1.1,
    "weight": 4.0,
    "max_durability": 3600,
    "wear_effects": [],
}
