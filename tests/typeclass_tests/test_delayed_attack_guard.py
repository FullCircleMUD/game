"""
Tests for AggressiveMixin._execute_attack — the guard against firing on a
deleted object.

_schedule_attack sets a delay of up to several seconds. Either party can
be deleted inside that window: a mob killed mid-countdown, a target that
logged out. Reading an AttributeProperty off a deleted row does not fall
back to a default — it tries to write one and raises on the missing id.

evennia test --settings settings tests.typeclass_tests.test_delayed_attack_guard
"""

from unittest.mock import MagicMock

from evennia.utils import create
from evennia.utils.test_resources import EvenniaTest


class TestDelayedAttackGuard(EvenniaTest):

    character_typeclass = "typeclasses.actors.character.FCMCharacter"
    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.char1.hp = 50
        self.char1.hp_max = 50
        self.wolf = self._create_wolf("a grey wolf")
        self.wolf.initiate_attack = MagicMock()

    def _create_wolf(self, key):
        wolf = create.create_object(
            "typeclasses.actors.mobs.wolf.Wolf", key=key, location=self.room1,
        )
        wolf.is_alive = True
        wolf.hp = 15
        return wolf

    def test_live_pair_still_attacks(self):
        """Guard — the rest of this class means nothing if this fails."""
        self.wolf._execute_attack(self.char1)
        self.wolf.initiate_attack.assert_called_once_with(self.char1)

    def test_deleted_attacker_is_a_no_op(self):
        self.wolf.delete()
        self.wolf._execute_attack(self.char1)
        self.wolf.initiate_attack.assert_not_called()

    def test_deleted_target_is_a_no_op(self):
        target = self._create_wolf("a second grey wolf")
        target.delete()
        self.wolf._execute_attack(target)
        self.wolf.initiate_attack.assert_not_called()

    def test_target_of_none_is_a_no_op(self):
        self.wolf._execute_attack(None)
        self.wolf.initiate_attack.assert_not_called()
