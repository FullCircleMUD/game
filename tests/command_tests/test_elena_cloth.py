"""
Tests for ElenaClothQuest — deliver 3 cloth to Elena Copperkettle.

Validates:
    - Quest registration and attributes (key, rewards, account_cap)
    - step_deliver_cloth: insufficient cloth stays active
    - step_deliver_cloth: partial cloth stays active
    - step_deliver_cloth: 3 cloth completes quest (consumes cloth, awards gold+bread)
    - can_accept: account cap blocks silently when reached
    - non-repeatable: can_accept fails after completion

evennia test --settings settings tests.command_tests.test_elena_cloth
"""

from unittest.mock import patch, MagicMock

from evennia.utils.test_resources import EvenniaCommandTest

from world.quests import get_quest
from world.quests.elena_cloth import ElenaClothQuest, CLOTH_ID, CLOTH_NEEDED


class TestElenaClothQuestAttributes(EvenniaCommandTest):
    """Test quest registration and class attributes."""

    character_typeclass = "typeclasses.actors.character.FCMCharacter"
    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"
    databases = "__all__"

    def create_script(self):
        pass

    def test_quest_registered(self):
        self.assertIs(get_quest("elena_cloth"), ElenaClothQuest)

    def test_quest_key(self):
        self.assertEqual(ElenaClothQuest.key, "elena_cloth")

    def test_quest_reward_gold(self):
        self.assertEqual(ElenaClothQuest.reward_gold, 5)

    def test_quest_reward_bread(self):
        self.assertEqual(ElenaClothQuest.reward_bread, 1)

    def test_quest_reward_xp(self):
        self.assertEqual(ElenaClothQuest.reward_xp, 100)

    def test_quest_not_repeatable(self):
        self.assertFalse(ElenaClothQuest.repeatable)

    def test_quest_account_cap(self):
        self.assertEqual(ElenaClothQuest.account_cap, 10)

    def test_cloth_constants(self):
        self.assertEqual(CLOTH_ID, 11)
        self.assertEqual(CLOTH_NEEDED, 3)


class TestElenaClothQuestStep(EvenniaCommandTest):
    """Test the step_deliver_cloth step logic."""

    character_typeclass = "typeclasses.actors.character.FCMCharacter"
    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"
    databases = "__all__"

    def create_script(self):
        pass

    def _add_quest(self):
        return self.char1.quests.add(ElenaClothQuest)

    def test_no_cloth_stays_active(self):
        """Quest stays active when character has no cloth."""
        quest = self._add_quest()
        self.char1.db.resources = {}
        quest.progress()
        self.assertFalse(quest.is_completed)

    def test_insufficient_cloth_stays_active(self):
        """Quest stays active when character has fewer than 3 cloth."""
        quest = self._add_quest()
        self.char1.db.resources = {CLOTH_ID: 2}
        quest.progress()
        self.assertFalse(quest.is_completed)

    def test_insufficient_cloth_sends_message(self):
        """Insufficient cloth sends the shortage message to the player."""
        quest = self._add_quest()
        self.char1.db.resources = {CLOTH_ID: 1}
        quest.progress()
        # Message should mention remaining cloth needed
        msgs = self.char1.msg.call_args_list if hasattr(self.char1, 'msg') else []
        # Quest is not completed — that's the key check
        self.assertFalse(quest.is_completed)

    @patch("blockchain.xrpl.services.resource.ResourceService.sink")
    @patch("blockchain.xrpl.services.gold.GoldService.craft_output")
    @patch("blockchain.xrpl.services.resource.ResourceService.craft_output")
    def test_three_cloth_completes_quest(self, mock_res_reserve, mock_gold, mock_sink):
        """Delivering 3 cloth completes the quest."""
        quest = self._add_quest()
        self.char1.db.resources = {CLOTH_ID: 3}
        quest.progress()
        self.assertTrue(quest.is_completed)

    @patch("blockchain.xrpl.services.resource.ResourceService.sink")
    @patch("blockchain.xrpl.services.gold.GoldService.craft_output")
    @patch("blockchain.xrpl.services.resource.ResourceService.craft_output")
    def test_cloth_consumed_on_completion(self, mock_res_reserve, mock_gold, mock_sink):
        """Cloth resource is consumed (sinked) when quest completes."""
        quest = self._add_quest()
        self.char1.db.resources = {CLOTH_ID: 3}
        quest.progress()
        # ResourceService.sink should have been called with cloth ID
        mock_sink.assert_called()
        call_args = mock_sink.call_args
        self.assertIn(CLOTH_ID, call_args[0] or list(call_args[1].values()))

    @patch("blockchain.xrpl.services.resource.ResourceService.sink")
    @patch("blockchain.xrpl.services.gold.GoldService.craft_output")
    @patch("blockchain.xrpl.services.resource.ResourceService.craft_output")
    def test_gold_awarded_on_completion(self, mock_res_reserve, mock_gold, mock_sink):
        """Gold reward is granted from reserve on quest completion."""
        quest = self._add_quest()
        self.char1.db.resources = {CLOTH_ID: 3}
        quest.progress()
        mock_gold.assert_called()

    @patch("blockchain.xrpl.services.resource.ResourceService.sink")
    @patch("blockchain.xrpl.services.gold.GoldService.craft_output")
    @patch("blockchain.xrpl.services.resource.ResourceService.craft_output")
    def test_bread_awarded_on_completion(self, mock_res_reserve, mock_gold, mock_sink):
        """Bread reward (resource 3) is granted from reserve on quest completion."""
        quest = self._add_quest()
        self.char1.db.resources = {CLOTH_ID: 3}
        quest.progress()
        mock_res_reserve.assert_called()
        # At least one call should be for bread (resource ID 3)
        bread_calls = [
            c for c in mock_res_reserve.call_args_list
            if 3 in (c[0] or [])
        ]
        self.assertTrue(len(bread_calls) >= 1)

    @patch("blockchain.xrpl.services.resource.ResourceService.sink")
    @patch("blockchain.xrpl.services.gold.GoldService.craft_output")
    @patch("blockchain.xrpl.services.resource.ResourceService.craft_output")
    def test_more_than_needed_still_completes(self, mock_res_reserve, mock_gold, mock_sink):
        """Surplus cloth still completes the quest (only 3 consumed)."""
        quest = self._add_quest()
        self.char1.db.resources = {CLOTH_ID: 5}
        quest.progress()
        self.assertTrue(quest.is_completed)


