import re

from evennia import Command

from commands.command import FCMCommandMixin
from utils.experience_table import get_xp_for_next_level


# ── Helpers ──────────────────────────────────────────────────────

def _visible_len(s):
    """Return length of string excluding Evennia color codes like |c |n |w etc.
    Counts || (escaped pipe) as 1 visible character."""
    # First replace || with a single-char placeholder, then strip color codes
    s2 = s.replace("||", "\x00")
    s2 = re.sub(r'\|[a-zA-Z]', '', s2)
    return len(s2)


def _pad(s, width):
    """Left-align string *s* in *width* chars, accounting for color codes."""
    visible = _visible_len(s)
    return s + " " * max(0, width - visible)


def _vital_color(current, maximum):
    """Return color code based on vital percentage."""
    if maximum <= 0:
        return "|w"
    ratio = current / maximum
    if ratio > 0.75:
        return "|g"
    elif ratio > 0.25:
        return "|y"
    return "|r"


def _hunger_color(hunger_level):
    """Return color code for hunger severity."""
    val = hunger_level.value if hasattr(hunger_level, "value") else hunger_level
    if val >= 5:
        return "|g"
    elif val >= 3:
        return "|y"
    return "|r"


# Column widths (visual characters, excluding border pipes)
_C1 = 17   # Vitals
_C2 = 15   # Abilities
_C3 = 12   # Combat
_C4 = 30   # Resistances / Vulnerabilities


_PIPE = "|c|||n"  # cyan literal pipe then reset: |c (cyan) + || (escaped pipe) + |n (reset)


def _row(c1, c2, c3, c4):
    """Build one body row with 4 columns separated by cyan pipes."""
    return (
        f"{_PIPE}{_pad(c1, _C1)}"
        f"{_PIPE}{_pad(c2, _C2)}"
        f"{_PIPE}{_pad(c3, _C3)}"
        f"{_PIPE}{_pad(c4, _C4)}"
        f"{_PIPE}"
    )


def _header_line(left, right):
    """Build a header row: left-aligned text, right-aligned text, 76 inner chars."""
    vis_left = _visible_len(left)
    vis_right = _visible_len(right)
    gap = max(1, 76 - vis_left - vis_right)
    return f"{_PIPE} {left}{' ' * gap}{right} {_PIPE}"


