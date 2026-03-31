from enums.unused_for_reference.damage_type import DamageType

BRONZE_SPIKED_CLUB = {
    "prototype_key": "bronze_spiked_club",
    "typeclass": "typeclasses.items.weapons.club_nft_item.ClubNFTItem",
    "key": "Bronze Spiked Club",
    "aliases": ["club", "spiked club", "bronze spiked club"],
    "desc": "A heavy wooden club studded with bronze spikes. Simple but effective.",
    "base_damage": "d6",
    "material": "bronze",
    "damage_type": DamageType.BLUDGEONING,
    "weapon_type": "melee",
    "speed": 2,
    "weight": 2.8,
    "max_durability": 3600,
}
