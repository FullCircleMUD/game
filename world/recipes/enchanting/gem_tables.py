"""
Gem enchantment rolling system.

The rolling produces two outputs that map directly onto the standard
item systems already used throughout FCM:

1. **wear_effects** — a list of wear_effect dicts in the *exact* shape
   used by every other item's `wear_effects` field (see e.g.
   veil_of_grace, runeforged_chain, n95_mask, defenders_helm). On
   inset, this list extends the weapon's existing `wear_effects` array;
   the equip pipeline (`_recalculate_stats`, condition ref-counting,
   resistance accumulation) does the rest with no special-casing.

2. **restrictions** — a dict whose keys are `ItemRestrictionMixin`
   field names (`required_classes`, `excluded_classes`, `required_races`,
   `excluded_races`, `min_alignment_score`, `max_alignment_score`).
   Applied directly to the gem's mixin fields; on inset, merged into
   the weapon's same fields. The existing `can_use()` enforcement
   handles everything from there.

Five data tables drive rolling; rebalancing touches data only:

- WEAR_EFFECT_TEMPLATES: catalog of partial wear_effect dicts. Each
  template is a wear_effect missing only its magnitude (filled in per
  gem type at roll time). Conditions take no magnitude and are stored
  whole.
- GEM_POOL_WEIGHTS: which templates each gem type can roll, with weights
  (uniform = 1 for now; edit to rebalance frequency per template).
- GEM_MAGNITUDES: per-gem-type integer magnitude for each magnitude-bearing
  template (per the design spreadsheet — ruby/emerald/diamond columns).
- CASCADE_PROBABILITIES: per-(gem, mastery) chance the Nth wear_effect
  rolls. Index 0 is always 1.0 (primary always rolls).
- RESTRICTION_PROBABILITIES: per-(gem, mastery) chance the Nth restriction
  rolls.

Rolling behavior:
- wear_effects cascade: primary→secondary→tertiary; duplicate template = no-op
- restrictions cascade: up to 3 categories (class/race/alignment), each
  category appears at most once per gem; class/race roll polarity
  (60% MUST_NOT_BE, 40% MUST_BE) and a value; alignment rolls a mode
  from a weighted distribution that maps to min/max alignment_score bounds.

NOTE: A few templates reference targets that don't yet exist in the
engine (e.g. detect_traps condition, regen_multiplier_bonus stat,
crit_chance stat). Those wear_effects silently no-op until the
underlying mechanic is wired — same pattern as the legacy "blessed"/
"alert" entries. Gem catalog design is intentionally decoupled from
effect implementation work.
"""

import random

from typeclasses.actors.char_classes import get_available_char_classes
from typeclasses.actors.races import get_available_races


# ── Wear-effect templates ────────────────────────────────────────────

# Each template is a partial wear_effect dict in the standard format
# used by every other item in the game. Magnitude (where applicable) is
# filled in from GEM_MAGNITUDES at roll time. Conditions take no
# magnitude and are emitted whole.

WEAR_EFFECT_TEMPLATES = {
    # Stat bonuses (S13 attacks_per_round excluded — covered by C07 hasted)
    "S01": {"type": "stat_bonus", "stat": "strength"},
    "S02": {"type": "stat_bonus", "stat": "dexterity"},
    "S03": {"type": "stat_bonus", "stat": "constitution"},
    "S04": {"type": "stat_bonus", "stat": "intelligence"},
    "S05": {"type": "stat_bonus", "stat": "wisdom"},
    "S06": {"type": "stat_bonus", "stat": "charisma"},
    "S07": {"type": "stat_bonus", "stat": "hp_max"},
    "S08": {"type": "stat_bonus", "stat": "mana_max"},
    "S09": {"type": "stat_bonus", "stat": "move_max"},
    "S10": {"type": "stat_bonus", "stat": "armor_class"},
    "S11": {"type": "stat_bonus", "stat": "total_hit_bonus"},
    "S12": {"type": "stat_bonus", "stat": "total_damage_bonus"},
    "S14": {"type": "stat_bonus", "stat": "initiative_bonus"},
    "S15": {"type": "stat_bonus", "stat": "stealth_bonus"},
    "S16": {"type": "stat_bonus", "stat": "perception_bonus"},
    "S17": {"type": "stat_bonus", "stat": "save_bonus"},
    "S18": {"type": "stat_bonus", "stat": "crit_chance"},

    # Damage resistances (all 13 damage types)
    "R01": {"type": "damage_resistance", "damage_type": "slashing"},
    "R02": {"type": "damage_resistance", "damage_type": "piercing"},
    "R03": {"type": "damage_resistance", "damage_type": "bludgeoning"},
    "R04": {"type": "damage_resistance", "damage_type": "fire"},
    "R05": {"type": "damage_resistance", "damage_type": "cold"},
    "R06": {"type": "damage_resistance", "damage_type": "lightning"},
    "R07": {"type": "damage_resistance", "damage_type": "acid"},
    "R08": {"type": "damage_resistance", "damage_type": "poison"},
    "R09": {"type": "damage_resistance", "damage_type": "necrotic"},
    "R10": {"type": "damage_resistance", "damage_type": "radiant"},
    "R11": {"type": "damage_resistance", "damage_type": "magic"},
    "R12": {"type": "damage_resistance", "damage_type": "force"},
    "R13": {"type": "damage_resistance", "damage_type": "psychic"},

    # Conditions (C03 hidden, C09 sanctuary excluded — both break under
    # permanent gem-granted application; alert removed as redundant
    # with initiative_bonus + perception_bonus stats)
    "C01": {"type": "condition", "condition": "detect_invis"},
    "C02": {"type": "condition", "condition": "darkvision"},
    "C04": {"type": "condition", "condition": "invisible"},
    "C05": {"type": "condition", "condition": "fly"},
    "C06": {"type": "condition", "condition": "water_breathing"},
    "C07": {"type": "condition", "condition": "hasted"},
    "C08": {"type": "condition", "condition": "crit_immune"},
    "C10": {"type": "condition", "condition": "comprehend_languages"},
    "C11": {"type": "condition", "condition": "speak_with_animals"},
    "C12": {"type": "condition", "condition": "detect_traps"},
    "C13": {"type": "condition", "condition": "detect_hidden"},

    # Regeneration — piggybacks on existing regen multiplier system
    # by adding to the regen_multiplier_bonus stat
    "G01": {"type": "stat_bonus", "stat": "regen_multiplier_bonus"},
}