class CmdScore(FCMCommandMixin, Command):
    """
    View your character sheet — a compact overview of your character.

    Usage:
        score

    Shows identity, vitals, ability scores, combat modifiers,
    resistances, vulnerabilities, conditions, hunger, and encumbrance
    in a single screen.
    """

    key = "score"
    aliases = ["sc", "sco"]
    locks = "cmd:all()"
    help_category = "Character"
    allow_while_sleeping = True

    def func(self):
        caller = self.caller

        # ── Gather data ──────────────────────────────────────────
        name = caller.key[:40]
        race = caller.race
        race_str = (race.value if hasattr(race, "value") else str(race)).capitalize()
        align_str = getattr(caller, "alignment_label", "Neutral")

        classes = caller.db.classes or {}
        if classes:
            class_parts = [
                f"{ck.capitalize()} {cd.get('level', 0)}"
                for ck, cd in classes.items()
            ]
            class_line = " / ".join(class_parts)
        else:
            class_line = "|xNo class -- visit a guildmaster!|n"

        total_lvl = caller.total_level
        xp = caller.experience_points
        xp_next = get_xp_for_next_level(total_lvl)
        xp_str = f"XP {xp:,}/{xp_next:,}"

        hp, hp_max = caller.hp, caller.effective_hp_max
        mp, mp_max = caller.mana, caller.mana_max
        mv, mv_max = caller.move, caller.move_max

        abilities = []
        for ab in ("strength", "dexterity", "constitution",
                    "intelligence", "wisdom", "charisma"):
            curr = getattr(caller, ab, 0)
            mod = caller.get_attribute_bonus(curr)
            abilities.append((ab[:3].upper(), curr, mod))

        ac = caller.effective_ac
        crit = caller.effective_crit_threshold
        init = caller.effective_initiative
        att = caller.attacks_per_round

        # Resistances / Vulnerabilities
        resistances_dict = getattr(caller, "damage_resistances", {})
        res_items = []
        vul_items = []
        for dmg_type in sorted(resistances_dict.keys()):
            capped = caller.get_resistance(dmg_type)
            dname = dmg_type.capitalize()
            if capped > 0:
                res_items.append(f"  {dname} {capped}%")
            elif capped < 0:
                vul_items.append(f"  {dname} {abs(capped)}%")

        # Build right column content (up to 6 rows)
        # Always show headers; "None" if no entries
        right = []
        right.append(" |wResist:|n")
        if res_items:
            right.extend(f" {r}" for r in res_items)
        else:
            right.append("   None")
        right.append(" |wVulner:|n")
        if vul_items:
            right.extend(f" {v}" for v in vul_items)
        else:
            right.append("   None")
        while len(right) < 6:
            right.append("")
        # Cap at 6 — overflow goes to the conditions/stats command
        right = right[:6]

        # Conditions
        conditions = getattr(caller, "conditions", {})
        cond_names = sorted(
            n.replace("_", " ").capitalize() for n in conditions.keys()
        ) if conditions else []

        # Hunger
        hunger = caller.hunger_level
        hunger_name = hunger.get_name(hunger.value)
        h_color = _hunger_color(hunger)

        # Carry
        weight = caller.current_weight_carried
        max_cap = caller.get_max_capacity()

        levels_to_spend = caller.levels_to_spend

        # ── Build output ─────────────────────────────────────────
        border = "|c+" + "=" * 76 + "+|n"
        lines = [""]
        lines.append(border)

        # Header: name | race + alignment
        lines.append(_header_line(
            f"|w{name}|n",
            f"{race_str} | {align_str}"
        ))

        # Header: classes | level + XP
        lines.append(_header_line(
            class_line,
            f"Lvl {total_lvl} | {xp_str}"
        ))

        lines.append(border)

        # ── Body (6 rows) ────────────────────────────────────────
        hp_c = _vital_color(hp, hp_max)
        mp_c = _vital_color(mp, mp_max)
        mv_c = _vital_color(mv, mv_max)
        init_sign = "+" if init >= 0 else ""

        def _ab(i):
            """Format ability cell: NAME: score (modifier)."""
            name, score, mod = abilities[i]
            sign = "+" if mod >= 0 else ""
            return f" {name}: {score:2d} ({sign}{mod})"

        lines.append(_row(
            f" {hp_c}HP: {hp:3d}/{hp_max:<3d}|n",
            _ab(0),
            f" AC:  {ac:4d}",
            right[0],
        ))
        lines.append(_row(
            f" {mp_c}MP: {mp:3d}/{mp_max:<3d}|n",
            _ab(1),
            f" Crit: {crit:3d}",
            right[1],
        ))
        lines.append(_row(
            f" {mv_c}MV: {mv:3d}/{mv_max:<3d}|n",
            _ab(2),
            f" Init: {init_sign}{init}",
            right[2],
        ))
        pos = getattr(caller, "position", "standing").capitalize()
        pos_colors = {
            "Standing": "|g", "Sitting": "|y",
            "Resting": "|y", "Sleeping": "|B", "Fighting": "|r",
        }
        pos_c = pos_colors.get(pos, "|w")
        lines.append(_row(
            f" {pos_c}{pos}|n",
            _ab(3),
            f" Att:  {att:3d}",
            right[3],
        ))
        lines.append(_row(
            f" {h_color}{hunger_name}|n",
            _ab(4),
            "",
            right[4],
        ))
        lines.append(_row(
            f" {weight:.0f}/{max_cap:.0f} kg",
            _ab(5),
            "",
            right[5],
        ))

        lines.append(border)

        # ── Footer ───────────────────────────────────────────────
        if cond_names:
            cond_str = "|wConditions:|n " + ", ".join(cond_names)
            if _visible_len(cond_str) > 74:
                cond_str = cond_str[:71] + "..."
        else:
            cond_str = "|wConditions:|n None"
        lines.append(f"{_PIPE} {_pad(cond_str, 74)} {_PIPE}")

        if levels_to_spend > 0:
            s = "s" if levels_to_spend > 1 else ""
            lvl_msg = f"|y{levels_to_spend} level{s} to spend -- visit a guildmaster!|n"
            lines.append(f"{_PIPE} {_pad(lvl_msg, 74)} {_PIPE}")

        lines.append(border)

        lines.append("")
        caller.msg("\n".join(lines))
