from enums.unused_for_reference.damage_type import DamageType

IRON_DAGGER = {
    "prototype_key": "iron_dagger",
    "typeclass": "typeclasses.items.weapons.dagger_nft_item.DaggerNFTItem",
    "mob_typeclass": "typeclasses.items.mob_items.mob_weapons.MobDagger",
    "key": "Iron Dagger",
    "aliases": ["dagger", "iron dagger"],
    "desc": "A sharp iron dagger. Small but deadly in skilled hands.",
    "base_damage": "d4",
    "material": "iron",
    "damage_type": DamageType.PIERCING,
    "weapon_type": "melee",
    "speed": 3,
    "weight": 0.5,
    "max_durability": 5400,
}
