"""
Inspection Templates — shared formatted-report builders for actors and items.

These are pure functions that take a game object + a mastery tier and return
either a formatted text block or a (success, result_dict) tuple ready for
multi-perspective spell/command output.

Used by:
    - Identify spell (items)
    - Augur spell (actors)
    - Holy Insight spell (actors + divine sight appendix) — future
    - Bard `identify` command (both actors and items)
    - Any future system that wants to display actor/item info (tooltips,
      shop previews, examine, etc.)

All functions are stateless — no class, no self, no side effects. Import
from anywhere:

    from utils.inspection_templates import inspect_actor, inspect_item
"""

from enums.mastery_level import MasteryLevel


# ================================================================== #
#  Actor mastery gate
# ================================================================== #

# Level thresholds for actor identification.
# (max_level, required_tier) — checked in order.
_LEVEL_TIER_THRESHOLDS = [
    (5, 1),    # levels 1-5 → BASIC
    (15, 2),   # levels 6-15 → SKILLED
    (25, 3),   # levels 16-25 → EXPERT
    (35, 4),   # levels 26-35 → MASTER
]
# levels 36+ → GM (5)


def required_tier_for_actor(target_level):
    """Return the minimum mastery tier needed to identify an actor."""
    for threshold, tier in _LEVEL_TIER_THRESHOLDS:
        if target_level <= threshold:
            return tier
    return 5


# ================================================================== #
#  Top-level entry points
# ================================================================== #

def inspect_actor(caster, target, tier):
    """
    Build a dynamic stat template for an actor (mob or PC).

    Returns (success, result) where result is either a message dict
    (on success or partial-success) or a string (on hard failure like
    PvP gate).
    """
    from typeclasses.actors.character import FCMCharacter

    is_pc = isinstance(target, FCMCharacter)

    # PvP room check for PCs
    if is_pc and target != caster:
        room = caster.location
        if not getattr(room, "allow_pvp", False):
            return (
                False,
                "You can only identify other players in PvP areas.",
            )

    # Level-based mastery gate
    target_level = target.get_level()
    required = required_tier_for_actor(target_level)
    if tier < required:
        # Mana consumed — you tried and failed
        return (True, {
            "first": (
                f"|cYou study {target.key} intently but the creature "
                f"is too powerful for you to discern its nature.|n"
            ),
            "second": None,
            "third": f"|c{caster.key} studies {target.key} intently.|n",
        })

    # Build the inspection output
    lines = [f"|w--- Identify: {target.key} ---|n"]

    if is_pc:
        _build_pc_header(target, lines)
    else:
        _build_mob_header(target, lines)

    _build_vitals(target, lines)
    _build_ability_scores(target, lines)

    if is_pc:
        _build_pc_combat(target, lines)
    else:
        _build_mob_combat(target, lines)

    _build_resistances(target, lines)
    _build_conditions(target, lines)
    _build_effects(target, lines)

    if is_pc:
        _build_memorised_spells(target, lines)

    identify_text = "\n".join(lines)
    return (True, {
        "first": identify_text,
        "second": None,
        "third": f"|c{caster.key} studies {target.key} intently.|n",
    })


