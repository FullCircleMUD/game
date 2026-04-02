from enums.wearslot import HumanoidWearSlot

WARRIORS_WRAPS = {
    "prototype_key": "warriors_wraps",
    "typeclass": "typeclasses.items.wearables.wearable_nft_item.WearableNFTItem",
    "mob_typeclass": "typeclasses.items.mob_items.mob_wearable.MobWearable",
    "key": "Warrior's Wraps",
    "aliases": ["wraps"],
    "desc": "Thick cloth strips wound tightly around the hands and wrists. They bolster the wearer's vitality.",
    "wearslot": HumanoidWearSlot.HANDS,
    "wear_effects": [{"type": "stat_bonus", "stat": "hp_max", "value": 10}],
    "excluded_classes": ["mage", "cleric", "thief"],
    "weight": 0.3,
    "max_durability": 720,
}
