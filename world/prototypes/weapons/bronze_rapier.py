from enums.unused_for_reference.damage_type import DamageType

BRONZE_RAPIER = {
    "prototype_key": "bronze_rapier",
    "typeclass": "typeclasses.items.weapons.rapier_nft_item.RapierNFTItem",
    "key": "Bronze Rapier",
    "aliases": ["rapier", "bronze rapier"],
    "desc": "A thin bronze thrusting blade. Fast and precise, favouring dexterity over brute strength.",
    "base_damage": "d8",
    "material": "bronze",
    "damage_type": DamageType.PIERCING,
    "weapon_type": "melee",
    "speed": 1,
    "weight": 1.5,
    "max_durability": 3600,
    "wear_effects": [],
}
