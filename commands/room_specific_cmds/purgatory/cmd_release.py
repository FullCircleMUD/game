"""
Release command — early release from purgatory for 50 gold.

Deducts from the player's bank (ACCOUNT) balance. If insufficient,
tells them to wait for the automatic 1-minute release.

Usage:
    release
"""

from evennia import Command

from commands.room_specific_cmds.bank.cmd_balance import ensure_bank

RELEASE_COST = 50


class CmdRelease(Command):
    """
    Pay for early release from purgatory.

    Usage:
        release

    Costs 50 gold from your bank balance.
    """

    key = "release"
    locks = "cmd:all()"
    help_category = "Death"

    def func(self):
        caller = self.caller

        if not getattr(caller, "in_purgatory", False):
            caller.msg("You are not in purgatory.")
            return

        account = caller.account
        if not account:
            caller.msg("You need to be logged in.")
            return

        bank = ensure_bank(account)
        bank_gold = bank.get_gold()

        if bank_gold < RELEASE_COST:
            caller.msg(
                f"Early release costs {RELEASE_COST} gold from your bank. "
                f"You only have {bank_gold} gold in the bank. "
                "Wait for the automatic release."
            )
            return

        # Debit from bank to sink
        bank.return_gold_to_sink(RELEASE_COST)

        caller.msg(f"{RELEASE_COST} gold deducted from your bank account.")

        # Release the character to their home (bound cemetery / Limbo fallback)
        destination = caller.home or caller._get_limbo()
        caller.move_to(destination, quiet=True, move_type="teleport")
        caller.msg("You feel yourself drawn back to the world of the living...")
        caller._dying = False  # allow future deaths
