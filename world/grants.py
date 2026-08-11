"""
Knowledge grants — mastery-derived spells and recipes.

Some knowledge is *learned* (transcribed scrolls, bought recipes) and is
permanent. Some is *granted*: it follows from skill mastery, and every
character holding that mastery is entitled to it. Granted knowledge is a
pure function of character state, so nothing has to remember which grants
were issued — this module just makes storage agree with the function.

    from world.grants import reconcile_grants
    gained = reconcile_grants(character)
    # {"spells": ["purify"], "recipes": []}

Two rules decide what auto-grants:

    Spells   — by class. A class with ``grants_spells`` (cleric, paladin)
               receives every spell in its schools at or below the
               character's mastery in that school.
    Recipes  — by skill. A skill listed in AUTO_GRANT_RECIPE_SKILLS hands
               out its whole catalogue by mastery tier. Enchanting is the
               only one; every other craft uses scrolls and trainers.

Reconciling is idempotent and additive — safe to call from anywhere, and
never removes. Downgrade is handled by remort clearing the granted stores
outright, because they hold quest and racial grants too, with nothing to
tell them apart.

See docs/knowledge-grants.md for the design and the trigger points.
"""

from enums.skills_enum import skills
from typeclasses.actors.char_classes import get_char_class
from world.recipes import get_recipes_for_skill
from world.spells.registry import get_spells_for_school


# Crafting skills whose recipes are granted by mastery rather than learned
# from scrolls. Adding a scroll-less craft is a one-line change here.
AUTO_GRANT_RECIPE_SKILLS = frozenset({skills.ENCHANTING})


def get_skill_mastery(character, skill):
    """Return a character's mastery (0-5) in a skill, from whichever pool
    holds it — general skills are available to all classes, class skills
    are not.
    """
    if skill.classes_available_to == {"all"}:
        levels = character.db.general_skill_mastery_levels or {}
        return int(levels.get(skill.value, 0) or 0)

    entry = (character.db.class_skill_mastery_levels or {}).get(skill.value, 0)
    # Entries are dict-shaped ({"mastery": 1, "classes": [...]}); bare ints
    # are tolerated so a partially-built character can't crash a login.
    if hasattr(entry, "get"):
        return int(entry.get("mastery", 0) or 0)
    return int(entry or 0)


def _granting_class_keys(character):
    """Class keys the character holds that grant their spells."""
    granting = set()
    for class_key in (character.db.classes or {}):
        charclass = get_char_class(class_key)
        if charclass and charclass.grants_spells:
            granting.add(class_key)
    return granting


def _eligible_spell_schools(character):
    """Yield (skill, mastery) for every spell school this character is
    granted from — a school of a class they hold that grants spells, in
    which they have at least BASIC mastery.
    """
    granting = _granting_class_keys(character)
    if not granting:
        return []

    eligible = []
    for skill in skills:
        available = skill.classes_available_to
        if available == {"all"} or not (granting & available):
            continue
        if not get_spells_for_school(skill):
            continue
        mastery = get_skill_mastery(character, skill)
        if mastery > 0:
            eligible.append((skill, mastery))
    return eligible


def _eligible_recipe_skills(character):
    """Yield (skill, mastery) for every auto-granting craft the character
    has mastery in.
    """
    eligible = []
    for skill in sorted(AUTO_GRANT_RECIPE_SKILLS, key=lambda s: s.value):
        mastery = get_skill_mastery(character, skill)
        if mastery > 0:
            eligible.append((skill, mastery))
    return eligible


def _reconcile(character, eligible, catalogue, min_mastery_of, knows, store_attr):
    """Add everything the character is owed and doesn't already have.

    Args:
        eligible: [(skill, mastery), ...] the character grants from
        catalogue: skill -> {key: entry} of everything that skill offers
        min_mastery_of: entry -> int tier the entry requires
        knows: key -> bool, True if already known by any route
        store_attr: name of the `db` dict to write into

    Returns:
        sorted list of newly granted keys
    """
    if not eligible:
        return []

    store = dict(getattr(character.db, store_attr) or {})
    gained = []

    for skill, mastery in eligible:
        for key, entry in catalogue(skill).items():
            if min_mastery_of(entry) > mastery:
                continue
            if key in store or knows(key):
                continue
            store[key] = True
            gained.append(key)

    if gained:
        setattr(character.db, store_attr, store)
    return sorted(gained)


def grant_spells(character):
    """Grant every spell this character's mastery entitles them to.

    Returns the sorted list of newly granted spell keys.
    """
    return _reconcile(
        character,
        _eligible_spell_schools(character),
        catalogue=get_spells_for_school,
        min_mastery_of=lambda spell: spell.min_mastery.value,
        knows=character.knows_spell,
        store_attr="granted_spells",
    )


def grant_recipes(character):
    """Grant every recipe this character's mastery entitles them to.

    Returns the sorted list of newly granted recipe keys.
    """
    return _reconcile(
        character,
        _eligible_recipe_skills(character),
        catalogue=get_recipes_for_skill,
        min_mastery_of=lambda recipe: recipe["min_mastery"].value,
        knows=character.knows_recipe,
        store_attr="granted_recipes",
    )


def reconcile_grants(character):
    """Bring a character's granted knowledge up to date with their mastery.

    Idempotent — an already-correct character is unchanged and both lists
    come back empty.

    Returns:
        {"spells": [key, ...], "recipes": [key, ...]} of what was added
    """
    return {
        "spells": grant_spells(character),
        "recipes": grant_recipes(character),
    }


def format_gains(gained):
    """Turn a reconcile_grants() result into player-facing lines."""
    from world.recipes import get_recipe
    from world.spells.registry import get_spell

    lines = []
    for key in gained.get("spells", []):
        spell = get_spell(key)
        name = spell.name if spell else key
        lines.append(f"|g*** You have gained the spell {name}! ***|n")
    for key in gained.get("recipes", []):
        recipe = get_recipe(key)
        name = recipe["name"] if recipe else key
        lines.append(f"|g*** You have gained the recipe for {name}! ***|n")
    return lines
