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
    WeaponType.NANCHAKU:     {"ninja"},
    WeaponType.SLING:        {"warrior", "thief", "cleric", "mage","ranger", "druid", "bard", "paladin", "ninja"},

    # SPECIAL
    WeaponType.BLOWGUN:      {"thief", "ninja", "ranger", "druid"},
    WeaponType.BOLA:         {"warrior", "thief", "ranger", "barbarian"},
    WeaponType.SHURIKEN:     {"ninja"},
    WeaponType.SAI:          {"ninja"},
}

_WEAPON_DESCRIPTIONS = {
    # ── Slashing ──
    WeaponType.GREAT_SWORD: (
        "A heavy two-handed blade (2d6). Highest melee damage dice. Cleave "
        "at SKILLED+ — successful hits cascade to nearby enemies (up to 3 "
        "targets at MASTER). Executioner at GM grants a free attack on kills."
    ),
    WeaponType.LONG_SWORD: (
        "A versatile one-handed blade (d8). Balanced offense and defense — "
        "parries at SKILLED+ (up to 3 at GM with parry advantage), plus "
        "extra attacks at MASTER+. A solid all-rounder."
    ),
    WeaponType.SHORT_SWORD: (
        "A light one-handed blade (d6). Finesse (uses DEX for hit). "
        "Dual-wieldable with off-hand attacks at EXPERT+. Parries at "
        "SKILLED+ (up to 2 at GM). Best in a pair for fast dual-wield builds."
    ),
    WeaponType.BATTLEAXE: (
        "A large two-handed axe (d10). Cleave at SKILLED+ (weaker than "
        "greatsword) plus Sunder — chance to reduce the target's AC on hit "
        "(stacking, up to -2 per hit at MASTER+). Anti-armor specialist."
    ),
    WeaponType.HANDAXE: (
        "A light one-handed axe (d6). Sunder at SKILLED+ — chance to reduce "
        "target AC by 1 on hit. Extra attacks at MASTER+. Lighter sunder "
        "than battleaxe but faster."
    ),
    WeaponType.NINJATO: (
        "A straight-bladed ninja sword (d8). Two-handed, finesse. Combines "
        "speed with defense — extra attacks at EXPERT+, parries at SKILLED+ "
        "(up to 2 at GM). Riposte and parry advantage at GM. Ninja only."
    ),
    # ── Piercing ──
    WeaponType.SPEAR: (
        "A long-hafted thrusting weapon (d8). Two-handed. Reach Counter at "
        "EXPERT+ — free counter-attacks when nearby allies are hit (up to 2 "
        "at GM). Also gains crit threshold reduction with mastery. Best for "
        "party support."
    ),
    WeaponType.BOW: (
        "A ranged weapon (d8). Two-handed. Slowing Shot at SKILLED+ — "
        "contested DEX vs STR roll to slow the target (caps their attacks "
        "at 1/round). Extra attacks at MASTER+. Primary ranged DPS weapon."
    ),
    WeaponType.CROSSBOW: (
        "A mechanical ranged weapon (d12). Two-handed. Highest ranged damage "
        "per shot but no extra attacks. Knockback at SKILLED+ — chance to "
        "knock the target prone (HUGE+ immune). Slow but devastating."
    ),
    WeaponType.RAPIER: (
        "A thin thrusting blade (d8). One-handed, finesse (uses DEX for "
        "hit). Riposte at EXPERT+ — counter-attack after a successful "
        "parry. Parry advantage at GM. The duelist's weapon."
    ),
    WeaponType.DAGGER: (
        "A small blade for quick stabs (d4). One-handed, finesse, "
        "dual-wieldable. Fastest weapon — extra attacks from SKILLED+, "
        "off-hand attacks at MASTER+. Crit threshold reduction at EXPERT+. "
        "Low damage per hit, high volume. Required for stab."
    ),
    WeaponType.LANCE: (
        "A mounted combat weapon (2d7). Two-handed. Devastating on "
        "horseback — prone chance, crit bonus, and extra attacks at "
        "MASTER+. Severe penalties when unmounted (disadvantage, 1 "
        "attack/round, no specials). A cavalry weapon only."
    ),
    # ── Bludgeoning ──
    WeaponType.STAFF: (
        "A two-handed wooden pole (d8). The best defensive weapon — highest "
        "parry count (up to 4 at GM) and the only weapon that parries ALL "
        "attack types (melee, unarmed, animal, missile). Parry advantage at "
        "EXPERT+, riposte at MASTER+."
    ),
    WeaponType.MACE: (
        "A heavy blunt weapon (d6). One-handed. Anti-armor Crush — bonus "
        "damage vs armored targets that scales with mastery (up to +8 vs "
        "heavy armor at GM). Extra attacks at MASTER+. Rewards targeting "
        "plate-wearers."
    ),
    WeaponType.CLUB: (
        "A simple one-handed bludgeon (d6). Stagger at SKILLED+ — chance "
        "to impose a -2 hit penalty on the target for 1 round. Extra "
        "attacks at MASTER+. Widely available to most classes."
    ),
    WeaponType.GREATCLUB: (
        "A massive two-handed club (d10). Heavy Stagger at SKILLED+ — "
        "stronger than club (up to -4 hit penalty for 2 rounds at MASTER+), "
        "higher proc chance (up to 30% at GM). Pure stagger specialist."
    ),
    WeaponType.HAMMER: (
        "A crushing one-handed weapon (d8). Devastating Blow — massively "
        "increased crit damage multiplier (up to 4x total at GM vs the "
        "normal 2x). Stack with crit threshold gear for spike damage builds."
    ),
    WeaponType.UNARMED: (
        "Fighting with fists and feet. Always available. Damage scales with "
        "mastery (d1 to d8). Stun at SKILLED+ via contested STR vs CON — "
        "PRONE on big wins at MASTER+. Extra attacks at EXPERT+. Trains "
        "well as a backup for any class."
    ),
    WeaponType.NANCHAKU: (
        "Linked sticks swung at high speed (d6). Two-handed. Stun on hit "
        "at SKILLED+ via contested DEX vs CON — PRONE on big wins at "
        "MASTER+ (GARGANTUAN only immune). Extra attacks from SKILLED+ "
        "(up to 2 at GM). Ninja only."
    ),
    WeaponType.SLING: (
        "A simple ranged weapon hurling stones (d6). One-handed. Available "
        "to all classes. Concussive Daze at SKILLED+ — chance to stun the "
        "target (HUGE+ immune). Extra attacks from EXPERT+. The most "
        "accessible ranged option."
    ),
    # ── Special ──
    WeaponType.BLOWGUN: (
        "A tube firing poisoned darts (d1). One-handed, finesse, ranged. "
        "Nearly no direct damage — instead applies stacking poison DoT "
        "(up to d6/round at GM) and paralysis via CON save (up to 3 rounds "
        "at GM, HUGE+ immune). A control weapon, not a damage weapon."
    ),
    WeaponType.BOLA: (
        "Weighted cords thrown to entangle (d1). One-handed, finesse, "
        "ranged. Minimal damage — the purpose is Entangle via contested "
        "DEX roll (up to 6 rounds at GM, HUGE+ immune). Target must break "
        "free with STR saves each round. Pure crowd control."
    ),
    WeaponType.SHURIKEN: (
        "Small thrown stars (d4). One-handed, finesse, ranged. Multi-throw "
        "scales dramatically — up to 4 throws per round at GM. Crit "
        "threshold reduction at SKILLED+. Consumable: each throw transfers "
        "the shuriken to the target or floor. Ninja only."
    ),
    WeaponType.SAI: (
        "A pronged defensive weapon (d6). One-handed, dual-wieldable. "
        "Highest one-handed parry count (up to 5 at GM). Disarm-on-parry "
        "at SKILLED+ — contested DEX vs STR to knock the attacker's weapon "
        "from their grip. No extra attacks. Ninja only."
    ),
}
