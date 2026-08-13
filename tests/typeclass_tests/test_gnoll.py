"""
Tests for Gnoll mob — stats, aggression, rampage, and retreat.

evennia test --settings settings tests.typeclass_tests.test_gnoll
"""

from unittest.mock import patch, MagicMock

from evennia.utils import create
from evennia.utils.test_resources import EvenniaTest

from enums.condition import Condition


class TestGnollStats(EvenniaTest):
    """Gnoll should have correct L4 stats."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.gnoll = create.create_object(
            "typeclasses.actors.mobs.gnoll.Gnoll",
            key="a gnoll raider",
            location=self.room1,
        )
        self.gnoll.is_alive = True
        self.gnoll.hp = 40

    def test_gnoll_stats(self):
        self.assertEqual(self.gnoll.hp_max, 40)
        self.assertEqual(self.gnoll.damage_dice, "1d6")
        self.assertEqual(self.gnoll.level, 4)
        self.assertEqual(self.gnoll.strength, 14)
        self.assertEqual(self.gnoll.base_armor_class, 14)

    def test_gnoll_max_per_room(self):
        self.assertEqual(self.gnoll.max_per_room, 2)

    def test_low_aggro_threshold(self):
        """Gnolls fight to 25% HP before fleeing."""
        self.assertEqual(self.gnoll.aggro_hp_threshold, 0.25)

    def test_is_aggressive(self):
        self.assertTrue(self.gnoll.is_aggressive_to_players)


class TestGnollAggression(EvenniaTest):
    """Gnoll should aggro on players via AggressiveMob pattern."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.gnoll = create.create_object(
            "typeclasses.actors.mobs.gnoll.Gnoll",
            key="a gnoll raider",
            location=self.room1,
        )
        self.gnoll.is_alive = True
        self.gnoll.hp = 40

    @patch("typeclasses.mixins.aggressive_mixin.delay")
    def test_at_new_arrival_aggros_player(self, mock_delay):
        """Gnoll should schedule attack when a player enters."""
        self.char1.is_pc = True
        self.gnoll.at_new_arrival(self.char1)
        self.assertTrue(mock_delay.called)

    @patch("typeclasses.mixins.aggressive_mixin.delay")
    def test_no_aggro_when_low_health(self, mock_delay):
        """Gnoll should not aggro below 25% HP."""
        self.gnoll.hp = 5  # 12.5% — below 25% threshold
        self.char1.is_pc = True
        self.gnoll.at_new_arrival(self.char1)
        self.assertFalse(mock_delay.called)

    @patch("typeclasses.mixins.aggressive_mixin.delay")
    def test_ai_wander_targets_player(self, mock_delay):
        """ai_wander should attack player in room."""
        self.char1.is_pc = True
        self.char1.location = self.room1
        self.gnoll.ai_wander()
        self.assertTrue(mock_delay.called)


