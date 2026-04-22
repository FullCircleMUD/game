"""
Character creation EvMenu wizard.

Nodes:
    node_race_select     → pick a race
    node_class_select    → pick a class (filtered by race)
    node_point_buy       → allocate ability scores via point buy
    node_weapon_skills   → choose starting weapon proficiencies
    node_class_skills    → choose starting class skills
    node_general_skills      → choose starting general skills
    node_starting_knowledge  → choose starting recipes and spells
    node_languages           → choose bonus languages (INT-based)
    node_name                → choose character name
    node_confirm         → review and confirm
    node_create          → create the character and exit

State is accumulated in caller.ndb._chargen throughout the flow.
"""

import math

from evennia.objects.models import ObjectDB

from enums.abilities_enum import Ability
from enums.languages import Languages
from enums.mastery_level import MasteryLevel
from enums.skills_enum import skills
from enums.weapon_type import WeaponType
from typeclasses.actors.races import get_race, get_available_races
from typeclasses.actors.char_classes import get_char_class, get_available_char_classes
from world.recipes import get_recipe, get_recipes_for_skill
from world.spells.registry import get_spell, get_spells_for_school


# -----------------------------------------------------------------------
#  Point buy cost table
# -----------------------------------------------------------------------

POINT_COSTS = {
    5: -3, 6: -2, 7: -1,
    8: 0, 9: 1, 10: 2, 11: 3, 12: 4, 13: 5, 14: 7, 15: 9,
    16: 12, 17: 15, 18: 19, 19: 23, 20: 28,
}

MIN_SCORE = 5
MAX_SCORE = 20

# Ordered list of all six abilities for display
ABILITIES = [Ability.STR, Ability.DEX, Ability.CON,
             Ability.INT, Ability.WIS, Ability.CHA]

# Short labels for display
ABILITY_SHORT = {
    Ability.STR: "STR", Ability.DEX: "DEX", Ability.CON: "CON",
    Ability.INT: "INT", Ability.WIS: "WIS", Ability.CHA: "CHA",
}


def _get_chargen(caller):
    """Get the chargen state dict, creating defaults if needed."""
    if not caller.ndb._chargen:
        caller.ndb._chargen = {}
    return caller.ndb._chargen


def _calculate_points_spent(scores):
    """Calculate total points spent for a scores dict."""
    return sum(POINT_COSTS[score] for score in scores.values())


def _get_racial_bonuses(race_key):
    """Get ability bonuses dict for a race key."""
    race = get_race(race_key)
    if race:
        return race.ability_score_bonuses
    return {}


def _get_skill_budget(state, budget_key):
    """Get chargen skill budget including flat remort bonuses."""
    charclass = get_char_class(state.get("class_key", ""))
    budget = charclass.level_progression[1][budget_key] if charclass else 0
    char = state.get("character")
    if char:
        bonus_attr = {
            "weapon_skill_pts": "bonus_weapon_skill_pts",
            "class_skill_pts": "bonus_class_skill_pts",
            "general_skill_pts": "bonus_general_skill_pts",
        }.get(budget_key)
        if bonus_attr:
            budget += getattr(char, bonus_attr, 0)
    return budget


# =======================================================================
#  NODE: Race Selection
# =======================================================================

def _build_race_detail(race):
    """Build full detail text for a race."""
    lines = []
    lines.append(f"|w{race.display_name}|n")
    lines.append(race.description)
    lines.append(
        f"  HP: {race.base_hp}  Mana: {race.base_mana}  Move: {race.base_move}"
    )
    if race.ability_score_bonuses:
        bonuses = ", ".join(
            f"{ABILITY_SHORT[ab]:>3} {bonus:+d}"
            for ab, bonus in race.ability_score_bonuses.items()
        )
        lines.append(f"  Ability bonuses: {bonuses}")
    if race.racial_languages:
        lines.append(
            f"  Languages: Common, {', '.join(lang.capitalize() for lang in race.racial_languages)}"
        )
    else:
        lines.append("  Languages: Common")
    if race.racial_weapon_proficiencies:
        lines.append(
            f"  Weapon proficiencies: {', '.join(w.value.replace('_', ' ').title() for w in race.racial_weapon_proficiencies)}"
        )
    return "\n".join(lines)


def node_race_select(caller, raw_input, **kwargs):
    state = _get_chargen(caller)
    num_remorts = state.get("num_remorts", 0)
    races = get_available_races(num_remorts)

    # Cache race keys for info/selection lookup
    state["_race_keys"] = list(races.keys())

    text = "|gCharacter Creation - Step 1: Choose Your Race|n\n"
    text += "-" * 50 + "\n\n"

    # Show detail for a specific race if requested
    detail_info = kwargs.get("detail", "")
    if detail_info:
        text += detail_info + "\n\n"

    text += "Type |winfo <#>|n for full details, or pick a number to choose.\n"

    options = []
    for i, (key, race) in enumerate(races.items(), 1):
        teaser = race.description[:60]
        if len(race.description) > 60:
            teaser += "..."
        tag = " |c[Remort]|n" if race.min_remort > 0 else ""
        options.append({
            "key": str(i),
            "desc": f"|w{race.display_name:<10}|n{tag} {teaser}",
            "goto": (_set_race, {"race_key": key}),
        })

    # Default handler for "info <n>" commands
    options.append({
        "key": "_default",
        "goto": (_handle_race_info, {}),
    })

    return text, tuple(options)


def _handle_race_info(caller, raw_input, **kwargs):
    """Handle 'info <n>' input on the race selection node."""
    state = _get_chargen(caller)
    text = raw_input.strip().lower()

    if not text.startswith("info"):
        return "node_race_select", {"detail": f"|rUnknown command: {raw_input.strip()}. Type a number to choose or 'info <#>' for details.|n"}

    arg = text[4:].strip()
    race_keys = state.get("_race_keys", [])

    # Try numeric index
    try:
        idx = int(arg) - 1
        if 0 <= idx < len(race_keys):
            race = get_race(race_keys[idx])
            return "node_race_select", {"detail": _build_race_detail(race)}
    except (ValueError, IndexError):
        pass

    # Try race name
    for key in race_keys:
        race = get_race(key)
        if arg == key or arg == race.display_name.lower():
            return "node_race_select", {"detail": _build_race_detail(race)}

    return "node_race_select", {"detail": f"|rNo race found for '{arg}'. Use a number (e.g. info 1).|n"}


def _set_race(caller, raw_input, **kwargs):
    state = _get_chargen(caller)
    state["race_key"] = kwargs["race_key"]
    return "node_class_select"


# =======================================================================
#  NODE: Class Selection
# =======================================================================

