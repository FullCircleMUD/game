"""
Tests for mob perception — what AIHandler.get_targets_in_room returns.

A mob must not be handed a target it cannot perceive. Concealment is
answered by the shared targeting predicates, so the counters behave the
same way for a mob as they do for a character: ``true_sight`` pierces
HIDDEN, ``DETECT_INVIS`` pierces INVISIBLE, and neither covers for the
other.

The helper answers what the mob can perceive; the caller's predicates say
what it cares about. It applies no filter of its own beyond perception.

evennia test --settings settings tests.typeclass_tests.test_ai_perception
"""

from evennia.utils import create
from evennia.utils.test_resources import EvenniaTest

from enums.condition import Condition
from utils.targeting.predicates import p_is_character, p_living


class MobPerceptionTest(EvenniaTest):
    """A mob and a player character sharing a room."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"
    character_typeclass = "typeclasses.actors.character.FCMCharacter"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.mob = self._mob("test wolf")

    def _mob(self, key):
        return create.create_object(
            "typeclasses.actors.mobs.aggressive_mob.AggressiveMob",
            key=key,
            location=self.room1,
            home=self.room1,
            nohome=True,
        )

    def _scan(self, *predicates):
        return self.mob.ai.get_targets_in_room(*predicates)


class TestNoImplicitFiltering(MobPerceptionTest):
    """The helper assumes nothing about what the caller wants."""

    def test_a_bare_scan_returns_other_mobs_too(self):
        """No predicates means everything perceived, not just players."""
        other = self._mob("a second wolf")
        found = self._scan()
        self.assertIn(other, found)
        self.assertIn(self.char1, found)

    def test_p_is_character_narrows_to_players(self):
        other = self._mob("a second wolf")
        found = self._scan(p_is_character)
        self.assertNotIn(other, found)
        self.assertIn(self.char1, found)

    def test_the_mob_never_returns_itself(self):
        self.assertNotIn(self.mob, self._scan())

    def test_predicates_may_be_passed_as_a_list(self):
        loose = self._scan(p_is_character, p_living)
        packed = self._scan([p_is_character, p_living])
        self.assertEqual(loose, packed)
        self.assertIn(self.char1, packed)


class TestPerceptionFloor(MobPerceptionTest):
    """Concealed actors are withheld whatever the caller asks for."""

    def test_visible_player_is_returned(self):
        self.assertIn(self.char1, self._scan(p_is_character))

    def test_invisible_player_is_not_returned(self):
        self.char1.add_condition(Condition.INVISIBLE)
        self.assertNotIn(self.char1, self._scan(p_is_character))

    def test_hidden_player_is_not_returned(self):
        self.char1.add_condition(Condition.HIDDEN)
        self.assertNotIn(self.char1, self._scan(p_is_character))

    def test_a_bare_scan_still_withholds_a_concealed_player(self):
        """Perception applies even when the caller narrows nothing."""
        self.char1.add_condition(Condition.INVISIBLE)
        self.assertNotIn(self.char1, self._scan())

    def test_predicates_narrow_but_cannot_widen(self):
        self.char1.add_condition(Condition.INVISIBLE)
        self.assertNotIn(self.char1, self._scan(lambda obj, caller: True))

    def test_a_predicate_narrows_within_what_is_perceived(self):
        self.assertIn(self.char1, self._scan(lambda obj, caller: True))
        self.assertNotIn(self.char1, self._scan(lambda obj, caller: False))


class TestCounters(MobPerceptionTest):
    """A mob holding a counter perceives what it counters, and no more."""

    def test_detect_invis_reveals_an_invisible_player(self):
        self.char1.add_condition(Condition.INVISIBLE)
        self.mob.add_condition(Condition.DETECT_INVIS)
        self.assertIn(self.char1, self._scan(p_is_character))

    def test_true_sight_reveals_a_hidden_player(self):
        self.char1.add_condition(Condition.HIDDEN)
        self.mob.apply_true_sight(duration_seconds=300)
        self.assertIn(self.char1, self._scan(p_is_character))

    def test_true_sight_does_not_reveal_an_invisible_player(self):
        """True Sight pierces HIDDEN only — DETECT_INVIS is a separate axis."""
        self.char1.add_condition(Condition.INVISIBLE)
        self.mob.apply_true_sight(duration_seconds=300)
        self.assertNotIn(self.char1, self._scan(p_is_character))

    def test_detect_invis_does_not_reveal_a_hidden_player(self):
        self.char1.add_condition(Condition.HIDDEN)
        self.mob.add_condition(Condition.DETECT_INVIS)
        self.assertNotIn(self.char1, self._scan(p_is_character))

    def test_both_conditions_need_both_counters(self):
        self.char1.add_condition(Condition.HIDDEN)
        self.char1.add_condition(Condition.INVISIBLE)
        self.mob.apply_true_sight(duration_seconds=300)
        self.assertNotIn(self.char1, self._scan(p_is_character))

        self.mob.add_condition(Condition.DETECT_INVIS)
        self.assertIn(self.char1, self._scan(p_is_character))
