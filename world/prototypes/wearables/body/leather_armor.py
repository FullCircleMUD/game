from enums.wearslot import HumanoidWearSlot

LEATHER_ARMOR = {
    "prototype_key": "leather_armor",
    "typeclass": "typeclasses.items.wearables.wearable_nft_item.WearableNFTItem",
    "key": "Leather Armor",
    "aliases": ["armor", "leather armor"],
    "desc": "A gambeson reinforced with leather plates and straps. Offers solid protection without heavy metal.",
    "wearslot": HumanoidWearSlot.BODY,
    "wear_effects": [{"type": "stat_bonus", "stat": "armor_class", "value": 2}],
    "excluded_classes": ["mage"],
    "weight": 5.0,
    "max_durability": 1440,
}