def _build_class_detail(cls):
    """Build full detail text for a character class."""
    lines = []
    lines.append(f"|w{cls.display_name}|n")
    lines.append(cls.description)
    if cls.prime_attribute:
        lines.append(f"  Prime attribute: {ABILITY_SHORT[cls.prime_attribute]}")
    level1 = cls.level_progression.get(1, {})
    if level1:
        lines.append(
            f"  Level 1: HP +{level1.get('hp_gain', 0)}  "
            f"Mana +{level1.get('mana_gain', 0)}  "
            f"Move +{level1.get('move_gain', 0)}"
        )
        lines.append(
            f"  Level 1 skill pts: Weapon {level1.get('weapon_skill_pts', 0)}  "
            f"Class {level1.get('class_skill_pts', 0)}  "
            f"General {level1.get('general_skill_pts', 0)}"
        )
    if cls.multi_class_requirements:
        reqs = ", ".join(
            f"{ABILITY_SHORT[ab]} {val}"
            for ab, val in cls.multi_class_requirements.items()
        )
        lines.append(f"  Multiclass requirements: {reqs}")
    return "\n".join(lines)


def _get_compatible_classes(state):
    """Get classes compatible with the chosen race, as an ordered dict."""
    num_remorts = state.get("num_remorts", 0)
    race_key = state.get("race_key", "human")
    all_classes = get_available_char_classes(num_remorts)
    compatible = {}
    for key, cls in all_classes.items():
        if cls.required_races and race_key not in cls.required_races:
            continue
        if cls.excluded_races and race_key in cls.excluded_races:
            continue
        compatible[key] = cls
    return compatible


def node_class_select(caller, raw_input, **kwargs):
    state = _get_chargen(caller)
    race_key = state.get("race_key", "human")
    compatible = _get_compatible_classes(state)

    # Cache class keys for info lookup
    state["_class_keys"] = list(compatible.keys())

    race = get_race(race_key)
    text = "|gCharacter Creation - Step 2: Choose Your Class|n\n"
    text += f"Race: |w{race.display_name}|n\n"
    text += "-" * 50 + "\n\n"

    # Show detail if requested
    detail_info = kwargs.get("detail", "")
    if detail_info:
        text += detail_info + "\n\n"

    text += "Type |winfo <#>|n for full details, or pick a number to choose.\n"

    options = []
    for i, (key, cls) in enumerate(compatible.items(), 1):
        teaser = cls.description[:60]
        if len(cls.description) > 60:
            teaser += "..."
        tag = " |c[Remort]|n" if cls.min_remort > 0 else ""
        options.append({
            "key": str(i),
            "desc": f"|w{cls.display_name:<10}|n{tag} {teaser}",
            "goto": (_set_class, {"class_key": key}),
        })

    options.append({
        "key": ("b", "back"),
        "desc": "Back to race selection",
        "goto": "node_race_select",
    })

    # Default handler for "info <n>" commands
    options.append({
        "key": "_default",
        "goto": (_handle_class_info, {}),
    })

    return text, tuple(options)


def _handle_class_info(caller, raw_input, **kwargs):
    """Handle 'info <n>' input on the class selection node."""
    state = _get_chargen(caller)
    text = raw_input.strip().lower()

    if not text.startswith("info"):
        return "node_class_select", {"detail": f"|rUnknown command: {raw_input.strip()}. Type a number to choose or 'info <#>' for details.|n"}

    arg = text[4:].strip()
    class_keys = state.get("_class_keys", [])

    # Try numeric index
    try:
        idx = int(arg) - 1
        if 0 <= idx < len(class_keys):
            cls = get_char_class(class_keys[idx])
            return "node_class_select", {"detail": _build_class_detail(cls)}
    except (ValueError, IndexError):
        pass

    # Try class name
    for key in class_keys:
        cls = get_char_class(key)
        if arg == key or arg == cls.display_name.lower():
            return "node_class_select", {"detail": _build_class_detail(cls)}

    return "node_class_select", {"detail": f"|rNo class found for '{arg}'. Use a number (e.g. info 1).|n"}


def _set_class(caller, raw_input, **kwargs):
    state = _get_chargen(caller)
    state["class_key"] = kwargs["class_key"]
    if "scores" not in state:
        state["scores"] = {ab: 8 for ab in ABILITIES}
        state["points_remaining"] = state.get("point_buy", 27)
    return "node_point_buy"



    return "node_alignment_select", {"error": f"Unknown command: {text}. Type a number to choose."}


# =======================================================================
#  NODE: Point Buy
# =======================================================================

def node_point_buy(caller, raw_input, **kwargs):
    state = _get_chargen(caller)
    scores = state["scores"]
    points = state["points_remaining"]
    race_key = state.get("race_key", "human")
    racial_bonuses = _get_racial_bonuses(race_key)

    # Check for error message from a previous action
    error = kwargs.get("error", "")

    text = "|gCharacter Creation - Step 4: Ability Scores|n\n"
    text += "-" * 50 + "\n"
    text += f"Points remaining: |w{points}|n\n\n"

    # Display each ability with score, racial bonus, final, and cost info
    text += f"  {'Ability':<8} {'Base':>4}  {'Racial':>6}  {'Final':>5}  {'Cost +1':>7}  {'Refund -1':>9}\n"
    text += f"  {'------':<8} {'----':>4}  {'------':>6}  {'-----':>5}  {'-------':>7}  {'---------':>9}\n"

    for ab in ABILITIES:
        score = scores[ab]
        racial = racial_bonuses.get(ab, 0)
        final = score + racial
        # Cost to increment
        if score < MAX_SCORE:
            cost_up = POINT_COSTS[score + 1] - POINT_COSTS[score]
            cost_str = str(cost_up)
        else:
            cost_str = "-"
        # Refund from decrement
        if score > MIN_SCORE:
            refund = POINT_COSTS[score] - POINT_COSTS[score - 1]
            refund_str = str(refund)
        else:
            refund_str = "-"

        racial_str = f"{racial:+d}" if racial != 0 else " 0"
        text += (
            f"  {ABILITY_SHORT[ab]:<8} {score:>4}  {racial_str:>6}  "
            f"{final:>5}  {cost_str:>7}  {refund_str:>9}\n"
        )

    text += "\n"
    text += "Commands: |wstr+|n |wstr-|n |wdex+|n ... or |wstr 14|n to set directly\n"

    if error:
        text += f"\n|r{error}|n\n"

    # Build options
    options = []

    # Done option — routes through confirmation if points remain
    if points > 0:
        options.append({
            "key": ("d", "done"),
            "desc": f"Accept scores ({points} points unspent)",
            "goto": "node_point_buy_confirm",
        })
    else:
        options.append({
            "key": ("d", "done"),
            "desc": "Accept scores",
            "goto": "node_weapon_skills",
        })

    # Back option
    options.append({
        "key": ("b", "back"),
        "desc": "Back to class selection",
        "goto": (_reset_scores_and_back, {}),
    })

    # Default handler for free-text input (str+, str-, str 14, etc.)
    options.append({
        "key": "_default",
        "goto": (_handle_point_buy_input, {}),
    })

    return text, tuple(options)


