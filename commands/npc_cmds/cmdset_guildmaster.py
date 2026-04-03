"""
Guildmaster NPC commands — guild info, join class, advance level.

The ``quest`` command is now provided by QuestGiverMixin (shared across all
quest-giving NPCs). These guild-specific commands remain here.

These commands live on the GuildmasterNPC object's CmdSet. When a player is in
the same room as a guildmaster, these commands become available. self.obj is the
guildmaster NPC.
"""

from evennia import CmdSet, Command

from commands.command import FCMCommandMixin
from enums.mastery_level import MasteryLevel


# ── CmdGuild ──

class CmdGuild(FCMCommandMixin, Command):
    """
    View guild information and your progress.

    Usage:
        guild     — show guild info, class description, requirements,
                    and your current levels/progress in this class

    Available when in the same room as a Guildmaster NPC.
    """

    key = "guild"
    aliases = ["gu"]
    locks = "cmd:all()"
    help_category = "Guild"

    def func(self):
        caller = self.caller
        guildmaster = self.obj

        if guildmaster.location != caller.location:
            caller.msg("There is no guildmaster here.")
            return

        class_key = guildmaster.guild_class
        if not class_key:
            caller.msg("This guildmaster has not been assigned a guild class.")
            return

        from typeclasses.actors.char_classes import get_char_class
        char_class = get_char_class(class_key)
        if not char_class:
            caller.msg(f"Unknown class: {class_key}")
            return

        lines = []
        lines.append(f"|w=== {char_class.display_name} Guild ===|n")
        lines.append(f"{char_class.description}")
        lines.append("")

        # Requirements
        if char_class.multi_class_requirements:
            req_strs = []
            for ability, min_score in char_class.multi_class_requirements.items():
                req_strs.append(f"{ability.name}: {min_score}")
            lines.append(f"|wAbility Requirements:|n {', '.join(req_strs)}")

        if char_class.required_alignments:
            align_strs = [a.value for a in char_class.required_alignments]
            lines.append(f"|wRequired Alignments:|n {', '.join(align_strs)}")
        elif char_class.excluded_alignments:
            align_strs = [a.value for a in char_class.excluded_alignments]
            lines.append(f"|wExcluded Alignments:|n {', '.join(align_strs)}")

        if char_class.required_races:
            lines.append(f"|wRequired Races:|n {', '.join(char_class.required_races)}")
        elif char_class.excluded_races:
            lines.append(f"|wExcluded Races:|n {', '.join(char_class.excluded_races)}")

        if char_class.min_remort > 0:
            lines.append(f"|wMinimum Remorts:|n {char_class.min_remort}")

        if char_class.prime_attribute:
            lines.append(f"|wPrime Attribute:|n {char_class.prime_attribute.name}")

        lines.append("")

        # Character's progress in this class
        classes = caller.db.classes or {}
        if class_key in classes:
            # Already a member — show progress, skip the join quest
            class_data = classes[class_key]
            class_level = class_data.get("level", 0)
            skill_pts = class_data.get("skill_pts_available", 0)
            lines.append(
                f"|wYou are a level {class_level} "
                f"{char_class.display_name}.|n"
            )
            lines.append(f"|wClass Skill Points:|n {skill_pts}")
            if caller.levels_to_spend > 0:
                lines.append(
                    f"Type |wadvance|n to spend a level in "
                    f"{char_class.display_name}."
                )
        else:
            # Not a member — show the join quest if one exists
            quest_key = guildmaster.multi_class_quest_key
            if quest_key:
                from world.quests import get_quest
                quest_class = get_quest(quest_key)
                quest_name = quest_class.name if quest_class else quest_key
                if caller.quests.is_completed(quest_key):
                    lines.append(
                        f"|wGuild Quest:|n {quest_name} |g(Completed)|n"
                    )
                elif caller.quests.has(quest_key):
                    lines.append(
                        f"|wGuild Quest:|n {quest_name} |y(In Progress)|n"
                    )
                else:
                    lines.append(
                        f"|wGuild Quest:|n {quest_name} — "
                        f"Type |wquest|n to learn more."
                    )
                lines.append("")

            lines.append(f"You are not yet a {char_class.display_name}.")
            can_take = char_class.char_can_take_class(caller)
            if can_take:
                lines.append(
                    f"You meet the requirements. Type |wjoin|n to "
                    f"become a {char_class.display_name}."
                )
            else:
                lines.append(
                    f"|rYou do not currently meet the requirements "
                    f"to join this guild.|n"
                )

        lines.append("")
        lines.append(
            f"|wTotal Level:|n {caller.total_level}  "
            f"|wLevels to Spend:|n {caller.levels_to_spend}"
        )

        caller.msg("\n".join(lines))


# ── CmdQuest — now provided by QuestGiverMixin via QuestGiverCmdSet ──
# The quest command has been moved to typeclasses/mixins/quest_giver.py
# and is shared across all quest-giving NPCs (guildmasters, shopkeepers, etc.)


# ── CmdJoin ──

