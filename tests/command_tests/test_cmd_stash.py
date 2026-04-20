"""
Tests for CmdStash — currently stubbed pending passive redesign.

evennia test --settings settings tests.command_tests.test_cmd_stash
"""

from evennia.utils.test_resources import EvenniaCommandTest

from commands.class_skill_cmdsets.class_skill_cmds.cmd_stash import CmdStash


WALLET_A = "0xAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"


class TestCmdStash(EvenniaCommandTest):

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"
    character_typeclass = "typeclasses.actors.character.FCMCharacter"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.room1.always_lit = True
        self.account.attributes.add("wallet_address", WALLET_A)

    def test_stash_shows_stub_message(self):
        """Stash command shows the redesign stub message."""
        result = self.call(CmdStash(), "")
        self.assertIn("passive ability", result)

    def test_stash_with_args_shows_stub(self):
        """Stash with arguments still shows the stub message."""
        result = self.call(CmdStash(), "sword")
        self.assertIn("passive ability", result)