def node_point_buy_confirm(caller, raw_input, **kwargs):
    """Confirm leaving point buy with unspent points."""
    state = _get_chargen(caller)
    points = state.get("points_remaining", 0)

    text = f"|yYou still have |w{points}|y points to spend. Are you sure?|n\n"

    options = (
        {
            "key": ("y", "yes"),
            "desc": "Yes, continue with unspent points",
            "goto": "node_weapon_skills",
        },
        {
            "key": ("n", "no"),
            "desc": "No, go back and spend them",
            "goto": "node_point_buy",
        },
    )

    return text, options


def _reset_scores_and_back(caller, raw_input, **kwargs):
    """Reset scores when going back so they re-initialize on return."""
    state = _get_chargen(caller)
    if "scores" in state:
        del state["scores"]
    if "points_remaining" in state:
        del state["points_remaining"]
    return "node_class_select"


def _handle_point_buy_input(caller, raw_input, **kwargs):
    """Parse free-text point buy commands: str+, str-, str 14, etc."""
    state = _get_chargen(caller)
    scores = state["scores"]
    points = state["points_remaining"]
    text = raw_input.strip().lower()

    # Parse input
    ability = None
    action = None  # "inc", "dec", or "set"
    target_value = None

    # Try "str+" / "str-" format
    for short, ab in _SHORT_TO_ABILITY.items():
        if text == f"{short}+":
            ability = ab
            action = "inc"
            break
        elif text == f"{short}-":
            ability = ab
            action = "dec"
            break
        elif text.startswith(short + " "):
            try:
                target_value = int(text[len(short):].strip())
                ability = ab
                action = "set"
            except ValueError:
                pass
            break

    if ability is None:
        return "node_point_buy", {"error": f"Unknown command: {raw_input.strip()}"}

    current = scores[ability]

    if action == "inc":
        if current >= MAX_SCORE:
            return "node_point_buy", {"error": f"{ABILITY_SHORT[ability]} is already at maximum ({MAX_SCORE})."}
        cost = POINT_COSTS[current + 1] - POINT_COSTS[current]
        if cost > points:
            return "node_point_buy", {"error": f"Not enough points. {ABILITY_SHORT[ability]}+1 costs {cost}, you have {points}."}
        scores[ability] = current + 1
        state["points_remaining"] = points - cost

    elif action == "dec":
        if current <= MIN_SCORE:
            return "node_point_buy", {"error": f"{ABILITY_SHORT[ability]} is already at minimum ({MIN_SCORE})."}
        refund = POINT_COSTS[current] - POINT_COSTS[current - 1]
        scores[ability] = current - 1
        state["points_remaining"] = points + refund

    elif action == "set":
        if target_value < MIN_SCORE or target_value > MAX_SCORE:
            return "node_point_buy", {"error": f"Score must be between {MIN_SCORE} and {MAX_SCORE}."}
        cost_diff = POINT_COSTS[target_value] - POINT_COSTS[current]
        if cost_diff > points:
            return "node_point_buy", {"error": f"Not enough points. Setting {ABILITY_SHORT[ability]} to {target_value} costs {cost_diff}, you have {points}."}
        scores[ability] = target_value
        state["points_remaining"] = points - cost_diff

    return "node_point_buy"


# Shorthand lookup for point buy input parsing
_SHORT_TO_ABILITY = {
    "str": Ability.STR, "dex": Ability.DEX, "con": Ability.CON,
    "int": Ability.INT, "wis": Ability.WIS, "cha": Ability.CHA,
}


# =======================================================================
#  Shared skill toggle helpers
# =======================================================================

def _build_skill_toggle_text(title, step, items, selected, budget, race_name,
                             class_name, racial_free=None, error=""):
    """Build display text for a skill/language toggle node."""
    spent = len(selected)
    remaining = budget - spent

    text = f"|gCharacter Creation - Step {step}: {title}|n\n"
    text += f"Race: |w{race_name}|n  Class: |w{class_name}|n\n"
    text += "-" * 50 + "\n"
    text += f"Points: {spent} of {budget} spent ({remaining} remaining)\n\n"

    if racial_free:
        text += "  Racial (free): "
        text += ", ".join(f"{name} (BASIC)" for name, _ in racial_free)
        text += "\n\n"

    text += f"  Choose proficiencies (1 point each):\n"
    for i, (display_name, key) in enumerate(items, 1):
        marker = "X" if key in selected else " "
        text += f"    |w{i:>2}|n. [{marker}] {display_name}\n"

    text += "\nType a number to toggle, |winfo <#>|n for details. |wdone|n to continue, |wback|n to go back.\n"

    if error:
        text += f"\n|r{error}|n\n"

    return text


def _get_skill_description(key):
    """Look up a description for a skill or weapon type key."""
    try:
        return skills(key).description
    except ValueError:
        pass
    try:
        return WeaponType(key).description
    except ValueError:
        pass
    return "No description available."


def _handle_skill_toggle(caller, raw_input, state_key, items, budget, node_name):
    """Parse numeric toggle input for skill/language selection nodes."""
    state = _get_chargen(caller)
    selected = state.get(state_key, set())
    text = raw_input.strip()

    # Handle "info <n>" input
    if text.lower().startswith("info"):
        arg = text[4:].strip()
        try:
            idx = int(arg) - 1
            if 0 <= idx < len(items):
                display_name, key = items[idx]
                desc = _get_skill_description(key)
                return node_name, {"error": f"|c{display_name}|n: {desc}"}
        except (ValueError, IndexError):
            pass
        return node_name, {"error": "Use |winfo <#>|n with a valid number."}

    try:
        idx = int(text) - 1
        if 0 <= idx < len(items):
            _, key = items[idx]
            if key in selected:
                selected.discard(key)
            else:
                if len(selected) >= budget:
                    return node_name, {"error": "No points remaining. Remove a selection first."}
                selected.add(key)
            state[state_key] = selected
            return node_name
    except (ValueError, IndexError):
        pass

    return node_name, {"error": f"Unknown command: {text}. Type a number to toggle."}


def node_skill_confirm(caller, raw_input, **kwargs):
    """Generic confirmation for unspent skill/language points."""
    points_unspent = kwargs.get("points_unspent", 0)
    skill_type = kwargs.get("skill_type", "skill")
    return_node = kwargs.get("return_node", "")
    next_node = kwargs.get("next_node", "")
    save_msg = kwargs.get("save_msg", "They will be saved for training later.")

    text = (f"|yYou have |w{points_unspent}|y unspent {skill_type} points. "
            f"{save_msg} Continue?|n\n")

    options = (
        {
            "key": ("y", "yes"),
            "desc": "Yes, continue",
            "goto": next_node,
        },
        {
            "key": ("n", "no"),
            "desc": "No, go back",
            "goto": return_node,
        },
    )

    return text, options


# =======================================================================
#  NODE: Weapon Skills (Step 5)
# =======================================================================

def _get_weapon_items(race, class_key):
    """Get toggleable weapon items, excluding racial profs, filtered by class."""
    racial_keys = {w.value for w in race.racial_weapon_proficiencies}
    items = []
    for wt in WeaponType:
        if wt.value not in racial_keys and wt.can_be_used_by(class_key):
            items.append((wt.value.replace("_", " ").title(), wt.value))
    return sorted(items, key=lambda x: x[0])


