from enums.unused_for_reference.damage_type import DamageType

SHORTBOW = {
    "prototype_key": "shortbow",
    "typeclass": "typeclasses.items.weapons.bow_nft_item.BowNFTItem",
    "mob_typeclass": "typeclasses.items.mob_items.mob_weapons.MobBow",
    "key": "Shortbow",
    "aliases": ["bow", "shortbow", "short bow"],
    "desc": "A compact timber bow with good draw strength. Light and quick to fire.",
    "base_damage": "d8",
    "material": "wood",
    "damage_type": DamageType.PIERCING,
    "weapon_type": "missile",
    "speed": 1,
    "weight": 1.5,
    "max_durability": 2880,
    "wear_effects": [],
}
