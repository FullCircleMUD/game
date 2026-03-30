from enums.unused_for_reference.damage_type import DamageType

SLING = {
    "prototype_key": "sling",
    "typeclass": "typeclasses.items.weapons.sling_nft_item.SlingNFTItem",
    "key": "Sling",
    "aliases": ["sling"],
    "desc": "A simple leather sling for hurling stones. Light and easy to use.",
    "base_damage": "d6",
    "material": "bronze",
    "damage_type": DamageType.BLUDGEONING,
    "weapon_type": "missile",
    "speed": 2,
    "weight": 0.3,
    "max_durability": 1440,
}
