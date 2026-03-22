"""
Tests for QuestGiverMixin — shared quest command infrastructure.

Covers: mixin adds QuestGiverCmdSet, CmdNPCQuest accept/abandon/view/turn-in,
get_quest_completion_message hook, quest_key AttributeProperty,
interaction with real quest classes.

evennia test --settings settings tests.typeclass_tests.test_quest_giver_mixin
"""

from unittest.mock import patch

from evennia import create_object
from evennia.utils.test_resources import EvenniaCommandTest

from typeclasses.mixins.quest_giver import CmdNPCQuest, QuestGiverMixin
from typeclasses.actors.npcs.bartender_npc import BartenderNPC
from typeclasses.actors.npcs.baker_npc import BakerNPC


class TestQuestGiverMixinSetup(EvenniaCommandTest):
    """Test QuestGiverMixin attaches correctly to NPCs."""

    character_typeclass = "typeclasses.actors.character.FCMCharacter"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.bartender = create_object(
            BartenderNPC,
            key="Rowan",
            location=self.room1,
        )
        self.bartender.quest_key = "rat_cellar"

    def tearDown(self):
        if self.bartender and self.bartender.pk:
            self.bartender.delete()
        super().tearDown()

    def test_has_quest_giver_cmdset(self):
        """QuestGiverCmdSet should be attached on creation."""
        cmdset_keys = [cs.key for cs in self.bartender.cmdset.all()]
        self.assertIn("QuestGiverCmdSet", cmdset_keys)

    def test_quest_key_attribute(self):
        """quest_key should be set on the NPC."""
        self.assertEqual(self.bartender.quest_key, "rat_cellar")

    def test_quest_key_default_none(self):
        """quest_key defaults to None when not set."""
        npc = create_object(BartenderNPC, key="NoQuest", location=self.room1)
        self.assertIsNone(npc.quest_key)
        npc.delete()

    def test_default_completion_message(self):
        """Default get_quest_completion_message returns generic text."""
        from unittest.mock import MagicMock
        quest = MagicMock()
        quest.name = "Test Quest"
        # BartenderNPC overrides this, so test the mixin default via a
        # direct call to QuestGiverMixin's method
        msg = QuestGiverMixin.get_quest_completion_message(
            self.bartender, self.char1, quest
        )
        self.assertIn("Quest completed", msg)

    def test_bartender_completion_message(self):
        """BartenderNPC should have custom completion message."""
        from unittest.mock import MagicMock
        quest = MagicMock()
        quest.name = "Rats in the Cellar"
        msg = self.bartender.get_quest_completion_message(self.char1, quest)
        self.assertIn("cellar", msg.lower())


class TestCmdNPCQuestAccept(EvenniaCommandTest):
    """Test the quest accept flow via CmdNPCQuest."""

    character_typeclass = "typeclasses.actors.character.FCMCharacter"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.bartender = create_object(
            BartenderNPC,
            key="Rowan",
            location=self.room1,
        )
        self.bartender.quest_key = "rat_cellar"

    def tearDown(self):
        if self.bartender and self.bartender.pk:
            self.bartender.delete()
        super().tearDown()

    def test_accept_quest(self):
        """quest accept adds quest to character."""
        result = self.call(
            CmdNPCQuest(), "accept", obj=self.bartender
        )
        self.assertIn("accepted", result.lower())
        self.assertTrue(self.char1.quests.has("rat_cellar"))

    def test_accept_already_active(self):
        """quest accept when already on quest says so."""
        from world.quests.rat_cellar import RatCellarQuest
        self.char1.quests.add(RatCellarQuest)
        result = self.call(
            CmdNPCQuest(), "accept", obj=self.bartender
        )
        self.assertIn("already on", result.lower())

    def test_accept_already_completed(self):
        """quest accept when quest already completed says so."""
        from world.quests.rat_cellar import RatCellarQuest
        quest = self.char1.quests.add(RatCellarQuest)
        quest.status = "completed"
        result = self.call(
            CmdNPCQuest(), "accept", obj=self.bartender
        )
        self.assertIn("already completed", result.lower())

    def test_accept_fails_prereqs(self):
        """quest accept shows reason when can_accept fails."""
        from unittest.mock import MagicMock
        from world.quests.rat_cellar import RatCellarQuest

        with patch.object(
            RatCellarQuest, "can_accept",
            return_value=(False, "You must be level 5")
        ):
            result = self.call(
                CmdNPCQuest(), "accept", obj=self.bartender
            )
        self.assertIn("level 5", result.lower())
        self.assertFalse(self.char1.quests.has("rat_cellar"))


