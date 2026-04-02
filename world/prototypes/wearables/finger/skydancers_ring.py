from enums.wearslot import HumanoidWearSlot

SKYDANCERS_RING = {
    "prototype_key": "skydancers_ring",
    "typeclass": "typeclasses.items.wearables.wearable_nft_item.WearableNFTItem",
    "mob_typeclass": "typeclasses.items.mob_items.mob_wearable.MobWearable",
    "key": "Skydancer's Ring",
    "aliases": ["ring", "skydancer's ring", "skydancers ring"],
    "desc": "A pewter ring carved with feathered motifs. The metal feels impossibly light, as though yearning to take flight.",
    "wearslot": [HumanoidWearSlot.LEFT_RING_FINGER, HumanoidWearSlot.RIGHT_RING_FINGER],
    "wear_effects": [{"type": "condition", "condition": "fly"}],
    "weight": 0.2,
    "max_durability": 3600,
}
