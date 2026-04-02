from enums.unused_for_reference.damage_type import DamageType

CROSSBOW = {
    "prototype_key": "crossbow",
    "typeclass": "typeclasses.items.weapons.crossbow_nft_item.CrossbowNFTItem",
    "mob_typeclass": "typeclasses.items.mob_items.mob_weapons.MobCrossbow",
    "key": "Crossbow",
    "aliases": ["crossbow"],
    "desc": "A mechanical crossbow with an iron prod and timber stock. High damage, slow to reload.",
    "base_damage": "d12",
    "material": "wood",
    "damage_type": DamageType.PIERCING,
    "weapon_type": "missile",
    "speed": 0,
    "weight": 3.5,
    "max_durability": 5400,
    "wear_effects": [],
}
