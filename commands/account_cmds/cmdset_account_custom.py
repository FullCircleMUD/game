"""
Custom Account-level CmdSet.

Inherits Evennia's default AccountCmdSet and replaces CmdCharCreate and
CmdCharDelete with our custom versions. Also overrides several Evennia
defaults to recategorise them for the help system.
"""

from evennia import CmdSet
from commands.account_cmds.cmd_override_ic import CmdIC
from commands.account_cmds.cmd_override_ooc import CmdOOC
from commands.account_cmds.cmd_override_sessions import CmdSessions
from commands.account_cmds.cmd_override_who import CmdWho
from commands.account_cmds.cmd_override_option import CmdOption
from commands.account_cmds.cmd_override_password import CmdPassword
from commands.account_cmds.cmd_override_newpassword import CmdNewPassword
from commands.account_cmds.cmd_override_colortest import CmdColorTest
from commands.account_cmds.cmd_override_quell import CmdQuell
from commands.account_cmds.cmd_override_style import CmdStyle
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
from commands.account_cmds.cmd_recover_nft import CmdRecoverNft
from commands.account_cmds.cmd_botsetup import CmdBotSetup
from commands.account_cmds.cmd_botlist import CmdBotList
from commands.account_cmds.cmd_botreset import CmdBotReset
from commands.account_cmds.cmd_wipe_spawns import CmdWipeSpawns
from commands.account_cmds.cmd_spawn_report import CmdSpawnReport
from commands.account_cmds.cmd_run_saturation import CmdRunSaturation
from commands.account_cmds.cmd_run_spawns import CmdRunSpawns
from commands.account_cmds.cmd_run_telemetry import CmdRunTelemetry
from commands.account_cmds.cmd_broadcast import CmdBroadcast
from commands.account_cmds.cmd_subscribe import CmdSubscribe
from commands.account_cmds.cmd_rebuild_world import CmdRebuildWorld
from commands.account_cmds.cmd_rebuild_test import CmdRebuildTest
from commands.account_cmds.cmd_rebuild_zone import CmdRebuildZone
from commands.account_cmds.cmd_service_report import CmdServiceRun


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

        # Subscription
        self.add(CmdSubscribe())

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
        self.add(CmdRecoverNft())
        self.add(CmdBotSetup())
        self.add(CmdBotList())
        self.add(CmdBotReset())
        self.add(CmdWipeSpawns())
        self.add(CmdSpawnReport())
        self.add(CmdRunSaturation())
        self.add(CmdRunSpawns())
        self.add(CmdRunTelemetry())
        self.add(CmdBroadcast())
        self.add(CmdRebuildWorld())
        self.add(CmdRebuildTest())
        self.add(CmdRebuildZone())
        self.add(CmdServiceRun())
