"""
Damage descriptor tables — percentage-based combat message flavour.

Maps (DamageType, damage_as_%_of_target_hp) to descriptive verbs.
Capitalisation conveys severity: lowercase for grazes, ALL CAPS for
devastating blows. No damage numbers are shown to players.

Usage:
    from rules.damage_descriptors import get_descriptor, get_miss_verb

    second, third = get_descriptor(DamageType.SLASHING, damage, target.effective_hp_max)
    # ("nick", "nicks")  or  ("DECAPITATE", "DECAPITATES")

    second, third = get_miss_verb(DamageType.SLASHING)
    # ("swing", "swings")

Tuples: (min_pct, max_pct, second_person_verb, third_person_verb)
"""

from enums.damage_type import DamageType

# ================================================================== #
#  Descriptor Tables — keyed by DamageType
# ================================================================== #

DAMAGE_DESCRIPTORS = {

    DamageType.SLASHING: [
        (0,   4,  "nick",       "nicks"),
        (5,  10,  "cut",        "cuts"),
        (11, 20,  "slash",      "slashes"),
        (21, 35,  "cleave",     "cleaves"),
        (36, 50,  "Rend",       "Rends"),
        (51, 65,  "LACERATE",   "LACERATES"),
        (66, 80,  "EVISCERATE", "EVISCERATES"),
        (81, 95,  "FLAY",       "FLAYS"),
        (96, 999, "DECAPITATE", "DECAPITATES"),
    ],

    DamageType.PIERCING: [
        (0,   4,  "prick",      "pricks"),
        (5,  10,  "stab",       "stabs"),
        (11, 20,  "pierce",     "pierces"),
        (21, 35,  "gouge",      "gouges"),
        (36, 50,  "Impale",     "Impales"),
        (51, 65,  "SKEWER",     "SKEWERS"),
        (66, 80,  "BORE",       "BORES"),
        (81, 95,  "TRANSFIX",   "TRANSFIXES"),
        (96, 999, "ANNIHILATE", "ANNIHILATES"),
    ],

    DamageType.BLUDGEONING: [
        (0,   4,  "tap",        "taps"),
        (5,  10,  "bruise",     "bruises"),
        (11, 20,  "bash",       "bashes"),
        (21, 35,  "crush",      "crushes"),
        (36, 50,  "Shatter",    "Shatters"),
        (51, 65,  "SMASH",      "SMASHES"),
        (66, 80,  "OBLITERATE", "OBLITERATES"),
        (81, 95,  "DEMOLISH",   "DEMOLISHES"),
        (96, 999, "PULVERIZE",  "PULVERIZES"),
    ],

    DamageType.FIRE: [
        (0,   4,  "singe",      "singes"),
        (5,  10,  "scorch",     "scorches"),
        (11, 20,  "burn",       "burns"),
        (21, 35,  "sear",       "sears"),
        (36, 50,  "Blaze",      "Blazes"),
        (51, 65,  "CHAR",       "CHARS"),
        (66, 80,  "INCINERATE", "INCINERATES"),
        (81, 95,  "CREMATE",    "CREMATES"),
        (96, 999, "IMMOLATE",   "IMMOLATES"),
    ],

    DamageType.COLD: [
        (0,   4,  "chill",      "chills"),
        (5,  10,  "frost",      "frosts"),
        (11, 20,  "freeze",     "freezes"),
        (21, 35,  "numb",       "numbs"),
        (36, 50,  "Glaciate",   "Glaciates"),
        (51, 65,  "SHATTER",    "SHATTERS"),
        (66, 80,  "FLASH-FREEZE", "FLASH-FREEZES"),
        (81, 95,  "ENCASE",     "ENCASES"),
        (96, 999, "PETRIFY",    "PETRIFIES"),
    ],

    DamageType.LIGHTNING: [
        (0,   4,  "spark",      "sparks"),
        (5,  10,  "zap",        "zaps"),
        (11, 20,  "shock",      "shocks"),
        (21, 35,  "jolt",       "jolts"),
        (36, 50,  "Electrify",  "Electrifies"),
        (51, 65,  "SURGE",      "SURGES"),
        (66, 80,  "BLAST",      "BLASTS"),
        (81, 95,  "FULMINATE",  "FULMINATES"),
        (96, 999, "ELECTROCUTE", "ELECTROCUTES"),
    ],

    DamageType.ACID: [
        (0,   4,  "splash",     "splashes"),
        (5,  10,  "sting",      "stings"),
        (11, 20,  "corrode",    "corrodes"),
        (21, 35,  "dissolve",   "dissolves"),
        (36, 50,  "Melt",       "Melts"),
        (51, 65,  "DEVOUR",     "DEVOURS"),
        (66, 80,  "LIQUEFY",    "LIQUEFIES"),
        (81, 95,  "CONSUME",    "CONSUMES"),
        (96, 999, "DISINTEGRATE", "DISINTEGRATES"),
    ],

    DamageType.POISON: [
        (0,   4,  "irritate",   "irritates"),
        (5,  10,  "sting",      "stings"),
        (11, 20,  "poison",     "poisons"),
        (21, 35,  "envenom",    "envenoms"),
        (36, 50,  "Toxify",     "Toxifies"),
        (51, 65,  "CORRUPT",    "CORRUPTS"),
        (66, 80,  "BLIGHT",     "BLIGHTS"),
        (81, 95,  "PUTREFY",    "PUTREFIES"),
        (96, 999, "ANNIHILATE", "ANNIHILATES"),
    ],

    DamageType.NECROTIC: [
        (0,   4,  "wither",     "withers"),
        (5,  10,  "drain",      "drains"),
        (11, 20,  "decay",      "decays"),
        (21, 35,  "blight",     "blights"),
        (36, 50,  "Wilt",       "Wilts"),
        (51, 65,  "ROT",        "ROTS"),
        (66, 80,  "DESICCATE",  "DESICCATES"),
        (81, 95,  "CONSUME",    "CONSUMES"),
        (96, 999, "ANNIHILATE", "ANNIHILATES"),
    ],

    DamageType.RADIANT: [
        (0,   4,  "glow",       "glows"),
        (5,  10,  "burn",       "burns"),
        (11, 20,  "scorch",     "scorches"),
        (21, 35,  "smite",      "smites"),
        (36, 50,  "Blaze",      "Blazes"),
        (51, 65,  "SEAR",       "SEARS"),
        (66, 80,  "PURGE",      "PURGES"),
        (81, 95,  "CONSECRATE", "CONSECRATES"),
        (96, 999, "OBLITERATE", "OBLITERATES"),
    ],

    DamageType.MAGIC: [
        (0,   4,  "spark",      "sparks"),
        (5,  10,  "sting",      "stings"),
        (11, 20,  "blast",      "blasts"),
        (21, 35,  "smite",      "smites"),
        (36, 50,  "Surge",      "Surges"),
        (51, 65,  "RAVAGE",     "RAVAGES"),
        (66, 80,  "DEVASTATE",  "DEVASTATES"),
        (81, 95,  "UNMAKE",     "UNMAKES"),
        (96, 999, "ANNIHILATE", "ANNIHILATES"),
    ],

    DamageType.FORCE: [
        (0,   4,  "nudge",      "nudges"),
        (5,  10,  "slam",       "slams"),
        (11, 20,  "batter",     "batters"),
        (21, 35,  "pummel",     "pummels"),
        (36, 50,  "Crush",      "Crushes"),
        (51, 65,  "SHATTER",    "SHATTERS"),
        (66, 80,  "OBLITERATE", "OBLITERATES"),
        (81, 95,  "DEMOLISH",   "DEMOLISHES"),
        (96, 999, "ANNIHILATE", "ANNIHILATES"),
    ],

    DamageType.PSYCHIC: [
        (0,   4,  "distract",   "distracts"),
        (5,  10,  "daze",       "dazes"),
        (11, 20,  "rattle",     "rattles"),
        (21, 35,  "stagger",    "staggers"),
        (36, 50,  "Overwhelm",  "Overwhelms"),
        (51, 65,  "SHATTER",    "SHATTERS"),
        (66, 80,  "RUPTURE",    "RUPTURES"),
        (81, 95,  "UNRAVEL",    "UNRAVELS"),
        (96, 999, "ANNIHILATE", "ANNIHILATES"),
    ],
}

