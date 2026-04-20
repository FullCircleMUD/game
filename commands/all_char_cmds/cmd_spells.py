"""
Spells command — display known and memorised spells, or view spell details.

Usage:
    spells                  — list all known spells
    spells info <name>      — view detailed info about a spell (accepts aliases)
"""

from evennia import Command

from commands.command import FCMCommandMixin
from world.spells.registry import SPELL_REGISTRY


class CmdSpells(FCMCommandMixin, Command):
    """
    Display your known and memorised spells, or view spell details.

    Usage:
        spells                  — list all known spells
        spells info <name>      — view detailed info about a spell

    The info command accepts spell names or aliases (e.g. "spells info mm"
    for Magic Missile).
    """

    key = "spells"
    aliases = []
    locks = "cmd:all()"
    help_category = "Magic"
    allow_while_sleeping = True

    def func(self):
        caller = self.caller
        args = self.args.strip()

        # Handle "spells info <name>"
        if args.lower().startswith("info "):
            self._show_spell_info(caller, args[5:].strip())
            return
        if args.lower() == "info":
            caller.msg("Usage: spells info <spell name or alias>")
            return

        # Default: list all known spells
        self._list_spells(caller)

    def _list_spells(self, caller):
        """Display the full spellbook listing."""
        known = caller.get_known_spells()
        memorised = caller.get_memorised_spells()

        if not known:
            caller.msg("You don't know any spells.")
            return

        cap = caller.get_memorisation_cap()
        mem_count = len(memorised)

        lines = []
        lines.append("|y--- Spellbook ---|n")
        lines.append(f"Memory slots: {mem_count} / {cap}")
        lines.append("")
        lines.append("Type |wspells info <name>|n for details on a spell.")
        lines.append("")

        # Group by school
        schools = {}
        for key, spell in known.items():
            school_key = spell.school_key
            if school_key not in schools:
                schools[school_key] = []
            schools[school_key].append((key, spell))

        for school, spell_list in sorted(schools.items()):
            lines.append(f"|w{school.replace('_', ' ').title()}|n")
            for key, spell in sorted(spell_list, key=lambda x: x[1].name):
                mem_marker = " |g[M]|n" if key in memorised else ""
                grant_marker = " |c[G]|n" if caller.is_granted(key) else ""
                tier = spell.get_caster_tier(caller)
                if hasattr(tier, "get"):
                    tier = tier.get("mastery", 0)
                cost = spell.mana_cost.get(tier, "?")
                alias_str = f" |c[{', '.join(spell.aliases)}]|n" if spell.aliases else ""
                lines.append(
                    f"  {spell.name}{alias_str} (mana: {cost}){mem_marker}{grant_marker}"
                )
            lines.append("")

        caller.msg("\n".join(lines).rstrip())

    def _show_spell_info(self, caller, query):
        """Show detailed info about a specific spell."""
        known = caller.get_known_spells()
        if not known:
            caller.msg("You don't know any spells.")
            return

        # Match by name or alias (case-insensitive)
        query_lower = query.lower()
        match = None
        for key, spell in known.items():
            if spell.name.lower() == query_lower or key == query_lower:
                match = (key, spell)
                break
            if query_lower in [a.lower() for a in spell.aliases]:
                match = (key, spell)
                break

        if not match:
            caller.msg(
                f"You don't know a spell called '{query}'. "
                f"Type |wspells|n to see your spellbook."
            )
            return

        spell_key, spell = match
        memorised = caller.get_memorised_spells()

        lines = []

        # Header
        alias_str = f" [{', '.join(spell.aliases)}]" if spell.aliases else ""
        lines.append(f"|w=== {spell.name}{alias_str} ===|n")
        lines.append(
            f"|wSchool:|n {spell.school_key.replace('_', ' ').title()}"
        )

        # Status markers
        status = []
        if spell_key in memorised:
            status.append("|g[Memorised]|n")
        if caller.is_granted(spell_key):
            status.append("|c[Granted]|n")
        if status:
            lines.append(" ".join(status))

        lines.append("")

        # Description
        if spell.description:
            lines.append(spell.description)
            lines.append("")

        # Mechanics
        if spell.mechanics:
            lines.append("|wMechanics:|n")
            for line in spell.mechanics.strip().split("\n"):
                lines.append(f"  {line}")
            lines.append("")

        # Stats
        lines.append(
            f"|wTarget:|n {spell.target_type}  "
            f"|wRange:|n {spell.range}  "
            f"|wCooldown:|n {spell.get_cooldown()} rounds"
        )
        lines.append(
            f"|wMin mastery:|n {spell.min_mastery.name}"
        )

        # Mana cost table
        if spell.mana_cost:
            cost_strs = [f"{t}:{c}" for t, c in sorted(spell.mana_cost.items())]
            lines.append(f"|wMana by tier:|n {' '.join(cost_strs)}")

        caller.msg("\n".join(lines))
