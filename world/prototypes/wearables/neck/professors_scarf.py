from enums.wearslot import HumanoidWearSlot

PROFESSORS_SCARF = {
    "prototype_key": "professors_scarf",
    "typeclass": "typeclasses.items.wearables.wearable_nft_item.WearableNFTItem",
    "key": "Professor's Scarf",
    "aliases": ["scarf", "professors scarf"],
    "desc": "A finely woven scarf embroidered with arcane sigils. It hums faintly with intellectual energy.",
    "wearslot": HumanoidWearSlot.NECK,
    "wear_effects": [{"type": "stat_bonus", "stat": "intelligence", "value": 1}],
    "required_classes": ["mage"],
    "weight": 0.2,
    "max_durability": 720,
}
