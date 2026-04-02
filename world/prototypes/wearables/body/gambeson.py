from enums.wearslot import HumanoidWearSlot

GAMBESON = {
    "prototype_key": "gambeson",
    "typeclass": "typeclasses.items.wearables.wearable_nft_item.WearableNFTItem",
    "mob_typeclass": "typeclasses.items.mob_items.mob_wearable.MobWearable",
    "key": "Gambeson",
    "aliases": ["gambeson"],
    "desc": "Layers of quilted cloth stitched over a linen lining. Light but protective.",
    "wearslot": HumanoidWearSlot.BODY,
    "wear_effects": [{"type": "stat_bonus", "stat": "armor_class", "value": 1}],
    "excluded_classes": ["mage"],
    "weight": 3.0,
    "max_durability": 1440,
}
