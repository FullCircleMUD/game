from enums.unused_for_reference.damage_type import DamageType

WOODEN_GREATCLUB = {
    "prototype_key": "wooden_greatclub",
    "typeclass": "typeclasses.items.weapons.greatclub_nft_item.GreatclubNFTItem",
    "mob_typeclass": "typeclasses.items.mob_items.mob_weapons.MobGreatclub",
    "key": "Wooden Greatclub",
    "aliases": ["greatclub", "wooden greatclub", "great club"],
    "desc": (
        "A massive length of timber as thick as a man's thigh, carved with "
        "a rough grip at one end and left raw everywhere else. Swung with "
        "enough weight behind it to rattle a target's skull even through a "
        "helmet."
    ),
    "base_damage": "d10",
    "material": "wood",
    "damage_type": DamageType.BLUDGEONING,
    "weapon_type": "melee",
    "two_handed": True,
    "speed": 0,
    "weight": 5.0,
    "max_durability": 2880,
    "wear_effects": [],
}
