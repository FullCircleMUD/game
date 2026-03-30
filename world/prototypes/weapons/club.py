from enums.unused_for_reference.damage_type import DamageType

CLUB = {
    "prototype_key": "club",
    "typeclass": "typeclasses.items.weapons.club_nft_item.ClubNFTItem",
    "key": "Club",
    "aliases": ["club", "cudgel"],
    "desc": "A heavy wooden club. Simple, brutal, and effective.",
    "base_damage": "d4",
    "material": "wood",
    "damage_type": DamageType.BLUDGEONING,
    "weapon_type": "melee",
    "speed": 1,
    "weight": 2.5,
    "max_durability": 2880,
}
