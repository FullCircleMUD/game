"""
Tests for the pickpocket command — steal from a cased target.

evennia test --settings settings tests.command_tests.test_cmd_pickpocket
"""

import time
from unittest.mock import patch

from evennia.utils.test_resources import EvenniaCommandTest
from evennia.utils import create

from commands.class_skill_cmdsets.class_skill_cmds.cmd_pickpocket import CmdPickpocket
from enums.condition import Condition
from enums.mastery_level import MasteryLevel
from enums.skills_enum import skills

_ROOM = "typeclasses.terrain.rooms.room_base.RoomBase"
_CHAR = "typeclasses.actors.character.FCMCharacter"

WALLET_A = "0xAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
WALLET_B = "0xBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB"


def _set_subterfuge(char, mastery=MasteryLevel.BASIC):
    """Give a character subterfuge mastery."""
    if not char.db.class_skill_mastery_levels:
        char.db.class_skill_mastery_levels = {}
    char.db.class_skill_mastery_levels[skills.SUBTERFUGE.value] = {"mastery": mastery.value, "classes": ["Thief"]}


def _pre_case(caller, target, gold_visible=True, gold_desc="some gold",
              resources_visible=None, items_visible=None):
    """Pre-populate case cache so pickpocket doesn't require actual case."""
    if not caller.ndb.case_results:
        caller.ndb.case_results = {}
    caller.ndb.case_results[target.id] = {
        "timestamp": time.time(),
        "gold_visible": gold_visible,
        "gold_desc": gold_desc,
        "resources_visible": resources_visible or {},
        "items_visible": items_visible or {},
    }


# ── Gate Checks ───────────────────────────────────────────────────

class TestPickpocketGates(EvenniaCommandTest):
    """Test pickpocket command gate checks."""
    room_typeclass = _ROOM
    character_typeclass = _CHAR
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        _set_subterfuge(self.char1, MasteryLevel.BASIC)
        self.char2.db.gold = 100
        self.char2.db.resources = {}
        self.room1.db.allow_combat = True
        self.room1.db.allow_pvp = True
        self.account.attributes.add("wallet_address", WALLET_A)
        self.account2.attributes.add("wallet_address", WALLET_B)

    def test_no_args(self):
        self.call(CmdPickpocket(), "", "Usage: pickpocket <thing> from <target>")

    def test_no_from_keyword(self):
        self.call(CmdPickpocket(), "gold Char2", "Usage: pickpocket <thing> from <target>")

    def test_self_target(self):
        _pre_case(self.char1, self.char1)
        self.call(CmdPickpocket(), "gold from Char", "You can't pickpocket yourself.")

    def test_unskilled_blocked(self):
        _set_subterfuge(self.char1, MasteryLevel.UNSKILLED)
        _pre_case(self.char1, self.char2)
        self.call(CmdPickpocket(), "gold from Char2", "You have no idea how to pick a pocket")

    def test_in_combat_blocked(self):
        from combat.combat_handler import CombatHandler
        self.char1.scripts.add(CombatHandler, autostart=False)
        _pre_case(self.char1, self.char2)
        self.call(CmdPickpocket(), "gold from Char2", "You can't pickpocket while in combat!")

    def test_no_combat_room_blocked(self):
        self.room1.db.allow_combat = False
        _pre_case(self.char1, self.char2)
        self.call(CmdPickpocket(), "gold from Char2", "You can't pickpocket here.")

    def test_pvp_room_required_for_players(self):
        self.room1.db.allow_pvp = False
        _pre_case(self.char1, self.char2)
        self.call(CmdPickpocket(), "gold from Char2", "You can't pickpocket players here.")

    def test_must_case_first(self):
        self.call(CmdPickpocket(), "gold from Char2", "You need to case them first.")

    def test_cooldown_blocks(self):
        _pre_case(self.char1, self.char2)
        self.char1.ndb.pickpocket_cooldowns = {self.char2.id: time.time()}
        self.call(CmdPickpocket(), "gold from Char2", "You need to wait")

    def test_didnt_spot_gold(self):
        """Can't steal gold if case didn't reveal it."""
        _pre_case(self.char1, self.char2, gold_visible=False)
        self.call(CmdPickpocket(), "gold from Char2", "You didn't spot any gold")


# ── Success ───────────────────────────────────────────────────────