def _get_racial_weapon_display(race):
    """Get racial weapon proficiencies for display."""
    return [
        (w.value.replace("_", " ").title(), w.value)
        for w in race.racial_weapon_proficiencies
    ]


def node_weapon_skills(caller, raw_input, **kwargs):
    state = _get_chargen(caller)
    race = get_race(state["race_key"])
    charclass = get_char_class(state["class_key"])

    budget = _get_skill_budget(state, "weapon_skill_pts")

    if "selected_weapon_skills" not in state:
        state["selected_weapon_skills"] = set()

    items = _get_weapon_items(race, state["class_key"])
    racial_free = _get_racial_weapon_display(race)

    # Cache items for toggle handler
    state["_weapon_items"] = items

    text = _build_skill_toggle_text(
        "Weapon Skills", 5, items, state["selected_weapon_skills"],
        budget, race.display_name, charclass.display_name,
        racial_free=racial_free, error=kwargs.get("error", ""),
    )

    spent = len(state["selected_weapon_skills"])
    remaining = budget - spent

    options = []

    if remaining > 0:
        options.append({
            "key": ("d", "done"),
            "desc": f"Continue ({remaining} points unspent)",
            "goto": ("node_skill_confirm", {
                "points_unspent": remaining,
                "skill_type": "weapon skill",
                "return_node": "node_weapon_skills",
                "next_node": "node_class_skills",
            }),
        })
    else:
        options.append({
            "key": ("d", "done"),
            "desc": "Continue",
            "goto": "node_class_skills",
        })

    options.append({
        "key": ("b", "back"),
        "desc": "Back to ability scores",
        "goto": (_clear_skills_and_back_to_pointbuy, {}),
    })

    options.append({
        "key": "_default",
        "goto": (_handle_weapon_toggle, {}),
    })

    return text, tuple(options)


def _handle_weapon_toggle(caller, raw_input, **kwargs):
    state = _get_chargen(caller)
    items = state.get("_weapon_items", [])
    budget = _get_skill_budget(state, "weapon_skill_pts")
    return _handle_skill_toggle(
        caller, raw_input, "selected_weapon_skills", items, budget,
        "node_weapon_skills",
    )


def _clear_skills_and_back_to_pointbuy(caller, raw_input, **kwargs):
    """Clear ALL skill/language selections when going back to point buy."""
    state = _get_chargen(caller)
    for key in ("selected_weapon_skills", "selected_class_skills",
                "selected_general_skills", "selected_extra_languages",
                "selected_starting_recipes", "selected_starting_spells",
                "_weapon_items", "_class_skill_items", "_general_skill_items",
                "_language_items", "_knowledge_queue",
                "_current_knowledge_options", "_current_knowledge_type",
                "_current_knowledge_skill", "_granted_spell_schools",
                "_auto_granted_spells"):
        state.pop(key, None)
    return "node_point_buy"


# =======================================================================
#  NODE: Class Skills (Step 6)
# =======================================================================

def _get_class_skill_items(class_key):
    """Get class skills available to the chosen class."""
    items = []
    for skill in skills:
        available = skill.classes_available_to
        if available != {"all"} and class_key in available:
            items.append((skill.value.replace("_", " ").title(), skill.value))
    return sorted(items, key=lambda x: x[0])


def node_class_skills(caller, raw_input, **kwargs):
    state = _get_chargen(caller)
    race = get_race(state["race_key"])
    charclass = get_char_class(state["class_key"])

    budget = _get_skill_budget(state, "class_skill_pts")

    if "selected_class_skills" not in state:
        state["selected_class_skills"] = set()

    items = _get_class_skill_items(state["class_key"])
    state["_class_skill_items"] = items

    text = _build_skill_toggle_text(
        "Class Skills", 6, items, state["selected_class_skills"],
        budget, race.display_name, charclass.display_name,
        error=kwargs.get("error", ""),
    )

    spent = len(state["selected_class_skills"])
    remaining = budget - spent

    options = []

    if remaining > 0:
        options.append({
            "key": ("d", "done"),
            "desc": f"Continue ({remaining} points unspent)",
            "goto": ("node_skill_confirm", {
                "points_unspent": remaining,
                "skill_type": "class skill",
                "return_node": "node_class_skills",
                "next_node": "node_general_skills",
            }),
        })
    else:
        options.append({
            "key": ("d", "done"),
            "desc": "Continue",
            "goto": "node_general_skills",
        })

    options.append({
        "key": ("b", "back"),
        "desc": "Back to weapon skills",
        "goto": "node_weapon_skills",
    })

    options.append({
        "key": "_default",
        "goto": (_handle_class_skill_toggle, {}),
    })

    return text, tuple(options)


def _handle_class_skill_toggle(caller, raw_input, **kwargs):
    state = _get_chargen(caller)
    items = state.get("_class_skill_items", [])
    budget = _get_skill_budget(state, "class_skill_pts")
    return _handle_skill_toggle(
        caller, raw_input, "selected_class_skills", items, budget,
        "node_class_skills",
    )


# =======================================================================
#  NODE: General Skills (Step 7)
# =======================================================================

def _get_general_skill_items():
    """Get general skills (available to all classes)."""
    items = []
    for skill in skills:
        if skill.classes_available_to == {"all"}:
            items.append((skill.value.replace("_", " ").title(), skill.value))
    return sorted(items, key=lambda x: x[0])


def node_general_skills(caller, raw_input, **kwargs):
    state = _get_chargen(caller)
    # Clear knowledge queue so it rebuilds if skills changed
    for key in ("_knowledge_queue", "_current_knowledge_options",
                "_current_knowledge_type", "_current_knowledge_skill"):
        state.pop(key, None)
    race = get_race(state["race_key"])
    charclass = get_char_class(state["class_key"])

    budget = _get_skill_budget(state, "general_skill_pts")

    if "selected_general_skills" not in state:
        state["selected_general_skills"] = set()

    items = _get_general_skill_items()
    state["_general_skill_items"] = items

    text = _build_skill_toggle_text(
        "General Skills", 7, items, state["selected_general_skills"],
        budget, race.display_name, charclass.display_name,
        error=kwargs.get("error", ""),
    )

    spent = len(state["selected_general_skills"])
    remaining = budget - spent

    options = []

    if remaining > 0:
        options.append({
            "key": ("d", "done"),
            "desc": f"Continue ({remaining} points unspent)",
            "goto": ("node_skill_confirm", {
                "points_unspent": remaining,
                "skill_type": "general skill",
                "return_node": "node_general_skills",
                "next_node": "node_starting_knowledge",
            }),
        })
    else:
        options.append({
            "key": ("d", "done"),
            "desc": "Continue",
            "goto": "node_starting_knowledge",
        })

    options.append({
        "key": ("b", "back"),
        "desc": "Back to class skills",
        "goto": "node_class_skills",
    })

    options.append({
        "key": "_default",
        "goto": (_handle_general_skill_toggle, {}),
    })

    return text, tuple(options)


