"""
Tests for CmdSkills — skills display command.

Verifies display of general, class, and weapon skills at various
mastery levels, plus empty skill lists.

evennia test --settings settings tests.command_tests.test_cmd_skills
"""

from evennia.utils.test_resources import EvenniaCommandTest

from commands.all_char_cmds.cmd_skills import CmdSkills
from enums.mastery_level import MasteryLevel


WALLET_A = "0xAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"


class TestCmdSkills(EvenniaCommandTest):
    """Test the skills command."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)

    def test_no_skills(self):
        """Character with no skills should show empty messages."""
        self.char1.db.general_skill_mastery_levels = {}
        self.char1.db.class_skill_mastery_levels = {}
        self.char1.db.weapon_skill_mastery_levels = {}
        result = self.call(CmdSkills(), "")
        self.assertIn("no general skills", result.lower())

    def test_general_skills_displayed(self):
        """General skills should appear in output."""
        self.char1.db.general_skill_mastery_levels = {
            "swimming": MasteryLevel.BASIC.value,
        }
        self.char1.db.class_skill_mastery_levels = {}
        self.char1.db.weapon_skill_mastery_levels = {}
        result = self.call(CmdSkills(), "")
        self.assertIn("Swimming", result)
        self.assertIn("BASIC", result)

    def test_weapon_skills_displayed(self):
        """Weapon skills should appear in output."""
        self.char1.db.general_skill_mastery_levels = {}
        self.char1.db.class_skill_mastery_levels = {}
        self.char1.db.weapon_skill_mastery_levels = {
            "longsword": MasteryLevel.EXPERT.value,
        }
        result = self.call(CmdSkills(), "")
        self.assertIn("Longsword", result)
        self.assertIn("EXPERT", result)

    def test_class_skills_displayed(self):
        """Class skills should show mastery under their own class heading."""
        self.char1.db.general_skill_mastery_levels = {}
        self.char1.db.class_skill_mastery_levels = {
            "fireball": {
                "mastery": MasteryLevel.SKILLED.value,
                "classes": ["mage"],
            },
        }
        self.char1.db.weapon_skill_mastery_levels = {}
        self.char1.db.classes = {"mage": {"level": 1, "skill_pts_available": 4}}
        result = self.call(CmdSkills(), "")
        self.assertIn("Mage Class Skills", result)
        self.assertIn("Fireball", result)
        self.assertIn("SKILLED", result)

    def test_class_skills_split_by_class(self):
        """Each class gets its own heading, points, and skill list."""
        self.char1.db.general_skill_mastery_levels = {}
        self.char1.db.class_skill_mastery_levels = {
            "fireball": {
                "mastery": MasteryLevel.SKILLED.value,
                "classes": ["mage"],
            },
            "bash": {
                "mastery": MasteryLevel.BASIC.value,
                "classes": ["warrior"],
            },
        }
        self.char1.db.weapon_skill_mastery_levels = {}
        self.char1.db.classes = {
            "warrior": {"level": 1, "skill_pts_available": 2},
            "mage": {"level": 1, "skill_pts_available": 4},
        }
        result = self.call(CmdSkills(), "")
        self.assertIn("Warrior Class Skills", result)
        self.assertIn("Mage Class Skills", result)
        self.assertIn("2 pts available", result)
        self.assertIn("4 pts available", result)

        warrior_section = result.split("Warrior Class Skills")[1].split("Mage Class Skills")[0]
        self.assertIn("Bash", warrior_section)
        self.assertNotIn("Fireball", warrior_section)

    def test_skills_alias_sk(self):
        """'sk' alias should work."""
        self.char1.db.general_skill_mastery_levels = {}
        self.char1.db.class_skill_mastery_levels = {}
        self.char1.db.weapon_skill_mastery_levels = {}
        result = self.call(CmdSkills(), "", cmdstring="sk")
        self.assertIn("no general skills", result.lower())
