"""
Tests for OakwrightTimberQuest — deliver 4 timber to Master Oakwright.

Validates:
    - Quest registration and attributes (key, rewards, account_cap)
    - Requires 4 timber (not 3 like the other delivery quests)
    - step_deliver_timber: insufficient timber stays active
    - step_deliver_timber: 4 timber completes quest (consumes timber, awards gold+bread)
    - can_accept: account cap blocks silently when reached
    - non-repeatable: can_accept fails after completion

evennia test --settings settings tests.command_tests.test_oakwright_timber
"""

from unittest.mock import patch

from evennia.utils.test_resources import EvenniaCommandTest

from world.quests import get_quest
from world.quests.oakwright_timber import OakwrightTimberQuest, TIMBER_ID, TIMBER_NEEDED


class TestOakwrightTimberQuestAttributes(EvenniaCommandTest):
    """Test quest registration and class attributes."""

    character_typeclass = "typeclasses.actors.character.FCMCharacter"
    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"
    databases = "__all__"

    def create_script(self):
        pass

    def test_quest_registered(self):
        self.assertIs(get_quest("oakwright_timber"), OakwrightTimberQuest)

    def test_quest_key(self):
        self.assertEqual(OakwrightTimberQuest.key, "oakwright_timber")

    def test_quest_reward_gold(self):
        self.assertEqual(OakwrightTimberQuest.reward_gold, 5)

    def test_quest_reward_bread(self):
        self.assertEqual(OakwrightTimberQuest.reward_bread, 1)

    def test_quest_reward_xp(self):
        self.assertEqual(OakwrightTimberQuest.reward_xp, 100)

    def test_quest_not_repeatable(self):
        self.assertFalse(OakwrightTimberQuest.repeatable)

    def test_quest_account_cap(self):
        self.assertEqual(OakwrightTimberQuest.account_cap, 10)

    def test_timber_constants(self):
        self.assertEqual(TIMBER_ID, 7)
        self.assertEqual(TIMBER_NEEDED, 4)


class TestOakwrightTimberQuestStep(EvenniaCommandTest):
    """Test the step_deliver_timber step logic."""

    character_typeclass = "typeclasses.actors.character.FCMCharacter"
    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"
    databases = "__all__"

    def create_script(self):
        pass

    def _add_quest(self):
        return self.char1.quests.add(OakwrightTimberQuest)

    def test_no_timber_stays_active(self):
        """Quest stays active when character has no timber."""
        quest = self._add_quest()
        self.char1.db.resources = {}
        quest.progress()
        self.assertFalse(quest.is_completed)

    def test_insufficient_timber_stays_active(self):
        """Quest stays active when character has fewer than 4 timber."""
        quest = self._add_quest()
        self.char1.db.resources = {TIMBER_ID: 3}
        quest.progress()
        self.assertFalse(quest.is_completed)

    def test_three_timber_is_not_enough(self):
        """3 timber is insufficient — this quest needs 4, not 3."""
        quest = self._add_quest()
        self.char1.db.resources = {TIMBER_ID: 3}
        quest.progress()
        self.assertFalse(quest.is_completed)

    @patch("blockchain.xrpl.services.resource.ResourceService.sink")
    @patch("blockchain.xrpl.services.gold.GoldService.craft_output")
    @patch("blockchain.xrpl.services.resource.ResourceService.craft_output")
    def test_four_timber_completes_quest(self, mock_res_reserve, mock_gold, mock_sink):
        """Delivering 4 timber completes the quest."""
        quest = self._add_quest()
        self.char1.db.resources = {TIMBER_ID: 4}
        quest.progress()
        self.assertTrue(quest.is_completed)

    @patch("blockchain.xrpl.services.resource.ResourceService.sink")
    @patch("blockchain.xrpl.services.gold.GoldService.craft_output")
    @patch("blockchain.xrpl.services.resource.ResourceService.craft_output")
    def test_timber_consumed_on_completion(self, mock_res_reserve, mock_gold, mock_sink):
        """Timber is consumed (sinked) on quest completion."""
        quest = self._add_quest()
        self.char1.db.resources = {TIMBER_ID: 4}
        quest.progress()
        mock_sink.assert_called()
        call_args = mock_sink.call_args
        self.assertIn(TIMBER_ID, call_args[0] or list(call_args[1].values()))

    @patch("blockchain.xrpl.services.resource.ResourceService.sink")
    @patch("blockchain.xrpl.services.gold.GoldService.craft_output")
    @patch("blockchain.xrpl.services.resource.ResourceService.craft_output")
    def test_gold_awarded_on_completion(self, mock_res_reserve, mock_gold, mock_sink):
        """Gold is granted from reserve on quest completion."""
        quest = self._add_quest()
        self.char1.db.resources = {TIMBER_ID: 4}
        quest.progress()
        mock_gold.assert_called()

    @patch("blockchain.xrpl.services.resource.ResourceService.sink")
    @patch("blockchain.xrpl.services.gold.GoldService.craft_output")
    @patch("blockchain.xrpl.services.resource.ResourceService.craft_output")
    def test_bread_awarded_on_completion(self, mock_res_reserve, mock_gold, mock_sink):
        """Bread (resource 3) is granted from reserve on quest completion."""
        quest = self._add_quest()
        self.char1.db.resources = {TIMBER_ID: 4}
        quest.progress()
        mock_res_reserve.assert_called()
        bread_calls = [
            c for c in mock_res_reserve.call_args_list
            if 3 in (c[0] or [])
        ]
        self.assertTrue(len(bread_calls) >= 1)

    @patch("blockchain.xrpl.services.resource.ResourceService.sink")
    @patch("blockchain.xrpl.services.gold.GoldService.craft_output")
    @patch("blockchain.xrpl.services.resource.ResourceService.craft_output")
    def test_surplus_timber_still_completes(self, mock_res_reserve, mock_gold, mock_sink):
        """Surplus timber still completes the quest."""
        quest = self._add_quest()
        self.char1.db.resources = {TIMBER_ID: 6}
        quest.progress()
        self.assertTrue(quest.is_completed)


