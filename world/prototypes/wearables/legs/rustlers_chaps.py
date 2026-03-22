from enums.wearslot import HumanoidWearSlot

RUSTLERS_CHAPS = {
    "prototype_key": "rustlers_chaps",
    "typeclass": "typeclasses.items.wearables.wearable_nft_item.WearableNFTItem",
    "key": "Rustler's Chaps",
    "aliases": ["chaps", "rustlers chaps"],
    "desc": "Rugged leather chaps enchanted to grant the wearer tireless stamina on long rides.",
    "wearslot": HumanoidWearSlot.LEGS,
    "wear_effects": [{"type": "stat_bonus", "stat": "move_max", "value": 15}],
    "weight": 1.5,
    "max_durability": 1440,
}
