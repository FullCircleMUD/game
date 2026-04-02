from enums.wearslot import HumanoidWearSlot

STUDDED_LEATHER_ARMOR = {
    "prototype_key": "studded_leather_armor",
    "typeclass": "typeclasses.items.wearables.wearable_nft_item.WearableNFTItem",
    "mob_typeclass": "typeclasses.items.mob_items.mob_wearable.MobWearable",
    "key": "Studded Leather Armor",
    "aliases": ["armor", "studded leather", "studded leather armor"],
    "desc": "Leather armor reinforced with iron studs and rivets. Tougher than plain leather.",
    "wearslot": HumanoidWearSlot.BODY,
    "wear_effects": [{"type": "stat_bonus", "stat": "armor_class", "value": 3}],
    "excluded_classes": ["mage"],
    "weight": 6.0,
    "max_durability": 1440,
}
