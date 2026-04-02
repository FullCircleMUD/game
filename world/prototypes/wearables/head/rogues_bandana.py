from enums.wearslot import HumanoidWearSlot

ROGUES_BANDANA = {
    "prototype_key": "rogues_bandana",
    "typeclass": "typeclasses.items.wearables.wearable_nft_item.WearableNFTItem",
    "mob_typeclass": "typeclasses.items.mob_items.mob_wearable.MobWearable",
    "key": "Rogue's Bandana",
    "aliases": ["bandana", "rogues bandana"],
    "desc": "A dark cloth bandana imbued with enchantment. It sharpens the senses and quickens the hands.",
    "wearslot": HumanoidWearSlot.HEAD,
    "wear_effects": [{"type": "stat_bonus", "stat": "dexterity", "value": 1}],
    "required_classes": ["thief"],
    "weight": 0.1,
    "max_durability": 720,
}
