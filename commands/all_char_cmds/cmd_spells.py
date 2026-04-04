"""
Spells command — display known and memorised spells.

Usage:
    spells
"""

from evennia import Command

from commands.command import FCMCommandMixin
from world.spells.registry import SPELL_REGISTRY


class CmdSpells(FCMCommandMixin, Command):
    """
    Display your known and memorised spells.

    Usage:
        spells
    """

    key = "spells"
    aliases = ["sp", "spe"]
    locks = "cmd:all()"
    help_category = "Magic"
    allow_while_sleeping = True

    def func(self):
        caller = self.caller

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

        # Group by school (use school_key for string representation)
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
                # tier may be a _SaverDict if db data is nested —
                # extract the mastery int if so
                if hasattr(tier, "get"):
                    tier = tier.get("mastery", 0)
                cost = spell.mana_cost.get(tier, "?")
                lines.append(
                    f"  {spell.name} (mana: {cost}){mem_marker}{grant_marker}"
                )
            lines.append("")

        caller.msg("\n".join(lines).rstrip())
