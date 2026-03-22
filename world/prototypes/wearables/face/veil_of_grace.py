from enums.wearslot import HumanoidWearSlot

VEIL_OF_GRACE = {
    "prototype_key": "veil_of_grace",
    "typeclass": "typeclasses.items.wearables.wearable_nft_item.WearableNFTItem",
    "key": "Veil of Grace",
    "aliases": ["veil", "veil of grace"],
    "desc": "A delicate cloth veil that shimmers with enchantment. Its wearer exudes an air of quiet charm.",
    "wearslot": HumanoidWearSlot.FACE,
    "wear_effects": [{"type": "stat_bonus", "stat": "charisma", "value": 1}],
    "weight": 0.1,
    "max_durability": 720,
}
