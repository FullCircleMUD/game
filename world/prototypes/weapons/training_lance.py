from enums.unused_for_reference.damage_type import DamageType

TRAINING_LANCE = {
    "prototype_key": "training_lance",
    "typeclass": "typeclasses.items.weapons.lance_nft_item.LanceNFTItem",
    "mob_typeclass": "typeclasses.items.mob_items.mob_weapons.MobLance",
    "key": "Training Lance",
    "aliases": ["lance", "training lance"],
    "desc": "A long wooden lance with a blunted tip. Used for jousting practice and mounted drills.",
    "base_damage": "2d7",
    "material": "wood",
    "damage_type": DamageType.BLUDGEONING,
    "weapon_type": "melee",
    "speed": 0,
    "weight": 4.0,
    "max_durability": 1440,
    "wear_effects": [],
}
