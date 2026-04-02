from enums.wearslot import HumanoidWearSlot

SAGES_KIPPAH = {
    "prototype_key": "sages_kippah",
    "typeclass": "typeclasses.items.wearables.wearable_nft_item.WearableNFTItem",
    "mob_typeclass": "typeclasses.items.mob_items.mob_wearable.MobWearable",
    "key": "Sage's Kippah",
    "aliases": ["kippah", "sages kippah"],
    "desc": "An embroidered skullcap that glows faintly with arcane wisdom.",
    "wearslot": HumanoidWearSlot.HEAD,
    "wear_effects": [{"type": "stat_bonus", "stat": "wisdom", "value": 1}],
    "weight": 0.1,
    "max_durability": 720,
}
