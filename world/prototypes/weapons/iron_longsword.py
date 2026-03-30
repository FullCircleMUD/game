from enums.unused_for_reference.damage_type import DamageType

IRON_LONGSWORD = {
    "prototype_key": "iron_longsword",
    "typeclass": "typeclasses.items.weapons.longsword_nft_item.LongswordNFTItem",
    "key": "Iron Longsword",
    "aliases": ["sword", "longsword", "iron"],
    "desc": "A sturdy iron blade, forged by a competent smith.",
    "base_damage": "d8",
    "material": "iron",
    "damage_type": DamageType.SLASHING,
    "weapon_type": "melee",
    "speed": 2,
    "weight": 3.0,
    "max_durability": 5400,
}
