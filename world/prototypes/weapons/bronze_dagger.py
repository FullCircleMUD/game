from enums.unused_for_reference.damage_type import DamageType

BRONZE_DAGGER = {
    "prototype_key": "bronze_dagger",
    "typeclass": "typeclasses.items.weapons.dagger_nft_item.DaggerNFTItem",
    "mob_typeclass": "typeclasses.items.mob_items.mob_weapons.MobDagger",
    "key": "Bronze Dagger",
    "aliases": ["dagger", "bronze dagger"],
    "desc": "A small bronze dagger. Light and quick, with a greenish sheen.",
    "base_damage": "d4",
    "material": "bronze",
    "damage_type": DamageType.PIERCING,
    "weapon_type": "melee",
    "speed": 3,
    "weight": 0.5,
    "max_durability": 3600,
    "wear_effects": [],
}
