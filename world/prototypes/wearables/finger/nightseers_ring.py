from enums.wearslot import HumanoidWearSlot

NIGHTSEERS_RING = {
    "prototype_key": "nightseers_ring",
    "typeclass": "typeclasses.items.wearables.wearable_nft_item.WearableNFTItem",
    "mob_typeclass": "typeclasses.items.mob_items.mob_wearable.MobWearable",
    "key": "Nightseer's Ring",
    "aliases": ["ring", "nightseer's ring", "nightseers ring"],
    "desc": "A copper ring etched with tiny runes that glow faintly in darkness. It grants sight beyond sight.",
    "wearslot": [HumanoidWearSlot.LEFT_RING_FINGER, HumanoidWearSlot.RIGHT_RING_FINGER],
    "wear_effects": [{"type": "condition", "condition": "darkvision"}],
    "weight": 0.2,
    "max_durability": 3600,
}
