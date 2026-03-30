from enums.unused_for_reference.damage_type import DamageType

BRONZE_MACE = {
    "prototype_key": "bronze_mace",
    "typeclass": "typeclasses.items.weapons.mace_nft_item.MaceNFTItem",
    "key": "Bronze Mace",
    "aliases": ["mace", "bronze mace"],
    "desc": "A heavy bronze mace head fixed to a wooden haft. Crushes armour effectively.",
    "base_damage": "d6",
    "material": "bronze",
    "damage_type": DamageType.BLUDGEONING,
    "weapon_type": "melee",
    "speed": 2,
    "weight": 2.5,
    "max_durability": 3600,
    "wear_effects": [],
}
