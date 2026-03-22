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
        """Class skills should show mastery and classes."""
        self.char1.db.general_skill_mastery_levels = {}
        self.char1.db.class_skill_mastery_levels = {
            "fireball": {
                "mastery": MasteryLevel.SKILLED.value,
                "classes": ["mage"],
            },
        }
        self.char1.db.weapon_skill_mastery_levels = {}
        result = self.call(CmdSkills(), "")
        self.assertIn("Fireball", result)
        self.assertIn("SKILLED", result)
        self.assertIn("mage", result)

    def test_skills_alias_sk(self):
        """'sk' alias should work."""
        self.char1.db.general_skill_mastery_levels = {}
        self.char1.db.class_skill_mastery_levels = {}
        self.char1.db.weapon_skill_mastery_levels = {}
        result = self.call(CmdSkills(), "", cmdstring="sk")
        self.assertIn("no general skills", result.lower())
