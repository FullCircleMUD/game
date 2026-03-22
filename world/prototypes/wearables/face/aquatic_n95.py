from enums.wearslot import HumanoidWearSlot

AQUATIC_N95 = {
    "prototype_key": "aquatic_n95",
    "typeclass": "typeclasses.items.wearables.wearable_nft_item.WearableNFTItem",
    "key": "Aquatic N95",
    "aliases": ["mask", "n95", "aquatic n95"],
    "desc": "A tightly woven cloth mask shimmering with enchantment. Tiny runes along the seams glow faintly blue. When worn, it filters breathable air from water itself.",
    "wearslot": HumanoidWearSlot.FACE,
    "wear_effects": [{"type": "condition", "condition": "water_breathing"}],
    "weight": 0.1,
    "max_durability": 720,
}
