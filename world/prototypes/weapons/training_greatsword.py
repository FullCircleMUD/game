from enums.unused_for_reference.damage_type import DamageType
from enums.mastery_level import MasteryLevel

TRAINING_GREATSWORD = {
    "prototype_key": "training_greatsword",
    "typeclass": "typeclasses.items.weapons.greatsword_nft_item.GreatswordNFTItem",
    "key": "Training Greatsword",
    "aliases": ["greatsword", "training greatsword"],
    "desc": "A heavy two-handed practice sword carved from timber. It won't cut, but it'll flatten.",
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
    "two_handed": True,
    "speed": 1.2,
    "weight": 3.5,
    "max_durability": 1440,
    "wear_effects": [],
}
