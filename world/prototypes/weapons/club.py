from enums.unused_for_reference.damage_type import DamageType
from enums.mastery_level import MasteryLevel

CLUB = {
    "prototype_key": "club",
    "typeclass": "typeclasses.items.weapons.club_nft_item.ClubNFTItem",
    "key": "Club",
    "aliases": ["club", "cudgel"],
    "desc": "A heavy wooden club. Simple, brutal, and effective.",
    "damage": {
        MasteryLevel.UNSKILLED: "1D3",
        MasteryLevel.BASIC: "1D6",
        MasteryLevel.SKILLED: "1D8",
        MasteryLevel.EXPERT: "1D8",
        MasteryLevel.MASTER: "1D8",
        MasteryLevel.GRANDMASTER: "1D8",
    },
    "damage_type": DamageType.BLUDGEONING,
    "weapon_type": "melee",
    "speed": 1.2,
    "weight": 2.5,
    "max_durability": 2880,
}
