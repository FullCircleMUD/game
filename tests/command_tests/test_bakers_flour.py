"""
Tests for BakersFlourQuest — deliver 3 flour to Bron the Baker.

Validates:
    - Quest registration and attributes (key, rewards, account_cap)
    - step_deliver_flour: insufficient flour stays active
    - step_deliver_flour: 3 flour completes quest (consumes flour, awards gold+bread)
    - can_accept: account cap blocks silently when reached
    - non-repeatable: can_accept fails after completion

evennia test --settings settings tests.command_tests.test_bakers_flour
"""

from unittest.mock import patch

from evennia.utils.test_resources import EvenniaCommandTest

from world.quests import get_quest
from world.quests.bakers_flour import BakersFlourQuest, FLOUR_ID, FLOUR_NEEDED


class TestBakersFlourQuestAttributes(EvenniaCommandTest):
    """Test quest registration and class attributes."""

    character_typeclass = "typeclasses.actors.character.FCMCharacter"
    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"
    databases = "__all__"

    def create_script(self):
        pass

    def test_quest_registered(self):
        self.assertIs(get_quest("bakers_flour"), BakersFlourQuest)

    def test_quest_key(self):
        self.assertEqual(BakersFlourQuest.key, "bakers_flour")

    def test_quest_reward_gold(self):
        self.assertEqual(BakersFlourQuest.reward_gold, 4)

    def test_quest_reward_bread(self):
        self.assertEqual(BakersFlourQuest.reward_bread, 1)

    def test_quest_reward_xp(self):
        self.assertEqual(BakersFlourQuest.reward_xp, 100)

    def test_quest_not_repeatable(self):
        self.assertFalse(BakersFlourQuest.repeatable)

    def test_quest_account_cap(self):
        self.assertEqual(BakersFlourQuest.account_cap, 10)

    def test_flour_constants(self):
        self.assertEqual(FLOUR_ID, 2)
        self.assertEqual(FLOUR_NEEDED, 3)


class TestBakersFlourQuestStep(EvenniaCommandTest):
    """Test the step_deliver_flour step logic."""

    character_typeclass = "typeclasses.actors.character.FCMCharacter"
    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"
    databases = "__all__"

    def create_script(self):
        pass

    def _add_quest(self):
        return self.char1.quests.add(BakersFlourQuest)

    def test_no_flour_stays_active(self):
        """Quest stays active when character has no flour."""
        quest = self._add_quest()
        self.char1.db.resources = {}
        quest.progress()
        self.assertFalse(quest.is_completed)

    def test_insufficient_flour_stays_active(self):
        """Quest stays active when character has fewer than 3 flour."""
        quest = self._add_quest()
        self.char1.db.resources = {FLOUR_ID: 2}
        quest.progress()
        self.assertFalse(quest.is_completed)

    @patch("blockchain.xrpl.services.resource.ResourceService.sink")
    @patch("blockchain.xrpl.services.gold.GoldService.reserve_to_game")
    @patch("blockchain.xrpl.services.resource.ResourceService.reserve_to_game")
    def test_three_flour_completes_quest(self, mock_res_reserve, mock_gold, mock_sink):
        """Delivering 3 flour completes the quest."""
        quest = self._add_quest()
        self.char1.db.resources = {FLOUR_ID: 3}
        quest.progress()
        self.assertTrue(quest.is_completed)

    @patch("blockchain.xrpl.services.resource.ResourceService.sink")
    @patch("blockchain.xrpl.services.gold.GoldService.reserve_to_game")
    @patch("blockchain.xrpl.services.resource.ResourceService.reserve_to_game")
    def test_flour_consumed_on_completion(self, mock_res_reserve, mock_gold, mock_sink):
        """Flour is consumed (sinked) on quest completion."""
        quest = self._add_quest()
        self.char1.db.resources = {FLOUR_ID: 3}
        quest.progress()
        mock_sink.assert_called()
        call_args = mock_sink.call_args
        self.assertIn(FLOUR_ID, call_args[0] or list(call_args[1].values()))

    @patch("blockchain.xrpl.services.resource.ResourceService.sink")
    @patch("blockchain.xrpl.services.gold.GoldService.reserve_to_game")
    @patch("blockchain.xrpl.services.resource.ResourceService.reserve_to_game")
    def test_gold_awarded_on_completion(self, mock_res_reserve, mock_gold, mock_sink):
        """Gold is granted from reserve on quest completion."""
        quest = self._add_quest()
        self.char1.db.resources = {FLOUR_ID: 3}
        quest.progress()
        mock_gold.assert_called()

    @patch("blockchain.xrpl.services.resource.ResourceService.sink")
    @patch("blockchain.xrpl.services.gold.GoldService.reserve_to_game")
    @patch("blockchain.xrpl.services.resource.ResourceService.reserve_to_game")
    def test_bread_awarded_on_completion(self, mock_res_reserve, mock_gold, mock_sink):
        """Bread (resource 3) is granted from reserve on quest completion."""
        quest = self._add_quest()
        self.char1.db.resources = {FLOUR_ID: 3}
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
    def test_surplus_flour_still_completes(self, mock_res_reserve, mock_gold, mock_sink):
        """Surplus flour still completes the quest."""
        quest = self._add_quest()
        self.char1.db.resources = {FLOUR_ID: 5}
        quest.progress()
        self.assertTrue(quest.is_completed)


