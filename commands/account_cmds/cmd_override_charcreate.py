"""
Override of Evennia's default charcreate command.

Instead of the simple `charcreate <name> [= desc]`, this launches a guided
EvMenu wizard that walks the player through race, class, alignment, ability
score point buy, and name selection before creating the character.
"""

from evennia.commands.default.account import CmdCharCreate as DefaultCmdCharCreate
from evennia.utils.evmenu import EvMenu

from subscriptions.utils import is_subscribed


class CmdCharCreate(DefaultCmdCharCreate):
    """
    create a new character

    Usage:
        charcreate
        cc

    Launches the guided character creation wizard. You will choose
    a race, class, alignment, allocate ability scores, and pick a
    name for your new character.
    """

    key = "charcreate"
    aliases = ["cc"]
    locks = "cmd:pperm(Player) and is_ooc()"
    help_category = "System"
    account_caller = True

    def func(self):
        account = self.account

        if not is_subscribed(account):
            self.msg(
                "|rYour subscription has expired.|n\n"
                "Use |wsubscribe|n to renew."
            )
            return

        # Check character slot availability
        if slot_err := account.check_available_slots():
            self.msg(slot_err)
            return

        # Initialize chargen state
        account.ndb._chargen = {"session": self.session}

        # Launch the character creation menu
        EvMenu(
            account,
            "server.main_menu.chargen.chargen_menu",
            startnode="node_race_select",
            cmd_on_exit="look",
        )
