"""
Tests for HendricksOreQuest — deliver 3 bronze ingots to Old Hendricks.

Validates:
    - Quest registration and attributes (key, rewards, account_cap)
    - No bread reward (harder quest, higher gold)
    - step_deliver_ingots: insufficient ingots stays active
    - step_deliver_ingots: 3 ingots completes quest (consumes ingots, awards gold only)
    - can_accept: account cap blocks silently when reached
    - non-repeatable: can_accept fails after completion

evennia test --settings settings tests.command_tests.test_hendricks_ore
"""

from unittest.mock import patch

from evennia.utils.test_resources import EvenniaCommandTest

from world.quests import get_quest
from world.quests.hendricks_ore import HendricksOreQuest, BRONZE_INGOT_ID, INGOTS_NEEDED


class TestHendricksOreQuestAttributes(EvenniaCommandTest):
    """Test quest registration and class attributes."""

    character_typeclass = "typeclasses.actors.character.FCMCharacter"
    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"
    databases = "__all__"

    def create_script(self):
        pass

    def test_quest_registered(self):
        self.assertIs(get_quest("hendricks_ore"), HendricksOreQuest)

    def test_quest_key(self):
        self.assertEqual(HendricksOreQuest.key, "hendricks_ore")

    def test_quest_reward_gold(self):
        self.assertEqual(HendricksOreQuest.reward_gold, 10)

    def test_quest_no_bread_reward(self):
        """Hendricks pays well in gold — no bread reward."""
        self.assertEqual(HendricksOreQuest.reward_bread, 0)

    def test_quest_reward_xp(self):
        self.assertEqual(HendricksOreQuest.reward_xp, 250)

    def test_quest_not_repeatable(self):
        self.assertFalse(HendricksOreQuest.repeatable)

    def test_quest_account_cap(self):
        self.assertEqual(HendricksOreQuest.account_cap, 10)

    def test_ingot_constants(self):
        self.assertEqual(BRONZE_INGOT_ID, 32)
        self.assertEqual(INGOTS_NEEDED, 3)


class TestHendricksOreQuestStep(EvenniaCommandTest):
    """Test the step_deliver_ingots step logic."""

    character_typeclass = "typeclasses.actors.character.FCMCharacter"
    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"
    databases = "__all__"

    def create_script(self):
        pass

    def _add_quest(self):
        return self.char1.quests.add(HendricksOreQuest)

    def test_no_ingots_stays_active(self):
        """Quest stays active when character has no bronze ingots."""
        quest = self._add_quest()
        self.char1.db.resources = {}
        quest.progress()
        self.assertFalse(quest.is_completed)

    def test_insufficient_ingots_stays_active(self):
        """Quest stays active when character has fewer than 3 ingots."""
        quest = self._add_quest()
        self.char1.db.resources = {BRONZE_INGOT_ID: 2}
        quest.progress()
        self.assertFalse(quest.is_completed)

    @patch("blockchain.xrpl.services.resource.ResourceService.sink")
    @patch("blockchain.xrpl.services.gold.GoldService.reserve_to_game")
    def test_three_ingots_completes_quest(self, mock_gold, mock_sink):
        """Delivering 3 bronze ingots completes the quest."""
        quest = self._add_quest()
        self.char1.db.resources = {BRONZE_INGOT_ID: 3}
        quest.progress()
        self.assertTrue(quest.is_completed)

    @patch("blockchain.xrpl.services.resource.ResourceService.sink")
    @patch("blockchain.xrpl.services.gold.GoldService.reserve_to_game")
    def test_ingots_consumed_on_completion(self, mock_gold, mock_sink):
        """Bronze ingots are consumed (sinked) on quest completion."""
        quest = self._add_quest()
        self.char1.db.resources = {BRONZE_INGOT_ID: 3}
        quest.progress()
        mock_sink.assert_called()
        call_args = mock_sink.call_args
        self.assertIn(BRONZE_INGOT_ID, call_args[0] or list(call_args[1].values()))

    @patch("blockchain.xrpl.services.resource.ResourceService.sink")
    @patch("blockchain.xrpl.services.gold.GoldService.reserve_to_game")
    def test_gold_awarded_on_completion(self, mock_gold, mock_sink):
        """Gold is granted from reserve on quest completion."""
        quest = self._add_quest()
        self.char1.db.resources = {BRONZE_INGOT_ID: 3}
        quest.progress()
        mock_gold.assert_called()

    @patch("blockchain.xrpl.services.resource.ResourceService.sink")
    @patch("blockchain.xrpl.services.gold.GoldService.reserve_to_game")
    @patch("blockchain.xrpl.services.resource.ResourceService.reserve_to_game")
    def test_no_bread_awarded(self, mock_res_reserve, mock_gold, mock_sink):
        """No bread (resource 3) is awarded — gold-only reward."""
        quest = self._add_quest()
        self.char1.db.resources = {BRONZE_INGOT_ID: 3}
        quest.progress()
        # reserve_to_game for resources should NOT be called (no bread reward)
        bread_calls = [
            c for c in mock_res_reserve.call_args_list
            if 3 in (c[0] or [])
        ]
        self.assertEqual(len(bread_calls), 0)

    @patch("blockchain.xrpl.services.resource.ResourceService.sink")
    @patch("blockchain.xrpl.services.gold.GoldService.reserve_to_game")
    def test_more_than_needed_still_completes(self, mock_gold, mock_sink):
        """Surplus ingots still completes the quest."""
        quest = self._add_quest()
        self.char1.db.resources = {BRONZE_INGOT_ID: 5}
        quest.progress()
        self.assertTrue(quest.is_completed)