class TestBakersFlourQuestAcceptance(EvenniaCommandTest):
    """Test can_accept gating for the bakers_flour quest."""

    character_typeclass = "typeclasses.actors.character.FCMCharacter"
    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"
    databases = "__all__"

    def create_script(self):
        pass

    def test_can_accept_fresh_character(self):
        """New character can accept."""
        can, reason = BakersFlourQuest.can_accept(self.char1)
        self.assertTrue(can)

    @patch("blockchain.xrpl.services.resource.ResourceService.sink")
    @patch("blockchain.xrpl.services.gold.GoldService.reserve_to_game")
    @patch("blockchain.xrpl.services.resource.ResourceService.reserve_to_game")
    def test_cannot_accept_after_completion(self, mock_res_reserve, mock_gold, mock_sink):
        """Non-repeatable quest cannot be re-accepted after completion."""
        quest = self.char1.quests.add(BakersFlourQuest)
        self.char1.db.resources = {FLOUR_ID: 3}
        quest.progress()
        can, reason = BakersFlourQuest.can_accept(self.char1)
        self.assertFalse(can)
        self.assertIn("already completed", reason.lower())

    def test_account_cap_silently_blocks(self):
        """When account cap is reached, can_accept returns (False, '') — silent."""
        counts = {BakersFlourQuest.key: BakersFlourQuest.account_cap}
        self.char1.account.attributes.add("quest_completion_counts", counts)
        can, reason = BakersFlourQuest.can_accept(self.char1)
        self.assertFalse(can)
        self.assertEqual(reason, "")

    def test_below_account_cap_can_accept(self):
        """One below the cap still allows acceptance."""
        counts = {BakersFlourQuest.key: BakersFlourQuest.account_cap - 1}
        self.char1.account.attributes.add("quest_completion_counts", counts)
        can, reason = BakersFlourQuest.can_accept(self.char1)
        self.assertTrue(can)

    def test_account_cap_incremented_on_completion(self):
        """Completion increments the account-level counter."""
        initial_counts = self.char1.account.attributes.get(
            "quest_completion_counts", default={}
        ) or {}
        initial = initial_counts.get(BakersFlourQuest.key, 0)

        with patch("blockchain.xrpl.services.resource.ResourceService.sink"), \
             patch("blockchain.xrpl.services.gold.GoldService.reserve_to_game"), \
             patch("blockchain.xrpl.services.resource.ResourceService.reserve_to_game"):
            quest = self.char1.quests.add(BakersFlourQuest)
            self.char1.db.resources = {FLOUR_ID: 3}
            quest.progress()

        counts = self.char1.account.attributes.get(
            "quest_completion_counts", default={}
        ) or {}
        self.assertEqual(counts.get(BakersFlourQuest.key, 0), initial + 1)
