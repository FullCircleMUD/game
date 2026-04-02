from enums.wearslot import HumanoidWearSlot

SUN_BLEACHED_SASH = {
    "prototype_key": "sun_bleached_sash",
    "typeclass": "typeclasses.items.wearables.wearable_nft_item.WearableNFTItem",
    "mob_typeclass": "typeclasses.items.mob_items.mob_wearable.MobWearable",
    "key": "Sun Bleached Sash",
    "aliases": ["sash", "sun bleached sash"],
    "desc": "A wide cloth sash bleached by sun and suffused with enchantment. Toughens the body of its wearer.",
    "wearslot": HumanoidWearSlot.WAIST,
    "wear_effects": [{"type": "stat_bonus", "stat": "constitution", "value": 1}],
    "weight": 0.2,
    "max_durability": 720,
}
