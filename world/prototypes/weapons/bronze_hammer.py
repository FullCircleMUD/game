from enums.unused_for_reference.damage_type import DamageType

BRONZE_HAMMER = {
    "prototype_key": "bronze_hammer",
    "typeclass": "typeclasses.items.weapons.hammer_nft_item.HammerNFTItem",
    "key": "Bronze Hammer",
    "aliases": ["hammer", "bronze hammer"],
    "desc": "A solid bronze hammer head mounted on a wooden haft. Delivers devastating blows.",
    "base_damage": "d8",
    "material": "bronze",
    "damage_type": DamageType.BLUDGEONING,
    "weapon_type": "melee",
    "speed": 1,
    "weight": 3.5,
    "max_durability": 3600,
    "wear_effects": [],
}