def _handle_general_skill_toggle(caller, raw_input, **kwargs):
    state = _get_chargen(caller)
    items = state.get("_general_skill_items", [])
    budget = _get_skill_budget(state, "general_skill_pts")
    return _handle_skill_toggle(
        caller, raw_input, "selected_general_skills", items, budget,
        "node_general_skills",
    )


# =======================================================================
#  NODE: Starting Knowledge (Step 8)
# =======================================================================

def _build_knowledge_queue(state):
    """
    Build list of skills that have BASIC-tier recipes or spells to offer.

    Returns list of (skill_enum, "recipe"|"spell", [(name, key), ...]) tuples.
    Also cleans up orphaned selections from prior visits, and tracks which
    spell schools belong to classes with grants_spells=True (for routing
    starting spells to db.granted_spells vs db.spellbook in node_create).
    """
    queue = []
    granted_spell_schools = set()

    # Determine if the selected class grants spells (e.g. cleric)
    charclass = get_char_class(state.get("class_key", ""))
    class_grants = charclass.grants_spells if charclass else False

    # Auto-granted spells for classes with grants_spells=True (cleric, paladin).
    # These classes receive ALL basic spells from their schools automatically
    # and skip the interactive spell selection UI entirely.
    auto_granted_spells = []

    # Check selected class skills for spell schools
    for skill_key in sorted(state.get("selected_class_skills", set())):
        try:
            skill_enum = skills(skill_key)
        except ValueError:
            continue
        if skill_enum.classes_available_to == {"all"}:
            continue
        school_spells = get_spells_for_school(skill_enum)
        basic_spells = [
            (sp.name, sp.key)
            for sp in school_spells.values()
            if sp.min_mastery == MasteryLevel.BASIC
        ]
        if basic_spells:
            if class_grants:
                # Auto-grant ALL basic spells — no user selection needed
                granted_spell_schools.add(skill_key)
                for _name, spell_key in basic_spells:
                    auto_granted_spells.append(spell_key)
            else:
                queue.append((skill_enum, "spell", sorted(basic_spells)))

    # Check selected general skills for crafting recipes
    for skill_key in sorted(state.get("selected_general_skills", set())):
        try:
            skill_enum = skills(skill_key)
        except ValueError:
            continue
        skill_recipes = get_recipes_for_skill(skill_enum)
        basic_recipes = [
            (r["name"], r["recipe_key"])
            for r in skill_recipes.values()
            if r["min_mastery"] == MasteryLevel.BASIC
        ]
        if basic_recipes:
            queue.append((skill_enum, "recipe", sorted(basic_recipes)))

    # Track which schools produce granted (temporary) vs learned (permanent) spells
    state["_granted_spell_schools"] = granted_spell_schools
    state["_auto_granted_spells"] = auto_granted_spells

    # Clean up orphaned selections (skill was deselected since last visit)
    valid_recipe_skills = {s.value for s, typ, _ in queue if typ == "recipe"}
    valid_spell_schools = {s.value for s, typ, _ in queue if typ == "spell"}
    state["selected_starting_recipes"] = {
        k: v for k, v in state.get("selected_starting_recipes", {}).items()
        if k in valid_recipe_skills
    }
    state["selected_starting_spells"] = {
        k: v for k, v in state.get("selected_starting_spells", {}).items()
        if k in valid_spell_schools
    }

    return queue


def node_starting_knowledge(caller, raw_input, **kwargs):
    """Choose starting recipes/spells — one per eligible skill."""
    state = _get_chargen(caller)
    race = get_race(state["race_key"])
    charclass = get_char_class(state["class_key"])

    # Build queue on first entry
    if "_knowledge_queue" not in state:
        state["_knowledge_queue"] = _build_knowledge_queue(state)
        state.setdefault("selected_starting_recipes", {})
        state.setdefault("selected_starting_spells", {})

    queue = state["_knowledge_queue"]

    # Skip entirely if no skills have BASIC-tier knowledge
    if not queue:
        return node_languages(caller, raw_input, **kwargs)

    idx = kwargs.get("queue_index", 0)

    # Past the end — move to languages
    if idx >= len(queue):
        return node_languages(caller, raw_input, **kwargs)

    skill_enum, knowledge_type, options_list = queue[idx]
    skill_name = skill_enum.value.replace("_", " ").title()
    kind_label = "spell" if knowledge_type == "spell" else "recipe"
    error = kwargs.get("error", "")

    # Determine next/back destinations
    if idx + 1 >= len(queue):
        next_dest = "node_languages"
    else:
        next_dest = ("node_starting_knowledge", {"queue_index": idx + 1})

    if idx == 0:
        back_dest = "node_general_skills"
    else:
        back_dest = ("node_starting_knowledge", {"queue_index": idx - 1})

    # --- Auto-grant if exactly 1 option ---
    if len(options_list) == 1:
        name, key = options_list[0]
        if knowledge_type == "spell":
            state["selected_starting_spells"][skill_enum.value] = key
        else:
            state["selected_starting_recipes"][skill_enum.value] = key

        text = f"|gCharacter Creation - Step 8: Starting Knowledge|n\n"
        text += f"Race: |w{race.display_name}|n  Class: |w{charclass.display_name}|n\n"
        text += "-" * 50 + "\n\n"
        text += f"  |w{skill_name}|n — |g{name}|n automatically learned.\n"
        if len(queue) > 1:
            text += f"  ({idx + 1} of {len(queue)} skills)\n"

        options = (
            {"key": ("d", "done", ""), "desc": "Continue", "goto": next_dest},
            {"key": ("b", "back"), "desc": "Back", "goto": back_dest},
        )
        return text, options

    # --- Multiple options — show selection ---
    if knowledge_type == "spell":
        current_selection = state["selected_starting_spells"].get(skill_enum.value)
    else:
        current_selection = state["selected_starting_recipes"].get(skill_enum.value)

    # Cache for handler
    state["_current_knowledge_options"] = options_list
    state["_current_knowledge_type"] = knowledge_type
    state["_current_knowledge_skill"] = skill_enum.value

    text = f"|gCharacter Creation - Step 8: Starting Knowledge|n\n"
    text += f"Race: |w{race.display_name}|n  Class: |w{charclass.display_name}|n\n"
    text += "-" * 50 + "\n\n"
    text += f"  Choose 1 starting {kind_label} from |w{skill_name}|n:\n"
    if len(queue) > 1:
        text += f"  ({idx + 1} of {len(queue)} skills)\n"
    text += "\n"

    for i, (name, key) in enumerate(options_list, 1):
        marker = "*" if key == current_selection else " "
        text += f"    |w{i:>2}|n. [{marker}] {name}\n"

    text += "\nType a number to choose. |wdone|n to continue, |wback|n to go back.\n"

    if error:
        text += f"\n|r{error}|n\n"

    options = []

    if current_selection:
        options.append({
            "key": ("d", "done"),
            "desc": "Continue",
            "goto": next_dest,
        })
    else:
        options.append({
            "key": ("d", "done"),
            "desc": f"Continue (pick a {kind_label} first)",
            "goto": ("node_starting_knowledge", {
                "queue_index": idx,
                "error": f"You must select a starting {kind_label}.",
            }),
        })

    options.append({"key": ("b", "back"), "desc": "Back", "goto": back_dest})
    options.append({
        "key": "_default",
        "goto": (_handle_knowledge_select, {"queue_index": idx}),
    })

    return text, tuple(options)


