from enums.unused_for_reference.damage_type import DamageType

BRONZE_BATTLEAXE = {
    "prototype_key": "bronze_battleaxe",
    "typeclass": "typeclasses.items.weapons.battleaxe_nft_item.BattleaxeNFTItem",
    "key": "Bronze Battleaxe",
    "aliases": ["battleaxe", "battle axe", "bronze battleaxe"],
    "desc": "A large two-handed bronze axe head mounted on a wooden haft. Heavy hits, slow recovery.",
    "base_damage": "d10",
    "material": "bronze",
    "damage_type": DamageType.SLASHING,
    "weapon_type": "melee",
    "two_handed": True,
    "speed": 0,
    "weight": 4.0,
    "max_durability": 3600,
    "wear_effects": [],
}
