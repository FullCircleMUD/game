from enums.unused_for_reference.damage_type import DamageType

BRONZE_LONGSWORD = {
    "prototype_key": "bronze_longsword",
    "typeclass": "typeclasses.items.weapons.longsword_nft_item.LongswordNFTItem",
    "key": "Bronze Longsword",
    "aliases": ["longsword", "bronze longsword"],
    "desc": "A broad bronze blade. Heavier than iron but a solid weapon.",
    "base_damage": "d8",
    "material": "bronze",
    "damage_type": DamageType.SLASHING,
    "weapon_type": "melee",
    "speed": 1,
    "weight": 3.0,
    "max_durability": 3600,
    "wear_effects": [],
}