def _handle_knowledge_select(caller, raw_input, **kwargs):
    """Parse numeric input for starting knowledge selection."""
    state = _get_chargen(caller)
    idx = kwargs.get("queue_index", 0)
    options_list = state.get("_current_knowledge_options", [])
    knowledge_type = state.get("_current_knowledge_type", "recipe")
    skill_key = state.get("_current_knowledge_skill", "")

    text = raw_input.strip()

    try:
        choice = int(text) - 1
        if 0 <= choice < len(options_list):
            name, key = options_list[choice]
            if knowledge_type == "spell":
                state.setdefault("selected_starting_spells", {})[skill_key] = key
            else:
                state.setdefault("selected_starting_recipes", {})[skill_key] = key
            return "node_starting_knowledge", {"queue_index": idx}
    except (ValueError, IndexError):
        pass

    return "node_starting_knowledge", {
        "queue_index": idx,
        "error": f"Unknown command: {text}. Type a number to choose.",
    }


def _back_from_languages(caller, raw_input, **kwargs):
    """Navigate back from languages to last knowledge queue item or general skills."""
    state = _get_chargen(caller)
    queue = state.get("_knowledge_queue", [])
    if queue:
        return "node_starting_knowledge", {"queue_index": len(queue) - 1}
    return "node_general_skills"


def _goto_after_languages(caller, raw_input, **kwargs):
    """After languages, skip name for remort characters."""
    state = _get_chargen(caller)
    if state.get("is_remort"):
        state["char_name"] = state["character"].key
        return "node_confirm"
    return "node_name"


# =======================================================================
#  NODE: Languages (Step 9)
# =======================================================================

def _get_bonus_language_picks(state):
    """Calculate bonus language picks from INT modifier."""
    scores = state.get("scores", {})
    int_score = scores.get(Ability.INT, 8)
    racial_bonuses = _get_racial_bonuses(state.get("race_key", "human"))
    racial_int = racial_bonuses.get(Ability.INT, 0)
    final_int = int_score + racial_int
    return max(0, math.floor((final_int - 10) / 2))


def _get_auto_languages(race):
    """Get languages automatically granted (Common + racial)."""
    auto = {"common"}
    for lang in race.racial_languages:
        auto.add(lang)
    return auto


def _get_choosable_languages(auto_languages):
    """Get languages available for player choice.

    Excludes the ANIMAL language — it is non-learnable and gated behind the
    SPEAK_WITH_ANIMALS condition (granted only by the speak_with_animals
    spell or potion).
    """
    items = []
    for lang in Languages:
        if lang.value == Languages.ANIMAL.value:
            continue
        if lang.value not in auto_languages:
            items.append((lang.value.capitalize(), lang.value))
    return sorted(items, key=lambda x: x[0])


def node_languages(caller, raw_input, **kwargs):
    state = _get_chargen(caller)
    race = get_race(state["race_key"])
    charclass = get_char_class(state["class_key"])

    bonus_picks = _get_bonus_language_picks(state)
    auto_langs = _get_auto_languages(race)
    choosable = _get_choosable_languages(auto_langs)

    if "selected_extra_languages" not in state:
        state["selected_extra_languages"] = set()

    error = kwargs.get("error", "")

    text = f"|gCharacter Creation - Step 9: Languages|n\n"
    text += f"Race: |w{race.display_name}|n  Class: |w{charclass.display_name}|n\n"
    text += "-" * 50 + "\n\n"
    text += "  Your languages: "
    text += ", ".join(lang.capitalize() for lang in sorted(auto_langs))
    text += "\n\n"

    if bonus_picks == 0:
        # No bonus picks — informational only
        text += "  Your Intelligence modifier grants no bonus languages.\n"

        options = (
            {
                "key": ("d", "done"),
                "desc": "Continue",
                "goto": (_goto_after_languages, {}),
            },
            {
                "key": ("b", "back"),
                "desc": "Back",
                "goto": (_back_from_languages, {}),
            },
        )

        return text, options

    if bonus_picks >= len(choosable):
        # Auto-grant all remaining languages
        all_extra = {key for _, key in choosable}
        state["selected_extra_languages"] = all_extra
        text += (
            f"  Your Intelligence modifier grants {bonus_picks} bonus languages.\n"
            f"  All remaining languages automatically granted: "
        )
        text += ", ".join(name for name, _ in choosable)
        text += "\n"

        options = (
            {
                "key": ("d", "done"),
                "desc": "Continue",
                "goto": (_goto_after_languages, {}),
            },
            {
                "key": ("b", "back"),
                "desc": "Back",
                "goto": (_back_from_languages, {}),
            },
        )

        return text, options

    # Normal case — player has picks to make
    state["_language_items"] = choosable
    selected = state["selected_extra_languages"]
    spent = len(selected)
    remaining = bonus_picks - spent

    text += f"  Bonus language picks: {spent} of {bonus_picks} used ({remaining} remaining)\n\n"
    text += "  Choose additional languages:\n"
    for i, (display_name, key) in enumerate(choosable, 1):
        marker = "X" if key in selected else " "
        text += f"    |w{i:>2}|n. [{marker}] {display_name}\n"

    text += "\nType a number to toggle. |wdone|n to continue, |wback|n to go back.\n"

    if error:
        text += f"\n|r{error}|n\n"

    options = []

    if remaining > 0:
        options.append({
            "key": ("d", "done"),
            "desc": f"Continue ({remaining} picks unused)",
            "goto": ("node_skill_confirm", {
                "points_unspent": remaining,
                "skill_type": "language",
                "return_node": "node_languages",
                "next_node": (_goto_after_languages, {}),
                "save_msg": "Unused picks cannot be saved.",
            }),
        })
    else:
        options.append({
            "key": ("d", "done"),
            "desc": "Continue",
            "goto": (_goto_after_languages, {}),
        })

    options.append({
        "key": ("b", "back"),
        "desc": "Back",
        "goto": (_back_from_languages, {}),
    })

    options.append({
        "key": "_default",
        "goto": (_handle_language_toggle, {}),
    })

    return text, tuple(options)


def _handle_language_toggle(caller, raw_input, **kwargs):
    state = _get_chargen(caller)
    items = state.get("_language_items", [])
    bonus_picks = _get_bonus_language_picks(state)
    return _handle_skill_toggle(
        caller, raw_input, "selected_extra_languages", items, bonus_picks,
        "node_languages",
    )


# =======================================================================
#  NODE: Name (Step 10)
# =======================================================================

