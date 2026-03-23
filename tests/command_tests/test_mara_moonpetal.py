"""
Tests for MaraMoonpetalQuest — deliver 3 moonpetal to Mara Brightwater.

Validates:
    - Quest registration and attributes (key, rewards, account_cap)
    - step_deliver_moonpetal: insufficient moonpetal stays active
    - step_deliver_moonpetal: 3 moonpetal completes quest (consumes moonpetal, awards gold+bread)
    - can_accept: account cap blocks silently when reached
    - non-repeatable: can_accept fails after completion

evennia test --settings settings tests.command_tests.test_mara_moonpetal
"""

from unittest.mock import patch

from evennia.utils.test_resources import EvenniaCommandTest

from world.quests import get_quest
from world.quests.mara_moonpetal import MaraMoonpetalQuest, MOONPETAL_ID, MOONPETAL_NEEDED


class TestMaraMoonpetalQuestAttributes(EvenniaCommandTest):
    """Test quest registration and class attributes."""

    character_typeclass = "typeclasses.actors.character.FCMCharacter"
    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"
    databases = "__all__"

    def create_script(self):
        pass

    def test_quest_registered(self):
        self.assertIs(get_quest("mara_moonpetal"), MaraMoonpetalQuest)

    def test_quest_key(self):
        self.assertEqual(MaraMoonpetalQuest.key, "mara_moonpetal")

    def test_quest_reward_gold(self):
        self.assertEqual(MaraMoonpetalQuest.reward_gold, 5)

    def test_quest_reward_bread(self):
        self.assertEqual(MaraMoonpetalQuest.reward_bread, 1)

    def test_quest_reward_xp(self):
        self.assertEqual(MaraMoonpetalQuest.reward_xp, 150)

    def test_quest_not_repeatable(self):
        self.assertFalse(MaraMoonpetalQuest.repeatable)

    def test_quest_account_cap(self):
        self.assertEqual(MaraMoonpetalQuest.account_cap, 10)

    def test_moonpetal_constants(self):
        self.assertEqual(MOONPETAL_ID, 12)
        self.assertEqual(MOONPETAL_NEEDED, 3)


class TestMaraMoonpetalQuestStep(EvenniaCommandTest):
    """Test the step_deliver_moonpetal step logic."""

    character_typeclass = "typeclasses.actors.character.FCMCharacter"
    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"
    databases = "__all__"

    def create_script(self):
        pass

    def _add_quest(self):
        return self.char1.quests.add(MaraMoonpetalQuest)

    def test_no_moonpetal_stays_active(self):
        """Quest stays active when character has no moonpetal."""
        quest = self._add_quest()
        self.char1.db.resources = {}
        quest.progress()
        self.assertFalse(quest.is_completed)

    def test_insufficient_moonpetal_stays_active(self):
        """Quest stays active when character has fewer than 3 moonpetal."""
        quest = self._add_quest()
        self.char1.db.resources = {MOONPETAL_ID: 2}
        quest.progress()
        self.assertFalse(quest.is_completed)

    @patch("blockchain.xrpl.services.resource.ResourceService.sink")
    @patch("blockchain.xrpl.services.gold.GoldService.reserve_to_game")
    @patch("blockchain.xrpl.services.resource.ResourceService.reserve_to_game")
    def test_three_moonpetal_completes_quest(self, mock_res_reserve, mock_gold, mock_sink):
        """Delivering 3 moonpetal completes the quest."""
        quest = self._add_quest()
        self.char1.db.resources = {MOONPETAL_ID: 3}
        quest.progress()
        self.assertTrue(quest.is_completed)

    @patch("blockchain.xrpl.services.resource.ResourceService.sink")
    @patch("blockchain.xrpl.services.gold.GoldService.reserve_to_game")
    @patch("blockchain.xrpl.services.resource.ResourceService.reserve_to_game")
    def test_moonpetal_consumed_on_completion(self, mock_res_reserve, mock_gold, mock_sink):
        """Moonpetal is consumed (sinked) on quest completion."""
        quest = self._add_quest()
        self.char1.db.resources = {MOONPETAL_ID: 3}
        quest.progress()
        mock_sink.assert_called()
        call_args = mock_sink.call_args
        self.assertIn(MOONPETAL_ID, call_args[0] or list(call_args[1].values()))

    @patch("blockchain.xrpl.services.resource.ResourceService.sink")
    @patch("blockchain.xrpl.services.gold.GoldService.reserve_to_game")
    @patch("blockchain.xrpl.services.resource.ResourceService.reserve_to_game")
    def test_gold_awarded_on_completion(self, mock_res_reserve, mock_gold, mock_sink):
        """Gold is granted from reserve on quest completion."""
        quest = self._add_quest()
        self.char1.db.resources = {MOONPETAL_ID: 3}
        quest.progress()
        mock_gold.assert_called()

    @patch("blockchain.xrpl.services.resource.ResourceService.sink")
    @patch("blockchain.xrpl.services.gold.GoldService.reserve_to_game")
    @patch("blockchain.xrpl.services.resource.ResourceService.reserve_to_game")
    def test_bread_awarded_on_completion(self, mock_res_reserve, mock_gold, mock_sink):
        """Bread reward (resource 3) is granted from reserve on quest completion."""
        quest = self._add_quest()
        self.char1.db.resources = {MOONPETAL_ID: 3}
        quest.progress()
        mock_res_reserve.assert_called()
        bread_calls = [
            c for c in mock_res_reserve.call_args_list
            if 3 in (c[0] or [])
        ]
        self.assertTrue(len(bread_calls) >= 1)

    @patch("blockchain.xrpl.services.resource.ResourceService.sink")
    @patch("blockchain.xrpl.services.gold.GoldService.reserve_to_game")
    @patch("blockchain.xrpl.services.resource.ResourceService.reserve_to_game")
    def test_surplus_moonpetal_still_completes(self, mock_res_reserve, mock_gold, mock_sink):
        """Surplus moonpetal still completes the quest."""
        quest = self._add_quest()
        self.char1.db.resources = {MOONPETAL_ID: 5}
        quest.progress()
        self.assertTrue(quest.is_completed)


