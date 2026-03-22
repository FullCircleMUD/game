from enums.wearslot import HumanoidWearSlot

WARDENS_LEATHER = {
    "prototype_key": "wardens_leather",
    "typeclass": "typeclasses.items.wearables.wearable_nft_item.WearableNFTItem",
    "key": "Warden's Leather",
    "aliases": ["armor", "leather", "warden's leather", "wardens leather"],
    "desc": "Leather armor enchanted to turn aside piercing blows. The surface shimmers faintly with protective magic.",
    "wearslot": HumanoidWearSlot.BODY,
    "wear_effects": [
        {"type": "stat_bonus", "stat": "armor_class", "value": 2},
        {"type": "damage_resistance", "damage_type": "piercing", "value": 10},
    ],
    "excluded_classes": ["mage"],
    "weight": 5.0,
    "max_durability": 1440,
}