def node_name(caller, raw_input, **kwargs):
    state = _get_chargen(caller)
    error = kwargs.get("error", "")

    text = "|gCharacter Creation - Step 10: Choose Your Name|n\n"
    text += "-" * 50 + "\n\n"
    text += "Enter a name for your character (3-20 letters).\n"
    text += 'For multi-word names use double quotes: |w"Bob Jane"|n\n'

    if error:
        text += f"\n|r{error}|n\n"

    options = []

    options.append({
        "key": ("b", "back"),
        "desc": "Back to languages",
        "goto": "node_languages",
    })

    options.append({
        "key": "_default",
        "goto": (_handle_name_input, {}),
    })

    return text, tuple(options)


def _handle_name_input(caller, raw_input, **kwargs):
    """Validate and store the character name."""
    state = _get_chargen(caller)
    name = raw_input.strip()

    # Handle quoted multi-word names
    if name.startswith('"') and name.endswith('"') and len(name) > 2:
        name = name[1:-1].strip()
        # Validate each word is alphabetic
        words = name.split()
        if not words:
            return "node_name", {"error": "Name cannot be empty."}
        for word in words:
            if not word.isalpha():
                return "node_name", {"error": "Name must contain only letters (a-z)."}
        name = " ".join(w.capitalize() for w in words)
    else:
        # Unquoted — single word only
        if " " in name:
            return "node_name", {"error": 'For multi-word names, use double quotes: "Bob Jane"'}
        if not name.isalpha():
            return "node_name", {"error": "Name must contain only letters (a-z)."}
        name = name.capitalize()

    if len(name) < 3:
        return "node_name", {"error": "Name must be at least 3 characters."}

    if len(name) > 20:
        return "node_name", {"error": "Name must be 20 characters or fewer."}

    # Check uniqueness
    exists = ObjectDB.objects.filter(db_key__iexact=name).exists()
    if exists:
        return "node_name", {"error": f"The name '{name}' is already taken."}

    state["char_name"] = name
    return "node_confirm"


# =======================================================================
#  NODE: Confirm
# =======================================================================

def node_confirm(caller, raw_input, **kwargs):
    state = _get_chargen(caller)
    race = get_race(state["race_key"])
    charclass = get_char_class(state["class_key"])
    scores = state["scores"]
    name = state["char_name"]
    racial_bonuses = race.ability_score_bonuses
    level1 = charclass.level_progression.get(1, {})
    is_remort = state.get("is_remort", False)

    if is_remort:
        text = "|wRemort - Character Rebuild Review|n\n"
        text += "=" * 50 + "\n"
        text += f"  Remort count: |c{state.get('num_remorts', 0)}|n\n\n"
    else:
        text = "|wCharacter Creation - Review|n\n"
        text += "=" * 50 + "\n\n"

    text += f"  Name:      |w{name}|n\n"
    text += f"  Race:      |w{race.display_name}|n\n"
    text += f"  Class:     |w{charclass.display_name}|n\n"
    text += f"  Alignment: |wNeutral|n (shifts with your actions)\n\n"

    text += "  Ability Scores:\n"
    for ab in ABILITIES:
        base = scores[ab]
        racial = racial_bonuses.get(ab, 0)
        final = base + racial
        if racial != 0:
            text += f"    {ABILITY_SHORT[ab]}: {final} (base {base} {racial:+d} racial)\n"
        else:
            text += f"    {ABILITY_SHORT[ab]}: {final}\n"

    final_con = scores[Ability.CON] + racial_bonuses.get(Ability.CON, 0)
    con_mod = math.floor((final_con - 10) / 2)

    hp_base = race.base_hp + level1.get("hp_gain", 0)
    hp_total = hp_base + con_mod
    text += f"\n  Starting HP:   {race.base_hp} (race)"
    if level1.get("hp_gain"):
        text += f" + {level1['hp_gain']} (class)"
    if con_mod != 0:
        text += f" {con_mod:+d} (CON)"
    text += f" = {hp_total}"

    text += f"\n  Starting Mana: {race.base_mana} (race)"
    if level1.get("mana_gain"):
        text += f" + {level1['mana_gain']} (class) = {race.base_mana + level1['mana_gain']}"
    text += f"\n  Starting Move: {race.base_move} (race)"
    if level1.get("move_gain"):
        text += f" + {level1['move_gain']} (class) = {race.base_move + level1['move_gain']}"

    # Weapon skills
    racial_profs = race.racial_weapon_proficiencies
    selected_weapons = state.get("selected_weapon_skills", set())
    text += "\n\n  Weapon Skills (BASIC):\n"
    if racial_profs:
        for w in racial_profs:
            text += f"    {w.value.replace('_', ' ').title()} (racial)\n"
    for w_key in sorted(selected_weapons):
        text += f"    {w_key.replace('_', ' ').title()}\n"
    weapon_budget = _get_skill_budget(state, "weapon_skill_pts")
    weapon_unspent = weapon_budget - len(selected_weapons)
    if weapon_unspent > 0:
        text += f"    ({weapon_unspent} points saved for later)\n"
    if not racial_profs and not selected_weapons:
        text += "    None\n"

    # Class skills
    selected_class = state.get("selected_class_skills", set())
    text += "\n  Class Skills (BASIC):\n"
    if selected_class:
        for s_key in sorted(selected_class):
            text += f"    {s_key.replace('_', ' ').title()}\n"
    else:
        text += "    None\n"
    class_budget = _get_skill_budget(state, "class_skill_pts")
    class_unspent = class_budget - len(selected_class)
    if class_unspent > 0:
        text += f"    ({class_unspent} points saved for later)\n"

    # General skills
    selected_general = state.get("selected_general_skills", set())
    text += "\n  General Skills (BASIC):\n"
    if selected_general:
        for s_key in sorted(selected_general):
            text += f"    {s_key.replace('_', ' ').title()}\n"
    else:
        text += "    None\n"
    general_budget = _get_skill_budget(state, "general_skill_pts")
    general_unspent = general_budget - len(selected_general)
    if general_unspent > 0:
        text += f"    ({general_unspent} points saved for later)\n"

    # Starting Knowledge
    starting_recipes = state.get("selected_starting_recipes", {})
    starting_spells = state.get("selected_starting_spells", {})
    if starting_recipes or starting_spells:
        text += "\n  Starting Knowledge:\n"
        for skill_key, recipe_key in sorted(starting_recipes.items()):
            recipe = get_recipe(recipe_key)
            skill_name = skill_key.replace("_", " ").title()
            recipe_name = recipe["name"] if recipe else recipe_key
            text += f"    {recipe_name} ({skill_name} recipe)\n"
        granted_schools = state.get("_granted_spell_schools", set())
        for school_key, spell_key in sorted(starting_spells.items()):
            spell = get_spell(spell_key)
            school_name = school_key.replace("_", " ").title()
            spell_name = spell.name if spell else spell_key
            source = "granted" if school_key in granted_schools else "learned"
            text += f"    {spell_name} ({school_name} spell, {source})\n"

    # Languages
    auto_langs = _get_auto_languages(race)
    extra_langs = state.get("selected_extra_languages", set())
    all_langs = auto_langs | extra_langs
    text += "\n  Languages: " + ", ".join(
        lang.capitalize() for lang in sorted(all_langs)
    ) + "\n"

    text += "\n"

    if is_remort:
        confirm_desc = "Rebuild this character"
        back_desc = "Back to languages"
        back_goto = "node_languages"
    else:
        confirm_desc = "Create this character"
        back_desc = "Back to name"
        back_goto = "node_name"

    options = (
        {
            "key": ("c", "confirm"),
            "desc": confirm_desc,
            "goto": "node_create",
        },
        {
            "key": ("b", "back"),
            "desc": back_desc,
            "goto": back_goto,
        },
        {
            "key": ("r", "restart"),
            "desc": "Start over",
            "goto": "node_restart_confirm",
        },
    )

    return text, options


