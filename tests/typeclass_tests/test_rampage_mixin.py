"""
Tests for RampageMixin — on-kill chain attack behavior.

evennia test --settings settings tests.typeclass_tests.test_rampage_mixin
"""

from unittest.mock import patch, MagicMock

from evennia.typeclasses.attributes import AttributeProperty
from evennia.utils import create
from evennia.utils.test_resources import EvenniaTest

from typeclasses.actors.mobs.aggressive_mob import AggressiveMob
from typeclasses.mixins.mob_behaviours.rampage_mixin import RampageMixin


class RampageTestMob(RampageMixin, AggressiveMob):
    """Test-only mob with rampage."""
    rampage_message = AttributeProperty(
        "|r{name} rampages toward {target}!|n"
    )


class TestRampageMixin(EvenniaTest):
    """Test at_kill chain attack."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.mob = create.create_object(
            RampageTestMob, key="a rampager", location=self.room1,
        )
        self.mob.is_alive = True
        self.mob.hp = 40

    @patch("combat.combat_utils.execute_attack")
    def test_rampage_attacks_next_player(self, mock_execute):
        """at_kill should fire execute_attack on another player in room."""
        victim = MagicMock()
        victim.is_pc = True
        victim.hp = 0

        self.char1.is_pc = True
        self.char1.hp = 30
        self.char1.location = self.room1
        self.char2.location = self.room2  # only char1 is valid target

        self.mob.at_kill(victim)
        mock_execute.assert_called_once_with(self.mob, self.char1)

    @patch("combat.combat_utils.execute_attack")
    def test_no_rampage_when_no_targets(self, mock_execute):
        """at_kill should not fire if no living players in room."""
        victim = MagicMock()
        victim.is_pc = True
        victim.hp = 0

        self.char1.location = self.room2
        self.char2.location = self.room2

        self.mob.at_kill(victim)
        mock_execute.assert_not_called()

    @patch("combat.combat_utils.execute_attack")
    def test_no_rampage_when_dead(self, mock_execute):
        """Dead mob should not rampage."""
        self.mob.is_alive = False
        victim = MagicMock()
        self.char1.is_pc = True
        self.char1.hp = 30
        self.char1.location = self.room1

        self.mob.at_kill(victim)
        mock_execute.assert_not_called()

    @patch("combat.combat_utils.execute_attack")
    def test_rampage_skips_dead_players(self, mock_execute):
        """Rampage should not target players at 0 HP."""
        victim = MagicMock()
        victim.is_pc = True
        victim.hp = 0

        self.char1.is_pc = True
        self.char1.hp = 0
        self.char1.location = self.room1
        self.char2.is_pc = True
        self.char2.hp = 0
        self.char2.location = self.room1

        self.mob.at_kill(victim)
        mock_execute.assert_not_called()
