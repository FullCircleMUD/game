"""
Tests for the roomdesc command.

evennia test --settings settings tests.command_tests.test_cmd_roomdesc
"""

from evennia.utils.test_resources import EvenniaCommandTest

from commands.all_char_cmds.cmd_roomdesc import CmdRoomDesc


WALLET_A = "0xAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"


class TestCmdRoomDesc(EvenniaCommandTest):
    """Test the roomdesc command."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)

    # ── Show default ──────────────────────────────────────────────────

    def test_show_default_roomdesc(self):
        """No args shows the default room description."""
        result = self.call(CmdRoomDesc(), "")
        self.assertIn("default", result)
        self.assertIn(self.char1.key, result)
        self.assertIn("unremarkable", result)

    # ── Set custom ────────────────────────────────────────────────────

    def test_set_custom_roomdesc(self):
        """Setting a custom room description stores it."""
        result = self.call(CmdRoomDesc(), "A grizzled warrior stands here.")
        self.assertIn("set to", result)
        self.assertIn("grizzled warrior", result)
        self.assertEqual(
            self.char1.room_description, "A grizzled warrior stands here."
        )

    def test_set_roomdesc_with_name_placeholder(self):
        """The {name} placeholder is replaced with character name."""
        self.call(CmdRoomDesc(), "{name} the brave stands watch here.")
        desc = self.char1.get_room_description()
        self.assertIn(self.char1.key, desc)
        self.assertNotIn("{name}", desc)

    # ── Clear ─────────────────────────────────────────────────────────

    def test_clear_roomdesc(self):
        """'roomdesc clear' resets to default."""
        self.call(CmdRoomDesc(), "A custom desc.")
        result = self.call(CmdRoomDesc(), "clear")
        self.assertIn("reset to default", result)
        self.assertIsNone(self.char1.room_description)

    # ── Length limit ──────────────────────────────────────────────────

    def test_roomdesc_too_long(self):
        """Descriptions exceeding the max length are rejected."""
        long_text = "x" * 201
        result = self.call(CmdRoomDesc(), long_text)
        self.assertIn("too long", result)
        self.assertIsNone(self.char1.room_description)

    # ── Show custom ───────────────────────────────────────────────────

    def test_show_custom_roomdesc(self):
        """No args with custom desc shows it without '(default)' label."""
        self.call(CmdRoomDesc(), "A tall elf stands here.")
        result = self.call(CmdRoomDesc(), "")
        self.assertIn("tall elf", result)
        self.assertNotIn("default", result)
