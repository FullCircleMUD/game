from enums.unused_for_reference.damage_type import DamageType

BRONZE_SHORTSWORD = {
    "prototype_key": "bronze_shortsword",
    "typeclass": "typeclasses.items.weapons.shortsword_nft_item.ShortswordNFTItem",
    "mob_typeclass": "typeclasses.items.mob_items.mob_weapons.MobShortsword",
    "key": "Bronze Shortsword",
    "aliases": ["shortsword", "bronze shortsword"],
    "desc": "A sturdy bronze shortsword. Quick and reliable.",
    "base_damage": "d6",
    "material": "bronze",
    "damage_type": DamageType.SLASHING,
    "weapon_type": "melee",
    "speed": 2,
    "weight": 2.0,
    "max_durability": 3600,
    "wear_effects": [],
}
