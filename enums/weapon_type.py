from enum import Enum


class WeaponType(Enum):
    """Types of weapons - simple string values with methods to get complex data"""
    # SLASHING
    GREAT_SWORD = "great_sword"
    LONG_SWORD = "long_sword"
    SHORT_SWORD = "short_sword"
    BATTLEAXE = "battleaxe"
    HANDAXE = "handaxe"
    NINJATO = "ninjato"

    # PIERCING
    SPEAR = "spear"
    BOW = "bow"
    CROSSBOW = "crossbow"
    RAPIER = "rapier"
    DAGGER = "dagger"
    LANCE = "lance" # bonuses when mounted

    # BLUDGEONING
    STAFF = "staff"
    MACE = "mace"
    CLUB = "club"
    GREATCLUB = "greatclub"
    HAMMER = "hammer"
    UNARMED = "unarmed"
    NANCHAKU = "nanchaku"
    SLING = "sling"

    # SPECIAL
    BLOWGUN = "blowgun"
    BOLA = "bola"
    SHURIKEN = "shuriken"
    SAI = "sai"

    @property
    def classes(self):
        """Class keys that can train mastery in this weapon."""
        return _WEAPON_CLASSES[self]

    @property
    def description(self) -> str:
        """Get a short description of this weapon type."""
        return _WEAPON_DESCRIPTIONS.get(self, "No description available.")

    def can_be_used_by(self, class_key):
        """Check if a class can train this weapon type."""
        return class_key in self.classes


# Which classes can train mastery in each weapon.
# This gates chargen choices and future training — NOT equipping.
# Any class can still pick up and use any weapon at UNSKILLED (-2 penalty).
_WEAPON_CLASSES = {
    # SLASHING
    WeaponType.GREAT_SWORD:  {"warrior", "paladin", "barbarian"},
    WeaponType.LONG_SWORD:   {"warrior", "paladin", "ranger"},
    WeaponType.SHORT_SWORD:  {"warrior", "thief", "paladin", "ranger", "bard", "ninja"},
    WeaponType.BATTLEAXE:    {"warrior", "paladin", "barbarian"},
    WeaponType.HANDAXE:      {"warrior", "thief", "barbarian", "ranger"},
    WeaponType.NINJATO:      {"ninja"},

    # PIERCING
    WeaponType.SPEAR:        {"warrior", "paladin", "barbarian", "ranger", "druid"},
    WeaponType.BOW:          {"warrior", "ranger", "thief"},
    WeaponType.CROSSBOW:     {"warrior", "thief", "ranger"},
    WeaponType.RAPIER:       {"warrior", "thief", "bard"},
    WeaponType.DAGGER:       {"warrior", "thief", "mage", "bard", "ninja", "ranger", "druid"},
    WeaponType.LANCE:        {"warrior", "paladin"},

    # BLUDGEONING
    WeaponType.STAFF:        {"warrior", "cleric", "mage", "druid"},
    WeaponType.MACE:         {"warrior", "cleric", "paladin"},
    WeaponType.CLUB:         {"warrior", "thief", "cleric", "barbarian", "ranger", "druid", "bard"},
    WeaponType.GREATCLUB:    {"warrior", "cleric", "barbarian", "druid"},
    WeaponType.HAMMER:       {"warrior", "cleric", "paladin", "barbarian"},
    WeaponType.UNARMED:      {"warrior", "thief", "cleric", "mage", "paladin", "barbarian",
                              "ranger", "druid", "ninja", "bard"},  # all classes
    WeaponType.NANCHAKU:     {"warrior", "ninja", "barbarian"},
    WeaponType.SLING:        {"warrior", "thief", "cleric", "mage","ranger", "druid", "bard", "paladin", "ninja"},

    # SPECIAL
    WeaponType.BLOWGUN:      {"thief", "ninja", "ranger", "druid"},
    WeaponType.BOLA:         {"warrior", "thief", "ranger", "barbarian"},
    WeaponType.SHURIKEN:     {"ninja"},
    WeaponType.SAI:          {"ninja"},
}

_WEAPON_DESCRIPTIONS = {
    # Slashing
    WeaponType.GREAT_SWORD: "A heavy two-handed blade. High damage, slow speed.",
    WeaponType.LONG_SWORD: "A versatile one-handed blade. Balanced damage and speed.",
    WeaponType.SHORT_SWORD: "A light one-handed blade. Fast strikes, moderate damage.",
    WeaponType.BATTLEAXE: "A large two-handed axe. Heavy hits, slow recovery.",
    WeaponType.HANDAXE: "A light one-handed axe. Can be thrown.",
    WeaponType.NINJATO: "A straight-bladed ninja sword. Combines speed, precision, and dual-wield capability.",
    # Piercing
    WeaponType.SPEAR: "A long-hafted thrusting weapon. Good reach, moderate speed.",
    WeaponType.BOW: "A ranged weapon firing arrows. Requires ammunition.",
    WeaponType.CROSSBOW: "A mechanical ranged weapon. High damage, slow reload.",
    WeaponType.RAPIER: "A thin thrusting blade. Fast, precise attacks. Favours dexterity.",
    WeaponType.DAGGER: "A small blade for quick stabs. Very fast, low damage.",
    WeaponType.LANCE: "A mounted combat weapon. Devastating on a charge.",
    # Bludgeoning
    WeaponType.STAFF: "A two-handed wooden pole. Decent reach, can be used for defence.",
    WeaponType.MACE: "A heavy blunt weapon. Effective against armored foes.",
    WeaponType.CLUB: "A simple one-handed bludgeon. Fast, crude, effective.",
    WeaponType.GREATCLUB: "A massive two-handed club. Slow but staggering.",
    WeaponType.HAMMER: "A crushing blunt weapon. High damage, slow speed.",
    WeaponType.UNARMED: "Fighting with fists and feet. Always available, improved by training.",
    WeaponType.NANCHAKU: "Linked sticks swung at high speed. Fast, requires skill.",
    WeaponType.SLING: "A simple ranged weapon hurling stones. Light, accurate, easy to learn.",
    # Special
    WeaponType.BLOWGUN: "A tube firing poisoned darts. Silent ranged weapon.",
    WeaponType.BOLA: "Weighted cords thrown to entangle. Can immobilise targets.",
    WeaponType.SHURIKEN: "Small thrown stars. Quick, low damage, can hit multiple times.",
    WeaponType.SAI: "A pronged defensive weapon. Good for disarming and parrying.",
}
