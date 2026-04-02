from enums.wearslot import HumanoidWearSlot

GREAVES_OF_THE_VANGUARD = {
    "prototype_key": "greaves_of_the_vanguard",
    "typeclass": "typeclasses.items.wearables.wearable_nft_item.WearableNFTItem",
    "mob_typeclass": "typeclasses.items.mob_items.mob_wearable.MobWearable",
    "key": "Greaves of the Vanguard",
    "aliases": ["greaves", "vanguard greaves", "greaves of the vanguard"],
    "desc": "Bronze greaves crackling with arcane swiftness. The wearer is always first to act.",
    "wearslot": HumanoidWearSlot.LEGS,
    "wear_effects": [{"type": "stat_bonus", "stat": "initiative_bonus", "value": 1}],
    "excluded_classes": ["mage"],
    "weight": 2.0,
    "max_durability": 5400,
}