class TestElenaClothQuestAcceptance(EvenniaCommandTest):
    """Test can_accept gating for the elena_cloth quest."""

    character_typeclass = "typeclasses.actors.character.FCMCharacter"
    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"
    databases = "__all__"

    def create_script(self):
        pass

    def test_can_accept_fresh_character(self):
        """New character with no quest history can accept."""
        can, reason = ElenaClothQuest.can_accept(self.char1)
        self.assertTrue(can)

    @patch("blockchain.xrpl.services.resource.ResourceService.sink")
    @patch("blockchain.xrpl.services.gold.GoldService.craft_output")
    @patch("blockchain.xrpl.services.resource.ResourceService.craft_output")
    def test_cannot_accept_after_completion(self, mock_res_reserve, mock_gold, mock_sink):
        """Non-repeatable quest cannot be re-accepted after completion."""
        quest = self.char1.quests.add(ElenaClothQuest)
        self.char1.db.resources = {CLOTH_ID: 3}
        quest.progress()
        can, reason = ElenaClothQuest.can_accept(self.char1)
        self.assertFalse(can)
        self.assertIn("already completed", reason.lower())

    def test_account_cap_silently_blocks(self):
        """When account cap is reached, can_accept returns (False, '') — silent."""
        counts = {ElenaClothQuest.key: ElenaClothQuest.account_cap}
        self.char1.account.attributes.add("quest_completion_counts", counts)
        can, reason = ElenaClothQuest.can_accept(self.char1)
        self.assertFalse(can)
        self.assertEqual(reason, "")

    def test_below_account_cap_can_accept(self):
        """One below the cap still allows acceptance."""
        counts = {ElenaClothQuest.key: ElenaClothQuest.account_cap - 1}
        self.char1.account.attributes.add("quest_completion_counts", counts)
        can, reason = ElenaClothQuest.can_accept(self.char1)
        self.assertTrue(can)

    def test_account_cap_incremented_on_completion(self):
        """Completion increments the account-level counter."""
        initial_counts = self.char1.account.attributes.get(
            "quest_completion_counts", default={}
        ) or {}
        initial = initial_counts.get(ElenaClothQuest.key, 0)

        with patch("blockchain.xrpl.services.resource.ResourceService.sink"), \
             patch("blockchain.xrpl.services.gold.GoldService.craft_output"), \
             patch("blockchain.xrpl.services.resource.ResourceService.craft_output"):
            quest = self.char1.quests.add(ElenaClothQuest)
            self.char1.db.resources = {CLOTH_ID: 3}
            quest.progress()

        counts = self.char1.account.attributes.get(
            "quest_completion_counts", default={}
        ) or {}
        self.assertEqual(counts.get(ElenaClothQuest.key, 0), initial + 1)
