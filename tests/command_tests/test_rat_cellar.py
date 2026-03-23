"""
Tests for RatCellarQuest — clear the cellar of rats for Rowan.

Validates:
    - Quest registration and attributes (key, quest_type, rewards, account_cap)
    - step_clear_cellar: no-op on unrecognised event
    - step_clear_cellar: completes on boss_killed event
    - Gold + bread rewards granted on completion
    - can_accept: account cap blocks silently when reached
    - non-repeatable: can_accept fails after completion

evennia test --settings settings tests.command_tests.test_rat_cellar
"""

from unittest.mock import patch

from evennia.utils.test_resources import EvenniaCommandTest

from world.quests import get_quest
from world.quests.rat_cellar import RatCellarQuest


class TestRatCellarQuestAttributes(EvenniaCommandTest):
    """Test quest registration and class attributes."""

    character_typeclass = "typeclasses.actors.character.FCMCharacter"
    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"
    databases = "__all__"

    def create_script(self):
        pass

    def test_quest_registered(self):
        self.assertIs(get_quest("rat_cellar"), RatCellarQuest)

    def test_quest_key(self):
        self.assertEqual(RatCellarQuest.key, "rat_cellar")

    def test_quest_type_is_main(self):
        """rat_cellar is a main quest, not a side quest."""
        self.assertEqual(RatCellarQuest.quest_type, "main")

    def test_quest_reward_gold(self):
        self.assertEqual(RatCellarQuest.reward_gold, 10)

    def test_quest_reward_bread(self):
        self.assertEqual(RatCellarQuest.reward_bread, 1)

    def test_quest_reward_xp(self):
        self.assertEqual(RatCellarQuest.reward_xp, 100)

    def test_quest_not_repeatable(self):
        self.assertFalse(RatCellarQuest.repeatable)

    def test_quest_account_cap(self):
        self.assertEqual(RatCellarQuest.account_cap, 10)

    def test_start_step(self):
        self.assertEqual(RatCellarQuest.start_step, "clear_cellar")


class TestRatCellarQuestStep(EvenniaCommandTest):
    """Test the step_clear_cellar step logic."""

    character_typeclass = "typeclasses.actors.character.FCMCharacter"
    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"
    databases = "__all__"

    def create_script(self):
        pass

    def _add_quest(self):
        return self.char1.quests.add(RatCellarQuest)

    def test_no_event_stays_active(self):
        """progress() with no event does nothing."""
        quest = self._add_quest()
        quest.progress()
        self.assertFalse(quest.is_completed)

    def test_wrong_event_stays_active(self):
        """Unrecognised event type does not complete the quest."""
        quest = self._add_quest()
        quest.progress(event_type="room_entered")
        self.assertFalse(quest.is_completed)

    @patch("blockchain.xrpl.services.gold.GoldService.reserve_to_game")
    @patch("blockchain.xrpl.services.resource.ResourceService.reserve_to_game")
    def test_boss_killed_event_completes_quest(self, mock_res_reserve, mock_gold):
        """boss_killed event completes the quest."""
        quest = self._add_quest()
        quest.progress(event_type="boss_killed")
        self.assertTrue(quest.is_completed)

    @patch("blockchain.xrpl.services.gold.GoldService.reserve_to_game")
    @patch("blockchain.xrpl.services.resource.ResourceService.reserve_to_game")
    def test_gold_awarded_on_completion(self, mock_res_reserve, mock_gold):
        """Gold is granted from reserve on quest completion."""
        quest = self._add_quest()
        quest.progress(event_type="boss_killed")
        mock_gold.assert_called()

    @patch("blockchain.xrpl.services.gold.GoldService.reserve_to_game")
    @patch("blockchain.xrpl.services.resource.ResourceService.reserve_to_game")
    def test_bread_awarded_on_completion(self, mock_res_reserve, mock_gold):
        """Bread (resource 3) is granted from reserve on quest completion."""
        quest = self._add_quest()
        quest.progress(event_type="boss_killed")
        mock_res_reserve.assert_called()
        bread_calls = [
            c for c in mock_res_reserve.call_args_list
            if 3 in (c[0] or [])
        ]
        self.assertTrue(len(bread_calls) >= 1)

    @patch("blockchain.xrpl.services.gold.GoldService.reserve_to_game")
    @patch("blockchain.xrpl.services.resource.ResourceService.reserve_to_game")
    def test_no_progress_after_completion(self, mock_res_reserve, mock_gold):
        """Sending boss_killed again after completion has no effect."""
        quest = self._add_quest()
        quest.progress(event_type="boss_killed")
        self.assertTrue(quest.is_completed)
        # Reset mocks and fire again
        mock_gold.reset_mock()
        quest.progress(event_type="boss_killed")
        # Gold should not be awarded a second time
        mock_gold.assert_not_called()


class TestRatCellarQuestAcceptance(EvenniaCommandTest):
    """Test can_accept gating for the rat_cellar quest."""

    character_typeclass = "typeclasses.actors.character.FCMCharacter"
    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"
    databases = "__all__"

    def create_script(self):
        pass

    def test_can_accept_fresh_character(self):
        """New character can accept."""
        can, reason = RatCellarQuest.can_accept(self.char1)
        self.assertTrue(can)

    @patch("blockchain.xrpl.services.gold.GoldService.reserve_to_game")
    @patch("blockchain.xrpl.services.resource.ResourceService.reserve_to_game")
    def test_cannot_accept_after_completion(self, mock_res_reserve, mock_gold):
        """Non-repeatable quest cannot be re-accepted after completion."""
        quest = self.char1.quests.add(RatCellarQuest)
        quest.progress(event_type="boss_killed")
        can, reason = RatCellarQuest.can_accept(self.char1)
        self.assertFalse(can)
        self.assertIn("already completed", reason.lower())

    def test_account_cap_silently_blocks(self):
        """When account cap is reached, can_accept returns (False, '') — silent."""
        counts = {RatCellarQuest.key: RatCellarQuest.account_cap}
        self.char1.account.attributes.add("quest_completion_counts", counts)
        can, reason = RatCellarQuest.can_accept(self.char1)
        self.assertFalse(can)
        self.assertEqual(reason, "")

    def test_below_account_cap_can_accept(self):
        """One below the cap still allows acceptance."""
        counts = {RatCellarQuest.key: RatCellarQuest.account_cap - 1}
        self.char1.account.attributes.add("quest_completion_counts", counts)
        can, reason = RatCellarQuest.can_accept(self.char1)
        self.assertTrue(can)

    def test_account_cap_incremented_on_completion(self):
        """Completion increments the account-level counter."""
        initial_counts = self.char1.account.attributes.get(
            "quest_completion_counts", default={}
        ) or {}
        initial = initial_counts.get(RatCellarQuest.key, 0)

        with patch("blockchain.xrpl.services.gold.GoldService.reserve_to_game"), \
             patch("blockchain.xrpl.services.resource.ResourceService.reserve_to_game"):
            quest = self.char1.quests.add(RatCellarQuest)
            quest.progress(event_type="boss_killed")

        counts = self.char1.account.attributes.get(
            "quest_completion_counts", default={}
        ) or {}
        self.assertEqual(counts.get(RatCellarQuest.key, 0), initial + 1)
