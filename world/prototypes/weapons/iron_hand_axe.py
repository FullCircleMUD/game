from enums.unused_for_reference.damage_type import DamageType

IRON_HAND_AXE = {
    "prototype_key": "iron_hand_axe",
    "typeclass": "typeclasses.items.weapons.axe_nft_item.AxeNFTItem",
    "key": "Iron Hand Axe",
    "aliases": ["axe", "hand axe", "handaxe", "iron axe"],
    "desc": "A compact iron axe. Good for chopping more than just wood.",
    "base_damage": "d6",
    "material": "iron",
    "damage_type": DamageType.SLASHING,
    "weapon_type": "melee",
    "speed": 3,
    "weight": 2.0,
    "max_durability": 5400,
}
