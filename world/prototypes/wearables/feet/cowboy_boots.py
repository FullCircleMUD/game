from enums.wearslot import HumanoidWearSlot

COWBOY_BOOTS = {
    "prototype_key": "cowboy_boots",
    "typeclass": "typeclasses.items.wearables.wearable_nft_item.WearableNFTItem",
    "key": "Cowboy Boots",
    "aliases": ["boots", "cowboy boots"],
    "desc": "Tooled leather boots with pointed toes, enchanted to reveal the unseen.",
    "wearslot": HumanoidWearSlot.FEET,
    "wear_effects": [{"type": "condition", "condition": "detect_invis"}],
    "weight": 1.0,
    "max_durability": 1440,
}
