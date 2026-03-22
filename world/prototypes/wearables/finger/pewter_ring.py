from enums.wearslot import HumanoidWearSlot

PEWTER_RING = {
    "prototype_key": "pewter_ring",
    "typeclass": "typeclasses.items.wearables.wearable_nft_item.WearableNFTItem",
    "key": "Pewter Ring",
    "aliases": ["ring"],
    "desc": "A simple band of pewter, polished to a dull sheen.",
    "wearslot": [HumanoidWearSlot.LEFT_RING_FINGER, HumanoidWearSlot.RIGHT_RING_FINGER],
    "wear_effects": [],
    "weight": 0.2,
    "max_durability": 3600,
}
