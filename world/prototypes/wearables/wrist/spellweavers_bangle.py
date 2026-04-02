from enums.wearslot import HumanoidWearSlot

SPELLWEAVERS_BANGLE = {
    "prototype_key": "spellweavers_bangle",
    "typeclass": "typeclasses.items.wearables.wearable_nft_item.WearableNFTItem",
    "mob_typeclass": "typeclasses.items.mob_items.mob_wearable.MobWearable",
    "key": "Spellweaver's Bangle",
    "aliases": ["bangle", "spellweaver's bangle", "spellweavers bangle"],
    "desc": "A copper bangle crackling with faint arcane sparks. It deepens the wearer's mana reserves.",
    "wearslot": [HumanoidWearSlot.LEFT_WRIST, HumanoidWearSlot.RIGHT_WRIST],
    "wear_effects": [{"type": "stat_bonus", "stat": "mana_max", "value": 5}],
    "weight": 0.2,
    "max_durability": 3600,
}
