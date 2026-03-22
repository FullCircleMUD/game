from enums.wearslot import HumanoidWearSlot

TRUEWATCH_STUDS = {
    "prototype_key": "truewatch_studs",
    "typeclass": "typeclasses.items.wearables.wearable_nft_item.WearableNFTItem",
    "key": "Truewatch Studs",
    "aliases": ["studs", "earrings", "truewatch studs"],
    "desc": "Copper studs enchanted to sharpen the wearer's awareness. Nothing escapes their notice.",
    "wearslot": [HumanoidWearSlot.LEFT_EAR, HumanoidWearSlot.RIGHT_EAR],
    "wear_effects": [{"type": "stat_bonus", "stat": "perception_bonus", "value": 1}],
    "weight": 0.2,
    "max_durability": 3600,
}
