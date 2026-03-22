from enums.unused_for_reference.damage_type import DamageType
from enums.mastery_level import MasteryLevel

IRON_SPIKED_CLUB = {
    "prototype_key": "iron_spiked_club",
    "typeclass": "typeclasses.items.weapons.club_nft_item.ClubNFTItem",
    "key": "Iron Spiked Club",
    "aliases": ["club", "spiked club", "iron spiked club"],
    "desc": "A heavy wooden club studded with iron spikes. Brutal and effective.",
    "damage": {
        MasteryLevel.UNSKILLED: "1D4",
        MasteryLevel.BASIC: "1D6+1",
        MasteryLevel.SKILLED: "1D8+1",
        MasteryLevel.EXPERT: "1D10",
        MasteryLevel.MASTER: "1D10",
        MasteryLevel.GRANDMASTER: "1D10",
    },
    "damage_type": DamageType.BLUDGEONING,
    "weapon_type": "melee",
    "speed": 1.2,
    "weight": 3.0,
    "max_durability": 5400,
    "wear_effects": [],
}
