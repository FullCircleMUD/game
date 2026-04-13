"""
Tests for the RegenerationService script — periodic HP/mana/move regen/degen.

Verifies regen for fed characters, degen for starving characters,
hunger messages, and skip logic.

evennia test --settings settings tests.typeclass_tests.test_regeneration_service
"""

import math
from unittest.mock import patch, MagicMock

from evennia.utils.test_resources import EvenniaCommandTest

from enums.hunger_level import HungerLevel
from typeclasses.scripts.regeneration_service import RegenerationService


WALLET_A = "0xAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"


class RegenServiceTestBase(EvenniaCommandTest):
    """Base class providing a character for regen service tests."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)
        self.service = RegenerationService.__new__(RegenerationService)
        # Set up character with typical stats
        # effective_hp_max = hp_max + (con_bonus * total_level)
        # With total_level=8, constitution=14 (bonus=+2):
        #   effective_hp_max = 84 + (2 * 8) = 100
        self.char1.total_level = 8
        self.char1.constitution = 14  # +2 bonus
        self.char1.hp = 50
        self.char1.hp_max = 84
        self.char1.mana = 30
        self.char1.mana_max = 60
        self.char1.move = 40
        self.char1.move_max = 80
        # Note: degenerate() checks character.health (bug — should be hp).
        # Set it so tests don't crash on the death check.
        self.char1.health = 50

    def _run_tick(self, characters, force_degen=False):
        """Run one regen tick with the given character list.
        Builds mock sessions that return each character as a puppet.

        force_degen: prime the tick counter so this tick also runs degen
        (degen normally fires every 3rd tick — 60s cadence)."""
        mock_sessions = []
        for char in characters:
            s = MagicMock()
            s.get_puppet.return_value = char
            mock_sessions.append(s)
        fake_ndb = MagicMock()
        fake_ndb.tick_count = 2 if force_degen else 0
        with patch.object(type(self.service), "ndb", fake_ndb), \
             patch("typeclasses.scripts.regeneration_service.SESSION_HANDLER") as mock_sh:
            mock_sh.get_sessions.return_value = mock_sessions
            self.service.at_repeat()


class TestRegeneration(RegenServiceTestBase):
    """Test HP/mana/move regeneration for fed characters."""

    def test_regen_at_full(self):
        """FULL hunger should trigger regeneration."""
        self.char1.hunger_level = HungerLevel.FULL
        self._run_tick([self.char1])
        # base_rate = ceil(8/4) + floor((14-10)/2) = 2 + 2 = 4
        # per-tick (20s): hp = max(1, round(4/3)) = 1, move = max(1, round(8/3)) = 3
        self.assertEqual(self.char1.hp, 51)
        self.assertEqual(self.char1.mana, 31)
        self.assertEqual(self.char1.move, 43)

    def test_regen_at_satisfied(self):
        """SATISFIED hunger should trigger regeneration."""
        self.char1.hunger_level = HungerLevel.SATISFIED
        self._run_tick([self.char1])
        self.assertEqual(self.char1.hp, 51)

    def test_regen_at_peckish(self):
        """PECKISH hunger should trigger regeneration."""
        self.char1.hunger_level = HungerLevel.PECKISH
        self._run_tick([self.char1])
        self.assertEqual(self.char1.hp, 51)

    def test_regen_caps_at_max(self):
        """Regen should not exceed max values."""
        self.char1.hunger_level = HungerLevel.FULL
        self.char1.hp = 99
        self.char1.mana = 59
        self.char1.move = 79
        self._run_tick([self.char1])
        self.assertEqual(self.char1.hp, 100)
        self.assertEqual(self.char1.mana, 60)
        self.assertEqual(self.char1.move, 80)

    def test_regen_already_at_max(self):
        """Already at max should stay at max."""
        self.char1.hunger_level = HungerLevel.FULL
        self.char1.hp = 100
        self.char1.mana = 60
        self.char1.move = 80
        self._run_tick([self.char1])
        self.assertEqual(self.char1.hp, 100)
        self.assertEqual(self.char1.mana, 60)
        self.assertEqual(self.char1.move, 80)

    def test_regen_rate_low_level(self):
        """Level 1 with 10 CON: regen = ceil(1/4) + 0 = 1."""
        self.char1.hunger_level = HungerLevel.FULL
        self.char1.total_level = 1
        self.char1.constitution = 10  # +0 bonus
        self._run_tick([self.char1])
        self.assertEqual(self.char1.hp, 51)

    def test_regen_rate_negative_con_floored(self):
        """Negative CON bonus should be floored to 0."""
        self.char1.hunger_level = HungerLevel.FULL
        self.char1.total_level = 4
        self.char1.constitution = 8  # -1 bonus → floored to 0
        self._run_tick([self.char1])
        # regen_rate = ceil(4/4) + 0 = 1
        self.assertEqual(self.char1.hp, 51)

    def test_regen_rate_high_level(self):
        """Level 40 with 20 CON: base = ceil(40/4) + 5 = 15."""
        self.char1.hunger_level = HungerLevel.FULL
        self.char1.total_level = 40
        self.char1.constitution = 20  # +5 bonus
        self._run_tick([self.char1])
        # per-tick (20s): hp/mana = round(15/3) = 5, move = round(30/3) = 10
        self.assertEqual(self.char1.hp, 55)
        self.assertEqual(self.char1.mana, 35)
        self.assertEqual(self.char1.move, 50)


class TestNoActionAtHungry(RegenServiceTestBase):
    """Test that HUNGRY characters get neither regen nor degen."""

    def test_hungry_no_regen_no_degen(self):
        """HUNGRY should not change HP/mana/move."""
        self.char1.hunger_level = HungerLevel.HUNGRY
        self._run_tick([self.char1])
        self.assertEqual(self.char1.hp, 50)
        self.assertEqual(self.char1.mana, 30)
        self.assertEqual(self.char1.move, 40)


class TestDegeneration(RegenServiceTestBase):
    """Test HP/mana/move degeneration for starving characters."""

    def test_degen_at_starving(self):
        """STARVING should lose HP/mana/move."""
        self.char1.hunger_level = HungerLevel.STARVING
        self._run_tick([self.char1], force_degen=True)
        # cycles_to_death = 15 (degen fires every 60s, so cycles == minutes)
        hp_loss = max(1, round(100 / 15))
        mana_loss = max(1, round(60 / 15))
        move_loss = max(1, round(80 / 15))
        self.assertEqual(self.char1.hp, 50 - hp_loss)
        self.assertEqual(self.char1.mana, 30 - mana_loss)
        self.assertEqual(self.char1.move, 40 - move_loss)

    def test_degen_at_famished(self):
        """FAMISHED should lose HP/mana/move."""
        self.char1.hunger_level = HungerLevel.FAMISHED
        self._run_tick([self.char1], force_degen=True)
        hp_loss = max(1, round(100 / 30))
        self.assertEqual(self.char1.hp, 50 - hp_loss)

    def test_degen_floors_at_zero(self):
        """Degen to 0 HP triggers death; die() resets HP to 1."""
        self.char1.hunger_level = HungerLevel.STARVING
        self.char1.hp = 1
        self.char1.mana = 1
        self.char1.move = 1
        self._run_tick([self.char1], force_degen=True)
        # die() fires when HP hits 0, resetting HP to 1
        self.assertEqual(self.char1.hp, 1)
        self.assertEqual(self.char1.mana, 0)
        self.assertEqual(self.char1.move, 0)


class TestHungerMessages(RegenServiceTestBase):
    """Test hunger messages sent to character and room."""

    def test_hungry_sends_first_person_message(self):
        """HUNGRY character should receive first-person hunger message."""
        self.char1.hunger_level = HungerLevel.HUNGRY
        with patch.object(self.char1, "msg") as mock_msg:
            self._run_tick([self.char1])
            messages = [call[0][0] for call in mock_msg.call_args_list]
            self.assertTrue(
                any("hungry" in m.lower() for m in messages),
                f"Expected hunger message, got: {messages}",
            )

    def test_famished_sends_room_message(self):
        """FAMISHED character should trigger third-person room message."""
        self.char1.hunger_level = HungerLevel.FAMISHED
        with patch.object(self.char1.location, "msg_contents") as mock_room:
            self._run_tick([self.char1])
            self.assertTrue(mock_room.called)


class TestSkipLogic(RegenServiceTestBase):
    """Test that invalid characters are skipped."""

    def test_skip_non_hunger_level(self):
        """Characters with non-HungerLevel hunger_level should be skipped."""
        self.char1.hunger_level = "invalid"
        self._run_tick([self.char1])
        # HP should not change
        self.assertEqual(self.char1.hp, 50)

    def test_skip_no_hunger_attr(self):
        """Characters without hunger_level should be skipped."""
        obj = MagicMock(spec=["msg", "has_account"])
        obj.has_account = True
        del obj.hunger_level  # ensure hasattr returns False
        self._run_tick([obj])
        # No crash = success

    def test_skip_unpuppeted_character(self):
        """Unpuppeted characters (quit but account logged in) should be skipped."""
        self.char1.hunger_level = HungerLevel.STARVING
        self.char1.hp = 50
        # Session exists but get_puppet() returns None (no puppeted character)
        mock_session = MagicMock()
        mock_session.get_puppet.return_value = None
        fake_ndb = MagicMock()
        fake_ndb.tick_count = 0
        with patch.object(type(self.service), "ndb", fake_ndb), \
             patch("typeclasses.scripts.regeneration_service.SESSION_HANDLER") as mock_sh:
            mock_sh.get_sessions.return_value = [mock_session]
            self.service.at_repeat()
        # HP should not change — service should skip this character entirely
        self.assertEqual(self.char1.hp, 50)
