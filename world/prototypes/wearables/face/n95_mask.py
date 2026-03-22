from enums.wearslot import HumanoidWearSlot

N95_MASK = {
    "prototype_key": "n95_mask",
    "typeclass": "typeclasses.items.wearables.wearable_nft_item.WearableNFTItem",
    "key": "N95 Mask",
    "aliases": ["mask", "n95"],
    "desc": "A tightly woven cloth mask that fits snugly over the nose and mouth. The weave is remarkably fine, filtering all but the smallest particles.",
    "wearslot": HumanoidWearSlot.FACE,
    "wear_effects": [{"type": "damage_resistance", "damage_type": "poison", "value": 25}],
    "weight": 0.1,
    "max_durability": 720,
}
