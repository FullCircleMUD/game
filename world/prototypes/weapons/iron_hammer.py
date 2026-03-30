from enums.unused_for_reference.damage_type import DamageType

IRON_HAMMER = {
    "prototype_key": "iron_hammer",
    "typeclass": "typeclasses.items.weapons.hammer_nft_item.HammerNFTItem",
    "key": "Iron Hammer",
    "aliases": ["hammer", "iron hammer"],
    "desc": "A solid iron hammer head mounted on a wooden haft. Delivers devastating blows.",
    "base_damage": "d8",
    "material": "iron",
    "damage_type": DamageType.BLUDGEONING,
    "weapon_type": "melee",
    "speed": 1,
    "weight": 3.5,
    "max_durability": 5400,
    "wear_effects": [],
}
