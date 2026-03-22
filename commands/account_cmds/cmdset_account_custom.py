"""
Custom Account-level CmdSet.

Inherits Evennia's default AccountCmdSet and replaces CmdCharCreate and
CmdCharDelete with our custom versions. Also overrides several Evennia
defaults to recategorise them for the help system.
"""

from evennia import CmdSet
from evennia.commands.default.account import (
    CmdIC as _CmdIC,
    CmdOOC as _CmdOOC,
    CmdSessions as _CmdSessions,
    CmdWho as _CmdWho,
    CmdOption as _CmdOption,
    CmdPassword as _CmdPassword,
    CmdColorTest as _CmdColorTest,
    CmdQuell as _CmdQuell,
    CmdStyle as _CmdStyle,
)
from evennia.commands.default.admin import CmdNewPassword as _CmdNewPassword
from commands.account_cmds.cmd_override_charcreate import CmdCharCreate
from commands.account_cmds.cmd_override_chardelete import CmdCharDelete
from commands.account_cmds.cmd_bank import CmdBank
from commands.account_cmds.cmd_wallet import CmdWallet
from commands.account_cmds.cmd_import import CmdImport
from commands.account_cmds.cmd_export import CmdExport
from commands.account_cmds.cmd_sync_nfts import CmdSyncNfts
from commands.account_cmds.cmd_reconcile import CmdReconcile
from commands.account_cmds.cmd_amm_check import CmdAMMCheck
from commands.account_cmds.cmd_economy import CmdEconomy
from commands.account_cmds.cmd_sync_reserves import CmdSyncReserves
from commands.account_cmds.cmd_spawn_poc import CmdSpawnPoc


# ── Thin overrides of Evennia defaults (category / lock only) ───────

class CmdIC(_CmdIC):
    help_category = "System"

class CmdOOC(_CmdOOC):
    help_category = "System"

class CmdSessions(_CmdSessions):
    help_category = "System"

class CmdWho(_CmdWho):
    """
    List who is currently online.

    Usage:
        who

    Shows online players with their character name, level, class, and race.
    """

    help_category = "Communication"

    def func(self):
        import time
        import evennia
        from evennia.utils import utils

        account = self.account
        session_list = evennia.SESSION_HANDLER.get_sessions()
        session_list = sorted(session_list, key=lambda o: o.account.key)

        is_admin = account.check_permstring(
            "Developer"
        ) or account.check_permstring("Admins")

        if is_admin:
            table = self.styled_table(
                "|wName", "|wLvl", "|wClass", "|wRace", "|wIdle", "|wLocation",
            )
        else:
            table = self.styled_table(
                "|wName", "|wLvl", "|wClass", "|wRace", "|wIdle",
            )

        count = 0
        for session in session_list:
            if not session.logged_in:
                continue

            count += 1
            char = session.get_puppet()

            # Idle time
            idle_secs = time.time() - session.cmd_last_visible
            if idle_secs < 120:
                idle_str = ""
            elif idle_secs < 3600:
                idle_str = f"{int(idle_secs // 60)}m"
            else:
                idle_str = f"{int(idle_secs // 3600)}h"

            if char:
                name = utils.crop(char.key, width=20)

                level = getattr(char, "total_level", 0)

                classes = getattr(char.db, "classes", None) or {}
                if classes:
                    class_parts = [
                        f"{ck.capitalize()} {cd.get('level', 0)}"
                        for ck, cd in classes.items()
                    ]
                    class_str = " / ".join(class_parts)
                else:
                    class_str = "No class"

                race = getattr(char, "race", None)
                race_str = (
                    race.value if hasattr(race, "value") else str(race)
                ).capitalize() if race else "-"

                location = char.location.key if char and char.location else "-"
            else:
                # OOC — not puppeting
                name = f"{session.get_account().key} |x(OOC)|n"
                level = "-"
                class_str = "-"
                race_str = "-"
                location = "-"

            if is_admin:
                table.add_row(name, level, class_str, race_str, idle_str, location)
            else:
                table.add_row(name, level, class_str, race_str, idle_str)

        is_one = count == 1
        self.msg(
            "|wPlayers Online|n\n%s\n%s player%s online."
            % (table, "One" if is_one else count, "" if is_one else "s")
        )

class CmdOption(_CmdOption):
    help_category = "System"

class CmdPassword(_CmdPassword):
    # Only superuser (account #1) can change passwords — FCM uses wallet signatures
    locks = "cmd:id(1)"
    help_category = "System"

class CmdNewPassword(_CmdNewPassword):
    # Only superuser (account #1) can reset passwords — FCM uses wallet signatures
    locks = "cmd:id(1)"
    help_category = "System"

class CmdColorTest(_CmdColorTest):
    help_category = "System"

class CmdQuell(_CmdQuell):
    help_category = "System"

class CmdStyle(_CmdStyle):
    help_category = "System"


class CmdSetAccountCustom(CmdSet):

    key = "CmdSetAccountCustom"

    def at_cmdset_creation(self):

        # Evennia default overrides (recategorised)
        self.add(CmdIC())
        self.add(CmdOOC())
        self.add(CmdSessions())
        self.add(CmdWho())
        self.add(CmdOption())
        self.add(CmdPassword())
        self.add(CmdNewPassword())
        self.add(CmdColorTest())
        self.add(CmdQuell())
        self.add(CmdStyle())

        # Character management (OOC only)
        self.add(CmdCharCreate())
        self.add(CmdCharDelete())

        # Blockchain commands (OOC only)
        self.add(CmdBank())
        self.add(CmdWallet())
        self.add(CmdImport())
        self.add(CmdExport())

        # Admin commands (superuser only)
        self.add(CmdSyncNfts())
        self.add(CmdReconcile())
        self.add(CmdAMMCheck())
        self.add(CmdEconomy())
        self.add(CmdSyncReserves())
        self.add(CmdSpawnPoc())