def inspect_item(caster, target, tier):
    """
    Build a dynamic property template for an NFT item.

    Returns (success, result_dict). Non-NFT objects get a sassy one-liner.
    """
    from typeclasses.items.base_nft_item import BaseNFTItem

    if not isinstance(target, BaseNFTItem):
        # Mundane objects — sassy one-liner, mana consumed
        name = target.key
        return (True, {
            "first": (
                f"|cYou study {name} intently... "
                f"{name} is {name}. 'Nuf said.|n"
            ),
            "second": None,
            "third": f"|c{caster.key} studies {name} intently.|n",
        })

    from typeclasses.items.weapons.weapon_nft_item import WeaponNFTItem
    from typeclasses.items.holdables.holdable_nft_item import HoldableNFTItem
    from typeclasses.items.wearables.wearable_nft_item import WearableNFTItem
    from typeclasses.items.consumables.potion_nft_item import PotionNFTItem
    from typeclasses.items.consumables.spell_scroll_nft_item import SpellScrollNFTItem
    from typeclasses.items.consumables.crafting_recipe_nft_item import CraftingRecipeNFTItem
    from typeclasses.items.containers.container_nft_item import ContainerNFTItem

    # Item mastery gate — some items require higher mastery to identify
    required = getattr(target, "identify_mastery_gate", 1)
    if tier < required:
        return (True, {
            "first": (
                f"|cYou study {target.key} closely but its properties "
                f"elude your understanding.|n"
            ),
            "second": None,
            "third": f"|c{caster.key} studies {target.key} closely.|n",
        })

    lines = [f"|w--- Identify: {target.key} ---|n"]
    desc = target.db.desc
    if desc:
        lines.append(desc)

    # Most specific first (weapon/holdable inherit from wearable)
    if isinstance(target, WeaponNFTItem):
        _build_weapon_info(target, lines)
    elif isinstance(target, HoldableNFTItem):
        _build_holdable_info(target, lines)
    elif isinstance(target, WearableNFTItem):
        _build_wearable_info(target, lines)
    elif isinstance(target, PotionNFTItem):
        _build_potion_info(target, lines)
    elif isinstance(target, SpellScrollNFTItem):
        _build_scroll_info(target, lines)
    elif isinstance(target, CraftingRecipeNFTItem):
        _build_recipe_info(target, lines)
    elif isinstance(target, ContainerNFTItem):
        _build_container_info(target, lines)
    else:
        lines.append("|cType:|n Item")

    _build_item_weight(target, lines)
    _build_item_restrictions(target, lines)

    identify_text = "\n".join(lines)
    return (True, {
        "first": identify_text,
        "second": None,
        "third": f"|c{caster.key} studies {target.key} closely.|n",
    })


# ================================================================== #
#  Actor template builders
# ================================================================== #

def _build_pc_header(target, lines):
    """Race and class info for PCs."""
    race_name = "Unknown"
    if hasattr(target, "race") and target.race:
        race_name = getattr(target.race, "display_name", str(target.race))
    class_str = target.get_class_string() if hasattr(target, "get_class_string") else ""
    lines.append(f"|cRace:|n {race_name}   |cClasses:|n {class_str}")


def _build_mob_header(target, lines):
    """Level and size info for mobs."""
    level = target.get_level()
    size = getattr(target, "size", "medium")
    if size:
        size = str(size).capitalize()
    lines.append(f"|cLevel:|n {level}   |cSize:|n {size}")


def _build_vitals(target, lines):
    """HP, Mana, Move, AC."""
    hp = getattr(target, "hp", 0)
    hp_max = getattr(target, "effective_hp_max", getattr(target, "hp_max", 0))
    mana = getattr(target, "mana", 0)
    mana_max = getattr(target, "mana_max", 0)
    move = getattr(target, "move", 0)
    move_max = getattr(target, "move_max", 0)
    ac = getattr(target, "effective_ac", getattr(target, "armor_class", 10))
    lines.append("|cVitals:|n")
    lines.append(
        f"  HP: {hp}/{hp_max}   Mana: {mana}/{mana_max}   "
        f"Move: {move}/{move_max}   AC: {ac}"
    )


def _build_ability_scores(target, lines):
    """Six ability scores with modifiers."""
    lines.append("|cAbility Scores:|n")
    stats = [
        ("STR", "strength"), ("DEX", "dexterity"), ("CON", "constitution"),
        ("INT", "intelligence"), ("WIS", "wisdom"), ("CHA", "charisma"),
    ]
    row1 = []
    row2 = []
    for i, (label, attr) in enumerate(stats):
        score = getattr(target, attr, 10)
        mod = target.get_attribute_bonus(score)
        sign = "+" if mod >= 0 else ""
        entry = f"{label}: {score:>2} ({sign}{mod})"
        if i < 3:
            row1.append(entry)
        else:
            row2.append(entry)
    lines.append("  " + "  ".join(row1))
    lines.append("  " + "  ".join(row2))


