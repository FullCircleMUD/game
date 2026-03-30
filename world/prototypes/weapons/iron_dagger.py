from enums.unused_for_reference.damage_type import DamageType

IRON_DAGGER = {
    "prototype_key": "iron_dagger",
    "typeclass": "typeclasses.items.weapons.dagger_nft_item.DaggerNFTItem",
    "key": "Iron Dagger",
    "aliases": ["dagger", "iron dagger"],
    "desc": "A sharp iron dagger. Small but deadly in skilled hands.",
    "base_damage": "d4",
    "material": "iron",
    "damage_type": DamageType.PIERCING,
    "weapon_type": "melee",
    "speed": 4,
    "weight": 0.5,
    "max_durability": 5400,
}
