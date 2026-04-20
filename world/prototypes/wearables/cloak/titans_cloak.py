from enums.wearslot import HumanoidWearSlot

TITANS_CLOAK = {
    "prototype_key": "titans_cloak",
    "typeclass": "typeclasses.items.wearables.wearable_nft_item.WearableNFTItem",
    "mob_typeclass": "typeclasses.items.mob_items.mob_wearable.MobWearable",
    "key": "Titan's Cloak",
    "aliases": ["cloak", "titans cloak"],
    "desc": "A heavy, full-length cloak suffused with enchantment. Its weight settles on the shoulders like a mantle of strength.",
    "wearslot": HumanoidWearSlot.CLOAK,
    "wear_effects": [{"type": "stat_bonus", "stat": "strength", "value": 1}],
    "weight": 1.5,
    "max_durability": 720,
    "size": "small",
}
