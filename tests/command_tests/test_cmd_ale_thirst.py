"""
Tests for the inn `ale` command's thirst restoration.

Ale steps the thirst meter up by ONE stage per mug — parallel to how
stew raises hunger by one level per bowl. Drink multiple ales to fully
refresh.

The gold sink path goes through GoldService.sink which needs a real
FungibleGameState row, so we mock has_gold + return_gold_to_sink to
isolate the test to the thirst side-effect.
"""

from unittest.mock import patch

from evennia.utils.test_resources import EvenniaCommandTest

from commands.room_specific_cmds.inn.cmd_ale import CmdAle
from enums.thirst_level import ThirstLevel


class TestCmdAleThirst(EvenniaCommandTest):
    room_typeclass = "typeclasses.terrain.rooms.room_inn.RoomInn"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.char1.thirst_free_pass_tick = False

    @patch("typeclasses.actors.character.FCMCharacter.return_gold_to_sink")
    @patch("typeclasses.actors.character.FCMCharacter.has_gold", return_value=True)
    def test_ale_steps_thirst_up_by_one(self, _has_gold, _sink):
        self.char1.thirst_level = ThirstLevel.PARCHED  # 3
        self.call(CmdAle(), "")
        self.assertEqual(self.char1.thirst_level, ThirstLevel.VERY_THIRSTY)  # 4

    @patch("typeclasses.actors.character.FCMCharacter.return_gold_to_sink")
    @patch("typeclasses.actors.character.FCMCharacter.has_gold", return_value=True)
    def test_ale_at_refreshed_minus_one_lands_at_refreshed(self, _has_gold, _sink):
        self.char1.thirst_level = ThirstLevel.HYDRATED  # 11
        self.call(CmdAle(), "")
        self.assertEqual(self.char1.thirst_level, ThirstLevel.REFRESHED)  # 12

    @patch("typeclasses.actors.character.FCMCharacter.return_gold_to_sink")
    @patch("typeclasses.actors.character.FCMCharacter.has_gold", return_value=True)
    def test_ale_at_refreshed_does_not_overflow(self, _has_gold, _sink):
        self.char1.thirst_level = ThirstLevel.REFRESHED
        self.call(CmdAle(), "")
        self.assertEqual(self.char1.thirst_level, ThirstLevel.REFRESHED)

    @patch("typeclasses.actors.character.FCMCharacter.return_gold_to_sink")
    @patch("typeclasses.actors.character.FCMCharacter.has_gold", return_value=True)
    def test_ale_sets_free_pass_only_when_landing_at_refreshed(self, _has_gold, _sink):
        # Mid-meter ale should NOT set the free-pass tick.
        self.char1.thirst_level = ThirstLevel.PARCHED
        self.call(CmdAle(), "")
        self.assertFalse(self.char1.thirst_free_pass_tick)

        # Ale that lands them at REFRESHED SHOULD set the free-pass tick.
        self.char1.thirst_level = ThirstLevel.HYDRATED
        self.char1.thirst_free_pass_tick = False
        self.call(CmdAle(), "")
        self.assertTrue(self.char1.thirst_free_pass_tick)

    @patch("typeclasses.actors.character.FCMCharacter.has_gold", return_value=False)
    def test_ale_no_gold_does_not_restore_thirst(self, _has_gold):
        self.char1.thirst_level = ThirstLevel.PARCHED
        self.call(CmdAle(), "")
        self.assertEqual(self.char1.thirst_level, ThirstLevel.PARCHED)
