from enums.unused_for_reference.damage_type import DamageType

TRAINING_GREATSWORD = {
    "prototype_key": "training_greatsword",
    "typeclass": "typeclasses.items.weapons.greatsword_nft_item.GreatswordNFTItem",
    "key": "Training Greatsword",
    "aliases": ["greatsword", "training greatsword"],
    "desc": "A heavy two-handed practice sword carved from timber. It won't cut, but it'll flatten.",
    "base_damage": "2d6",
    "material": "wood",
    "damage_type": DamageType.BLUDGEONING,
    "weapon_type": "melee",
    "two_handed": True,
    "speed": 0,
    "weight": 3.5,
    "max_durability": 1440,
    "wear_effects": [],
}
