"""
Offence — set the group's offensive fighting stance.

STRATEGY skill (warrior, paladin). Group leader command.

Toggles offensive stance for the leader and all followers in the same room
who are in combat. Mutually exclusive with defensive stance — activating
offence removes defence and vice versa.

Stat bonuses scale with the leader's mastery:
  BASIC:       +2 hit, -1 AC
  SKILLED:     +3 hit, -1 AC
  EXPERT:      +3 hit, +1 dam, -1 AC
  MASTER:      +3 hit, +2 dam, -1 AC
  GRANDMASTER: +3 hit, +3 dam (no AC penalty)

Usage:
    offence     — toggle offensive stance
    offense     — US alias
"""

from enums.mastery_level import MasteryLevel
from enums.skills_enum import skills
from .cmd_skill_base import CmdSkillBase

OFFENCE_SCALING = {
    MasteryLevel.BASIC:       {"hit": 2, "dam": 0, "ac": -1},
    MasteryLevel.SKILLED:     {"hit": 3, "dam": 0, "ac": -1},
    MasteryLevel.EXPERT:      {"hit": 3, "dam": 1, "ac": -1},
    MasteryLevel.MASTER:      {"hit": 3, "dam": 2, "ac": -1},
    MasteryLevel.GRANDMASTER: {"hit": 3, "dam": 3, "ac": 0},
}


def _get_group_in_combat(caller):
    """Get caller + followers in same room who are in combat."""
    members = [caller]
    if hasattr(caller, "get_followers"):
        members.extend(caller.get_followers(same_room=True))
    return [
        m for m in members
        if m.scripts.get("combat_handler")
    ]


def _build_effects(scaling):
    """Build effects list from scaling dict."""
    effects = [
        {"type": "stat_bonus", "stat": "total_hit_bonus", "value": scaling["hit"]},
    ]
    if scaling["ac"] != 0:
        effects.append(
            {"type": "stat_bonus", "stat": "armor_class", "value": scaling["ac"]}
        )
    if scaling["dam"] > 0:
        effects.append(
            {"type": "stat_bonus", "stat": "total_damage_bonus", "value": scaling["dam"]}
        )
    return effects


class CmdOffence(CmdSkillBase):
    """
    Set the group's offensive fighting stance.

    Usage:
        offence
        offense

    Toggles an aggressive stance for your group: increased hit and
    damage at the cost of AC. Calling again removes the stance.
    Mutually exclusive with defence — activating offence removes
    any active defensive stance.

    Must be the group leader (or solo) and in combat.
    """

    key = "offence"
    aliases = ["offense"]
    skill = skills.STRATEGY.value
    help_category = "Group Combat"

    def func(self):
        caller = self.caller

        # ── Mastery check ──
        mastery_dict = caller.db.skill_mastery_levels
        if not mastery_dict:
            return self.mob_func()

        mastery_int = mastery_dict.get(self.skill, MasteryLevel.UNSKILLED.value)
        mastery = MasteryLevel(mastery_int)

        if mastery == MasteryLevel.UNSKILLED:
            caller.msg("You need training in strategy before you can set stances.")
            return

        # ── Must be in combat ──
        handlers = caller.scripts.get("combat_handler")
        if not handlers:
            caller.msg("You must be in combat to set a fighting stance.")
            return

        # ── Must be leader or solo ──
        if caller.following:
            caller.msg("Only the group leader can set the fighting stance.")
            return

        # ── Get group members in combat ──
        group = _get_group_in_combat(caller)

        # ── Toggle check: if offensive stance active, remove it ──
        if caller.has_effect("offensive_stance"):
            for member in group:
                member.remove_named_effect("offensive_stance")
            caller.msg("|yYou signal the group to return to a normal stance.|n")
            if caller.location:
                caller.location.msg_contents(
                    f"|y{caller.key} signals the group to return to a normal stance.|n",
                    exclude=[caller],
                )
            return

        # ── Remove defensive stance if active ──
        for member in group:
            if member.has_effect("defensive_stance"):
                member.remove_named_effect("defensive_stance")

        # ── Apply offensive stance to all group members ──
        scaling = OFFENCE_SCALING[mastery]
        effects = _build_effects(scaling)

        for member in group:
            member.apply_named_effect(
                key="offensive_stance",
                source=caller,
                effects=effects,
                duration=None,
                duration_type="combat_rounds",
            )

        # ── Summary message ──
        parts = [f"+{scaling['hit']} hit"]
        if scaling["dam"] > 0:
            parts.append(f"+{scaling['dam']} damage")
        if scaling["ac"] != 0:
            parts.append(f"{scaling['ac']} AC")
        bonus_str = ", ".join(parts)

        caller.msg(
            f"|g*OFFENCE* You command the group to fight aggressively! "
            f"({bonus_str})|n"
        )
        if caller.location:
            caller.location.msg_contents(
                f"|y{caller.key} commands the group to fight aggressively!|n",
                exclude=[caller],
            )

    # ── Mob fallback ──
    def mob_func(self):
        pass

    # Mastery stubs — not used (func overridden)
    def unskilled_func(self):
        pass

    def basic_func(self):
        pass

    def skilled_func(self):
        pass

    def expert_func(self):
        pass

    def master_func(self):
        pass

    def grandmaster_func(self):
        pass
