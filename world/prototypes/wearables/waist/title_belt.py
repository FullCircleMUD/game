from enums.wearslot import HumanoidWearSlot

TITLE_BELT = {
    "prototype_key": "title_belt",
    "typeclass": "typeclasses.items.wearables.wearable_nft_item.WearableNFTItem",
    "mob_typeclass": "typeclasses.items.mob_items.mob_wearable.MobWearable",
    "key": "Title Belt",
    "aliases": ["belt", "title belt"],
    "desc": "A championship belt of thick, enchanted leather that absorbs the force of blunt impacts.",
    "wearslot": HumanoidWearSlot.WAIST,
    "wear_effects": [{"type": "damage_resistance", "damage_type": "bludgeoning", "value": 10}],
    "weight": 0.5,
    "max_durability": 1440,
}
