"""
Tests for mob perception — what AIHandler.get_targets_in_room returns.

A mob must not be handed a target it cannot perceive. Concealment is
answered by the shared targeting predicates, so the counters behave the
same way for a mob as they do for a character: ``true_sight`` pierces
HIDDEN, ``DETECT_INVIS`` pierces INVISIBLE, and neither covers for the
other.

evennia test --settings settings tests.typeclass_tests.test_ai_perception
"""

from evennia.utils import create
from evennia.utils.test_resources import EvenniaTest

from enums.condition import Condition


class MobPerceptionTest(EvenniaTest):
    """A mob and a player character sharing a room."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"
    character_typeclass = "typeclasses.actors.character.FCMCharacter"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.mob = create.create_object(
            "typeclasses.actors.mobs.aggressive_mob.AggressiveMob",
            key="test wolf",
            location=self.room1,
            home=self.room1,
            nohome=True,
        )

    def _scan(self, target_filter=None):
        return self.mob.ai.get_targets_in_room(target_filter)


class TestDefaultScan(MobPerceptionTest):
    """The no-argument path every aggro caller uses."""

    def test_visible_player_is_returned(self):
        self.assertIn(self.char1, self._scan())

    def test_invisible_player_is_not_returned(self):
        self.char1.add_condition(Condition.INVISIBLE)
        self.assertNotIn(self.char1, self._scan())

    def test_hidden_player_is_not_returned(self):
        self.char1.add_condition(Condition.HIDDEN)
        self.assertNotIn(self.char1, self._scan())

    def test_the_mob_never_returns_itself(self):
        self.assertNotIn(self.mob, self._scan())


class TestCounters(MobPerceptionTest):
    """A mob holding a counter perceives what it counters, and no more."""

    def test_detect_invis_reveals_an_invisible_player(self):
        self.char1.add_condition(Condition.INVISIBLE)
        self.mob.add_condition(Condition.DETECT_INVIS)
        self.assertIn(self.char1, self._scan())

    def test_true_sight_reveals_a_hidden_player(self):
        self.char1.add_condition(Condition.HIDDEN)
        self.mob.apply_true_sight(duration_seconds=300)
        self.assertIn(self.char1, self._scan())

    def test_true_sight_does_not_reveal_an_invisible_player(self):
        """True Sight pierces HIDDEN only — DETECT_INVIS is a separate axis."""
        self.char1.add_condition(Condition.INVISIBLE)
        self.mob.apply_true_sight(duration_seconds=300)
        self.assertNotIn(self.char1, self._scan())

    def test_detect_invis_does_not_reveal_a_hidden_player(self):
        self.char1.add_condition(Condition.HIDDEN)
        self.mob.add_condition(Condition.DETECT_INVIS)
        self.assertNotIn(self.char1, self._scan())

    def test_both_conditions_need_both_counters(self):
        self.char1.add_condition(Condition.HIDDEN)
        self.char1.add_condition(Condition.INVISIBLE)
        self.mob.apply_true_sight(duration_seconds=300)
        self.assertNotIn(self.char1, self._scan())

        self.mob.add_condition(Condition.DETECT_INVIS)
        self.assertIn(self.char1, self._scan())


class TestTargetFilterCannotWiden(MobPerceptionTest):
    """Perception is the floor — a caller's filter only narrows."""

    def test_permissive_filter_still_excludes_an_invisible_player(self):
        self.char1.add_condition(Condition.INVISIBLE)
        self.assertNotIn(self.char1, self._scan(lambda obj: True))

    def test_permissive_filter_still_excludes_a_hidden_player(self):
        self.char1.add_condition(Condition.HIDDEN)
        self.assertNotIn(self.char1, self._scan(lambda obj: True))

    def test_a_filter_narrows_within_what_is_perceived(self):
        self.assertIn(self.char1, self._scan(lambda obj: True))
        self.assertNotIn(self.char1, self._scan(lambda obj: False))
