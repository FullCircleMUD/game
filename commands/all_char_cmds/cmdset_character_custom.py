from evennia import CmdSet

from commands.general_skill_cmds.cmdset_general_skills import CmdSetGeneralSkills
from commands.all_char_cmds.cmdset_socials import CmdSetSocials

# overrides of Evennia default commands
from commands.all_char_cmds.cmd_override_pose import CmdPose
from commands.all_char_cmds.cmd_override_nick import CmdNick
from commands.all_char_cmds.cmd_override_setdesc import CmdSetDesc
from commands.all_char_cmds.cmd_override_access import CmdAccess

# overrides of default commands
from commands.all_char_cmds.cmd_override_get import CmdGet
from commands.all_char_cmds.cmd_override_drop import CmdDrop
from commands.all_char_cmds.cmd_override_give import CmdGive
from commands.all_char_cmds.cmd_override_look import CmdLook
from commands.all_char_cmds.cmd_override_inventory import CmdInventory
from commands.all_char_cmds.cmd_go import CmdGo
from commands.all_char_cmds.cmd_override_help import CmdHelp

# new custom commands
from commands.all_char_cmds.cmd_skills import CmdSkills
from commands.all_char_cmds.cmd_stats import CmdStats
from commands.all_char_cmds.cmd_score import CmdScore
from commands.all_char_cmds.cmd_where import CmdWhere
from commands.all_char_cmds.cmd_fly import CmdFly
from commands.all_char_cmds.cmd_swim import CmdSwim
from commands.all_char_cmds.cmd_climb import CmdClimb
from commands.all_char_cmds.cmd_switch import CmdSwitch
from commands.all_char_cmds.cmd_quit_ic import CmdQuitIC
from commands.all_char_cmds.cmd_junk import CmdJunk
from commands.all_char_cmds.cmd_put import CmdPut
from commands.all_char_cmds.cmd_eat import CmdEat
from commands.all_char_cmds.cmd_hunger import CmdHunger
from commands.all_char_cmds.cmd_languages import CmdLanguages
from commands.all_char_cmds.cmd_weight import CmdWeight
from commands.all_char_cmds.cmd_learn import CmdLearn
from commands.all_char_cmds.cmd_recipes import CmdRecipes
from commands.all_char_cmds.cmd_quaff import CmdQuaff
from commands.all_char_cmds.cmd_say import CmdSay
from commands.all_char_cmds.cmd_whisper import CmdWhisper
from commands.all_char_cmds.cmd_shout import CmdShout
from commands.all_char_cmds.cmd_remort import CmdRemort
from commands.all_char_cmds.cmd_quests import CmdQuests
from commands.all_char_cmds.cmd_hide import CmdHide
from commands.all_char_cmds.cmd_trade import CmdTrade
from commands.all_char_cmds.cmd_toggle import CmdToggle
from commands.all_char_cmds.cmd_afk import CmdAfk
from commands.all_char_cmds.cmd_prompt import CmdPrompt
from commands.all_char_cmds.cmd_roomdesc import CmdRoomDesc
from commands.all_char_cmds.cmd_exits import CmdExits
from commands.all_char_cmds.cmd_posture import CmdSit, CmdRest, CmdSleep, CmdStand, CmdWake
from commands.all_char_cmds.cmd_recalc import CmdRecalc

# world object interaction commands
from commands.all_char_cmds.cmd_open import CmdOpen
from commands.all_char_cmds.cmd_close import CmdClose
from commands.all_char_cmds.cmd_unlock import CmdUnlock
from commands.all_char_cmds.cmd_lock import CmdLock
from commands.all_char_cmds.cmd_search import CmdSearch
from commands.all_char_cmds.cmd_show import CmdShow
from commands.all_char_cmds.cmd_read import CmdRead
from commands.all_char_cmds.cmd_recall import CmdRecall
from commands.all_char_cmds.cmd_light import CmdLight, CmdExtinguish
from commands.all_char_cmds.cmd_refuel import CmdRefuel

# magic commands
from commands.all_char_cmds.cmd_cast import CmdCast
from commands.all_char_cmds.cmd_transcribe import CmdTranscribe
from commands.all_char_cmds.cmd_memorise import CmdMemorise, CmdForget
from commands.all_char_cmds.cmd_spells import CmdSpells

