from enums.wearslot import HumanoidWearSlot

PEWTER_BRACELET = {
    "prototype_key": "pewter_bracelet",
    "typeclass": "typeclasses.items.wearables.wearable_nft_item.WearableNFTItem",
    "mob_typeclass": "typeclasses.items.mob_items.mob_wearable.MobWearable",
    "key": "Pewter Bracelet",
    "aliases": ["bracelet"],
    "desc": "A flat pewter bracelet with a hammered finish.",
    "wearslot": [HumanoidWearSlot.LEFT_WRIST, HumanoidWearSlot.RIGHT_WRIST],
    "wear_effects": [],
    "weight": 0.2,
    "max_durability": 3600,
}