class TestHendricksOreQuestAcceptance(EvenniaCommandTest):
    """Test can_accept gating for the hendricks_ore quest."""

    character_typeclass = "typeclasses.actors.character.FCMCharacter"
    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"
    databases = "__all__"

    def create_script(self):
        pass

    def test_can_accept_fresh_character(self):
        """New character can accept."""
        can, reason = HendricksOreQuest.can_accept(self.char1)
        self.assertTrue(can)

    @patch("blockchain.xrpl.services.resource.ResourceService.sink")
    @patch("blockchain.xrpl.services.gold.GoldService.reserve_to_game")
    def test_cannot_accept_after_completion(self, mock_gold, mock_sink):
        """Non-repeatable quest cannot be re-accepted after completion."""
        quest = self.char1.quests.add(HendricksOreQuest)
        self.char1.db.resources = {BRONZE_INGOT_ID: 3}
        quest.progress()
        can, reason = HendricksOreQuest.can_accept(self.char1)
        self.assertFalse(can)
        self.assertIn("already completed", reason.lower())

    def test_account_cap_silently_blocks(self):
        """When account cap is reached, can_accept returns (False, '') — silent."""
        counts = {HendricksOreQuest.key: HendricksOreQuest.account_cap}
        self.char1.account.attributes.add("quest_completion_counts", counts)
        can, reason = HendricksOreQuest.can_accept(self.char1)
        self.assertFalse(can)
        self.assertEqual(reason, "")

    def test_below_account_cap_can_accept(self):
        """One below the cap still allows acceptance."""
        counts = {HendricksOreQuest.key: HendricksOreQuest.account_cap - 1}
        self.char1.account.attributes.add("quest_completion_counts", counts)
        can, reason = HendricksOreQuest.can_accept(self.char1)
        self.assertTrue(can)

    def test_account_cap_incremented_on_completion(self):
        """Completion increments the account-level counter."""
        initial_counts = self.char1.account.attributes.get(
            "quest_completion_counts", default={}
        ) or {}
        initial = initial_counts.get(HendricksOreQuest.key, 0)

        with patch("blockchain.xrpl.services.resource.ResourceService.sink"), \
             patch("blockchain.xrpl.services.gold.GoldService.reserve_to_game"):
            quest = self.char1.quests.add(HendricksOreQuest)
            self.char1.db.resources = {BRONZE_INGOT_ID: 3}
            quest.progress()

        counts = self.char1.account.attributes.get(
            "quest_completion_counts", default={}
        ) or {}
        self.assertEqual(counts.get(HendricksOreQuest.key, 0), initial + 1)
