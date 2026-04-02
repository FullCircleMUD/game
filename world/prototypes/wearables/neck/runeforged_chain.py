from enums.wearslot import HumanoidWearSlot

RUNEFORGED_CHAIN = {
    "prototype_key": "runeforged_chain",
    "typeclass": "typeclasses.items.wearables.wearable_nft_item.WearableNFTItem",
    "mob_typeclass": "typeclasses.items.mob_items.mob_wearable.MobWearable",
    "key": "Runeforged Chain",
    "aliases": ["chain", "necklace", "runeforged chain"],
    "desc": "A copper chain inscribed with dwarven runes of war. It hums with quiet fury in dwarven hands.",
    "wearslot": HumanoidWearSlot.NECK,
    "wear_effects": [
        {"type": "stat_bonus", "stat": "total_hit_bonus", "value": 1},
        {"type": "stat_bonus", "stat": "total_damage_bonus", "value": 1},
    ],
    "required_races": ["dwarf"],
    "weight": 0.2,
    "max_durability": 3600,
}
