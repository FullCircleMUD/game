"""
Tests for CmdRecognise — bard LORE skill for identifying creatures/actors.

evennia test --settings settings tests.command_tests.test_cmd_recognise
"""

from evennia.utils.test_resources import EvenniaCommandTest
from evennia.utils import create

from commands.class_skill_cmdsets.class_skill_cmds.cmd_recognise import (
    CmdRecognise,
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


def _make_mob(location, level=3, **kwargs):
    """Create a CombatMob for testing."""
    from typeclasses.actors.mob import CombatMob
    mob = create.create_object(CombatMob, key="test goblin",
                               location=location, nohome=True)
    mob.level = level
    mob.hp = kwargs.get("hp", 20)
    mob.hp_max = kwargs.get("hp_max", 20)
    mob.mana = kwargs.get("mana", 0)
    mob.mana_max = kwargs.get("mana_max", 0)
    mob.move = kwargs.get("move", 10)
    mob.move_max = kwargs.get("move_max", 10)
    mob.damage_dice = kwargs.get("damage_dice", "1d6")
    mob.attack_message = kwargs.get("attack_message", "slashes")
    mob.size = kwargs.get("size", "medium")
    mob.strength = kwargs.get("strength", 14)
    mob.dexterity = kwargs.get("dexterity", 12)
    mob.constitution = kwargs.get("constitution", 13)
    mob.intelligence = kwargs.get("intelligence", 8)
    mob.wisdom = kwargs.get("wisdom", 10)
    mob.charisma = kwargs.get("charisma", 6)
    mob.armor_class = kwargs.get("armor_class", 2)
    mob.damage_resistances = kwargs.get("damage_resistances", {})
    return mob


class TestCmdRecognise(EvenniaCommandTest):

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
        self.call(CmdRecognise(), "", "Recognise what?")

    def test_unskilled_rejected(self):
        """Character without LORE can't recognise."""
        self.call(CmdRecognise(), "goblin",
                  "You don't have enough lore knowledge")

    def test_target_not_found(self):
        _give_lore(self.char1)
        result = self.call(CmdRecognise(), "nobody_here")
        self.assertIn("no 'nobody_here' here", result)

    # ── Actor identification ──

    def test_recognise_mob_basic(self):
        """Level 3 mob with BASIC lore shows full stat template."""
        mob = _make_mob(self.room1, level=3)
        _give_lore(self.char1, MasteryLevel.BASIC)
        result = self.call(CmdRecognise(), "test goblin",
                           "Identify: test goblin")
        self.assertIn("STR:", result)
        self.assertIn("HP:", result)

    def test_recognise_mob_too_powerful(self):
        """Level 16 mob with BASIC lore shows 'too powerful'."""
        mob = _make_mob(self.room1, level=16)
        _give_lore(self.char1, MasteryLevel.BASIC)
        self.call(CmdRecognise(), "test goblin",
                  "You study test goblin intently but the creature")

    def test_recognise_mob_mastery_tiers(self):
        """LORE mastery gates match the spell's level-to-tier boundaries."""
        test_cases = [
            (5, MasteryLevel.BASIC, True),
            (6, MasteryLevel.BASIC, False),
            (6, MasteryLevel.SKILLED, True),
            (15, MasteryLevel.SKILLED, True),
            (16, MasteryLevel.SKILLED, False),
            (16, MasteryLevel.EXPERT, True),
        ]
        for mob_level, mastery, expect_stats in test_cases:
            mob = _make_mob(self.room1, level=mob_level)
            _give_lore(self.char1, mastery)
            result = self.call(CmdRecognise(), "test goblin")
            has_stats = "STR:" in result
            self.assertEqual(
                has_stats, expect_stats,
                f"level={mob_level}, mastery={mastery.name}: "
                f"expected stats={expect_stats}, got={has_stats}"
            )
            mob.delete()

    # ── PvP restriction ──

    def test_pvp_restriction_blocks(self):
        """Can't recognise other players in non-PvP rooms."""
        _give_lore(self.char1)
        self.call(CmdRecognise(), "Char2",
                  "You can only recognise other players in PvP areas")

    def test_pvp_allowed(self):
        """Can recognise other players in PvP rooms."""
        self.room1.allow_pvp = True
        _give_lore(self.char1, MasteryLevel.BASIC)
        result = self.call(CmdRecognise(), "Char2", "Identify: Char2")
        self.assertIn("STR:", result)
        self.room1.allow_pvp = False

    def test_recognise_self(self):
        """Can recognise yourself without PvP room."""
        _give_lore(self.char1, MasteryLevel.BASIC)
        result = self.call(CmdRecognise(), "me", "Identify: Char")
        self.assertIn("STR:", result)

    # ── Darkness ──

    def test_darkness_blocks(self):
        """Recognise in darkness should fail."""
        _give_lore(self.char1)
        mob = _make_mob(self.room1, level=3)
        self.room1.always_lit = False
        self.room1.natural_light = False
        result = self.call(CmdRecognise(), "test goblin")
        self.assertIn("too dark", result)