# Fallback for any DamageType not in the table above.
_GENERIC_DESCRIPTORS = [
    (0,   4,  "graze",      "grazes"),
    (5,  10,  "hit",        "hits"),
    (11, 20,  "wound",      "wounds"),
    (21, 35,  "maul",       "mauls"),
    (36, 50,  "Ravage",     "Ravages"),
    (51, 65,  "DEVASTATE",  "DEVASTATES"),
    (66, 80,  "DESTROY",    "DESTROYS"),
    (81, 95,  "OBLITERATE", "OBLITERATES"),
    (96, 999, "ANNIHILATE", "ANNIHILATES"),
]


# ================================================================== #
#  Miss Verbs — keyed by DamageType
# ================================================================== #

MISS_VERBS = {
    DamageType.SLASHING:    ("swing",  "swings"),
    DamageType.PIERCING:    ("thrust", "thrusts"),
    DamageType.BLUDGEONING: ("swing",  "swings"),
    DamageType.FIRE:        ("hurl fire at",   "hurls fire at"),
    DamageType.COLD:        ("hurl frost at",  "hurls frost at"),
    DamageType.LIGHTNING:   ("hurl lightning at", "hurls lightning at"),
    DamageType.ACID:        ("hurl acid at",   "hurls acid at"),
    DamageType.POISON:      ("strike at",      "strikes at"),
    DamageType.NECROTIC:    ("reach for",      "reaches for"),
    DamageType.RADIANT:     ("strike at",      "strikes at"),
    DamageType.MAGIC:       ("hurl magic at",  "hurls magic at"),
    DamageType.FORCE:       ("swing",          "swings"),
    DamageType.PSYCHIC:     ("focus on",       "focuses on"),
}

_GENERIC_MISS_VERB = ("swing", "swings")


# ================================================================== #
#  Public API
# ================================================================== #

def get_descriptor(damage_type, damage_dealt, target_hp_max):
    """Return (second_person_verb, third_person_verb) for the damage tier.

    Args:
        damage_type: DamageType enum member
        damage_dealt: int, final damage after resistances
        target_hp_max: int, target's effective_hp_max

    Returns:
        (str, str) — e.g. ("nick", "nicks") or ("DECAPITATE", "DECAPITATES")
    """
    pct = (damage_dealt * 100) // max(1, target_hp_max)
    table = DAMAGE_DESCRIPTORS.get(damage_type, _GENERIC_DESCRIPTORS)
    for min_pct, max_pct, second, third in table:
        if min_pct <= pct <= max_pct:
            return (second, third)
    # Overflow — damage exceeds table range, use highest tier
    return (table[-1][2], table[-1][3])


def get_miss_verb(damage_type):
    """Return (second_person_verb, third_person_verb) for a miss.

    Args:
        damage_type: DamageType enum member

    Returns:
        (str, str) — e.g. ("swing", "swings")
    """
    return MISS_VERBS.get(damage_type, _GENERIC_MISS_VERB)
