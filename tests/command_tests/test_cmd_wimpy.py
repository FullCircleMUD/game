"""
Tests for CmdWimpy — auto-flee HP threshold command and _wimpy_flee() logic.

evennia test --settings settings tests.command_tests.test_cmd_wimpy
"""

from unittest.mock import patch

from evennia.utils.test_resources import EvenniaCommandTest
from evennia.utils import create

from commands.all_char_cmds.cmd_wimpy import CmdWimpy


class TestCmdWimpy(EvenniaCommandTest):
    """Test the wimpy command (set/show/disable threshold)."""

    character_typeclass = "typeclasses.actors.character.FCMCharacter"
    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.char1.hp = 50
        self.char1.hp_max = 50

    def test_show_wimpy_off(self):
        """No args with wimpy disabled shows 'off'."""
        self.char1.wimpy_threshold = 0
        result = self.call(CmdWimpy(), "", caller=self.char1)
        self.assertIn("off", result.lower())

    def test_show_wimpy_on(self):
        """No args with wimpy enabled shows current value."""
        self.char1.wimpy_threshold = 15
        result = self.call(CmdWimpy(), "", caller=self.char1)
        self.assertIn("15", result)

    def test_set_wimpy(self):
        """wimpy <number> sets threshold."""
        self.call(CmdWimpy(), "20", caller=self.char1)
        self.assertEqual(self.char1.wimpy_threshold, 20)

    def test_wimpy_off(self):
        """wimpy off disables."""
        self.char1.wimpy_threshold = 15
        self.call(CmdWimpy(), "off", caller=self.char1)
        self.assertEqual(self.char1.wimpy_threshold, 0)

    def test_wimpy_zero(self):
        """wimpy 0 disables."""
        self.char1.wimpy_threshold = 15
        self.call(CmdWimpy(), "0", caller=self.char1)
        self.assertEqual(self.char1.wimpy_threshold, 0)

    def test_wimpy_negative_rejected(self):
        """Negative wimpy value is rejected."""
        result = self.call(CmdWimpy(), "-5", caller=self.char1)
        self.assertIn("positive", result.lower())
        self.assertEqual(self.char1.wimpy_threshold, 0)

    def test_wimpy_invalid_rejected(self):
        """Non-numeric wimpy value is rejected."""
        result = self.call(CmdWimpy(), "abc", caller=self.char1)
        self.assertIn("usage", result.lower())

    def test_wimpy_capped_at_50_pct(self):
        """Wimpy threshold can't exceed 50% of max HP."""
        max_hp = self.char1.effective_hp_max
        too_high = max_hp  # 100% — way over cap
        result = self.call(CmdWimpy(), str(too_high), caller=self.char1)
        self.assertIn("50%", result)
        self.assertEqual(self.char1.wimpy_threshold, 0)


class TestWimpyFlee(EvenniaCommandTest):
    """Test _wimpy_flee() auto-flee during combat."""

    character_typeclass = "typeclasses.actors.character.FCMCharacter"
    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.room1.allow_combat = True
        self.room1.allow_pvp = True
        self.char1.hp = 50
        self.char1.hp_max = 50
        self.char2.hp = 50
        self.char2.hp_max = 50
        # Remove default exit
        if self.exit:
            self.exit.delete()
            self.exit = None
        # Create controlled exit
        self.exit1 = create.create_object(
            "evennia.objects.objects.DefaultExit",
            key="north",
            location=self.room1,
            destination=self.room2,
        )

    def tearDown(self):
        for char in (self.char1, self.char2):
            handlers = char.scripts.get("combat_handler")
            if handlers:
                for h in handlers:
                    h.stop()
                    h.delete()
        if self.exit1:
            self.exit1.delete()
        super().tearDown()

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_wimpy_triggers_flee(self, mock_ticker):
        """HP below wimpy threshold in combat triggers auto-flee."""
        from combat.combat_utils import enter_combat
        enter_combat(self.char1, self.char2)

        self.char1.wimpy_threshold = 15
        self.char1.hp = 10  # below threshold
        self.char1._wimpy_flee()

        self.assertEqual(self.char1.location, self.room2)
        self.assertFalse(self.char1.scripts.get("combat_handler"))

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_wimpy_no_flee_above_threshold(self, mock_ticker):
        """HP above wimpy threshold does NOT trigger flee."""
        from combat.combat_utils import enter_combat
        enter_combat(self.char1, self.char2)

        self.char1.wimpy_threshold = 15
        self.char1.hp = 20  # above threshold
        self.char1._wimpy_flee()

        self.assertEqual(self.char1.location, self.room1)
        self.assertTrue(self.char1.scripts.get("combat_handler"))

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_wimpy_disabled_no_flee(self, mock_ticker):
        """Wimpy at 0 does NOT trigger flee."""
        from combat.combat_utils import enter_combat
        enter_combat(self.char1, self.char2)

        self.char1.wimpy_threshold = 0
        self.char1.hp = 5
        self.char1._wimpy_flee()

        self.assertEqual(self.char1.location, self.room1)

    def test_wimpy_not_in_combat_no_flee(self):
        """Wimpy does NOT trigger when not in combat."""
        self.char1.wimpy_threshold = 15
        self.char1.hp = 5
        self.char1._wimpy_flee()

        self.assertEqual(self.char1.location, self.room1)

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_wimpy_no_exits_stays(self, mock_ticker):
        """Wimpy with no open exits stays in room."""
        from combat.combat_utils import enter_combat
        enter_combat(self.char1, self.char2)

        # Remove all exits
        self.exit1.delete()
        self.exit1 = None

        self.char1.wimpy_threshold = 15
        self.char1.hp = 5
        self.char1._wimpy_flee()

        self.assertEqual(self.char1.location, self.room1)
        # Still in combat (couldn't flee)
        self.assertTrue(self.char1.scripts.get("combat_handler"))

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_wimpy_ends_enemy_combat(self, mock_ticker):
        """Wimpy flee cleans up combat for remaining enemies."""
        from combat.combat_utils import enter_combat
        enter_combat(self.char1, self.char2)

        self.char1.wimpy_threshold = 15
        self.char1.hp = 5
        self.char1._wimpy_flee()

        # char2 should also have combat ended (no enemies left)
        self.assertFalse(self.char2.scripts.get("combat_handler"))

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_wimpy_via_take_damage(self, mock_ticker):
        """take_damage() triggers wimpy flee when HP drops below threshold."""
        from combat.combat_utils import enter_combat
        enter_combat(self.char1, self.char2)

        self.char1.wimpy_threshold = 15
        self.char1.hp = 20
        # Deal 10 damage → HP drops to 10, below wimpy of 15
        self.char1.take_damage(10, cause="combat")

        self.assertEqual(self.char1.location, self.room2)
        self.assertFalse(self.char1.scripts.get("combat_handler"))