class TestPickpocketSuccess(EvenniaCommandTest):
    """Test successful pickpocket attempts."""
    room_typeclass = _ROOM
    character_typeclass = _CHAR
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        _set_subterfuge(self.char1, MasteryLevel.SKILLED)
        self.char2.db.gold = 100
        self.char2.db.resources = {}
        self.room1.db.allow_combat = True
        self.room1.db.allow_pvp = True
        self.account.attributes.add("wallet_address", WALLET_A)
        self.account2.attributes.add("wallet_address", WALLET_B)

    @patch("blockchain.xrpl.services.gold.GoldService.transfer")
    @patch("commands.class_skill_cmdsets.class_skill_cmds.cmd_pickpocket.dice")
    def test_steal_gold(self, mock_dice, mock_gold_svc):
        """Successful pickpocket should transfer gold."""
        mock_dice.roll_with_advantage_or_disadvantage.return_value = 20
        mock_dice.roll.return_value = 3  # steal 3 + mastery bonus
        _pre_case(self.char1, self.char2, gold_visible=True)

        result = self.call(CmdPickpocket(), "gold from Char2")
        self.assertIn("deftly lift", result)

        # Gold should have moved (3 + skilled bonus 2 = 5)
        self.assertEqual(self.char2.get_gold(), 95)
        self.assertEqual(self.char1.get_gold(), 5)

    @patch("blockchain.xrpl.services.gold.GoldService.transfer")
    @patch("commands.class_skill_cmdsets.class_skill_cmds.cmd_pickpocket.dice")
    def test_steal_capped_at_target_gold(self, mock_dice, mock_gold_svc):
        """Can't steal more gold than the target has."""
        self.char2.db.gold = 2
        mock_dice.roll_with_advantage_or_disadvantage.return_value = 20
        mock_dice.roll.return_value = 6  # 6 + 2 = 8, but target only has 2
        _pre_case(self.char1, self.char2, gold_visible=True)

        self.call(CmdPickpocket(), "gold from Char2")
        self.assertEqual(self.char2.get_gold(), 0)
        self.assertEqual(self.char1.get_gold(), 2)

    @patch("utils.dice_roller.DiceRoller.roll_with_advantage_or_disadvantage")
    def test_steal_item(self, mock_roll):
        """Successful pickpocket should move item to thief."""
        mock_roll.return_value = 20
        item = create.create_object(
            "typeclasses.world_objects.base_world_item.WorldItem",
            key="ruby ring",
            location=self.char2,
        )
        _pre_case(self.char1, self.char2, items_visible={item.id: True})

        result = self.call(CmdPickpocket(), "ruby ring from Char2")
        self.assertIn("deftly lift", result)
        self.assertEqual(item.location, self.char1)

    @patch("utils.dice_roller.DiceRoller.roll_with_advantage_or_disadvantage")
    def test_hidden_advantage(self, mock_roll):
        """HIDDEN should give advantage (dice roller handles best-of-two)."""
        mock_roll.return_value = 20  # dice roller returns the best roll
        self.char1.add_condition(Condition.HIDDEN)

        item = create.create_object(
            "typeclasses.world_objects.base_world_item.WorldItem",
            key="dagger",
            location=self.char2,
        )
        _pre_case(self.char1, self.char2, items_visible={item.id: True})

        result = self.call(CmdPickpocket(), "dagger from Char2")
        self.assertIn("deftly lift", result)
        self.assertIn("(adv)", result)

    @patch("utils.dice_roller.DiceRoller.roll_with_advantage_or_disadvantage")
    def test_hidden_broken_on_success(self, mock_roll):
        """HIDDEN should break even on successful pickpocket."""
        mock_roll.return_value = 20
        self.char1.add_condition(Condition.HIDDEN)

        item = create.create_object(
            "typeclasses.world_objects.base_world_item.WorldItem",
            key="gem",
            location=self.char2,
        )
        _pre_case(self.char1, self.char2, items_visible={item.id: True})

        self.call(CmdPickpocket(), "gem from Char2")
        self.assertFalse(self.char1.has_condition(Condition.HIDDEN))


# ── Failure ───────────────────────────────────────────────────────

class TestPickpocketFailure(EvenniaCommandTest):
    """Test failed pickpocket attempts."""
    room_typeclass = _ROOM
    character_typeclass = _CHAR
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        _set_subterfuge(self.char1, MasteryLevel.BASIC)
        self.char2.db.gold = 100
        self.char2.db.resources = {}
        self.room1.db.allow_combat = True
        self.room1.db.allow_pvp = True
        self.account.attributes.add("wallet_address", WALLET_A)
        self.account2.attributes.add("wallet_address", WALLET_B)
        # Give char2 high perception to make failure easy
        self.char2.wisdom = 18

    @patch("utils.dice_roller.DiceRoller.roll_with_advantage_or_disadvantage")
    def test_failed_attempt_alerts_target(self, mock_roll):
        """Failed pickpocket should alert the target."""
        mock_roll.return_value = 1
        _pre_case(self.char1, self.char2, gold_visible=True)

        result = self.call(CmdPickpocket(), "gold from Char2")
        self.assertIn("hand slips", result)
        # Gold should NOT have moved
        self.assertEqual(self.char2.get_gold(), 100)
        self.assertEqual(self.char1.get_gold(), 0)

    @patch("utils.dice_roller.DiceRoller.roll_with_advantage_or_disadvantage")
    def test_hidden_broken_on_failure(self, mock_roll):
        """HIDDEN should break on failed pickpocket."""
        mock_roll.return_value = 1
        self.char1.add_condition(Condition.HIDDEN)
        _pre_case(self.char1, self.char2, gold_visible=True)

        self.call(CmdPickpocket(), "gold from Char2")
        self.assertFalse(self.char1.has_condition(Condition.HIDDEN))

    @patch("utils.dice_roller.DiceRoller.roll_with_advantage_or_disadvantage")
    def test_sets_cooldown(self, mock_roll):
        """After attempt, cooldown should be set."""
        mock_roll.return_value = 1
        _pre_case(self.char1, self.char2, gold_visible=True)

        self.call(CmdPickpocket(), "gold from Char2")
        self.assertIn(self.char2.id, self.char1.ndb.pickpocket_cooldowns)
