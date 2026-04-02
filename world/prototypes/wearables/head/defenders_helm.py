from enums.wearslot import HumanoidWearSlot

DEFENDERS_HELM = {
    "prototype_key": "defenders_helm",
    "typeclass": "typeclasses.items.wearables.wearable_nft_item.WearableNFTItem",
    "mob_typeclass": "typeclasses.items.mob_items.mob_wearable.MobWearable",
    "key": "Defender's Helm",
    "aliases": ["helm", "helmet", "defender's helm", "defenders helm"],
    "desc": "A bronze helmet radiating protective magic. Critical blows glance harmlessly off its surface.",
    "wearslot": HumanoidWearSlot.HEAD,
    "wear_effects": [{"type": "condition", "condition": "crit_immune"}],
    "excluded_classes": ["mage"],
    "weight": 2.0,
    "max_durability": 5400,
}
