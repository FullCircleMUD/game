from enums.unused_for_reference.damage_type import DamageType

BRONZE_SPEAR = {
    "prototype_key": "bronze_spear",
    "typeclass": "typeclasses.items.weapons.spear_nft_item.SpearNFTItem",
    "mob_typeclass": "typeclasses.items.mob_items.mob_weapons.MobSpear",
    "key": "Bronze Spear",
    "aliases": ["spear", "bronze spear"],
    "desc": "A bronze-tipped spear mounted on a wooden shaft. Good reach.",
    "base_damage": "d6",
    "material": "bronze",
    "damage_type": DamageType.PIERCING,
    "weapon_type": "melee",
    "speed": 1,
    "weight": 3.0,
    "max_durability": 3600,
    "wear_effects": [],
}