def node_restart_confirm(caller, raw_input, **kwargs):
    """Confirm starting over — all choices will be lost."""
    text = "|yAre you sure you want to start over? All choices will be lost.|n\n"

    options = (
        {
            "key": ("y", "yes"),
            "desc": "Yes, start over",
            "goto": (_restart, {}),
        },
        {
            "key": ("n", "no"),
            "desc": "No, go back",
            "goto": "node_confirm",
        },
    )

    return text, options


def _restart(caller, raw_input, **kwargs):
    """Reset all chargen state and start over (preserve remort context)."""
    state = _get_chargen(caller)
    preserved = {"session": state.get("session")}
    for key in ("is_remort", "character", "num_remorts", "point_buy"):
        if key in state:
            preserved[key] = state[key]
    caller.ndb._chargen = preserved
    return "node_race_select"


# =======================================================================
#  NODE: Create
# =======================================================================

def _apply_chargen_to_character(char, state):
    """Apply all chargen selections to a character (shared by create and remort)."""
    race_key = state["race_key"]
    class_key = state["class_key"]
    scores = state["scores"]

    # 1. Apply point buy ability scores (BEFORE race, which adds bonuses on top)
    for ab, score in scores.items():
        setattr(char, f"base_{ab.value}", score)
        setattr(char, ab.value, score)

    # 2. Apply race (sets HP/mana/move, adds racial ability bonuses, conditions,
    #    languages, weapon proficiencies, cmdset)
    race = get_race(race_key)
    race.at_taking_race(char)

    # 3. Alignment — starts at 0 (Neutral), shifts dynamically via gameplay
    char.alignment_score = 0

    # 4. Apply class (adds HP/mana/move on top of racial base, grants skill
    #    points, adds class cmdset, initializes db.classes entry)
    charclass = get_char_class(class_key)
    charclass.at_char_first_gaining_class(char)

    # 5. Apply chargen skill selections

    # 5a. Weapon skills — merge with racial profs (already set by at_taking_race)
    weapon_mastery = dict(char.db.weapon_skill_mastery_levels or {})
    selected_weapons = state.get("selected_weapon_skills", set())
    for wkey in selected_weapons:
        weapon_mastery[wkey] = MasteryLevel.BASIC.value
    char.db.weapon_skill_mastery_levels = weapon_mastery
    char.weapon_skill_pts_available -= len(selected_weapons)

    # 5b. Class skills — init ALL class skills at UNSKILLED, upgrade selected to BASIC
    class_mastery = dict(char.db.class_skill_mastery_levels or {})
    for skill_member in skills:
        available = skill_member.classes_available_to
        if available != {"all"} and class_key in available:
            if skill_member.value not in class_mastery:
                class_mastery[skill_member.value] = {
                    "mastery": MasteryLevel.UNSKILLED.value,
                    "classes": [class_key],
                }
    selected_class_skills = state.get("selected_class_skills", set())
    for skey in selected_class_skills:
        if skey in class_mastery:
            class_mastery[skey]["mastery"] = MasteryLevel.BASIC.value
        else:
            class_mastery[skey] = {
                "mastery": MasteryLevel.BASIC.value,
                "classes": [class_key],
            }
    char.db.class_skill_mastery_levels = class_mastery
    cdata = char.db.classes[class_key]
    cdata["skill_pts_available"] -= len(selected_class_skills)
    char.db.classes[class_key] = cdata

    # 5c. General skills — set selected to BASIC
    general_mastery = dict(char.db.general_skill_mastery_levels or {})
    selected_general_skills = state.get("selected_general_skills", set())
    for skey in selected_general_skills:
        general_mastery[skey] = MasteryLevel.BASIC.value
    char.db.general_skill_mastery_levels = general_mastery
    char.general_skill_pts_available -= len(selected_general_skills)

    # 5d. Apply starting recipes (merges with existing for remort)
    starting_recipes = state.get("selected_starting_recipes", {})
    if starting_recipes:
        recipe_book = dict(char.db.recipe_book or {})
        for skill_key, recipe_key in starting_recipes.items():
            recipe_book[recipe_key] = True
        char.db.recipe_book = recipe_book

    # 5e. Apply starting spells (learned vs granted based on class)
    starting_spells = state.get("selected_starting_spells", {})
    granted_schools = state.get("_granted_spell_schools", set())
    auto_granted = state.get("_auto_granted_spells", [])
    spellbook = dict(char.db.spellbook or {})
    granted = dict(char.db.granted_spells or {})
    # User-selected spells (mage schools — one per school, learned)
    for school_key, spell_key in starting_spells.items():
        if school_key in granted_schools:
            granted[spell_key] = True
        else:
            spellbook[spell_key] = True
    # Auto-granted spells (cleric/paladin — all basic spells, granted)
    for spell_key in auto_granted:
        granted[spell_key] = True
    char.db.spellbook = spellbook
    char.db.granted_spells = granted

    # 6. Apply extra language selections (Common + racial already set by at_taking_race)
    extra_langs = state.get("selected_extra_languages", set())
    if extra_langs:
        langs = set(char.db.languages or set())
        langs.update(extra_langs)
        char.db.languages = langs

    # 7. Set current HP to effective max (includes CON modifier)
    char.hp = char.effective_hp_max


def node_create(caller, raw_input, **kwargs):
    state = _get_chargen(caller)
    is_remort = state.get("is_remort", False)

    if is_remort:
        # Remort — rebuild existing character
        char = state["character"]
        _apply_chargen_to_character(char, state)

        caller.ndb._chargen = None
        caller.msg(
            f"\n|g{char.key} has been reborn!|n\n"
            f"Remort #{state.get('num_remorts', 1)} complete.\n"
            f"Use |wic {char.key}|n to enter the game."
        )
    else:
        # New character creation
        name = state["char_name"]
        session = state.get("session")
        ip = session.address if session else ""

        new_char, errors = caller.create_character(key=name, ip=ip)

        if errors:
            caller.msg(f"|rCharacter creation failed: {errors}|n")
            return None

        if not new_char:
            caller.msg("|rCharacter creation failed unexpectedly.|n")
            return None

        _apply_chargen_to_character(new_char, state)

        caller.ndb._chargen = None
        caller.msg(
            f"\n|gCharacter '{new_char.key}' created successfully!|n\n"
            f"Use |wic {new_char.key}|n to enter the game."
        )

    # Exit menu
    return None
