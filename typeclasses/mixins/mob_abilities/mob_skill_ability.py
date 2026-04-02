"""
MobSkillAbility — base classes for command-based mob abilities.

Mob abilities are mixins that give combat mobs access to player skill
commands (bash, stab, dodge, etc.). Each ability mixin:

1. Merges a cmdset containing the skill command onto the mob
2. Registers the command in ``db.combat_commands`` for AI selection
3. Sets the mastery level in the correct mastery dict so the command
   scales identically to a player using the same skill

From the combat engine's perspective, a mob using bash is
indistinguishable from a player using bash — same command, same
mastery dispatch, same cooldowns, same resolution.

Two subclasses handle the two mastery dict types:

- **MobClassSkillAbility** — writes to ``db.class_skill_mastery_levels``
  (bash, pummel, stab, protect, taunt, etc.)
- **MobGeneralSkillAbility** — writes to ``db.general_skill_mastery_levels``
  (dodge, assist, etc.)

Usage::

    class BashAbility(MobClassSkillAbility):
        ability_key = "bash"
        ability_cmdset = CmdSetMobBash
        ability_weight = 30
        ability_mastery = MasteryLevel.SKILLED

    class KoboldWarrior(BashAbility, HumanoidWearslotsMixin, AggressiveMob):
        pass
"""

from enums.mastery_level import MasteryLevel


class MobSkillAbility:
    """
    Base mixin for command-based mob abilities.

    Subclass attributes to set:
        ability_key     — command name, e.g. "bash"
        ability_cmdset  — CmdSet class containing the command
        ability_weight  — AI selection weight (default 30)
        ability_mastery — default MasteryLevel (overridable via spawn attrs)
        mastery_dict    — which db dict to write mastery to (set by subclass)
    """

    ability_key = None
    ability_cmdset = None
    ability_weight = 30
    ability_mastery = MasteryLevel.SKILLED
    mastery_dict = None  # set by MobClassSkillAbility or MobGeneralSkillAbility

    def at_object_creation(self):
        super().at_object_creation()
        if self.ability_cmdset:
            self.cmdset.add(self.ability_cmdset)
        if self.ability_key and self.mastery_dict:
            # Register for AI command selection
            combat_commands = self.db.combat_commands or {}
            combat_commands[self.ability_key] = {
                "weight": self.ability_weight,
            }
            self.db.combat_commands = combat_commands
            # Set mastery in correct dict
            levels = getattr(self.db, self.mastery_dict) or {}
            levels[self.ability_key] = self.ability_mastery.value
            setattr(self.db, self.mastery_dict, levels)


class MobClassSkillAbility(MobSkillAbility):
    """Command-based ability using class skill mastery.

    Writes mastery to ``db.class_skill_mastery_levels``.
    Used for: bash, pummel, stab, protect, taunt, offence, defence,
    retreat, frenzy, turn, etc.
    """

    mastery_dict = "class_skill_mastery_levels"


class MobGeneralSkillAbility(MobSkillAbility):
    """Command-based ability using general skill mastery.

    Writes mastery to ``db.general_skill_mastery_levels``.
    Used for: dodge, assist, etc.
    """

    mastery_dict = "general_skill_mastery_levels"
