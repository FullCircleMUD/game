from enums.unused_for_reference.damage_type import DamageType

TRAINING_DAGGER = {
    "prototype_key": "training_dagger",
    "typeclass": "typeclasses.items.weapons.dagger_nft_item.DaggerNFTItem",
    "mob_typeclass": "typeclasses.items.mob_items.mob_weapons.MobDagger",
    "key": "Training Dagger",
    "aliases": ["dagger", "training dagger"],
    "desc": "A blunt wooden dagger used for practice. Light and fast, but harmless.",
    "base_damage": "d4",
    "material": "wood",
    "damage_type": DamageType.BLUDGEONING,
    "weapon_type": "melee",
    "speed": 3,
    "weight": 0.5,
    "max_durability": 1440,
}
