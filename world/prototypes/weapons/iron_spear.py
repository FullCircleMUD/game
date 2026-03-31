from enums.unused_for_reference.damage_type import DamageType

IRON_SPEAR = {
    "prototype_key": "iron_spear",
    "typeclass": "typeclasses.items.weapons.spear_nft_item.SpearNFTItem",
    "key": "Iron Spear",
    "aliases": ["spear", "iron spear"],
    "desc": "An iron-tipped spear mounted on a wooden shaft. Good reach and piercing damage.",
    "base_damage": "d8",
    "material": "iron",
    "damage_type": DamageType.PIERCING,
    "weapon_type": "melee",
    "speed": 1,
    "weight": 3.0,
    "max_durability": 5400,
}