class CmdJoin(FCMCommandMixin, Command):
    """
    Join this guild's class.

    Usage:
        join      — attempt to join this guild's class

    If this is your first class, you join immediately (subject to race,
    alignment, and remort requirements). For multiclassing, you must also
    meet the class's ability score requirements and complete any guild quest.

    Available when in the same room as a Guildmaster NPC.
    """

    key = "join"
    aliases = []
    locks = "cmd:all()"
    help_category = "Guild"

    def func(self):
        caller = self.caller
        guildmaster = self.obj

        if guildmaster.location != caller.location:
            caller.msg("There is no guildmaster here.")
            return

        class_key = guildmaster.guild_class
        if not class_key:
            caller.msg("This guildmaster has not been assigned a guild class.")
            return

        from typeclasses.actors.char_classes import get_char_class
        char_class = get_char_class(class_key)
        if not char_class:
            caller.msg(f"Unknown class: {class_key}")
            return

        # Already a member?
        classes = caller.db.classes or {}
        if class_key in classes:
            class_level = classes[class_key].get("level", 0)
            caller.msg(
                f"You are already a level {class_level} "
                f"{char_class.display_name}. Use |wadvance|n to "
                f"spend levels in this class."
            )
            return

        # Check race/alignment/remort requirements
        if not char_class.char_can_take_class(caller):
            caller.msg(
                f"|rYou do not meet the requirements to become a "
                f"{char_class.display_name}.|n Type |wguild|n "
                f"to see the requirements."
            )
            return

        # Check multiclass ability score requirements
        is_multiclass = len(classes) > 0
        if is_multiclass and char_class.multi_class_requirements:
            for ability, min_score in char_class.multi_class_requirements.items():
                current_score = getattr(caller, ability.value, 0)
                if current_score < min_score:
                    caller.msg(
                        f"|rYou need {ability.name} {min_score} to "
                        f"multiclass into {char_class.display_name}, "
                        f"but yours is {current_score}.|n"
                    )
                    return

        # Check multiclass quest requirement
        if is_multiclass and guildmaster.multi_class_quest_key:
            quest_key = guildmaster.multi_class_quest_key
            if not caller.quests.is_completed(quest_key):
                if not caller.quests.has(quest_key):
                    caller.msg(
                        f"|rYou must complete the guild quest before joining. "
                        f"Type |wquest|n to learn more.|n"
                    )
                else:
                    caller.msg(
                        f"|rYou have not yet completed the guild quest. "
                        f"Type |wquest|n to check your progress.|n"
                    )
                return

        # Join the class
        char_class.at_char_first_gaining_class(caller)

        caller.msg(
            f"|g*** You have joined the {char_class.display_name} "
            f"Guild! ***|n\n"
            f"You are now a level 1 {char_class.display_name}.\n"
            f"Type |wguild|n to see your progress."
        )

        if caller.location:
            caller.location.msg_contents(
                f"{caller.key} has joined the {char_class.display_name} Guild!",
                exclude=[caller],
                from_obj=caller,
            )


# ── CmdAdvance ──

class CmdAdvance(FCMCommandMixin, Command):
    """
    Spend a pending level on this guild's class.

    Usage:
        advance   — advance one level in this guild's class

    You must have levels to spend (earned via XP) and must already
    be a member of this guild's class.

    Available when in the same room as a Guildmaster NPC.
    """

    key = "advance"
    aliases = ["adv"]
    locks = "cmd:all()"
    help_category = "Guild"

    def func(self):
        caller = self.caller
        guildmaster = self.obj

        if guildmaster.location != caller.location:
            caller.msg("There is no guildmaster here.")
            return

        class_key = guildmaster.guild_class
        if not class_key:
            caller.msg("This guildmaster has not been assigned a guild class.")
            return

        from typeclasses.actors.char_classes import get_char_class
        char_class = get_char_class(class_key)
        if not char_class:
            caller.msg(f"Unknown class: {class_key}")
            return

        # Must be a member
        classes = caller.db.classes or {}
        if class_key not in classes:
            caller.msg(
                f"You are not a {char_class.display_name}. "
                f"Type |wjoin|n to become one first."
            )
            return

        # Check levels to spend (at_gain_subsequent_level_in_class also
        # validates this, but we give a friendlier message here)
        if caller.levels_to_spend <= 0:
            caller.msg(
                "You have no levels to spend. Gain more experience "
                "to earn additional levels."
            )
            return

        # Check guildmaster's authority level
        class_data = classes[class_key]
        current_class_level = class_data.get("level", 0)
        max_level = guildmaster.max_advance_level or 40
        if current_class_level >= max_level:
            hint = guildmaster.next_guildmaster_hint
            if hint:
                caller.msg(
                    f"\"You have surpassed what I can teach you, "
                    f"{caller.key}. Seek out {hint} "
                    f"to continue your training.\""
                )
            else:
                caller.msg(
                    f"\"You have surpassed what I can teach you, "
                    f"{caller.key}. You must find a more "
                    f"senior guildmaster to advance further.\""
                )
            return

        # Check absolute level cap (max 40 per class)
        if current_class_level >= 40:
            caller.msg(
                f"You have reached the maximum level in "
                f"{char_class.display_name}."
            )
            return

        # Advance — this deducts levels_to_spend, increments class level,
        # applies HP/mana/move/skill point gains, and announces the level-up
        char_class.at_gain_subsequent_level_in_class(caller)


# ── CmdSet ──

class GuildmasterCmdSet(CmdSet):
    """Commands available from a GuildmasterNPC."""

    key = "GuildmasterCmdSet"
    priority = 1
    mergetype = "Union"

    def at_cmdset_creation(self):
        self.add(CmdGuild())
        self.add(CmdJoin())
        self.add(CmdAdvance())