class TestOakwrightTimberQuestAcceptance(EvenniaCommandTest):
    """Test can_accept gating for the oakwright_timber quest."""

    character_typeclass = "typeclasses.actors.character.FCMCharacter"
    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"
    databases = "__all__"

    def create_script(self):
        pass

    def test_can_accept_fresh_character(self):
        """New character can accept."""
        can, reason = OakwrightTimberQuest.can_accept(self.char1)
        self.assertTrue(can)

    @patch("blockchain.xrpl.services.resource.ResourceService.sink")
    @patch("blockchain.xrpl.services.gold.GoldService.craft_output")
    @patch("blockchain.xrpl.services.resource.ResourceService.craft_output")
    def test_cannot_accept_after_completion(self, mock_res_reserve, mock_gold, mock_sink):
        """Non-repeatable quest cannot be re-accepted after completion."""
        quest = self.char1.quests.add(OakwrightTimberQuest)
        self.char1.db.resources = {TIMBER_ID: 4}
        quest.progress()
        can, reason = OakwrightTimberQuest.can_accept(self.char1)
        self.assertFalse(can)
        self.assertIn("already completed", reason.lower())

    def test_account_cap_silently_blocks(self):
        """When account cap is reached, can_accept returns (False, '') — silent."""
        counts = {OakwrightTimberQuest.key: OakwrightTimberQuest.account_cap}
        self.char1.account.attributes.add("quest_completion_counts", counts)
        can, reason = OakwrightTimberQuest.can_accept(self.char1)
        self.assertFalse(can)
        self.assertEqual(reason, "")

    def test_below_account_cap_can_accept(self):
        """One below the cap still allows acceptance."""
        counts = {OakwrightTimberQuest.key: OakwrightTimberQuest.account_cap - 1}
        self.char1.account.attributes.add("quest_completion_counts", counts)
        can, reason = OakwrightTimberQuest.can_accept(self.char1)
        self.assertTrue(can)

    def test_account_cap_incremented_on_completion(self):
        """Completion increments the account-level counter."""
        initial_counts = self.char1.account.attributes.get(
            "quest_completion_counts", default={}
        ) or {}
        initial = initial_counts.get(OakwrightTimberQuest.key, 0)

        with patch("blockchain.xrpl.services.resource.ResourceService.sink"), \
             patch("blockchain.xrpl.services.gold.GoldService.craft_output"), \
             patch("blockchain.xrpl.services.resource.ResourceService.craft_output"):
            quest = self.char1.quests.add(OakwrightTimberQuest)
            self.char1.db.resources = {TIMBER_ID: 4}
            quest.progress()

        counts = self.char1.account.attributes.get(
            "quest_completion_counts", default={}
        ) or {}
        self.assertEqual(counts.get(OakwrightTimberQuest.key, 0), initial + 1)