class TestCmdNPCQuestAbandon(EvenniaCommandTest):
    """Test the quest abandon flow via CmdNPCQuest."""

    character_typeclass = "typeclasses.actors.character.FCMCharacter"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.bartender = create_object(
            BartenderNPC,
            key="Rowan",
            location=self.room1,
        )
        self.bartender.quest_key = "rat_cellar"

    def tearDown(self):
        if self.bartender and self.bartender.pk:
            self.bartender.delete()
        super().tearDown()

    def test_abandon_quest(self):
        """quest abandon removes quest."""
        from world.quests.rat_cellar import RatCellarQuest
        self.char1.quests.add(RatCellarQuest)
        result = self.call(
            CmdNPCQuest(), "abandon", obj=self.bartender
        )
        self.assertIn("abandoned", result.lower())
        self.assertFalse(self.char1.quests.has("rat_cellar"))

    def test_abandon_not_on_quest(self):
        """quest abandon when not on quest says so."""
        result = self.call(
            CmdNPCQuest(), "abandon", obj=self.bartender
        )
        self.assertIn("not on this quest", result.lower())

    def test_abandon_completed_quest(self):
        """quest abandon when quest already completed says so."""
        from world.quests.rat_cellar import RatCellarQuest
        quest = self.char1.quests.add(RatCellarQuest)
        quest.status = "completed"
        result = self.call(
            CmdNPCQuest(), "abandon", obj=self.bartender
        )
        self.assertIn("already completed", result.lower())


class TestCmdNPCQuestView(EvenniaCommandTest):
    """Test the quest view flow via CmdNPCQuest."""

    character_typeclass = "typeclasses.actors.character.FCMCharacter"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.bartender = create_object(
            BartenderNPC,
            key="Rowan",
            location=self.room1,
        )
        self.bartender.quest_key = "rat_cellar"

    def tearDown(self):
        if self.bartender and self.bartender.pk:
            self.bartender.delete()
        super().tearDown()

    def test_view_no_quest_shows_accept(self):
        """Viewing quest when not on it shows accept prompt."""
        result = self.call(
            CmdNPCQuest(), "", obj=self.bartender
        )
        self.assertIn("Rats in the Cellar", result)
        self.assertIn("quest accept", result.lower())

    def test_view_active_quest_shows_progress(self):
        """Viewing quest when active shows In Progress."""
        from world.quests.rat_cellar import RatCellarQuest
        self.char1.quests.add(RatCellarQuest)
        result = self.call(
            CmdNPCQuest(), "", obj=self.bartender
        )
        self.assertIn("In Progress", result)

    def test_view_completed_shows_completion_message(self):
        """Viewing completed quest shows custom completion message."""
        from world.quests.rat_cellar import RatCellarQuest
        quest = self.char1.quests.add(RatCellarQuest)
        quest.status = "completed"
        result = self.call(
            CmdNPCQuest(), "", obj=self.bartender
        )
        # BartenderNPC's custom completion message mentions cellar
        self.assertIn("cellar", result.lower())

    def test_view_triggers_progress(self):
        """Viewing quest calls progress() for turn-in opportunity."""
        from world.quests.rat_cellar import RatCellarQuest
        quest = self.char1.quests.add(RatCellarQuest)
        with patch.object(quest, "progress") as mock_progress:
            self.call(CmdNPCQuest(), "", obj=self.bartender)
            mock_progress.assert_called_once()


class TestCmdNPCQuestEdgeCases(EvenniaCommandTest):
    """Test edge cases for CmdNPCQuest."""

    character_typeclass = "typeclasses.actors.character.FCMCharacter"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.bartender = create_object(
            BartenderNPC,
            key="Rowan",
            location=self.room1,
        )
        self.bartender.quest_key = "rat_cellar"

    def tearDown(self):
        if self.bartender and self.bartender.pk:
            self.bartender.delete()
        super().tearDown()

    def test_npc_not_in_room(self):
        """quest command fails when NPC is not in same room."""
        self.bartender.location = self.room2
        result = self.call(
            CmdNPCQuest(), "", obj=self.bartender
        )
        self.assertIn("nobody here", result.lower())

    def test_no_quest_key(self):
        """quest command says no quest when quest_key is None."""
        self.bartender.quest_key = None
        result = self.call(
            CmdNPCQuest(), "", obj=self.bartender
        )
        self.assertIn("no quest", result.lower())


class TestMixinOnBaker(EvenniaCommandTest):
    """Test QuestGiverMixin works correctly on BakerNPC (shopkeeper combo)."""

    character_typeclass = "typeclasses.actors.character.FCMCharacter"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.baker = create_object(
            BakerNPC,
            key="Bron",
            location=self.room1,
        )
        self.baker.quest_key = "bakers_flour"
        self.baker.tradeable_resources = [2, 3]
        self.baker.shop_name = "Goldencrust Bakery"

    def tearDown(self):
        if self.baker and self.baker.pk:
            self.baker.delete()
        super().tearDown()

    def test_has_both_cmdsets(self):
        """BakerNPC should have both QuestGiverCmdSet and ShopkeeperCmdSet."""
        cmdset_keys = [cs.key for cs in self.baker.cmdset.all()]
        self.assertIn("QuestGiverCmdSet", cmdset_keys)
        self.assertIn("ShopkeeperCmdSet", cmdset_keys)

    def test_baker_completion_message(self):
        """BakerNPC should have custom completion message."""
        from unittest.mock import MagicMock
        quest = MagicMock()
        quest.name = "Baker's Flour"
        msg = self.baker.get_quest_completion_message(self.char1, quest)
        self.assertIn("bakery", msg.lower())

    def test_quest_key_from_mixin(self):
        """quest_key comes from the QuestGiverMixin AttributeProperty."""
        self.assertEqual(self.baker.quest_key, "bakers_flour")
