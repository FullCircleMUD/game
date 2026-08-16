"""
Tests for Rabbit — skittish prey that flees from threats.

What counts as a threat is a predicate stack rather than a method, so
these pin both halves of it: aggression decides who frightens a rabbit,
and perception decides whether the rabbit knows they are there.

evennia test --settings settings tests.typeclass_tests.test_rabbit
"""

from unittest.mock import patch

from evennia.utils import create
from evennia.utils.test_resources import EvenniaTest

from enums.condition import Condition


class RabbitTest(EvenniaTest):
    """A rabbit in a lit room with one player character."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"
    character_typeclass = "typeclasses.actors.character.FCMCharacter"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.rabbit = self._mob(
            "typeclasses.actors.mobs.rabbit.Rabbit", "a rabbit"
        )
        self.char2.location = self.room2

    def _mob(self, typeclass, key, location=None):
        mob = create.create_object(
            typeclass,
            key=key,
            location=location or self.room1,
            nohome=True,
        )
        mob.is_alive = True
        return mob

    def _threats(self):
        from typeclasses.actors.mobs.rabbit import THREAT_PREDICATES

        return self.rabbit.ai.get_targets_in_room(THREAT_PREDICATES)


class TestWhatFrightensARabbit(RabbitTest):
    """Aggression, not combat-capability, is what makes a threat."""

    def test_a_player_character_is_a_threat(self):
        self.assertIn(self.char1, self._threats())

    def test_an_aggressive_mob_is_a_threat(self):
        wolf = self._mob("typeclasses.actors.mobs.wolf.Wolf", "a grey wolf")
        self.assertIn(wolf, self._threats())

    def test_a_harmless_mob_is_not_a_threat(self):
        """A mouse is a CombatMob but does not hunt rabbits."""
        mouse = self._mob("typeclasses.actors.mobs.mouse.Mouse", "a mouse")
        self.assertNotIn(mouse, self._threats())

    def test_a_butterfly_is_not_a_threat(self):
        moth = self._mob(
            "typeclasses.actors.mobs.butterfly.Butterfly", "a butterfly"
        )
        self.assertNotIn(moth, self._threats())

    def test_another_rabbit_is_not_a_threat(self):
        other = self._mob(
            "typeclasses.actors.mobs.rabbit.Rabbit", "another rabbit"
        )
        self.assertNotIn(other, self._threats())

    def test_the_rabbit_does_not_frighten_itself(self):
        self.assertNotIn(self.rabbit, self._threats())


class TestPerceptionGatesThreats(RabbitTest):
    """A rabbit cannot flee from what it cannot perceive."""

    def test_an_invisible_player_is_not_a_threat(self):
        self.char1.add_condition(Condition.INVISIBLE)
        self.assertNotIn(self.char1, self._threats())

    def test_a_hidden_player_is_not_a_threat(self):
        self.char1.add_condition(Condition.HIDDEN)
        self.assertNotIn(self.char1, self._threats())

    def test_detect_invis_restores_the_threat(self):
        self.char1.add_condition(Condition.INVISIBLE)
        self.rabbit.add_condition(Condition.DETECT_INVIS)
        self.assertIn(self.char1, self._threats())


class TestFleeScheduling(RabbitTest):
    """ai_wander schedules a flee, _flee_reaction commits to it."""

    def test_a_threat_present_schedules_a_flee(self):
        with patch("typeclasses.actors.mobs.rabbit.delay") as mock_delay:
            self.rabbit.ai_wander()
        mock_delay.assert_called_once()

    def test_no_threat_present_does_not_schedule(self):
        self.char1.location = self.room2
        with patch("typeclasses.actors.mobs.rabbit.delay") as mock_delay:
            with patch.object(self.rabbit, "wander"):
                self.rabbit.ai_wander()
        mock_delay.assert_not_called()

    def test_a_harmless_neighbour_does_not_schedule(self):
        self.char1.location = self.room2
        self._mob("typeclasses.actors.mobs.mouse.Mouse", "a mouse")
        with patch("typeclasses.actors.mobs.rabbit.delay") as mock_delay:
            with patch.object(self.rabbit, "wander"):
                self.rabbit.ai_wander()
        mock_delay.assert_not_called()


class TestAtNewArrival(RabbitTest):
    """The push path tests the arriving object against the same stack."""

    def test_an_arriving_player_schedules_a_flee(self):
        with patch("typeclasses.actors.mobs.rabbit.delay") as mock_delay:
            self.rabbit.at_new_arrival(self.char1)
        mock_delay.assert_called_once()

    def test_an_arriving_mouse_is_ignored(self):
        mouse = self._mob(
            "typeclasses.actors.mobs.mouse.Mouse", "a mouse", self.room2
        )
        with patch("typeclasses.actors.mobs.rabbit.delay") as mock_delay:
            self.rabbit.at_new_arrival(mouse)
        mock_delay.assert_not_called()

    def test_its_own_arrival_is_ignored(self):
        with patch("typeclasses.actors.mobs.rabbit.delay") as mock_delay:
            self.rabbit.at_new_arrival(self.rabbit)
        mock_delay.assert_not_called()


class TestFleeReactionRevalidates(RabbitTest):
    """The delayed callback re-checks before bolting."""

    def test_it_flees_while_the_threat_remains(self):
        with patch.object(self.rabbit, "flee_to_random_room") as flee:
            self.rabbit._flee_reaction()
        flee.assert_called_once()

    def test_a_departed_threat_cancels_the_flee(self):
        self.char1.location = self.room2
        with patch.object(self.rabbit, "flee_to_random_room") as flee:
            self.rabbit._flee_reaction()
        flee.assert_not_called()

    def test_a_concealed_threat_cancels_the_flee(self):
        """The rabbit stops perceiving them, so it settles again."""
        self.char1.add_condition(Condition.INVISIBLE)
        with patch.object(self.rabbit, "flee_to_random_room") as flee:
            self.rabbit._flee_reaction()
        flee.assert_not_called()

    def test_a_dead_rabbit_does_not_flee(self):
        self.rabbit.is_alive = False
        with patch.object(self.rabbit, "flee_to_random_room") as flee:
            self.rabbit._flee_reaction()
        flee.assert_not_called()