def _build_mob_combat(target, lines):
    """Damage dice and attacks for mobs."""
    damage_dice = getattr(target, "damage_dice", "1d2")
    attack_msg = getattr(target, "attack_message", "attacks")
    apr = getattr(target, "effective_attacks_per_round",
                  getattr(target, "attacks_per_round", 1))
    lines.append("|cCombat:|n")
    lines.append(
        f"  Damage: {damage_dice} ({attack_msg})   Attacks/Round: {apr}"
    )


def _build_pc_combat(target, lines):
    """Wielded weapon for PCs."""
    from combat.combat_utils import get_weapon
    from typeclasses.items.weapons.unarmed_weapon import UnarmedWeapon
    weapon = get_weapon(target)
    if weapon and not isinstance(weapon, UnarmedWeapon):
        lines.append(f"|cWielding:|n {weapon.key}")
    else:
        lines.append("|cWielding:|n Unarmed")


def _build_resistances(target, lines):
    """Damage resistances and vulnerabilities."""
    resists = getattr(target, "damage_resistances", {}) or {}
    non_zero = {k: v for k, v in resists.items() if v != 0}
    if non_zero:
        parts = []
        for dtype, value in sorted(non_zero.items()):
            capped = max(-75, min(75, value))
            suffix = " (vulnerable)" if capped < 0 else ""
            parts.append(f"{dtype.capitalize()}: {capped}%{suffix}")
        lines.append(f"|cResistances:|n {', '.join(parts)}")
    else:
        lines.append("|cResistances:|n None")


def _build_conditions(target, lines):
    """Active condition flags."""
    conds = getattr(target, "conditions", {}) or {}
    if conds:
        names = sorted(k.upper() for k in conds if conds[k] > 0)
        lines.append(f"|cConditions:|n {', '.join(names) if names else 'None'}")
    else:
        lines.append("|cConditions:|n None")


def _build_effects(target, lines):
    """Active named effects."""
    effects = getattr(target, "active_effects", {}) or {}
    if effects:
        names = sorted(effects.keys())
        lines.append(f"|cActive Effects:|n {', '.join(names)}")
    else:
        lines.append("|cActive Effects:|n None")


def _build_memorised_spells(target, lines):
    """Memorised spells for PCs."""
    if not hasattr(target, "get_memorised_spells"):
        lines.append("|cMemorised Spells:|n None")
        return
    spells = target.get_memorised_spells()
    if spells:
        names = sorted(s.name for s in spells.values())
        lines.append(f"|cMemorised Spells:|n {', '.join(names)}")
    else:
        lines.append("|cMemorised Spells:|n None")


# ================================================================== #
#  Item template builders
# ================================================================== #

def _build_weapon_info(target, lines):
    """Weapon stats: type, speed, damage table, durability, effects."""
    wtype = getattr(target, "weapon_type", "melee")
    dmg_type = getattr(target, "damage_type", None)
    dmg_type_name = dmg_type.value.capitalize() if dmg_type else "Physical"
    lines.append(f"|cType:|n Weapon ({wtype.capitalize()}, {dmg_type_name})")

    speed = getattr(target, "speed", 1.0)
    two_handed = "Yes" if getattr(target, "two_handed", False) else "No"
    finesse = "Yes" if getattr(target, "is_finesse", False) else "No"
    lines.append(
        f"|cSpeed:|n {speed}   |cTwo-Handed:|n {two_handed}   "
        f"|cFinesse:|n {finesse}"
    )

    # Damage table by mastery level
    damage = getattr(target, "damage", {}) or {}
    if damage:
        lines.append("|cDamage:|n")
        row1 = []
        row2 = []
        for i, ml in enumerate(MasteryLevel):
            dice = damage.get(ml)
            if dice:
                entry = f"{ml.name.replace('_', ' ').title()}: {dice}"
                if i < 3:
                    row1.append(entry)
                else:
                    row2.append(entry)
        if row1:
            lines.append("  " + "  ".join(row1))
        if row2:
            lines.append("  " + "  ".join(row2))

    _build_durability(target, lines)
    _build_wear_effects_line(target, lines)


