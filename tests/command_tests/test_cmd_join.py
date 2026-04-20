"""
Tests for CmdJoin — join an ally's fight.

evennia test --settings settings tests.command_tests.test_cmd_join
"""

from unittest.mock import patch

from evennia.utils.test_resources import EvenniaCommandTest
from evennia.utils import create

from commands.all_char_cmds.cmd_join import CmdJoin


class TestCmdJoin(EvenniaCommandTest):
    """Test joining an ally's fight."""

    character_typeclass = "typeclasses.actors.character.FCMCharacter"
    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.room1.always_lit = True
        self.room1.allow_combat = True
        self.room1.allow_pvp = True
        self.char1.hp = 50
        self.char1.hp_max = 50
        self.char2.hp = 50
        self.char2.hp_max = 50
        # Create a mob-like third character as the enemy
        self.enemy = create.create_object(
            "typeclasses.actors.character.FCMCharacter",
            key="Goblin",
            location=self.room1,
        )
        self.enemy.hp = 30
        self.enemy.hp_max = 30

    def tearDown(self):
        for char in (self.char1, self.char2, self.enemy):
            if char.pk:
                handlers = char.scripts.get("combat_handler")
                if handlers:
                    for h in handlers:
                        h.stop()
                        h.delete()
        if self.enemy.pk:
            self.enemy.delete()
        super().tearDown()

    def test_join_no_args(self):
        """join with no args shows usage."""
        result = self.call(CmdJoin(), "", caller=self.char1)
        self.assertIn("Join who", result)

    def test_join_self(self):
        """Can't join your own fight."""
        result = self.call(CmdJoin(), "Char", caller=self.char1)
        self.assertIn("your own fight", result)

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_join_ally_not_in_combat(self, mock_ticker):
        """Can't join if ally isn't in combat."""
        result = self.call(CmdJoin(), "Char2", caller=self.char1)
        self.assertIn("not in combat", result)

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_join_enters_combat(self, mock_ticker):
        """Joining puts you in combat against ally's target."""
        from combat.combat_utils import enter_combat
        enter_combat(self.char2, self.enemy)

        # Queue attack so char2 has a combat_target
        handler = self.char2.scripts.get("combat_handler")[0]
        handler.queue_action({
            "key": "attack", "target": self.enemy, "dt": 3, "repeat": True,
        })

        result = self.call(CmdJoin(), "Char2", caller=self.char1)
        self.assertIn("join", result.lower())
        self.assertIn("Goblin", result)

        # char1 should now be in combat
        self.assertTrue(self.char1.scripts.get("combat_handler"))
        # char1's target should be the enemy
        self.assertEqual(self.char1.ndb.combat_target, self.enemy)

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_join_already_fighting_same_target(self, mock_ticker):
        """Can't join if already fighting the same target."""
        from combat.combat_utils import enter_combat
        enter_combat(self.char2, self.enemy)
        enter_combat(self.char1, self.enemy)

        # Set combat targets
        for char in (self.char1, self.char2):
            h = char.scripts.get("combat_handler")[0]
            h.queue_action({
                "key": "attack", "target": self.enemy, "dt": 3, "repeat": True,
            })

        result = self.call(CmdJoin(), "Char2", caller=self.char1)
        self.assertIn("already fighting", result)
