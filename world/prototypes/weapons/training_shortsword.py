from enums.unused_for_reference.damage_type import DamageType

TRAINING_SHORTSWORD = {
    "prototype_key": "training_shortsword",
    "typeclass": "typeclasses.items.weapons.shortsword_nft_item.ShortswordNFTItem",
    "key": "Training Shortsword",
    "aliases": ["shortsword", "short sword", "training shortsword"],
    "desc": "A wooden practice shortsword. Lighter than a longsword, good for one-handed drills.",
    "base_damage": "d6",
    "material": "wood",
    "damage_type": DamageType.BLUDGEONING,
    "weapon_type": "melee",
    "speed": 3,
    "weight": 1.5,
    "max_durability": 1440,
}
