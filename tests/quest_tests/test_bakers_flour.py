"""
Tests for the Baker's Flour quest.

Covers: quest registration, acceptance, delivery turn-in, completion,
reward, non-repeatable, and edge cases.

evennia test --settings settings tests.quest_tests.test_bakers_flour
"""

from unittest.mock import patch

from evennia import create_object
from evennia.utils.test_resources import EvenniaCommandTest

from typeclasses.actors.npcs.baker_npc import BakerNPC
from typeclasses.mixins.quest_giver import CmdNPCQuest
from world.quests.bakers_flour import BakersFlourQuest, FLOUR_ID, FLOUR_NEEDED


class TestBakersFlourRegistration(EvenniaCommandTest):
    """Test quest is registered and discoverable."""

    databases = "__all__"

    def create_script(self):
        pass

    def test_registered_in_registry(self):
        from world.quests import get_quest
        self.assertIs(get_quest("bakers_flour"), BakersFlourQuest)

    def test_quest_metadata(self):
        self.assertEqual(BakersFlourQuest.key, "bakers_flour")
        self.assertEqual(BakersFlourQuest.name, "Flour for the Baker")
        self.assertEqual(BakersFlourQuest.quest_type, "side")
        self.assertFalse(BakersFlourQuest.repeatable)
        self.assertEqual(BakersFlourQuest.reward_xp, 100)
        self.assertEqual(BakersFlourQuest.reward_gold, 4)


class TestBakersFlourAccept(EvenniaCommandTest):
    """Test quest acceptance via CmdNPCQuest."""

    character_typeclass = "typeclasses.actors.character.FCMCharacter"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.baker = create_object(
            BakerNPC, key="Bron", location=self.room1
        )
        self.baker.quest_key = "bakers_flour"
        self.baker.tradeable_resources = [2, 3]
        self.baker.shop_name = "Goldencrust Bakery"

    def tearDown(self):
        if self.baker and self.baker.pk:
            self.baker.delete()
        super().tearDown()

    def test_accept_quest(self):
        """quest accept adds the quest to the character."""
        result = self.call(CmdNPCQuest(), "accept", obj=self.baker)
        self.assertIn("accepted", result.lower())
        self.assertTrue(self.char1.quests.has("bakers_flour"))

    def test_accept_shows_help(self):
        """quest accept shows the help text for the first step."""
        result = self.call(CmdNPCQuest(), "accept", obj=self.baker)
        self.assertIn("Flour", result)

    def test_accept_already_active(self):
        """quest accept when already on quest says so."""
        self.char1.quests.add(BakersFlourQuest)
        result = self.call(CmdNPCQuest(), "accept", obj=self.baker)
        self.assertIn("already on", result.lower())

    def test_accept_already_completed(self):
        """quest accept when completed says so (non-repeatable)."""
        quest = self.char1.quests.add(BakersFlourQuest)
        quest.status = "completed"
        result = self.call(CmdNPCQuest(), "accept", obj=self.baker)
        self.assertIn("already completed", result.lower())


class TestBakersFlourDelivery(EvenniaCommandTest):
    """Test flour delivery and turn-in mechanics."""

    character_typeclass = "typeclasses.actors.character.FCMCharacter"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.baker = create_object(
            BakerNPC, key="Bron", location=self.room1
        )
        self.baker.quest_key = "bakers_flour"
        self.baker.tradeable_resources = [2, 3]
        self.baker.shop_name = "Goldencrust Bakery"

    def tearDown(self):
        if self.baker and self.baker.pk:
            self.baker.delete()
        super().tearDown()

    def test_turn_in_no_flour(self):
        """Viewing quest with no flour shows shortage message."""
        self.char1.quests.add(BakersFlourQuest)
        result = self.call(CmdNPCQuest(), "", obj=self.baker)
        self.assertIn("In Progress", result)

    def test_turn_in_partial_flour(self):
        """Viewing quest with partial flour still in progress."""
        self.char1.quests.add(BakersFlourQuest)
        # Give 2 flour (need 3)
        resources = self.char1.db.resources or {}
        resources[FLOUR_ID] = 2
        self.char1.db.resources = resources

        result = self.call(CmdNPCQuest(), "", obj=self.baker)
        self.assertIn("In Progress", result)

    def test_turn_in_enough_flour(self):
        """Viewing quest with 3+ flour completes the quest."""
        quest = self.char1.quests.add(BakersFlourQuest)

        # Give 3 flour
        resources = self.char1.db.resources or {}
        resources[FLOUR_ID] = FLOUR_NEEDED
        self.char1.db.resources = resources

        # Mock blockchain-touching methods
        with patch.object(self.char1, "return_resource_to_sink"), \
             patch.object(self.char1, "receive_gold_from_reserve"), \
             patch.object(self.char1, "receive_resource_from_reserve"):
            result = self.call(CmdNPCQuest(), "", obj=self.baker)

        # Quest should be completed
        quest = self.char1.quests.get("bakers_flour")
        self.assertTrue(quest.is_completed)

    def test_flour_consumed_on_turn_in(self):
        """return_resource_to_sink is called with correct args."""
        self.char1.quests.add(BakersFlourQuest)

        resources = self.char1.db.resources or {}
        resources[FLOUR_ID] = 5  # More than needed
        self.char1.db.resources = resources

        with patch.object(self.char1, "return_resource_to_sink") as mock_sink, \
             patch.object(self.char1, "receive_gold_from_reserve"), \
             patch.object(self.char1, "receive_resource_from_reserve"):
            self.call(CmdNPCQuest(), "", obj=self.baker)

        # Should have called sink with flour ID and amount 3
        mock_sink.assert_called_once_with(FLOUR_ID, FLOUR_NEEDED)

    def test_completion_message(self):
        """Bron's custom completion message is shown."""
        quest = self.char1.quests.add(BakersFlourQuest)
        quest.status = "completed"

        result = self.call(CmdNPCQuest(), "", obj=self.baker)
        self.assertIn("bakery", result.lower())


class TestBakersFlourNotRepeatable(EvenniaCommandTest):
    """Test quest cannot be re-accepted after completion."""

    character_typeclass = "typeclasses.actors.character.FCMCharacter"
    databases = "__all__"

    def create_script(self):
        pass

    def test_cannot_reaccept(self):
        """Completed quest cannot be re-accepted."""
        quest = self.char1.quests.add(BakersFlourQuest)
        quest.status = "completed"

        can_accept, reason = BakersFlourQuest.can_accept(self.char1)
        self.assertFalse(can_accept)


class TestBakersFlourAbandon(EvenniaCommandTest):
    """Test quest abandon and re-accept."""

    character_typeclass = "typeclasses.actors.character.FCMCharacter"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.baker = create_object(
            BakerNPC, key="Bron", location=self.room1
        )
        self.baker.quest_key = "bakers_flour"
        self.baker.tradeable_resources = [2, 3]
        self.baker.shop_name = "Goldencrust Bakery"

    def tearDown(self):
        if self.baker and self.baker.pk:
            self.baker.delete()
        super().tearDown()

    def test_abandon_quest(self):
        """quest abandon removes the quest."""
        self.char1.quests.add(BakersFlourQuest)
        result = self.call(CmdNPCQuest(), "abandon", obj=self.baker)
        self.assertIn("abandoned", result.lower())
        self.assertFalse(self.char1.quests.has("bakers_flour"))