def _build_wearable_info(target, lines):
    """Armor/clothing/jewelry: slot, durability, effects."""
    slot_str = _format_slot(getattr(target, "wearslot", None))
    lines.append(f"|cType:|n Armor ({slot_str})")
    _build_durability(target, lines)
    _build_wear_effects_line(target, lines)


def _build_holdable_info(target, lines):
    """Shield/orb/torch: durability, effects."""
    lines.append("|cType:|n Holdable")
    _build_durability(target, lines)
    _build_wear_effects_line(target, lines)


def _build_potion_info(target, lines):
    """Potion: effects + duration."""
    lines.append("|cType:|n Potion")
    effects = getattr(target, "potion_effects", []) or []
    parts = []
    for eff in effects:
        etype = eff.get("type", "")
        if etype == "restore":
            stat = eff.get("stat", "hp").upper()
            if "dice" in eff:
                parts.append(f"Restores {stat} ({eff['dice']})")
            else:
                parts.append(f"Restores {stat} ({eff.get('value', 0)})")
        elif etype == "stat_bonus":
            stat = eff.get("stat", "").replace("_", " ").title()
            val = eff.get("value", 0)
            sign = "+" if val >= 0 else ""
            parts.append(f"{sign}{val} {stat}")
        elif etype == "condition":
            parts.append(eff.get("condition", "").replace("_", " ").title())
    if parts:
        lines.append(f"|cEffects:|n {', '.join(parts)}")
    else:
        lines.append("|cEffects:|n None")
    duration = getattr(target, "duration", 0) or 0
    if duration <= 0:
        lines.append("|cDuration:|n Instant")
    elif duration >= 60:
        minutes = duration // 60
        lines.append(f"|cDuration:|n {minutes} minute{'s' if minutes != 1 else ''}")
    else:
        lines.append(f"|cDuration:|n {duration} seconds")


def _build_scroll_info(target, lines):
    """Spell scroll: spell name + school."""
    lines.append("|cType:|n Spell Scroll")
    spell_key = getattr(target, "spell_key", "") or ""
    if spell_key:
        from world.spells.registry import SPELL_REGISTRY
        spell = SPELL_REGISTRY.get(spell_key)
        if spell:
            school_name = spell.school.value.replace("_", " ").title() if spell.school else ""
            lines.append(f"|cSpell:|n {spell.name} ({school_name})")
        else:
            lines.append(f"|cSpell:|n {spell_key}")
    else:
        lines.append("|cSpell:|n Unknown")


def _build_recipe_info(target, lines):
    """Crafting recipe: recipe key."""
    lines.append("|cType:|n Crafting Recipe")
    recipe_key = getattr(target, "recipe_key", "") or ""
    if recipe_key:
        display = recipe_key.replace("_", " ").title()
        lines.append(f"|cRecipe:|n {display}")
    else:
        lines.append("|cRecipe:|n Unknown")


def _build_container_info(target, lines):
    """Container: capacity + durability."""
    lines.append("|cType:|n Container")
    capacity = getattr(target, "max_container_capacity_kg", 0)
    if capacity:
        lines.append(f"|cCapacity:|n {capacity} kg")
    _build_durability(target, lines)


# ================================================================== #
#  Shared item helpers
# ================================================================== #

