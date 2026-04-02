from enums.unused_for_reference.damage_type import DamageType

TRAINING_BOW = {
    "prototype_key": "training_bow",
    "typeclass": "typeclasses.items.weapons.bow_nft_item.BowNFTItem",
    "mob_typeclass": "typeclasses.items.mob_items.mob_weapons.MobBow",
    "key": "Training Bow",
    "aliases": ["bow", "training bow"],
    "desc": "A crude practice bow carved from a single piece of timber. Fires blunt-tipped arrows.",
    "base_damage": "d6",
    "material": "wood",
    "damage_type": DamageType.BLUDGEONING,
    "weapon_type": "missile",
    "speed": 1,
    "weight": 1.5,
    "max_durability": 2880,
}
