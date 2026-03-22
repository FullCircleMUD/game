from enums.wearslot import HumanoidWearSlot

SCOUTS_CAP = {
    "prototype_key": "scouts_cap",
    "typeclass": "typeclasses.items.wearables.wearable_nft_item.WearableNFTItem",
    "key": "Scout's Cap",
    "aliases": ["cap", "scouts cap"],
    "desc": "A close-fitting leather cap enchanted to sharpen the wearer's reflexes.",
    "wearslot": HumanoidWearSlot.HEAD,
    "wear_effects": [{"type": "stat_bonus", "stat": "initiative_bonus", "value": 1}],
    "weight": 0.8,
    "max_durability": 1440,
}
