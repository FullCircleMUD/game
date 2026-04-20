from enums.wearslot import HumanoidWearSlot

COARSE_ROBE = {
    "prototype_key": "coarse_robe",
    "typeclass": "typeclasses.items.wearables.wearable_nft_item.WearableNFTItem",
    "mob_typeclass": "typeclasses.items.mob_items.mob_wearable.MobWearable",
    "key": "Coarse Robe",
    "aliases": ["robe"],
    "desc": "A rough-spun robe of undyed cloth. Simple and functional.",
    "wearslot": HumanoidWearSlot.BODY,
    "wear_effects": [{"type": "stat_bonus", "stat": "mana_max", "value": 10}],
    "weight": 1.5,
    "max_durability": 720,
    "size": "small",
}
