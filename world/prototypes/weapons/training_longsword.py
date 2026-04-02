from enums.unused_for_reference.damage_type import DamageType

TRAINING_LONGSWORD = {
    "prototype_key": "training_longsword",
    "typeclass": "typeclasses.items.weapons.longsword_nft_item.LongswordNFTItem",
    "mob_typeclass": "typeclasses.items.mob_items.mob_weapons.MobLongsword",
    "key": "Training Longsword",
    "aliases": ["sword", "longsword", "training", "practice"],
    "desc": "A wooden practice sword. Won't cut much, but it'll bruise.",
    "base_damage": "d8",
    "material": "wood",
    "damage_type": DamageType.BLUDGEONING,
    "weapon_type": "melee",
    "speed": 1,
    "weight": 2.0,
    "max_durability": 1440,
}
