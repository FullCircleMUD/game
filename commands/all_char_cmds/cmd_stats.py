import re

from evennia import Command

from commands.command import FCMCommandMixin


def _visible_len(s):
    """Return length of string excluding Evennia color codes."""
    s2 = s.replace("||", "\x00")
    s2 = re.sub(r'\|[a-zA-Z]', '', s2)
    return len(s2)


def _pad(s, width):
    """Left-align string *s* in *width* chars, accounting for color codes."""
    return s + " " * max(0, width - _visible_len(s))


_PIPE = "|c|||n"
_W = 60  # inner width


def _stat_row(label, base, effective, note=""):
    """Build a row: | Label        Base   Effective  (delta)  Note |

    The delta is shown only when both values are numeric and differ:
    green when the effective value is higher, red when it is lower.
    """
    base_str = str(base)
    eff_str = str(effective)

    try:
        delta = int(effective) - int(base)
    except (TypeError, ValueError):
        delta = 0

    if delta:
        sign = "+" if delta > 0 else ""
        color = "|g" if delta > 0 else "|r"
        diff = f" {color}({sign}{delta})|n"
    else:
        diff = ""

    note_str = f"  |x{note}|n" if note else ""

    cell = f" {_pad(label, 18)} {base_str:>5s}   {eff_str:>5s}{diff}{note_str}"
    return f"{_PIPE}{_pad(cell, _W)}{_PIPE}"


class CmdStats(FCMCommandMixin, Command):
    """
    View the base and effective values of your character's stats.

    Shows how equipment, spells, and ability score modifiers change
    your stats from their base values. For a quick overview, use |wscore|n.

    Usage:
        stats
    """

    key = "stats"
    locks = "cmd:all()"
    help_category = "Character"
    allow_while_sleeping = True

    def func(self):
        caller = self.caller

        border = "|c+" + "=" * _W + "+|n"
        thin = "|c+" + "-" * _W + "+|n"

        def header(text):
            return f"{_PIPE} |w{_pad(text, _W - 2)}|n {_PIPE}"

        def col_header():
            cell = f" {'':18s} {'Base':>5s}   {'Eff.':>5s}"
            return f"{_PIPE}{_pad(cell, _W)}{_PIPE}"

        lines = [""]
        lines.append(border)
        lines.append(header("Stat Breakdown — Base vs Effective"))
        lines.append(border)

        # ── Ability Scores ───────────────────────────────────
        lines.append(header("Ability Scores"))
        lines.append(col_header())
        lines.append(thin)

        for ab in ("strength", "dexterity", "constitution",
                    "intelligence", "wisdom", "charisma"):
            base = getattr(caller, f"base_{ab}", 0)
            curr = getattr(caller, ab, 0)
            mod = caller.get_attribute_bonus(curr)
            mod_sign = "+" if mod >= 0 else ""
            lines.append(_stat_row(
                ab.capitalize(),
                str(base), str(curr),
                note=f"mod {mod_sign}{mod}",
            ))

        lines.append(border)

        # ── Vitals ───────────────────────────────────────────
        lines.append(header("Vitals"))
        lines.append(col_header())
        lines.append(thin)

        hp_base = caller.hp_max
        hp_eff = caller.effective_hp_max
        con_mod = caller.get_attribute_bonus(caller.constitution)
        lvl = caller.get_level()
        hp_note = f"CON mod {'+' if con_mod >= 0 else ''}{con_mod} x Lvl {lvl}"
        lines.append(_stat_row("HP Max", str(hp_base), str(hp_eff), note=hp_note))
        lines.append(_stat_row("Mana Max", str(caller.mana_max), str(caller.mana_max)))
        lines.append(_stat_row("Move Max", str(caller.move_max), str(caller.move_max)))

        lines.append(border)

        # ── Combat ───────────────────────────────────────────
        lines.append(header("Combat"))
        lines.append(col_header())
        lines.append(thin)

        lines.append(_stat_row(
            "Armor Class",
            str(caller.base_armor_class), str(caller.effective_ac),
        ))
        lines.append(_stat_row(
            "Crit Threshold",
            str(caller.base_crit_threshold), str(caller.effective_crit_threshold),
        ))

        init_equip = caller.initiative_bonus
        dex_mod = caller.get_attribute_bonus(caller.dexterity)
        init_eff = caller.effective_initiative
        lines.append(_stat_row(
            "Initiative",
            str(init_equip), str(init_eff),
            note=f"DEX mod {'+' if dex_mod >= 0 else ''}{dex_mod}",
        ))

        lines.append(_stat_row(
            "Attacks/Round",
            str(caller.attacks_per_round), str(caller.effective_attacks_per_round),
            note="weapon mastery",
        ))

        wis_mod = caller.get_attribute_bonus(caller.wisdom)
        lines.append(_stat_row(
            "Perception",
            str(caller.perception_bonus), str(caller.effective_perception_bonus),
            note=f"WIS mod {'+' if wis_mod >= 0 else ''}{wis_mod}",
        ))

        lines.append(_stat_row(
            "Hit Bonus",
            str(caller.total_hit_bonus), str(caller.effective_hit_bonus),
            note="ability + weapon",
        ))

        lines.append(_stat_row(
            "Damage Bonus",
            str(caller.total_damage_bonus), str(caller.effective_damage_bonus),
            note="ability + weapon",
        ))

        lines.append(border)
        lines.append("")
        caller.msg("\n".join(lines))
