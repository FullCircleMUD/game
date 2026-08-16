"""
Tests for the diagnose command.

evennia test --settings settings tests.command_tests.test_cmd_diagnose
"""

from evennia.utils.test_resources import EvenniaCommandTest
from evennia.utils import create

from commands.all_char_cmds.cmd_diagnose import CmdDiagnose
from enums.condition import Condition


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
        self.assertIn("no 'dragon' here", result.lower())

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
        """Diagnosing a non-actor — actor_friendly doesn't find it."""
        create.create_object(
            "typeclasses.objects.Object",
            key="a rock",
            location=self.room1,
            nohome=True,
        )
        result = self.call(CmdDiagnose(), "rock")
        self.assertIn("no 'rock' here", result.lower())


class TestCmdDiagnoseSight(EvenniaCommandTest):
    """
    Reading someone's wounds is visual, so it needs working eyes. Your
    own injuries are the exception — you know those by feel.
    """

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"
    character_typeclass = "typeclasses.actors.character.FCMCharacter"

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

    def _darken(self):
        # has_natural_light is a read-only property derived from this.
        self.room1.always_lit = False
        self.room1.natural_light = False

    def test_a_lit_room_diagnoses_normally(self):
        result = self.call(CmdDiagnose(), "goblin")
        self.assertIn("HP", result)

    def test_a_dark_room_says_why_it_refuses(self):
        self._darken()
        result = self.call(CmdDiagnose(), "goblin")
        self.assertIn("too dark", result)

    def test_a_blinded_character_cannot_diagnose_others(self):
        self.char1.add_condition(Condition.BLINDED)
        result = self.call(CmdDiagnose(), "goblin")
        self.assertIn("too dark", result)

    def test_darkvision_restores_it(self):
        self._darken()
        self.char1.add_condition(Condition.DARKVISION)
        result = self.call(CmdDiagnose(), "goblin")
        self.assertIn("HP", result)

    def test_you_can_still_diagnose_yourself_blind(self):
        """Self short-circuits before the sight gate — you feel your own wounds."""
        self.char1.add_condition(Condition.BLINDED)
        result = self.call(CmdDiagnose(), "")
        self.assertIn("You are", result)
        self.assertIn("HP", result)

    def test_you_can_still_diagnose_yourself_in_the_dark(self):
        self._darken()
        result = self.call(CmdDiagnose(), "")
        self.assertIn("HP", result)

    def test_an_invisible_target_cannot_be_diagnosed(self):
        """Concealment still applies underneath sight."""
        self.mob.add_condition(Condition.INVISIBLE)
        result = self.call(CmdDiagnose(), "goblin")
        self.assertIn("no 'goblin' here", result.lower())

    def test_detect_invis_restores_an_invisible_target(self):
        self.mob.add_condition(Condition.INVISIBLE)
        self.char1.add_condition(Condition.DETECT_INVIS)
        result = self.call(CmdDiagnose(), "goblin")
        self.assertIn("HP", result)