# equipment commands
from commands.all_char_cmds.cmd_wear import CmdWear
from commands.all_char_cmds.cmd_wield import CmdWield
from commands.all_char_cmds.cmd_hold import CmdHold
from commands.all_char_cmds.cmd_remove import CmdRemove
from commands.all_char_cmds.cmd_equipment import CmdEquipment
from commands.all_char_cmds.cmd_owned import CmdOwned
from commands.all_char_cmds.cmd_loot import CmdLoot
from commands.all_char_cmds.cmd_follow import CmdFollow, CmdUnfollow, CmdNofollow, CmdDisband, CmdGroup
from commands.all_char_cmds.cmd_gtell import CmdGtell
from commands.all_char_cmds.cmd_attack import CmdAttack
from commands.all_char_cmds.cmd_flee import CmdFlee
from commands.all_char_cmds.cmd_smite import CmdSmite
from commands.all_char_cmds.cmd_shield import CmdShield
from commands.all_char_cmds.cmd_wimpy import CmdWimpy
from commands.all_char_cmds.cmd_join import CmdJoin
from commands.all_char_cmds.cmd_consider import CmdConsider
from commands.all_char_cmds.cmd_scan import CmdScan
from commands.all_char_cmds.cmd_diagnose import CmdDiagnose
from commands.all_char_cmds.cmd_areas import CmdAreas
from commands.all_char_cmds.cmd_pet import CmdPet

# tutorial commands
from commands.all_char_cmds.cmd_tutorial_entry import (
    CmdEnterTutorial, CmdLeaveTutorial
)

# =====================================================================
# Command set so the commands cen be added to the character cmdset.
# =====================================================================

class CmdSetCharacterCustom(CmdSet):

    key = "CmdSetCharacterCustom"

    def at_cmdset_creation(self):

        self.add(CmdSetGeneralSkills)
        self.add(CmdSetSocials)

        # DEFAULT COMMANDS AVAILABLE FOR OVERRIDE
        #CmdHome
        self.add(CmdHelp())
        self.add(CmdLook())
        self.add(CmdNick())
        self.add(CmdInventory())
        self.add(CmdSetDesc())
        self.add(CmdGet())
        self.add(CmdDrop())
        self.add(CmdGive())
        self.add(CmdSay())
        self.add(CmdWhisper())
        self.add(CmdShout())
        self.add(CmdPose())
        self.add(CmdAccess())


         # CUSTOM COMMANDS
        self.add(CmdQuitIC())
        self.add(CmdStats())
        self.add(CmdScore())
        self.add(CmdSkills())
        self.add(CmdFly())
        self.add(CmdSwim())
        self.add(CmdClimb())
        self.add(CmdSwitch())
        self.add(CmdJunk())
        self.add(CmdPut())
        self.add(CmdEat())
        self.add(CmdHunger())
        self.add(CmdLanguages())
        self.add(CmdWeight())
        self.add(CmdWear())
        self.add(CmdWield())
        self.add(CmdHold())
        self.add(CmdRemove())
        self.add(CmdEquipment())
        self.add(CmdOwned())
        self.add(CmdLoot())
        self.add(CmdRemort())
        self.add(CmdQuests())
        self.add(CmdWhere())

        # combat
        self.add(CmdAttack())
        self.add(CmdJoin())
        self.add(CmdFlee())
        self.add(CmdWimpy())
        self.add(CmdConsider())
        self.add(CmdScan())
        self.add(CmdDiagnose())
        self.add(CmdAreas())
        self.add(CmdSmite())
        self.add(CmdShield())

        # group / follow / pets
        self.add(CmdFollow())
        self.add(CmdUnfollow())
        self.add(CmdNofollow())
        self.add(CmdDisband())
        self.add(CmdGroup())
        self.add(CmdGtell())
        self.add(CmdPet())

        # stealth
        self.add(CmdHide())

        # trade
        self.add(CmdTrade())

        # preferences
        self.add(CmdToggle())
        self.add(CmdAfk())
        self.add(CmdPrompt())
        self.add(CmdRoomDesc())
        self.add(CmdExits())

        # movement
        self.add(CmdGo())

        # posture
        self.add(CmdSit())
        self.add(CmdRest())
        self.add(CmdSleep())
        self.add(CmdStand())
        self.add(CmdWake())

        # world object interaction
        self.add(CmdOpen())
        self.add(CmdClose())
        self.add(CmdUnlock())
        self.add(CmdLock())
        self.add(CmdSearch())
        self.add(CmdShow())

        # library book commands
        self.add(CmdRead())
        self.add(CmdRecall())

        # light source commands
        self.add(CmdLight())
        self.add(CmdExtinguish())
        self.add(CmdRefuel())

        # crafting commands
        self.add(CmdLearn())
        self.add(CmdRecipes())
        self.add(CmdQuaff())

        # magic commands
        self.add(CmdCast())
        self.add(CmdTranscribe())
        self.add(CmdMemorise())
        self.add(CmdForget())
        self.add(CmdSpells())

        # tutorial
        self.add(CmdEnterTutorial())
        self.add(CmdLeaveTutorial())

        # admin
        self.add(CmdRecalc())