# ── Per-gem template inclusion + weight ──────────────────────────────

# Which wear_effect templates each gem can roll. Initialised uniform
# (weight 1 per included template). Edit values here to rebalance.

_RUBY_INCLUDED = [
    # All 17 stat bonuses
    "S01", "S02", "S03", "S04", "S05", "S06",
    "S07", "S08", "S09",
    "S10", "S11", "S12", "S14", "S15", "S16", "S17", "S18",
    # All 13 damage resistances
    "R01", "R02", "R03", "R04", "R05", "R06", "R07",
    "R08", "R09", "R10", "R11", "R12", "R13",
    # 5 conditions per spreadsheet (no fly/water/speak/detect_traps/detect_hidden/hasted/regen)
    "C01", "C02", "C04", "C08", "C10",
]

_EMERALD_ADDS = [
    "C05", "C06", "C11", "C12", "C13", "G01",
]

_DIAMOND_ADDS = [
    "C07",  # hasted unique to diamond
]

_RUBY_POOL = list(_RUBY_INCLUDED)
_EMERALD_POOL = _RUBY_POOL + _EMERALD_ADDS
_DIAMOND_POOL = _EMERALD_POOL + _DIAMOND_ADDS

GEM_POOL_WEIGHTS = {
    "ruby":    {atom_id: 1 for atom_id in _RUBY_POOL},
    "emerald": {atom_id: 1 for atom_id in _EMERALD_POOL},
    "diamond": {atom_id: 1 for atom_id in _DIAMOND_POOL},
}


# ── Per-gem magnitudes ───────────────────────────────────────────────

# Per the design spreadsheet. Damage_resistance values are decimals
# (0.10 = 10%, etc.). Conditions don't use magnitude (binary atoms).

GEM_MAGNITUDES = {
    "ruby": {
        # Ability scores: +1
        "S01": 1, "S02": 1, "S03": 1, "S04": 1, "S05": 1, "S06": 1,
        # Pool maxima: 10
        "S07": 10, "S08": 10, "S09": 10,
        # Combat stats: +1
        "S10": 1, "S11": 1, "S12": 1, "S14": 1, "S15": 1, "S16": 1,
        # save_bonus (revised to ability-score scale): +1
        "S17": 1,
        # crit_chance: -1 (lower threshold = wider crit range)
        "S18": -1,
        # Damage resistances: 10 (= 10%, matches existing prototype convention
        # — see e.g. n95_mask "value": 25 for 25% poison resistance)
        "R01": 10, "R02": 10, "R03": 10, "R04": 10, "R05": 10,
        "R06": 10, "R07": 10, "R08": 10, "R09": 10, "R10": 10,
        "R11": 10, "R12": 10, "R13": 10,
    },
    "emerald": {
        "S01": 2, "S02": 2, "S03": 2, "S04": 2, "S05": 2, "S06": 2,
        "S07": 15, "S08": 15, "S09": 15,
        "S10": 3, "S11": 3, "S12": 3, "S14": 3, "S15": 3, "S16": 3,
        "S17": 2,
        "S18": -2,
        "R01": 20, "R02": 20, "R03": 20, "R04": 20, "R05": 20,
        "R06": 20, "R07": 20, "R08": 20, "R09": 20, "R10": 20,
        "R11": 20, "R12": 20, "R13": 20,
        # Regen: 3x multiplier (added to regen_multiplier_bonus)
        "G01": 3,
    },
    "diamond": {
        "S01": 3, "S02": 3, "S03": 3, "S04": 3, "S05": 3, "S06": 3,
        "S07": 20, "S08": 20, "S09": 20,
        "S10": 5, "S11": 5, "S12": 5, "S14": 5, "S15": 5, "S16": 5,
        "S17": 3,
        "S18": -3,
        "R01": 30, "R02": 30, "R03": 30, "R04": 30, "R05": 30,
        "R06": 30, "R07": 30, "R08": 30, "R09": 30, "R10": 30,
        "R11": 30, "R12": 30, "R13": 30,
        # Regen: 5x multiplier
        "G01": 5,
    },
}


