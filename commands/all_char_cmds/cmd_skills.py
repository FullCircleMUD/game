        

from evennia import Command
from evennia.utils import evtable

from commands.command import FCMCommandMixin
from enums.mastery_level import MasteryLevel


# displays a listing of a characters available skills and their level of mastery.

# helper functions
def display_general_skills(caller, skills, pts_available):

        if not skills:
            caller.msg("You have no general skills available.")
            return

        caller.msg(f"\n|c--- General Skills (|w{pts_available}|c pts available) ---|n")

        table = evtable.EvTable(
            "General Skill",
            "Mastery",
            border="header"
        )

        for skill_name in sorted(skills.keys()):
            mastery_value = skills.get(skill_name, 0)

            try:
                mastery_enum = MasteryLevel(mastery_value)
                mastery_name = mastery_enum.name
            except ValueError:
                mastery_name = "ERROR"

            table.add_row(skill_name.capitalize(), mastery_name)

        caller.msg(str(table))

def display_class_skills(caller, skills, classes_data):

        if not skills:
            caller.msg("\nYou have no class skills available.")
            return

        # Sum class skill points across all classes
        total_class_pts = sum(
            cls.get("skill_pts_available", 0)
            for cls in (classes_data or {}).values()
        )

        caller.msg(f"\n|c--- Class Skills (|w{total_class_pts}|c pts available) ---|n")

        table = evtable.EvTable(
            "Class Skill",
            "Mastery",
            "Classes",
            border="header"
        )

        for skill_name in sorted(skills.keys()):

            skill_data = skills[skill_name]

            mastery_value = skill_data["mastery"]
            classes_array = skill_data["classes"]

            classes_string = ""
            for cl in classes_array:
                classes_string += f"{cl} "

            try:
                mastery_enum = MasteryLevel(mastery_value)
                mastery_name = mastery_enum.name
            except ValueError:
                mastery_name = "ERROR"

            table.add_row(skill_name.capitalize(), mastery_name, classes_string)

        caller.msg(str(table))

def display_weapon_skills(caller, skills, pts_available):

        if not skills:
            caller.msg("\nYou have no weapon skills available.")
            return

        caller.msg(f"\n|c--- Weapon Skills (|w{pts_available}|c pts available) ---|n")

        table = evtable.EvTable(
            "Weapon Type",
            "Mastery",
            border="header"
        )

        for skill_name in sorted(skills.keys()):
            mastery_value = skills.get(skill_name, 0)

            try:
                mastery_enum = MasteryLevel(mastery_value)
                mastery_name = mastery_enum.name
            except ValueError:
                mastery_name = "ERROR"

            table.add_row(skill_name.capitalize(), mastery_name)

        caller.msg(str(table))

class CmdSkills(FCMCommandMixin, Command):
    key = "skills"
    aliases = []
    locks = "cmd:all()" # anyone can execute the command"
    help_category = "Character"
    allow_while_sleeping = True

    def func(self):

        caller = self.caller
        general_skills = caller.db.general_skill_mastery_levels or {}
        class_skills = caller.db.class_skill_mastery_levels or {}
        weapon_skills = caller.db.weapon_skill_mastery_levels or {}

        display_general_skills(caller, general_skills, caller.general_skill_pts_available)

        display_class_skills(caller, class_skills, caller.db.classes or {})

        display_weapon_skills(caller, weapon_skills, caller.weapon_skill_pts_available)
        

        
