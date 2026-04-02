from enums.wearslot import HumanoidWearSlot

BRACERS_OF_DEFLECTION = {
    "prototype_key": "bracers_of_deflection",
    "typeclass": "typeclasses.items.wearables.wearable_nft_item.WearableNFTItem",
    "mob_typeclass": "typeclasses.items.mob_items.mob_wearable.MobWearable",
    "key": "Bracers of Deflection",
    "aliases": ["bracers", "bracers of deflection"],
    "desc": "Bronze bracers shimmering with enchantment. Slashing blows slide off their surface.",
    "wearslot": [HumanoidWearSlot.LEFT_WRIST, HumanoidWearSlot.RIGHT_WRIST],
    "wear_effects": [{"type": "damage_resistance", "damage_type": "slashing", "value": 10}],
    "excluded_classes": ["mage"],
    "weight": 1.0,
    "max_durability": 5400,
}