# ── Per-(gem, mastery) probability tables ────────────────────────────

# Cascade for effect rolls. Index 0 is always 1.0 (primary always fires);
# index 1 is the secondary chance, index 2 is the tertiary chance.
CASCADE_PROBABILITIES = {
    ("ruby", 1):    [1.00, 0.10, 0.01],   # BASIC
    ("ruby", 2):    [1.00, 0.25, 0.05],   # SKILLED
    ("ruby", 3):    [1.00, 0.40, 0.10],   # EXPERT
    ("ruby", 4):    [1.00, 0.60, 0.15],   # MASTER
    ("ruby", 5):    [1.00, 0.80, 0.20],   # GRANDMASTER
    ("emerald", 3): [1.00, 0.20, 0.05],
    ("emerald", 4): [1.00, 0.40, 0.10],
    ("emerald", 5): [1.00, 0.60, 0.15],
    ("diamond", 5): [1.00, 0.40, 0.10],
}

# Cascade for restriction rolls. Each index is independent (not
# conditional in the rolling code — but the cascade is interpreted
# as "1st, then 2nd, then 3rd" to read like the spreadsheet).
RESTRICTION_PROBABILITIES = {
    ("ruby", 1):    [0.80, 0.60, 0.40],
    ("ruby", 2):    [0.60, 0.40, 0.20],
    ("ruby", 3):    [0.40, 0.20, 0.00],
    ("ruby", 4):    [0.20, 0.00, 0.00],
    ("ruby", 5):    [0.00, 0.00, 0.00],
    ("emerald", 3): [0.60, 0.40, 0.20],
    ("emerald", 4): [0.40, 0.20, 0.00],
    ("emerald", 5): [0.20, 0.00, 0.00],
    ("diamond", 5): [0.40, 0.20, 0.00],
}


# ── Output table key → gem type ──────────────────────────────────────

# Recipes specify `output_table` as a synthetic key like "enchanted_ruby".
# Map to the pure gem type used by the data tables above.

OUTPUT_TABLE_TO_GEM_TYPE = {
    "enchanted_ruby":    "ruby",
    "enchanted_emerald": "emerald",
    "enchanted_diamond": "diamond",
}


# ── Restriction algorithm constants ──────────────────────────────────

P_MUST_NOT_BE = 0.60
P_MUST_BE = 0.40

ALIGNMENT_MODE_WEIGHTS = {
    "no_evil":      0.30,
    "no_good":      0.30,
    "evil_only":    0.15,
    "good_only":    0.15,
    "neutral_only": 0.10,
}

RESTRICTION_CATEGORIES = ("class", "race", "alignment")


# ── Rolling functions ────────────────────────────────────────────────

def _build_wear_effect(template_id, gem_type):
    """Construct a complete wear_effect dict from a template + gem magnitude.

    Conditions return as-is (no magnitude). Other types get `value`
    filled in from GEM_MAGNITUDES — producing the same wear_effect
    dict shape any other item in the game uses.
    """
    template = WEAR_EFFECT_TEMPLATES[template_id]
    wear_effect = dict(template)

    if wear_effect["type"] == "condition":
        return wear_effect

    magnitudes = GEM_MAGNITUDES.get(gem_type, {})
    if template_id in magnitudes:
        wear_effect["value"] = magnitudes[template_id]

    return wear_effect


