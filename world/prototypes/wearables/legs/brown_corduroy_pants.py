from enums.wearslot import HumanoidWearSlot

BROWN_CORDUROY_PANTS = {
    "prototype_key": "brown_corduroy_pants",
    "typeclass": "typeclasses.items.wearables.wearable_nft_item.WearableNFTItem",
    "mob_typeclass": "typeclasses.items.mob_items.mob_wearable.MobWearable",
    "key": "Brown Corduroy Pants",
    "aliases": ["pants", "trousers", "corduroy"],
    "desc": "Sturdy brown corduroy trousers with a drawstring waist. Comfortable and hardwearing.",
    "wearslot": HumanoidWearSlot.LEGS,
    "wear_effects": [{"type": "stat_bonus", "stat": "move_max", "value": 10}],
    "weight": 0.8,
    "max_durability": 720,
    "size": "small",
}
