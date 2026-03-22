"""
Remort command — allows a max-level character to reset to level 1
while keeping learned knowledge and gaining a permanent perk.

Uses a yield-based Y/N confirmation followed by perk selection,
then launches the chargen EvMenu for a full character rebuild.
"""

from evennia.commands.command import Command
from evennia.utils.evmenu import EvMenu

from server.main_menu.remort.remort_perks import get_available_perks, apply_perk

MAX_LEVEL = 40


class CmdRemort(Command):
    """
    Remort your character back to level 1.

    Usage:
        remort

    When you reach level 40, you can remort to reset your character
    back to level 1. You will keep learned spells and recipes, gain
    a permanent perk, and unlock new races and classes.

    All equipment and currency is transferred to your account bank.
    """

    key = "remort"
    locks = "cmd:all()"
    help_category = "Character"

    def func(self):
        yield from self._do_remort()

    def _do_remort(self):
        caller = self.caller

        # --- Validation ---
        if caller.total_level < MAX_LEVEL:
            caller.msg(
                f"|rYou must be level {MAX_LEVEL} to remort. "
                f"You are level {caller.total_level}.|n"
            )
            return

        # --- Warning + Y/N confirmation ---
        remort_num = caller.num_remorts + 1
        answer = yield (
            f"\n|r--- REMORT WARNING ---|n"
            f"\n"
            f"\nYou are about to remort. This will:"
            f"\n"
            f"\n|rRESET:|n"
            f"\n  - Your level back to 1"
            f"\n  - All ability scores, HP, mana, and move"
            f"\n  - All XP and class progression"
            f"\n  - All skill mastery (weapon, class, general)"
            f"\n  - All deity-granted spells"
            f"\n"
            f"\n|rTRANSFER TO BANK:|n"
            f"\n  - All equipment and inventory"
            f"\n  - All gold and resources"
            f"\n"
            f"\n|gKEEP:|n"
            f"\n  - Learned spells (from scrolls)"
            f"\n  - Learned recipes"
            f"\n  - Your character name"
            f"\n"
            f"\n|gGAIN:|n"
            f"\n  - Remort count: {caller.num_remorts} → {remort_num}"
            f"\n  - A permanent remort perk"
            f"\n  - Access to new races and classes"
            f"\n"
            f"\nAre you sure? Y/[N]"
        )

        if answer.lower() not in ("y", "yes"):
            caller.msg("Remort cancelled.")
            return

        # --- Perk selection ---
        available_perks = get_available_perks(caller)

        if available_perks:
            # Build perk display
            perk_text = "\n|gChoose a permanent perk:|n\n"
            for i, perk in enumerate(available_perks, 1):
                current = getattr(caller, perk["attribute"], 0)
                new_val = min(current + perk["increment"], perk["cap"])
                perk_text += (
                    f"\n  |w{i}|n. {perk['name']}"
                    f"\n     {perk['desc']}"
                    f"\n     Current: {current} → {new_val} (cap: {perk['cap']})"
                )
            perk_text += "\n\nEnter a number:"

            while True:
                choice = yield perk_text

                try:
                    idx = int(choice.strip()) - 1
                    if 0 <= idx < len(available_perks):
                        chosen_perk = available_perks[idx]
                        success, msg = apply_perk(caller, chosen_perk)
                        if success:
                            caller.msg(f"\n{msg}")
                            break
                        else:
                            perk_text = f"\n|r{msg}|n\nEnter a number:"
                    else:
                        perk_text = f"\n|rInvalid choice. Enter 1-{len(available_perks)}.|n\nEnter a number:"
                except ValueError:
                    perk_text = f"\n|rEnter a number (1-{len(available_perks)}).|n\nEnter a number:"
        else:
            caller.msg("\n|yAll perks are at maximum — no perk to choose.|n")

        # --- Strip the character ---
        account = caller.account
        bank = account.db.bank

        if not bank:
            caller.msg("|rError: No account bank found. Contact an admin.|n")
            return

        caller.at_remort(bank)

        caller.msg(
            f"\n|g{'=' * 50}|n"
            f"\n|gRemort complete! You are now remort #{caller.num_remorts}.|n"
            f"\n|gYour items and currency have been transferred to your bank.|n"
            f"\n|g{'=' * 50}|n"
            f"\n\nLaunching character rebuild..."
        )

        # --- Launch remort chargen ---
        session = caller.sessions.get()[0] if caller.sessions.get() else None

        account.ndb._chargen = {
            "session": session,
            "is_remort": True,
            "character": caller,
            "num_remorts": caller.num_remorts,
            "point_buy": caller.point_buy,
        }

        EvMenu(
            account,
            "server.main_menu.chargen.chargen_menu",
            startnode="node_race_select",
            cmd_on_exit="look",
        )
