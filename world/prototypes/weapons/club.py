from enums.unused_for_reference.damage_type import DamageType

WOODEN_CLUB = {
    "prototype_key": "wooden_club",
    "typeclass": "typeclasses.items.weapons.club_nft_item.ClubNFTItem",
    "key": "Wooden Club",
    "aliases": ["club", "cudgel", "wooden club"],
    "desc": "A heavy wooden club. Simple, brutal, and effective.",
    "base_damage": "d6",
    "material": "wood",
    "damage_type": DamageType.BLUDGEONING,
    "weapon_type": "melee",
    "speed": 1,
    "weight": 2.5,
    "max_durability": 2880,
}