class TestGnollRampage(EvenniaTest):
    """Gnoll at_kill should trigger instant attack on next player."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.gnoll = create.create_object(
            "typeclasses.actors.mobs.gnoll.Gnoll",
            key="a gnoll raider",
            location=self.room1,
        )
        self.gnoll.is_alive = True
        self.gnoll.hp = 40

    @patch("combat.combat_utils.execute_attack")
    def test_rampage_attacks_next_player(self, mock_execute):
        """at_kill should fire execute_attack on another player in room."""
        # victim (just killed)
        victim = MagicMock()
        victim.is_pc = True
        victim.hp = 0

        # next target (still alive)
        self.char1.is_pc = True
        self.char1.hp = 30
        self.char1.location = self.room1

        # Ensure no other PCs in room that random.choice might pick
        self.char2.location = self.room2

        self.gnoll.at_kill(victim)

        mock_execute.assert_called_once_with(self.gnoll, self.char1)

    @patch("combat.combat_utils.execute_attack")
    def test_no_rampage_when_no_targets(self, mock_execute):
        """at_kill should not fire if no living players in room."""
        victim = MagicMock()
        victim.is_pc = True
        victim.hp = 0

        # Move all test chars out of the room
        self.char1.location = self.room2
        self.char2.location = self.room2

        self.gnoll.at_kill(victim)

        mock_execute.assert_not_called()

    @patch("combat.combat_utils.execute_attack")
    def test_no_rampage_when_dead(self, mock_execute):
        """Dead gnoll should not rampage."""
        self.gnoll.is_alive = False

        victim = MagicMock()
        self.char1.is_pc = True
        self.char1.hp = 30
        self.char1.location = self.room1

        self.gnoll.at_kill(victim)

        mock_execute.assert_not_called()

    @patch("combat.combat_utils.execute_attack")
    def test_rampage_skips_dead_players(self, mock_execute):
        """Rampage should not target players at 0 HP."""
        victim = MagicMock()
        victim.is_pc = True
        victim.hp = 0

        # All chars in room are dead
        self.char1.is_pc = True
        self.char1.hp = 0
        self.char1.location = self.room1
        self.char2.is_pc = True
        self.char2.hp = 0
        self.char2.location = self.room1

        self.gnoll.at_kill(victim)

        mock_execute.assert_not_called()


class TestGnollRampagePerception(EvenniaTest):
    """Rampage must not chain onto a character the gnoll cannot perceive."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"
    character_typeclass = "typeclasses.actors.character.FCMCharacter"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.gnoll = create.create_object(
            "typeclasses.actors.mobs.gnoll.Gnoll",
            key="a gnoll raider",
            location=self.room1,
        )
        self.gnoll.is_alive = True
        self.gnoll.hp = 40

        self.victim = MagicMock()
        self.victim.is_pc = True
        self.victim.hp = 0

        # char1 is the only live rampage candidate in the room
        self.char1.hp = 30
        self.char1.location = self.room1
        self.char2.location = self.room2

    @patch("combat.combat_utils.execute_attack")
    def test_rampage_attacks_a_visible_player(self, mock_execute):
        self.gnoll.at_kill(self.victim)
        mock_execute.assert_called_once_with(self.gnoll, self.char1)

    @patch("combat.combat_utils.execute_attack")
    def test_rampage_ignores_an_invisible_player(self, mock_execute):
        self.char1.add_condition(Condition.INVISIBLE)
        self.gnoll.at_kill(self.victim)
        mock_execute.assert_not_called()

    @patch("combat.combat_utils.execute_attack")
    def test_rampage_ignores_a_hidden_player(self, mock_execute):
        self.char1.add_condition(Condition.HIDDEN)
        self.gnoll.at_kill(self.victim)
        mock_execute.assert_not_called()

    @patch("combat.combat_utils.execute_attack")
    def test_detect_invis_lets_the_gnoll_rampage_on(self, mock_execute):
        self.char1.add_condition(Condition.INVISIBLE)
        self.gnoll.add_condition(Condition.DETECT_INVIS)
        self.gnoll.at_kill(self.victim)
        mock_execute.assert_called_once_with(self.gnoll, self.char1)

    @patch("combat.combat_utils.execute_attack")
    def test_the_broadcast_carries_names_as_mapping(self, mock_execute):
        """
        Names must resolve per recipient, not be formatted in up front —
        otherwise a concealed target is named to the whole room.
        """
        with patch.object(self.room1, "msg_contents") as mock_msg:
            self.gnoll.at_kill(self.victim)

        mapping = mock_msg.call_args.kwargs["mapping"]
        self.assertIs(mapping["target"], self.char1)
        self.assertIs(mapping["name"], self.gnoll)
        # The template travels unsubstituted
        self.assertIn("{target}", mock_msg.call_args.args[0])


class TestGnollRetreat(EvenniaTest):
    """Gnoll ai_retreating should flee to adjacent room."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.gnoll = create.create_object(
            "typeclasses.actors.mobs.gnoll.Gnoll",
            key="a gnoll raider",
            location=self.room1,
        )
        self.gnoll.is_alive = True
        self.gnoll.hp = 5  # 12.5% — below 25%
        self.gnoll.tags.clear(category="mob_area")  # allow free movement in tests

    def test_retreat_flees(self):
        """Wounded gnoll should flee to adjacent room."""
        self.gnoll.ai_retreating()
        self.assertEqual(self.gnoll.location, self.room2)

    def test_retreat_recovers(self):
        """Gnoll above threshold should switch back to wander."""
        self.gnoll.hp = 40  # full HP
        self.gnoll.ai_retreating()
        self.assertEqual(self.gnoll.ai.get_state(), "wander")
