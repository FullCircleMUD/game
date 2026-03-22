"""
Tests for CmdFlee — flee from combat or comic panic run.

evennia test --settings settings tests.command_tests.test_cmd_flee
"""

from unittest.mock import patch, MagicMock

from evennia.utils.test_resources import EvenniaCommandTest
from evennia.utils import create

from commands.all_char_cmds.cmd_flee import CmdFlee


class TestCmdFleeInCombat(EvenniaCommandTest):
    """Test flee during combat."""

    character_typeclass = "typeclasses.actors.character.FCMCharacter"
    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.room1.allow_combat = True
        self.room1.allow_pvp = True
        self.char1.hp = 20
        self.char1.hp_max = 20
        self.char2.hp = 20
        self.char2.hp_max = 20
        # Remove Evennia's default "out" exit so we control exits precisely
        if self.exit:
            self.exit.delete()
            self.exit = None
        # Create a single exit from room1 to room2
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

    @patch("commands.all_char_cmds.cmd_flee.dice")
    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_flee_success_moves_to_random_exit(self, mock_ticker, mock_dice):
        """Successful flee moves character to exit destination."""
        mock_dice.roll.return_value = 15
        from combat.combat_utils import enter_combat
        enter_combat(self.char1, self.char2)

        result = self.call(CmdFlee(), "", caller=self.char1)
        self.assertIn("flee", result.lower())
        self.assertEqual(self.char1.location, self.room2)

    @patch("commands.all_char_cmds.cmd_flee.dice")
    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_flee_success_removes_combat_handler(self, mock_ticker, mock_dice):
        """Successful flee removes the combat handler."""
        mock_dice.roll.return_value = 15
        from combat.combat_utils import enter_combat
        enter_combat(self.char1, self.char2)

        self.call(CmdFlee(), "", caller=self.char1)
        self.assertFalse(self.char1.scripts.get("combat_handler"))

    @patch("commands.all_char_cmds.cmd_flee.dice")
    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_flee_fail_stays_in_room(self, mock_ticker, mock_dice):
        """Failed flee keeps character in original room."""
        mock_dice.roll.return_value = 1
        self.char1.dexterity = 8  # -1 mod, total = 0
        from combat.combat_utils import enter_combat
        enter_combat(self.char1, self.char2)

        result = self.call(CmdFlee(), "", caller=self.char1)
        self.assertIn("can't escape", result)
        self.assertEqual(self.char1.location, self.room1)

    @patch("commands.all_char_cmds.cmd_flee.dice")
    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_flee_fail_enemies_get_advantage(self, mock_ticker, mock_dice):
        """Failed flee gives all enemies 1 round of advantage."""
        mock_dice.roll.return_value = 1
        self.char1.dexterity = 8
        from combat.combat_utils import enter_combat
        enter_combat(self.char1, self.char2)

        self.call(CmdFlee(), "", caller=self.char1)

        # char2 (enemy) should have advantage against char1
        enemy_handler = self.char2.scripts.get("combat_handler")
        self.assertTrue(enemy_handler)
        self.assertTrue(enemy_handler[0].has_advantage(self.char1))
        self.assertEqual(enemy_handler[0].advantage_against[self.char1.id], 1)

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_flee_no_exits(self, mock_ticker):
        """Flee with no available exits shows error."""
        from combat.combat_utils import enter_combat
        enter_combat(self.char1, self.char2)
        # Remove the exit
        self.exit1.delete()
        self.exit1 = None

        result = self.call(CmdFlee(), "", caller=self.char1)
        self.assertIn("nowhere to go", result)
        self.assertEqual(self.char1.location, self.room1)

    @patch("commands.all_char_cmds.cmd_flee.dice")
    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_flee_combat_ends_for_remaining(self, mock_ticker, mock_dice):
        """After flee, remaining side's combat ends if no enemies left."""
        mock_dice.roll.return_value = 15
        from combat.combat_utils import enter_combat
        enter_combat(self.char1, self.char2)

        self.call(CmdFlee(), "", caller=self.char1)

        # char2 should also have combat ended (no enemies left in room)
        self.assertFalse(self.char2.scripts.get("combat_handler"))

    @patch("commands.all_char_cmds.cmd_flee.dice")
    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_flee_locked_exit_filtered(self, mock_ticker, mock_dice):
        """Exits that fail traverse check are filtered out."""
        mock_dice.roll.return_value = 15
        from combat.combat_utils import enter_combat
        enter_combat(self.char1, self.char2)

        # Lock the only exit so traverse fails
        self.exit1.locks.add("traverse:false()")

        result = self.call(CmdFlee(), "", caller=self.char1)
        self.assertIn("nowhere to go", result)
        self.assertEqual(self.char1.location, self.room1)


class TestCmdFleeOutOfCombat(EvenniaCommandTest):
    """Test flee when not in combat (comic panic run)."""

    character_typeclass = "typeclasses.actors.character.FCMCharacter"
    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.char1.hp = 20
        self.char1.hp_max = 20
        # Remove Evennia's default "out" exit
        if self.exit:
            self.exit.delete()
            self.exit = None
        # Create a single exit
        self.exit1 = create.create_object(
            "evennia.objects.objects.DefaultExit",
            key="south",
            location=self.room1,
            destination=self.room2,
        )

    def tearDown(self):
        if self.exit1:
            self.exit1.delete()
        super().tearDown()

    def test_flee_not_in_combat_moves(self):
        """Out-of-combat flee moves through random exit."""
        result = self.call(CmdFlee(), "", caller=self.char1)
        self.assertIn("panic", result)
        self.assertEqual(self.char1.location, self.room2)

    def test_flee_not_in_combat_no_exits(self):
        """Out-of-combat flee with no exits shows panic message."""
        self.exit1.delete()
        self.exit1 = None

        result = self.call(CmdFlee(), "", caller=self.char1)
        self.assertIn("nowhere to run", result)
        self.assertEqual(self.char1.location, self.room1)
