"""
Tests for the diagnose command.

evennia test --settings settings tests.command_tests.test_cmd_diagnose
"""

from evennia.utils.test_resources import EvenniaCommandTest
from evennia.utils import create

from commands.all_char_cmds.cmd_diagnose import CmdDiagnose


WALLET_A = "0xAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"


class TestCmdDiagnoseSelf(EvenniaCommandTest):
    """Test diagnosing yourself."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)

    def test_no_args_diagnoses_self(self):
        """Diagnose with no args shows own health."""
        result = self.call(CmdDiagnose(), "")
        self.assertIn("You are", result)
        self.assertIn("HP", result)

    def test_self_shows_hp_values(self):
        """Diagnose self shows HP numbers."""
        result = self.call(CmdDiagnose(), "")
        self.assertIn("/", result)


class TestCmdDiagnoseTarget(EvenniaCommandTest):
    """Test diagnosing a target."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)
        self.room1.always_lit = True
        self.mob = create.create_object(
            "typeclasses.actors.mob.CombatMob",
            key="a goblin",
            location=self.room1,
            nohome=True,
        )

    def test_diagnose_target(self):
        """Diagnose a target shows their health."""
        result = self.call(CmdDiagnose(), "goblin")
        self.assertIn("goblin", result)
        self.assertIn("HP", result)

    def test_diagnose_missing_target(self):
        """Diagnose nonexistent target shows search failure."""
        result = self.call(CmdDiagnose(), "dragon")
        self.assertIn("Could not find", result)

    def test_full_health_description(self):
        """Full health target shows excellent condition."""
        result = self.call(CmdDiagnose(), "goblin")
        self.assertIn("excellent condition", result)

    def test_hurt_target_description(self):
        """Damaged target shows appropriate description."""
        self.mob.db.hp_max = 100
        self.mob.hp = 1
        result = self.call(CmdDiagnose(), "goblin")
        self.assertIn("awful condition", result)

    def test_diagnose_object_rejected(self):
        """Diagnosing a non-character object is rejected."""
        create.create_object(
            "typeclasses.objects.Object",
            key="a rock",
            location=self.room1,
            nohome=True,
        )
        result = self.call(CmdDiagnose(), "rock")
        self.assertIn("can't diagnose", result)