def _build_durability(target, lines):
    """Durability line for equipment."""
    max_dur = getattr(target, "max_durability", 0) or 0
    if max_dur > 0:
        dur = getattr(target, "durability", max_dur)
        lines.append(f"|cDurability:|n {dur}/{max_dur}")
    else:
        lines.append("|cDurability:|n Unbreakable")


def _build_wear_effects_line(target, lines):
    """Format wear_effects into a single Effects line."""
    effects = getattr(target, "wear_effects", []) or []
    parts = _format_wear_effects(effects)
    if parts:
        lines.append(f"|cEffects:|n {', '.join(parts)}")


def _format_wear_effects(effects):
    """Convert wear_effects dicts to human-readable strings."""
    parts = []
    for eff in effects:
        etype = eff.get("type", "")
        if etype == "stat_bonus":
            stat = eff.get("stat", "").replace("_", " ").title()
            val = eff.get("value", 0)
            sign = "+" if val >= 0 else ""
            parts.append(f"{sign}{val} {stat}")
        elif etype == "damage_resistance":
            dtype = eff.get("damage_type", "").capitalize()
            val = eff.get("value", 0)
            parts.append(f"{dtype} Resistance: {val}%")
        elif etype == "condition":
            cond = eff.get("condition", "").replace("_", " ").title()
            parts.append(cond)
        elif etype == "hit_bonus":
            wtype = eff.get("weapon_type", "").replace("_", " ").title()
            val = eff.get("value", 0)
            sign = "+" if val >= 0 else ""
            parts.append(f"{sign}{val} Hit ({wtype})")
        elif etype == "damage_bonus":
            wtype = eff.get("weapon_type", "").replace("_", " ").title()
            val = eff.get("value", 0)
            sign = "+" if val >= 0 else ""
            parts.append(f"{sign}{val} Damage ({wtype})")
    return parts


def _format_slot(wearslot):
    """Format wearslot enum value(s) to a display string."""
    if wearslot is None:
        return "Unknown"
    if isinstance(wearslot, list):
        if wearslot:
            val = wearslot[0].value if hasattr(wearslot[0], "value") else str(wearslot[0])
        else:
            return "Unknown"
    else:
        val = wearslot.value if hasattr(wearslot, "value") else str(wearslot)
    return val.replace("_", " ").title()


def _build_item_weight(target, lines):
    """Weight line."""
    weight = getattr(target, "weight", 0) or 0
    lines.append(f"|cWeight:|n {weight} kg")


def _build_item_restrictions(target, lines):
    """Item usage restrictions from ItemRestrictionMixin."""
    if not getattr(target, "is_restricted", False):
        lines.append("|cRestrictions:|n None")
        return
    parts = []
    req = getattr(target, "required_classes", []) or []
    if req:
        names = ", ".join(c.capitalize() for c in req)
        parts.append(f"Requires: {names}")
    exc = getattr(target, "excluded_classes", []) or []
    if exc:
        names = ", ".join(c.capitalize() for c in exc)
        parts.append(f"Excluded: {names}")
    min_lvl = getattr(target, "min_total_level", 0) or 0
    if min_lvl:
        parts.append(f"Min Level: {min_lvl}")
    min_attrs = getattr(target, "min_attributes", {}) or {}
    for attr, val in min_attrs.items():
        parts.append(f"Min {attr.upper()[:3]}: {val}")
    min_mastery = getattr(target, "min_mastery", {}) or {}
    for skill, lvl in min_mastery.items():
        parts.append(f"{skill.replace('_', ' ').title()}: {lvl}")
    req_races = getattr(target, "required_races", []) or []
    if req_races:
        names = ", ".join(str(r) for r in req_races)
        parts.append(f"Race: {names}")
    exc_races = getattr(target, "excluded_races", []) or []
    if exc_races:
        names = ", ".join(str(r) for r in exc_races)
        parts.append(f"Race Excluded: {names}")
    lines.append(f"|cRestrictions:|n {', '.join(parts)}" if parts else "|cRestrictions:|n None")
