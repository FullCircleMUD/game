from enums.unused_for_reference.damage_type import DamageType

BRONZE_GREATSWORD = {
    "prototype_key": "bronze_greatsword",
    "typeclass": "typeclasses.items.weapons.greatsword_nft_item.GreatswordNFTItem",
    "key": "Bronze Greatsword",
    "aliases": ["greatsword", "bronze greatsword"],
    "desc": "A massive two-handed bronze blade. Slow but devastating.",
    "base_damage": "2d6",
    "material": "bronze",
    "damage_type": DamageType.SLASHING,
    "weapon_type": "melee",
    "two_handed": True,
    "speed": 0,
    "weight": 4.5,
    "max_durability": 3600,
    "wear_effects": [],
}
