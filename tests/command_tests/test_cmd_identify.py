"""
Tests for CmdIdentify — bard LORE skill for identifying items.

Actor identification is now handled by CmdRecognise (see test_cmd_recognise.py).

evennia test --settings settings tests.command_tests.test_cmd_identify
"""

from evennia.utils.test_resources import EvenniaCommandTest
from evennia.utils import create

from commands.class_skill_cmdsets.class_skill_cmds.cmd_identify import (
    CmdIdentify,
)
from enums.mastery_level import MasteryLevel
from enums.skills_enum import skills


WALLET_A = "0xAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"

_ROOM = "typeclasses.terrain.rooms.room_base.RoomBase"
_CHAR = "typeclasses.actors.character.FCMCharacter"


def _give_lore(char, mastery=MasteryLevel.BASIC):
    char.db.class_skill_mastery_levels = {
        skills.LORE.value: {
            "mastery": mastery.value,
            "classes": ["Bard"],
        },
    }


class TestCmdIdentify(EvenniaCommandTest):

    room_typeclass = _ROOM
    character_typeclass = _CHAR

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.room1.always_lit = True
        self.account.attributes.add("wallet_address", WALLET_A)

    # ── Argument validation ──

    def test_no_args(self):
        _give_lore(self.char1)
        self.call(CmdIdentify(), "", "Identify what?")

    def test_unskilled_rejected(self):
        """Character without LORE can't identify."""
        self.call(CmdIdentify(), "rock",
                  "You don't have enough lore knowledge")

    def test_target_not_found(self):
        _give_lore(self.char1)
        self.call(CmdIdentify(), "unicorn")
        # resolve_target returns None, command sends "don't see"

    # ── Mundane objects ──

    def test_mundane_object_sassy(self):
        """Non-actor, non-NFT objects get sassy one-liner."""
        create.create_object(
            "evennia.objects.objects.DefaultObject",
            key="rock",
            location=self.room1,
            nohome=True,
        )
        _give_lore(self.char1)
        self.call(CmdIdentify(), "rock",
                  "You study rock intently... rock is rock.")

    # ── Darkness ──

    def test_darkness_blocks(self):
        """Identify in darkness should fail."""
        _give_lore(self.char1)
        self.room1.always_lit = False
        self.room1.natural_light = False
        result = self.call(CmdIdentify(), "rock")
        self.assertIn("too dark", result)
