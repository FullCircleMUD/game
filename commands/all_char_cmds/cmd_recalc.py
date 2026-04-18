"""
Recalc command — force a nuclear stat recalculate on a character.

Admin/builder tool for fixing desynced stats and debugging.
Rebuilds all Tier 2 stats from base values + equipment + active effects.

Usage:
    recalc          — recalculate your own stats
    recalc <target> — recalculate another character's stats
"""

from evennia import Command


class CmdRecalc(Command):
    """
    Force-recalculate all stats from scratch.

    Usage:
        recalc
        recalc <target>

    Rebuilds all Tier 2 stats (ability scores, AC, hit/damage bonuses,
    resistances, etc.) from base values + worn equipment + active spell
    effects. Useful for fixing stat desync or verifying consistency.

    Admin only.
    """

    key = "recalc"
    aliases = []
    locks = "cmd:perm(Admin)"
    help_category = "Admin"

    def func(self):
        caller = self.caller
        if self.args.strip():
            target = caller.search(self.args.strip())
            if not target:
                return
        else:
            target = caller

        if not hasattr(target, '_recalculate_stats'):
            caller.msg(f"{target.key} does not support stat recalculation.")
            return

        # Snapshot before
        before = {
            "armor_class": target.armor_class,
            "strength": target.strength,
            "dexterity": target.dexterity,
            "constitution": target.constitution,
            "intelligence": target.intelligence,
            "wisdom": target.wisdom,
            "charisma": target.charisma,
            "total_hit_bonus": target.total_hit_bonus,
            "total_damage_bonus": target.total_damage_bonus,
            "attacks_per_round": target.attacks_per_round,
        }

        target._recalculate_stats()

        # Report changes
        changes = []
        for stat, old_val in before.items():
            new_val = getattr(target, stat)
            if old_val != new_val:
                changes.append(f"  {stat}: {old_val} -> {new_val}")

        if changes:
            caller.msg(f"|yRecalculated {target.key}'s stats. Changes:|n\n"
                        + "\n".join(changes))
        else:
            caller.msg(f"|gRecalculated {target.key}'s stats. No changes — stats were consistent.|n")
