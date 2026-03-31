from enums.unused_for_reference.damage_type import DamageType

QUARTERSTAFF = {
    "prototype_key": "quarterstaff",
    "typeclass": "typeclasses.items.weapons.staff_nft_item.StaffNFTItem",
    "key": "Quarterstaff",
    "aliases": ["staff", "quarterstaff"],
    "desc": "A sturdy timber staff as tall as a man. Simple but effective in trained hands.",
    "base_damage": "d6",
    "material": "bronze",
    "damage_type": DamageType.BLUDGEONING,
    "weapon_type": "melee",
    "speed": 1,
    "weight": 2.0,
    "max_durability": 2880,
    "wear_effects": [],
}
