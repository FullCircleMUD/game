from enums.wearslot import HumanoidWearSlot

PUGILISTS_GLOVES = {
    "prototype_key": "pugilists_gloves",
    "typeclass": "typeclasses.items.wearables.wearable_nft_item.WearableNFTItem",
    "mob_typeclass": "typeclasses.items.mob_items.mob_wearable.MobWearable",
    "key": "Pugilist's Gloves",
    "aliases": ["gloves", "pugilists gloves"],
    "desc": "Leather gloves hardened with arcane energy. They hum faintly when a fist is clenched.",
    "wearslot": HumanoidWearSlot.HANDS,
    "wear_effects": [
        {"type": "hit_bonus", "weapon_type": "unarmed", "value": 1},
        {"type": "damage_bonus", "weapon_type": "unarmed", "value": 1},
    ],
    "weight": 0.5,
    "max_durability": 1440,
}
