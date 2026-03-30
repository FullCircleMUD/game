from enums.unused_for_reference.damage_type import DamageType

IRON_SHORTSWORD = {
    "prototype_key": "iron_shortsword",
    "typeclass": "typeclasses.items.weapons.shortsword_nft_item.ShortswordNFTItem",
    "key": "Iron Shortsword",
    "aliases": ["shortsword", "iron shortsword"],
    "desc": "A well-forged iron shortsword. Quick and versatile.",
    "base_damage": "d6",
    "material": "iron",
    "damage_type": DamageType.SLASHING,
    "weapon_type": "melee",
    "speed": 3,
    "weight": 2.0,
    "max_durability": 5400,
}
