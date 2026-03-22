"""
Tests for CmdShow — showing hidden objects to other players.

evennia test --settings settings tests.command_tests.test_cmd_show
"""

from evennia.utils.test_resources import EvenniaCommandTest
from evennia.utils import create

from commands.all_char_cmds.cmd_show import CmdShow


WALLET_A = "0xAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
WALLET_B = "0xBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB"


class TestCmdShow(EvenniaCommandTest):

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)
        self.char1.db.character_key = "char1_key"
        self.char2.db.character_key = "char2_key"

    def _make_hidden_fixture(self, key="hidden crevice", find_dc=10):
        obj = create.create_object(
            "typeclasses.world_objects.base_fixture.WorldFixture",
            key=key,
            location=self.room1,
            nohome=True,
        )
        obj.is_hidden = True
        obj.find_dc = find_dc
        return obj

    # ── Success case ───────────────────────────────────────────

    def test_show_adds_to_discovered_by(self):
        """Showing a hidden object adds target to discovered_by."""
        obj = self._make_hidden_fixture()
        # Caller discovers it first
        discovered = set(obj.discovered_by)
        discovered.add("char1_key")
        obj.discovered_by = discovered

        self.call(
            CmdShow(), "hidden crevice to Char2",
            "You point out hidden crevice to Char2.",
            caller=self.char1,
        )
        self.assertIn("char2_key", set(obj.discovered_by))

    # ── Info-leak prevention ───────────────────────────────────

    def test_show_undiscovered_gives_generic_not_found(self):
        """If caller hasn't discovered the object, get generic 'not found'."""
        self._make_hidden_fixture()
        self.call(
            CmdShow(), "hidden crevice to Char2",
            "Could not find 'hidden crevice'.",
            caller=self.char1,
        )

    # ── Non-hidden object ──────────────────────────────────────

    def test_show_non_hidden_object(self):
        """Showing a non-hidden-type object gives 'not something you need to point out'."""
        create.create_object(
            "evennia.objects.objects.DefaultObject",
            key="sword",
            location=self.room1,
        )
        self.call(
            CmdShow(), "sword to Char2",
            "That's not something you need to point out.",
            caller=self.char1,
        )

    # ── Already visible ────────────────────────────────────────

    def test_show_already_visible_to_everyone(self):
        """If object is not hidden (is_hidden=False), it's already visible."""
        obj = self._make_hidden_fixture()
        obj.is_hidden = False  # Discovered by someone, visible to all
        # Caller has it in discovered_by so passes visibility check
        discovered = set(obj.discovered_by)
        discovered.add("char1_key")
        obj.discovered_by = discovered

        self.call(
            CmdShow(), "hidden crevice to Char2",
            "That's already visible to everyone.",
            caller=self.char1,
        )

    # ── Target already discovered ──────────────────────────────

    def test_show_target_already_discovered(self):
        """If target has already found the object, say so."""
        obj = self._make_hidden_fixture()
        discovered = {"char1_key", "char2_key"}
        obj.discovered_by = discovered

        self.call(
            CmdShow(), "hidden crevice to Char2",
            "Char2 has already found hidden crevice.",
            caller=self.char1,
        )

    # ── No args ────────────────────────────────────────────────

    def test_show_no_args(self):
        """No arguments gives usage message."""
        self.call(CmdShow(), "", "Usage: show <object> to <character>")

    # ── Show to self ───────────────────────────────────────────

    def test_show_to_self(self):
        """Cannot show something to yourself."""
        obj = self._make_hidden_fixture()
        discovered = set(obj.discovered_by)
        discovered.add("char1_key")
        obj.discovered_by = discovered

        self.call(
            CmdShow(), "hidden crevice to Char",
            "You already know about that.",
            caller=self.char1,
        )
