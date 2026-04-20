"""
Defence — set the group's defensive fighting stance.

STRATEGY skill (warrior, paladin). Group leader command.

Toggles defensive stance for the leader and all followers in the same room
who are in combat. Mutually exclusive with offensive stance — activating
defence removes offence and vice versa.

Stat bonuses scale with the leader's mastery:
  BASIC:       +2 AC, -2 hit
  SKILLED:     +2 AC, -2 hit
  EXPERT:      +3 AC, -1 hit
  MASTER:      +4 AC, -1 hit
  GRANDMASTER: +5 AC (no hit penalty)

Usage:
    defence     — toggle defensive stance
    defense     — US alias
"""

from enums.mastery_level import MasteryLevel
from enums.skills_enum import skills
from .cmd_skill_base import CmdSkillBase

DEFENCE_SCALING = {
    MasteryLevel.BASIC:       {"ac": 2, "hit": -2},
    MasteryLevel.SKILLED:     {"ac": 2, "hit": -2},
    MasteryLevel.EXPERT:      {"ac": 3, "hit": -1},
    MasteryLevel.MASTER:      {"ac": 4, "hit": -1},
    MasteryLevel.GRANDMASTER: {"ac": 5, "hit": 0},
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


class CmdDefence(CmdSkillBase):
    """
    Set the group's defensive fighting stance.

    Usage:
        defence
        defense

    Toggles a defensive stance for your group: increased AC at the
    cost of hit accuracy. Calling again removes the stance.
    Mutually exclusive with offence — activating defence removes
    any active offensive stance.

    Must be the group leader (or solo) and in combat.
    """

    key = "defence"
    aliases = []
    skill = skills.STRATEGY.value
    help_category = "Group Combat"

    def func(self):
        caller = self.caller

        # ── Mastery check ──
        if not (getattr(caller.db, "general_skill_mastery_levels", None)
                or getattr(caller.db, "class_skill_mastery_levels", None)
                or getattr(caller.db, "weapon_skill_mastery_levels", None)):
            return self.mob_func()

        mastery_int = caller.get_skill_mastery(self.skill)
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

        # ── Toggle check: if defensive stance active, remove it ──
        if caller.has_effect("defensive_stance"):
            for member in group:
                member.remove_named_effect("defensive_stance")
            caller.msg("|yYou signal the group to return to a normal stance.|n")
            if caller.location:
                caller.location.msg_contents(
                    f"|y{caller.key} signals the group to return to a normal stance.|n",
                    exclude=[caller],
                )
            return

        # ── Remove offensive stance if active ──
        for member in group:
            if member.has_effect("offensive_stance"):
                member.remove_named_effect("offensive_stance")

        # ── Apply defensive stance to all group members ──
        scaling = DEFENCE_SCALING[mastery]
        effects = [
            {"type": "stat_bonus", "stat": "armor_class", "value": scaling["ac"]},
        ]
        if scaling["hit"] != 0:
            effects.append(
                {"type": "stat_bonus", "stat": "total_hit_bonus", "value": scaling["hit"]}
            )

        for member in group:
            member.apply_named_effect(
                key="defensive_stance",
                source=caller,
                effects=effects,
                duration=None,
                duration_type="combat_rounds",
            )

        # ── Summary message ──
        parts = [f"+{scaling['ac']} AC"]
        if scaling["hit"] != 0:
            parts.append(f"{scaling['hit']} hit")
        bonus_str = ", ".join(parts)

        caller.msg(
            f"|g*DEFENCE* You command the group to fight defensively! "
            f"({bonus_str})|n"
        )
        if caller.location:
            caller.location.msg_contents(
                f"|y{caller.key} commands the group to fight defensively!|n",
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
