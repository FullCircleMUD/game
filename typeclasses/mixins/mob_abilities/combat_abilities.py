"""
Concrete command-based mob abilities.

Each ability is a mixin composable onto any combat mob. It brings:
1. A cmdset containing the player command (same CmdBash players use)
2. An AI registry entry with weight for combat tick selection
3. A mastery level written to the correct mastery dict

All abilities inherit from MobClassSkillAbility or MobGeneralSkillAbility
which handle the boilerplate. Concrete abilities just declare their
key, cmdset, weight, and default mastery.

Usage::

    class KoboldWarrior(BashAbility, HumanoidWearslotsMixin, AggressiveMob):
        pass
"""

from evennia import CmdSet

from enums.mastery_level import MasteryLevel
from typeclasses.mixins.mob_abilities.mob_skill_ability import (
    MobClassSkillAbility,
    MobGeneralSkillAbility,
)


# ================================================================== #
#  Cmdset wrappers — tiny cmdsets importing the player command
# ================================================================== #

class CmdSetMobBash(CmdSet):
    key = "MobBash"
    priority = 1
    mergetype = "Union"

    def at_cmdset_creation(self):
        from commands.class_skill_cmdsets.class_skill_cmds.cmd_bash import CmdBash
        self.add(CmdBash())


class CmdSetMobPummel(CmdSet):
    key = "MobPummel"
    priority = 1
    mergetype = "Union"

    def at_cmdset_creation(self):
        from commands.class_skill_cmdsets.class_skill_cmds.cmd_pummel import CmdPummel
        self.add(CmdPummel())


class CmdSetMobStab(CmdSet):
    key = "MobStab"
    priority = 1
    mergetype = "Union"

    def at_cmdset_creation(self):
        from commands.class_skill_cmdsets.class_skill_cmds.cmd_backstab import CmdBackstab
        self.add(CmdBackstab())


class CmdSetMobDodge(CmdSet):
    key = "MobDodge"
    priority = 1
    mergetype = "Union"

    def at_cmdset_creation(self):
        from commands.class_skill_cmdsets.class_skill_cmds.cmd_dodge import CmdDodge
        self.add(CmdDodge())


class CmdSetMobTaunt(CmdSet):
    key = "MobTaunt"
    priority = 1
    mergetype = "Union"

    def at_cmdset_creation(self):
        from commands.class_skill_cmdsets.class_skill_cmds.cmd_taunt import CmdTaunt
        self.add(CmdTaunt())


class CmdSetMobProtect(CmdSet):
    key = "MobProtect"
    priority = 1
    mergetype = "Union"

    def at_cmdset_creation(self):
        from commands.class_skill_cmdsets.class_skill_cmds.cmd_protect import CmdProtect
        self.add(CmdProtect())


# ================================================================== #
#  Class skill abilities (db.class_skill_mastery_levels)
# ================================================================== #

class BashAbility(MobClassSkillAbility):
    """Bash — knock an enemy prone. Warrior skill."""

    ability_key = "bash"
    ability_cmdset = CmdSetMobBash
    ability_weight = 30
    ability_mastery = MasteryLevel.SKILLED


class PummelAbility(MobClassSkillAbility):
    """Pummel — stun an enemy. Warrior/paladin skill."""

    ability_key = "pummel"
    ability_cmdset = CmdSetMobPummel
    ability_weight = 20
    ability_mastery = MasteryLevel.SKILLED


class StabAbility(MobClassSkillAbility):
    """Stab — sneak attack with bonus damage dice. Thief/ninja skill."""

    ability_key = "stab"
    ability_cmdset = CmdSetMobStab
    ability_weight = 35
    ability_mastery = MasteryLevel.SKILLED


class TauntAbility(MobClassSkillAbility):
    """Taunt — provoke a target into attacking you. Warrior/paladin skill."""

    ability_key = "taunt"
    ability_cmdset = CmdSetMobTaunt
    ability_weight = 15
    ability_mastery = MasteryLevel.SKILLED


class ProtectAbility(MobClassSkillAbility):
    """Protect — intercept attacks aimed at an ally. Warrior/paladin skill."""

    ability_key = "protect"
    ability_cmdset = CmdSetMobProtect
    ability_weight = 20
    ability_mastery = MasteryLevel.SKILLED


# ================================================================== #
#  General skill abilities (db.general_skill_mastery_levels)
# ================================================================== #

class DodgeAbility(MobGeneralSkillAbility):
    """Dodge — sacrifice attack for disadvantage on incoming hits."""

    ability_key = "dodge"
    ability_cmdset = CmdSetMobDodge
    ability_weight = 25
    ability_mastery = MasteryLevel.BASIC