class TestMaraMoonpetalQuestAcceptance(EvenniaCommandTest):
    """Test can_accept gating for the mara_moonpetal quest."""

    character_typeclass = "typeclasses.actors.character.FCMCharacter"
    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"
    databases = "__all__"

    def create_script(self):
        pass

    def test_can_accept_fresh_character(self):
        """New character can accept."""
        can, reason = MaraMoonpetalQuest.can_accept(self.char1)
        self.assertTrue(can)

    @patch("blockchain.xrpl.services.resource.ResourceService.sink")
    @patch("blockchain.xrpl.services.gold.GoldService.reserve_to_game")
    @patch("blockchain.xrpl.services.resource.ResourceService.reserve_to_game")
    def test_cannot_accept_after_completion(self, mock_res_reserve, mock_gold, mock_sink):
        """Non-repeatable quest cannot be re-accepted after completion."""
        quest = self.char1.quests.add(MaraMoonpetalQuest)
        self.char1.db.resources = {MOONPETAL_ID: 3}
        quest.progress()
        can, reason = MaraMoonpetalQuest.can_accept(self.char1)
        self.assertFalse(can)
        self.assertIn("already completed", reason.lower())

    def test_account_cap_silently_blocks(self):
        """When account cap is reached, can_accept returns (False, '') — silent."""
        counts = {MaraMoonpetalQuest.key: MaraMoonpetalQuest.account_cap}
        self.char1.account.attributes.add("quest_completion_counts", counts)
        can, reason = MaraMoonpetalQuest.can_accept(self.char1)
        self.assertFalse(can)
        self.assertEqual(reason, "")

    def test_below_account_cap_can_accept(self):
        """One below the cap still allows acceptance."""
        counts = {MaraMoonpetalQuest.key: MaraMoonpetalQuest.account_cap - 1}
        self.char1.account.attributes.add("quest_completion_counts", counts)
        can, reason = MaraMoonpetalQuest.can_accept(self.char1)
        self.assertTrue(can)

    def test_account_cap_incremented_on_completion(self):
        """Completion increments the account-level counter."""
        initial_counts = self.char1.account.attributes.get(
            "quest_completion_counts", default={}
        ) or {}
        initial = initial_counts.get(MaraMoonpetalQuest.key, 0)

        with patch("blockchain.xrpl.services.resource.ResourceService.sink"), \
             patch("blockchain.xrpl.services.gold.GoldService.reserve_to_game"), \
             patch("blockchain.xrpl.services.resource.ResourceService.reserve_to_game"):
            quest = self.char1.quests.add(MaraMoonpetalQuest)
            self.char1.db.resources = {MOONPETAL_ID: 3}
            quest.progress()

        counts = self.char1.account.attributes.get(
            "quest_completion_counts", default={}
        ) or {}
        self.assertEqual(counts.get(MaraMoonpetalQuest.key, 0), initial + 1)