def roll_wear_effects(gem_type, mastery_level):
    """Roll a list of wear_effect dicts for a gem of (gem_type, mastery_level).

    Output is a wear_effects list — same shape as the wear_effects field
    on every other item in the game. Caller stores this on the gem's
    wear_effects attribute; on inset, it extends the weapon's.

    Cascade: primary always rolls; secondary/tertiary by chance per
    CASCADE_PROBABILITIES. Duplicate template = no-op (slot still consumed).
    """
    pool = GEM_POOL_WEIGHTS.get(gem_type, {})
    cascade = CASCADE_PROBABILITIES.get((gem_type, mastery_level))
    if not pool:
        raise ValueError(f"No template pool for gem={gem_type}")
    if not cascade:
        raise ValueError(
            f"No cascade for (gem={gem_type}, mastery={mastery_level})"
        )

    template_ids = list(pool.keys())
    weights = list(pool.values())

    chosen_ids = []
    for cascade_p in cascade:
        if random.random() >= cascade_p:
            break
        rolled_id = random.choices(template_ids, weights=weights, k=1)[0]
        if rolled_id in chosen_ids:
            continue
        chosen_ids.append(rolled_id)

    return [_build_wear_effect(tid, gem_type) for tid in chosen_ids]


def _apply_alignment_mode(restrictions, mode):
    """Translate an alignment mode to ItemRestrictionMixin score bounds.

    Boundary semantics: extremes own the boundary values; neutral is
    strictly between. So good_only admits >= 300, evil_only admits
    <= -300, neutral_only admits -300 < score < 300, no_evil admits
    > -300, no_good admits < 300.

    ItemRestrictionMixin's can_use checks `score < min` and `score > max`,
    so the boundary translations are:
        good_only     → min=300              (admit >= 300)
        evil_only     → max=-300             (admit <= -300)
        no_evil       → min=-299             (admit >= -299, i.e. > -300)
        no_good       → max=299              (admit <= 299, i.e. < 300)
        neutral_only  → min=-299, max=299    (admit -300 < score < 300)
    """
    if mode == "good_only":
        restrictions["min_alignment_score"] = 300
    elif mode == "evil_only":
        restrictions["max_alignment_score"] = -300
    elif mode == "no_evil":
        restrictions["min_alignment_score"] = -299
    elif mode == "no_good":
        restrictions["max_alignment_score"] = 299
    elif mode == "neutral_only":
        restrictions["min_alignment_score"] = -299
        restrictions["max_alignment_score"] = 299


def roll_restrictions(gem_type, mastery_level):
    """Roll restrictions for a gem of (gem_type, mastery_level).

    Returns a dict in `ItemRestrictionMixin` field format — only fields
    set by this roll are present (default-valued fields omitted). Empty
    dict = unrestricted.

    Procedural cascade up to 3 categories drawn without replacement from
    {class, race, alignment}. Class/race roll polarity (60% MUST_NOT_BE,
    40% MUST_BE) and a value. Alignment rolls a weighted mode that maps
    to min/max alignment_score bounds.

    Output fields (any subset):
        required_classes, excluded_classes,
        required_races,   excluded_races,
        min_alignment_score, max_alignment_score
    """
    cascade = RESTRICTION_PROBABILITIES.get((gem_type, mastery_level))
    if not cascade:
        return {}

    restrictions = {}
    remaining = list(RESTRICTION_CATEGORIES)

    for cascade_p in cascade:
        if not remaining:
            break
        if random.random() >= cascade_p:
            break

        category = random.choice(remaining)
        remaining.remove(category)

        if category == "alignment":
            modes = list(ALIGNMENT_MODE_WEIGHTS.keys())
            weights = list(ALIGNMENT_MODE_WEIGHTS.values())
            mode = random.choices(modes, weights=weights, k=1)[0]
            _apply_alignment_mode(restrictions, mode)
        else:
            polarity = (
                "must_not_be"
                if random.random() < P_MUST_NOT_BE
                else "must_be"
            )
            if category == "class":
                pool = list(get_available_char_classes(0).keys())
                field_prefix = "classes"
            else:
                pool = list(get_available_races(0).keys())
                field_prefix = "races"
            if not pool:
                continue
            value = random.choice(pool)
            field = (
                f"excluded_{field_prefix}"
                if polarity == "must_not_be"
                else f"required_{field_prefix}"
            )
            restrictions.setdefault(field, []).append(value)

    return restrictions


def roll_gem_enchantment(table_key, mastery_level):
    """Roll a complete gem enchantment outcome.

    Args:
        table_key: e.g. "enchanted_ruby" — synthetic recipe identifier.
        mastery_level: integer 1-5.

    Returns:
        (wear_effects, restrictions) tuple where:
        - wear_effects: list of wear_effect dicts in the standard shape
          used by every other item in the game (ready to extend
          weapon.wear_effects on inset)
        - restrictions: dict whose keys are ItemRestrictionMixin field
          names (ready to apply directly to the gem's mixin fields)
    """
    gem_type = OUTPUT_TABLE_TO_GEM_TYPE.get(table_key)
    if not gem_type:
        raise ValueError(f"Unknown gem enchant table: {table_key}")

    wear_effects = roll_wear_effects(gem_type, mastery_level)
    restrictions = roll_restrictions(gem_type, mastery_level)

    return wear_effects, restrictions
