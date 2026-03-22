"""
Tests for the quest system — base quest, quest handler, templates,
quest commands, and guildmaster quest integration.
"""

from unittest.mock import patch

from evennia.utils import create
from evennia.utils.test_resources import EvenniaCommandTest

from world.quests import register_quest, get_quest, list_quests, QUEST_REGISTRY
from world.quests.base_quest import FCMQuest
from world.quests.templates.collect_quest import CollectQuest
from world.quests.templates.visit_quest import VisitQuest
from world.quests.templates.multi_step_quest import MultiStepQuest
from commands.all_char_cmds.cmd_quests import CmdQuests
from commands.npc_cmds.cmdset_guildmaster import CmdJoin, CmdGuild, CmdAdvance
from typeclasses.mixins.quest_giver import CmdNPCQuest as CmdQuest


# ── Test quest classes (not registered in global registry) ──

class SimpleTestQuest(FCMQuest):
    """Single-step quest — step_start completes immediately when progress() called."""
    key = "test_simple"
    name = "Simple Test"
    desc = "A simple test quest."
    quest_type = "side"
    reward_xp = 50


class PrereqTestQuest(FCMQuest):
    """Quest with prerequisites."""
    key = "test_prereq"
    name = "Prereq Test"
    desc = "A quest that requires test_simple first."
    quest_type = "side"
    prerequisites = ["test_simple"]


class RepeatableTestQuest(FCMQuest):
    """Repeatable quest."""
    key = "test_repeatable"
    name = "Repeatable Test"
    desc = "Can be done again."
    quest_type = "repeatable"
    repeatable = True


class MultiStepTestQuest(FCMQuest):
    """Multi-step quest with custom steps."""
    key = "test_multi"
    name = "Multi Step Test"
    desc = "A multi step test quest."
    start_step = "step_a"

    help_step_a = "Do step A."
    help_step_b = "Do step B."

    def step_step_a(self, *args, **kwargs):
        if kwargs.get("event_type") == "step_a_done":
            self.current_step = "step_b"
            self.quester.msg("|gStep A complete!|n")

    def step_step_b(self, *args, **kwargs):
        if kwargs.get("event_type") == "step_b_done":
            self.complete()


class CollectTestQuest(CollectQuest):
    """Collect quest for testing."""
    key = "test_collect"
    name = "Collect Test"
    desc = "Bring 2 Iron Ingots."
    quest_type = "guild"
    required_resources = {5: 2}  # 2 Iron Ingots
    consume_on_complete = False  # skip blockchain calls in tests
    reward_xp = 0


class VisitTestQuest(VisitQuest):
    """Visit quest for testing."""
    key = "test_visit"
    name = "Visit Test"
    desc = "Go to the tagged room."
    quest_type = "side"
    reward_xp = 0


class MultiStepTemplateTestQuest(MultiStepQuest):
    """MultiStepQuest template for testing."""
    key = "test_multi_template"
    name = "Multi Step Template Test"
    desc = "An ordered multi-step quest."
    steps = [
        {"key": "gather", "type": "collect", "resources": {5: 1},
         "help": "Get 1 Iron Ingot."},
        {"key": "go_there", "type": "visit",
         "help": "Go to the destination."},
    ]


# Helper to complete a quest by calling progress (step_start auto-completes)
def _complete_quest(char, quest_class):
    """Add quest and call progress() so step_start completes it."""
    quest = char.quests.add(quest_class)
    quest.progress()
    return quest


# ═══════════════════════════════════════════════════════
# Registry tests
# ═══════════════════════════════════════════════════════

class TestQuestRegistry(EvenniaCommandTest):
    """Test the quest registry system."""

    def create_script(self):
        pass

    def test_register_quest_decorator(self):
        """@register_quest adds class to QUEST_REGISTRY."""

        @register_quest
        class _TempQuest(FCMQuest):
            key = "_temp_registry_test"
            name = "Temp"

        self.assertIn("_temp_registry_test", QUEST_REGISTRY)
        self.assertEqual(QUEST_REGISTRY["_temp_registry_test"], _TempQuest)
        # Cleanup
        del QUEST_REGISTRY["_temp_registry_test"]

    def test_get_quest(self):
        """get_quest returns registered class or None."""
        QUEST_REGISTRY["_test_get"] = SimpleTestQuest
        self.assertEqual(get_quest("_test_get"), SimpleTestQuest)
        self.assertIsNone(get_quest("nonexistent"))
        del QUEST_REGISTRY["_test_get"]

    def test_warrior_initiation_registered(self):
        """The warrior_initiation quest should be auto-registered."""
        quest = get_quest("warrior_initiation")
        self.assertIsNotNone(quest)
        self.assertEqual(quest.name, "Trial of Arms")
        self.assertEqual(quest.quest_type, "guild")


# ═══════════════════════════════════════════════════════
# Base quest tests
# ═══════════════════════════════════════════════════════

class TestFCMQuest(EvenniaCommandTest):
    """Test FCMQuest base class behaviour."""

    character_typeclass = "typeclasses.actors.character.FCMCharacter"
    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def test_quest_default_status_started(self):
        """New quest status is 'started' before progress() is called."""
        quest = self.char1.quests.add(SimpleTestQuest)
        self.assertEqual(quest.status, "started")

    def test_step_start_completes_on_progress(self):
        """step_start auto-completes when progress() is called."""
        quest = self.char1.quests.add(SimpleTestQuest)
        quest.progress()
        self.assertTrue(quest.is_completed)

    def test_quest_data_persistence(self):
        """Quest data persists via handler."""
        quest = self.char1.quests.add(MultiStepTestQuest)
        quest.add_data("custom_key", 42)
        self.assertEqual(quest.get_data("custom_key"), 42)

    def test_quest_status_tracking(self):
        """Quest status transitions correctly."""
        quest = self.char1.quests.add(MultiStepTestQuest)
        self.assertEqual(quest.status, "started")
        self.assertFalse(quest.is_completed)
        self.assertFalse(quest.is_abandoned)
        self.assertFalse(quest.is_failed)

    def test_quest_abandon(self):
        """Abandoning a quest sets status."""
        quest = self.char1.quests.add(MultiStepTestQuest)
        quest.abandon()
        self.assertTrue(quest.is_abandoned)

    def test_quest_fail(self):
        """Failing a quest sets status."""
        quest = self.char1.quests.add(MultiStepTestQuest)
        quest.fail()
        self.assertTrue(quest.is_failed)

    def test_quest_progress_calls_step(self):
        """progress() dispatches to the correct step method."""
        quest = self.char1.quests.add(MultiStepTestQuest)
        self.assertEqual(quest.current_step, "step_a")
        quest.progress(event_type="step_a_done")
        self.assertEqual(quest.current_step, "step_b")
        quest.progress(event_type="step_b_done")
        self.assertTrue(quest.is_completed)

    def test_progress_no_op_when_completed(self):
        """progress() does nothing if quest is completed."""
        quest = self.char1.quests.add(MultiStepTestQuest)
        quest.status = "completed"
        quest.progress(event_type="step_a_done")
        self.assertEqual(quest.current_step, "step_a")

    def test_quest_help_returns_step_help(self):
        """help() returns help text for current step."""
        quest = self.char1.quests.add(MultiStepTestQuest)
        self.assertEqual(quest.help(), "Do step A.")
        quest.progress(event_type="step_a_done")
        self.assertEqual(quest.help(), "Do step B.")

    def test_quest_help_completed(self):
        """help() returns completion text when done."""
        quest = _complete_quest(self.char1, SimpleTestQuest)
        self.assertIn("completed", quest.help().lower())

    def test_quest_reward_xp(self):
        """Quest completion awards XP."""
        MultiStepTestQuest.reward_xp = 50
        quest = self.char1.quests.add(MultiStepTestQuest)
        initial_xp = self.char1.experience_points
        quest.progress(event_type="step_a_done")
        quest.progress(event_type="step_b_done")
        self.assertEqual(
            self.char1.experience_points, initial_xp + 50
        )
        MultiStepTestQuest.reward_xp = 0  # reset

    def test_can_accept_no_prereqs(self):
        """can_accept returns True for quest with no prerequisites."""
        can, reason = SimpleTestQuest.can_accept(self.char1)
        self.assertTrue(can)

    def test_can_accept_prereq_not_met(self):
        """can_accept fails when prerequisite not completed."""
        can, reason = PrereqTestQuest.can_accept(self.char1)
        self.assertFalse(can)
        self.assertIn("complete", reason.lower())

    def test_can_accept_prereq_met(self):
        """can_accept succeeds when prerequisite is completed."""
        _complete_quest(self.char1, SimpleTestQuest)
        can, reason = PrereqTestQuest.can_accept(self.char1)
        self.assertTrue(can)

    def test_can_accept_already_active(self):
        """can_accept fails when quest is already active."""
        self.char1.quests.add(MultiStepTestQuest)
        can, reason = MultiStepTestQuest.can_accept(self.char1)
        self.assertFalse(can)
        self.assertIn("already on", reason.lower())

    def test_can_accept_completed_not_repeatable(self):
        """can_accept fails for completed non-repeatable quests."""
        _complete_quest(self.char1, SimpleTestQuest)
        can, reason = SimpleTestQuest.can_accept(self.char1)
        self.assertFalse(can)
        self.assertIn("already completed", reason.lower())

    def test_can_accept_completed_repeatable(self):
        """can_accept succeeds for completed repeatable quests."""
        _complete_quest(self.char1, RepeatableTestQuest)
        can, reason = RepeatableTestQuest.can_accept(self.char1)
        self.assertTrue(can)


# ═══════════════════════════════════════════════════════
# Quest handler tests
# ═══════════════════════════════════════════════════════

class TestFCMQuestHandler(EvenniaCommandTest):
    """Test FCMQuestHandler on character."""

    character_typeclass = "typeclasses.actors.character.FCMCharacter"
    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def test_handler_has(self):
        """has() returns True for quests the character has."""
        self.char1.quests.add(MultiStepTestQuest)
        self.assertTrue(self.char1.quests.has("test_multi"))
        self.assertFalse(self.char1.quests.has("nonexistent"))

    def test_handler_get(self):
        """get() returns quest instance or None."""
        self.char1.quests.add(MultiStepTestQuest)
        quest = self.char1.quests.get("test_multi")
        self.assertIsNotNone(quest)
        self.assertIsInstance(quest, MultiStepTestQuest)
        self.assertIsNone(self.char1.quests.get("nonexistent"))

    def test_handler_all(self):
        """all() returns all quest instances."""
        self.char1.quests.add(MultiStepTestQuest)
        self.char1.quests.add(RepeatableTestQuest)
        all_quests = self.char1.quests.all()
        self.assertEqual(len(all_quests), 2)

    def test_handler_active(self):
        """active() returns only started quests."""
        self.char1.quests.add(MultiStepTestQuest)
        _complete_quest(self.char1, SimpleTestQuest)
        active = self.char1.quests.active()
        self.assertEqual(len(active), 1)
        self.assertEqual(active[0].key, "test_multi")

    def test_handler_completed(self):
        """completed() returns only completed quests."""
        self.char1.quests.add(MultiStepTestQuest)
        _complete_quest(self.char1, SimpleTestQuest)
        completed = self.char1.quests.completed()
        self.assertEqual(len(completed), 1)
        self.assertEqual(completed[0].key, "test_simple")

    def test_handler_is_completed(self):
        """is_completed() convenience check."""
        _complete_quest(self.char1, SimpleTestQuest)
        self.assertTrue(self.char1.quests.is_completed("test_simple"))
        self.assertFalse(self.char1.quests.is_completed("nonexistent"))

    def test_handler_remove(self):
        """remove() removes quest and cleans up data."""
        self.char1.quests.add(MultiStepTestQuest)
        self.assertTrue(self.char1.quests.has("test_multi"))
        self.char1.quests.remove("test_multi")
        self.assertFalse(self.char1.quests.has("test_multi"))

    def test_handler_check_progress(self):
        """check_progress dispatches events to matching quests."""
        self.char1.quests.add(MultiStepTestQuest)
        quest = self.char1.quests.get("test_multi")
        self.assertEqual(quest.current_step, "step_a")
        self.char1.quests.check_progress("step_a_done")
        self.assertEqual(quest.current_step, "step_b")

    def test_handler_check_progress_filtered(self):
        """check_progress only fires on matching quest_keys."""
        self.char1.quests.add(MultiStepTestQuest)
        quest = self.char1.quests.get("test_multi")
        # Wrong quest key — should not advance
        self.char1.quests.check_progress(
            "step_a_done", quest_keys=["other_quest"]
        )
        self.assertEqual(quest.current_step, "step_a")
        # Right quest key — should advance
        self.char1.quests.check_progress(
            "step_a_done", quest_keys=["test_multi"]
        )
        self.assertEqual(quest.current_step, "step_b")


# ═══════════════════════════════════════════════════════
# CollectQuest template tests
# ═══════════════════════════════════════════════════════

class TestCollectQuest(EvenniaCommandTest):
    """Test the CollectQuest template."""

    character_typeclass = "typeclasses.actors.character.FCMCharacter"
    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def test_collect_quest_not_done_without_resources(self):
        """CollectQuest stays active when resources insufficient."""
        quest = self.char1.quests.add(CollectTestQuest)
        quest.progress()
        self.assertFalse(quest.is_completed)

    def test_collect_quest_completes_with_resources(self):
        """CollectQuest completes when resources are available."""
        quest = self.char1.quests.add(CollectTestQuest)
        # Set resources directly (bypasses blockchain service)
        self.char1.db.resources = {5: 2}
        quest.progress()
        self.assertTrue(quest.is_completed)

    def test_collect_quest_partial_resources(self):
        """CollectQuest stays active with insufficient resources."""
        quest = self.char1.quests.add(CollectTestQuest)
        self.char1.db.resources = {5: 1}  # only 1 of 2 needed
        quest.progress()
        self.assertFalse(quest.is_completed)


# ═══════════════════════════════════════════════════════
# VisitQuest template tests
# ═══════════════════════════════════════════════════════

class TestVisitQuest(EvenniaCommandTest):
    """Test the VisitQuest template."""

    character_typeclass = "typeclasses.actors.character.FCMCharacter"
    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def test_visit_quest_not_done_without_event(self):
        """VisitQuest stays active without enter_room event."""
        quest = self.char1.quests.add(VisitTestQuest)
        quest.progress(event_type="kill")
        self.assertFalse(quest.is_completed)

    def test_visit_quest_completes_on_enter_room(self):
        """VisitQuest completes on enter_room event."""
        quest = self.char1.quests.add(VisitTestQuest)
        quest.progress(event_type="enter_room")
        self.assertTrue(quest.is_completed)


# ═══════════════════════════════════════════════════════
# MultiStepQuest template tests
# ═══════════════════════════════════════════════════════

class TestMultiStepQuest(EvenniaCommandTest):
    """Test the MultiStepQuest template."""

    character_typeclass = "typeclasses.actors.character.FCMCharacter"
    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def test_multi_step_starts_at_step_0(self):
        """MultiStepQuest starts on step 0."""
        quest = self.char1.quests.add(MultiStepTemplateTestQuest)
        self.assertEqual(quest.current_step, "0")

    def test_multi_step_collect_not_done(self):
        """First step (collect) stays active without resources."""
        quest = self.char1.quests.add(MultiStepTemplateTestQuest)
        quest.progress(event_type="check")
        self.assertEqual(quest.current_step, "0")
        self.assertFalse(quest.is_completed)

    def test_multi_step_collect_advances(self):
        """First step (collect) advances when resources available."""
        quest = self.char1.quests.add(MultiStepTemplateTestQuest)
        self.char1.db.resources = {5: 1}
        quest.progress(event_type="check")
        self.assertEqual(quest.current_step, "1")

    def test_multi_step_visit_completes(self):
        """Second step (visit) completes the quest."""
        quest = self.char1.quests.add(MultiStepTemplateTestQuest)
        self.char1.db.resources = {5: 1}
        quest.progress(event_type="check")  # advance past collect
        quest.progress(event_type="enter_room")  # complete visit
        self.assertTrue(quest.is_completed)

    def test_multi_step_help(self):
        """help() returns current step help text."""
        quest = self.char1.quests.add(MultiStepTemplateTestQuest)
        self.assertEqual(quest.help(), "Get 1 Iron Ingot.")
        self.char1.db.resources = {5: 1}
        quest.progress(event_type="check")
        self.assertEqual(quest.help(), "Go to the destination.")


# ═══════════════════════════════════════════════════════
# QuestTagMixin tests
# ═══════════════════════════════════════════════════════

class TestQuestTagMixin(EvenniaCommandTest):
    """Test QuestTagMixin on rooms."""

    character_typeclass = "typeclasses.actors.character.FCMCharacter"
    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def test_room_has_quest_tags(self):
        """RoomBase inherits QuestTagMixin and has quest_tags."""
        self.assertEqual(self.room1.quest_tags, [])

    def test_fire_quest_event_no_tags(self):
        """fire_quest_event is a no-op when quest_tags is empty."""
        self.char1.quests.add(VisitTestQuest)
        self.room1.fire_quest_event(self.char1, "enter_room")
        quest = self.char1.quests.get("test_visit")
        self.assertFalse(quest.is_completed)

    def test_fire_quest_event_with_tags(self):
        """fire_quest_event dispatches when quest_tags match."""
        self.char1.quests.add(VisitTestQuest)
        self.room1.quest_tags = ["test_visit"]
        self.room1.fire_quest_event(self.char1, "enter_room")
        quest = self.char1.quests.get("test_visit")
        self.assertTrue(quest.is_completed)

    def test_fire_quest_event_wrong_tag(self):
        """fire_quest_event doesn't fire for non-matching tags."""
        self.char1.quests.add(VisitTestQuest)
        self.room1.quest_tags = ["other_quest"]
        self.room1.fire_quest_event(self.char1, "enter_room")
        quest = self.char1.quests.get("test_visit")
        self.assertFalse(quest.is_completed)

    def test_at_object_receive_fires_quest_event(self):
        """Room at_object_receive fires quest event on character entry."""
        self.char1.quests.add(VisitTestQuest)
        self.room2.quest_tags = ["test_visit"]
        self.char1.move_to(self.room2)
        quest = self.char1.quests.get("test_visit")
        self.assertTrue(quest.is_completed)


# ═══════════════════════════════════════════════════════
# CmdQuests (global character command) tests
# ═══════════════════════════════════════════════════════

class TestCmdQuests(EvenniaCommandTest):
    """Test the global quests command."""

    character_typeclass = "typeclasses.actors.character.FCMCharacter"
    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def test_quests_no_quests(self):
        """quests command shows message when no quests."""
        result = self.call(CmdQuests(), "")
        self.assertIn("no quests", result.lower())

    def test_quests_shows_active(self):
        """quests command lists active quests."""
        self.char1.quests.add(MultiStepTestQuest)
        result = self.call(CmdQuests(), "")
        self.assertIn("Active Quests", result)
        self.assertIn("Multi Step Test", result)

    def test_quests_shows_completed(self):
        """quests command lists completed quests."""
        _complete_quest(self.char1, SimpleTestQuest)
        result = self.call(CmdQuests(), "")
        self.assertIn("Completed Quests", result)
        self.assertIn("Simple Test", result)

    def test_quests_detail_by_key(self):
        """quests <key> shows quest details."""
        self.char1.quests.add(MultiStepTestQuest)
        result = self.call(CmdQuests(), "test_multi")
        self.assertIn("Multi Step Test", result)
        self.assertIn("started", result)

    def test_quests_detail_partial_match(self):
        """quests <partial> matches by name substring."""
        self.char1.quests.add(MultiStepTestQuest)
        result = self.call(CmdQuests(), "multi")
        self.assertIn("Multi Step Test", result)

    def test_quests_detail_not_found(self):
        """quests <bad_key> shows not found message."""
        result = self.call(CmdQuests(), "nonexistent")
        self.assertIn("No quest found", result)


# ═══════════════════════════════════════════════════════
# WarriorInitiation quest unit tests
# ═══════════════════════════════════════════════════════

class TestWarriorInitiation(EvenniaCommandTest):
    """Test WarriorInitiation quest logic directly."""

    character_typeclass = "typeclasses.actors.character.FCMCharacter"
    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        # Give char1 enough stats and a level to spend
        self.char1.strength = 14
        self.char1.constitution = 14
        self.char1.levels_to_spend = 1

    def test_can_accept_with_levels(self):
        """Can accept when levels_to_spend > 0."""
        quest_class = get_quest("warrior_initiation")
        can, reason = quest_class.can_accept(self.char1)
        self.assertTrue(can)

    def test_can_accept_no_levels(self):
        """Cannot accept when levels_to_spend == 0."""
        self.char1.levels_to_spend = 0
        quest_class = get_quest("warrior_initiation")
        can, reason = quest_class.can_accept(self.char1)
        self.assertFalse(can)
        self.assertIn("no levels", reason.lower())

    def test_can_accept_already_warrior(self):
        """Cannot accept when already a warrior."""
        self.char1.db.classes = {"warrior": {"level": 1}}
        quest_class = get_quest("warrior_initiation")
        can, reason = quest_class.can_accept(self.char1)
        self.assertFalse(can)
        self.assertIn("already a member", reason.lower())

    def test_can_accept_multiclass_low_str(self):
        """Cannot accept when multiclassing with low STR."""
        self.char1.db.classes = {"cleric": {"level": 1}}
        self.char1.strength = 10
        quest_class = get_quest("warrior_initiation")
        can, reason = quest_class.can_accept(self.char1)
        self.assertFalse(can)
        self.assertIn("STR", reason)

    def test_can_accept_multiclass_low_con(self):
        """Cannot accept when multiclassing with low CON."""
        self.char1.db.classes = {"cleric": {"level": 1}}
        self.char1.constitution = 10
        quest_class = get_quest("warrior_initiation")
        can, reason = quest_class.can_accept(self.char1)
        self.assertFalse(can)
        self.assertIn("CON", reason)

    def test_can_accept_first_class_no_stat_check(self):
        """First class (no existing classes) skips multiclass ability checks."""
        self.char1.strength = 8
        self.char1.constitution = 8
        quest_class = get_quest("warrior_initiation")
        can, reason = quest_class.can_accept(self.char1)
        self.assertTrue(can)

    def test_start_step_is_clear_rats(self):
        """Quest starts on clear_rats step."""
        quest_class = get_quest("warrior_initiation")
        quest = self.char1.quests.add(quest_class)
        self.assertEqual(quest.current_step, "clear_rats")

    def test_instant_induction_if_rat_cellar_done(self):
        """If rat_cellar already completed, quest completes on accept."""
        # Mark rat_cellar as completed
        rat_quest_class = get_quest("rat_cellar")
        rat_quest = self.char1.quests.add(rat_quest_class)
        rat_quest.status = "completed"

        quest_class = get_quest("warrior_initiation")
        quest = self.char1.quests.add(quest_class)
        self.assertTrue(quest.is_completed)
        classes = self.char1.db.classes or {}
        self.assertIn("warrior", classes)

    def test_step_clear_rats_not_done(self):
        """step_clear_rats tells player to go clear rats if not done."""
        quest_class = get_quest("warrior_initiation")
        quest = self.char1.quests.add(quest_class)
        quest.progress()  # rat_cellar not completed
        self.assertEqual(quest.current_step, "clear_rats")
        self.assertFalse(quest.is_completed)

    def test_step_clear_rats_done(self):
        """step_clear_rats completes if rat_cellar is done."""
        quest_class = get_quest("warrior_initiation")
        quest = self.char1.quests.add(quest_class)
        self.assertEqual(quest.current_step, "clear_rats")
        self.assertFalse(quest.is_completed)

        # Now complete rat_cellar and call progress
        rat_quest_class = get_quest("rat_cellar")
        rat_quest = self.char1.quests.add(rat_quest_class)
        rat_quest.status = "completed"

        quest.progress()
        self.assertTrue(quest.is_completed)

    def test_completion_grants_warrior(self):
        """Quest completion grants warrior level 1 and deducts levels_to_spend."""
        # Complete rat_cellar first
        rat_quest_class = get_quest("rat_cellar")
        rat_quest = self.char1.quests.add(rat_quest_class)
        rat_quest.status = "completed"

        quest_class = get_quest("warrior_initiation")
        quest = self.char1.quests.add(quest_class)

        self.assertTrue(quest.is_completed)
        self.assertEqual(self.char1.levels_to_spend, 0)
        classes = self.char1.db.classes or {}
        self.assertIn("warrior", classes)
        self.assertEqual(classes["warrior"]["level"], 1)

    def test_completion_fails_no_levels(self):
        """Quest fails if levels_to_spend is 0 at completion time."""
        quest_class = get_quest("warrior_initiation")
        quest = self.char1.quests.add(quest_class)
        # Simulate: player accepted quest, then spent their level elsewhere
        self.char1.levels_to_spend = 0

        # Complete rat_cellar so step_clear_rats tries to complete
        rat_quest_class = get_quest("rat_cellar")
        rat_quest = self.char1.quests.add(rat_quest_class)
        rat_quest.status = "completed"

        # Progress triggers step_clear_rats → complete → on_complete → fail
        quest.progress()

        self.assertTrue(quest.is_failed)
        classes = self.char1.db.classes or {}
        self.assertNotIn("warrior", classes)

    def test_help_text(self):
        """help() returns appropriate text for clear_rats step."""
        quest_class = get_quest("warrior_initiation")
        quest = self.char1.quests.add(quest_class)
        self.assertIn("cellar", quest.help().lower())


# ═══════════════════════════════════════════════════════
# Guildmaster CmdQuest tests
# ═══════════════════════════════════════════════════════

class TestCmdQuestGuildmaster(EvenniaCommandTest):
    """Test the guildmaster quest command."""

    character_typeclass = "typeclasses.actors.character.FCMCharacter"
    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.guildmaster = create.create_object(
            "typeclasses.actors.npcs.guildmaster.GuildmasterNPC",
            key="Warlord Thane",
            location=self.room1,
        )
        self.guildmaster.guild_class = "warrior"
        self.guildmaster.multi_class_quest_key = "warrior_initiation"
        # Give char1 a level to spend (required by WarriorInitiation.can_accept)
        self.char1.levels_to_spend = 1

    def test_quest_no_quest_key(self):
        """quest command says no quest when guildmaster has none."""
        self.guildmaster.multi_class_quest_key = None
        result = self.call(CmdQuest(), "", obj=self.guildmaster)
        self.assertIn("no quest", result.lower())

    def test_quest_shows_info(self):
        """quest command shows quest description."""
        result = self.call(CmdQuest(), "", obj=self.guildmaster)
        self.assertIn("Trial of Arms", result)
        self.assertIn("quest accept", result.lower())

    def test_quest_shows_info_no_levels(self):
        """quest command shows rejection when no levels to spend."""
        self.char1.levels_to_spend = 0
        result = self.call(CmdQuest(), "", obj=self.guildmaster)
        self.assertIn("Trial of Arms", result)
        self.assertIn("no levels", result.lower())

    def test_quest_accept(self):
        """quest accept adds quest to character."""
        result = self.call(CmdQuest(), "accept", obj=self.guildmaster)
        self.assertIn("accepted", result.lower())
        self.assertTrue(self.char1.quests.has("warrior_initiation"))

    def test_quest_accept_no_levels(self):
        """quest accept rejected when no levels to spend."""
        self.char1.levels_to_spend = 0
        result = self.call(CmdQuest(), "accept", obj=self.guildmaster)
        self.assertIn("no levels", result.lower())
        self.assertFalse(self.char1.quests.has("warrior_initiation"))

    def test_quest_accept_already_active(self):
        """quest accept when already on quest."""
        quest_class = get_quest("warrior_initiation")
        self.char1.quests.add(quest_class)
        result = self.call(CmdQuest(), "accept", obj=self.guildmaster)
        self.assertIn("already on", result.lower())

    def test_quest_shows_in_progress(self):
        """quest command shows in-progress status and triggers turn-in check."""
        quest_class = get_quest("warrior_initiation")
        self.char1.quests.add(quest_class)
        # No resources — should show "In Progress" and "need" message
        result = self.call(CmdQuest(), "", obj=self.guildmaster)
        self.assertIn("In Progress", result)

    def test_quest_triggers_progress_on_view(self):
        """Viewing quest at guildmaster calls progress() (turn-in)."""
        quest_class = get_quest("warrior_initiation")
        quest = self.char1.quests.add(quest_class)
        # Without rat_cellar done, step_clear_rats stays active
        self.call(CmdQuest(), "", obj=self.guildmaster)
        quest = self.char1.quests.get("warrior_initiation")
        self.assertEqual(quest.current_step, "clear_rats")

    def test_quest_abandon(self):
        """quest abandon removes quest."""
        quest_class = get_quest("warrior_initiation")
        self.char1.quests.add(quest_class)
        result = self.call(CmdQuest(), "abandon", obj=self.guildmaster)
        self.assertIn("abandoned", result.lower())
        self.assertFalse(self.char1.quests.has("warrior_initiation"))

    def test_quest_abandon_not_on_quest(self):
        """quest abandon when not on quest."""
        result = self.call(CmdQuest(), "abandon", obj=self.guildmaster)
        self.assertIn("not on this quest", result.lower())

    def test_quest_not_in_room(self):
        """quest command fails when guildmaster not in same room."""
        self.guildmaster.location = self.room2
        result = self.call(CmdQuest(), "", obj=self.guildmaster)
        self.assertIn("nobody here", result.lower())

    def test_quest_completed_shows_join_prompt(self):
        """quest command shows join prompt when quest is completed."""
        quest_class = get_quest("warrior_initiation")
        quest = self.char1.quests.add(quest_class)
        quest.status = "completed"
        result = self.call(CmdQuest(), "", obj=self.guildmaster)
        self.assertIn("completed", result.lower())
        self.assertIn("join", result.lower())


# ═══════════════════════════════════════════════════════
# Guildmaster CmdJoin quest integration tests
# ═══════════════════════════════════════════════════════

class TestCmdJoinQuestIntegration(EvenniaCommandTest):
    """Test that CmdJoin properly checks quest completion for multiclassing."""

    character_typeclass = "typeclasses.actors.character.FCMCharacter"
    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.guildmaster = create.create_object(
            "typeclasses.actors.npcs.guildmaster.GuildmasterNPC",
            key="Warlord Thane",
            location=self.room1,
        )
        self.guildmaster.guild_class = "warrior"
        self.guildmaster.multi_class_quest_key = "warrior_initiation"
        # Set high enough stats for multiclass requirements
        self.char1.strength = 14
        self.char1.dexterity = 14
        self.char1.constitution = 14
        self.char1.intelligence = 14
        self.char1.wisdom = 14
        self.char1.charisma = 14

    def test_join_first_class_no_quest_needed(self):
        """First class join doesn't require quest completion."""
        result = self.call(CmdJoin(), "", obj=self.guildmaster)
        self.assertIn("joined", result.lower())

    def test_join_multiclass_blocked_no_quest(self):
        """Multiclass join blocked when quest not started."""
        self.char1.db.classes = {"cleric": {"level": 1}}
        result = self.call(CmdJoin(), "", obj=self.guildmaster)
        self.assertIn("guild quest", result.lower())

    def test_join_multiclass_blocked_quest_in_progress(self):
        """Multiclass join blocked when quest is in progress."""
        self.char1.db.classes = {"cleric": {"level": 1}}
        self.char1.levels_to_spend = 1
        quest_class = get_quest("warrior_initiation")
        self.char1.quests.add(quest_class)
        result = self.call(CmdJoin(), "", obj=self.guildmaster)
        self.assertIn("not yet completed", result.lower())

    def test_join_multiclass_allowed_quest_completed(self):
        """Multiclass join succeeds when quest is completed."""
        self.char1.db.classes = {"cleric": {"level": 1}}
        # Add quest and mark complete directly (avoids blockchain calls)
        self.char1.levels_to_spend = 1
        quest_class = get_quest("warrior_initiation")
        quest = self.char1.quests.add(quest_class)
        quest.status = "completed"
        self.assertTrue(quest.is_completed)
        # Now join should work
        result = self.call(CmdJoin(), "", obj=self.guildmaster)
        self.assertIn("joined", result.lower())

    def test_join_no_quest_required(self):
        """Multiclass join works when guildmaster has no quest requirement."""
        self.char1.db.classes = {"cleric": {"level": 1}}
        self.guildmaster.multi_class_quest_key = None
        result = self.call(CmdJoin(), "", obj=self.guildmaster)
        self.assertIn("joined", result.lower())


# ═══════════════════════════════════════════════════════
# CmdGuild quest info display tests
# ═══════════════════════════════════════════════════════

class TestCmdGuildQuestDisplay(EvenniaCommandTest):
    """Test that CmdGuild shows quest status info."""

    character_typeclass = "typeclasses.actors.character.FCMCharacter"
    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.guildmaster = create.create_object(
            "typeclasses.actors.npcs.guildmaster.GuildmasterNPC",
            key="Warlord Thane",
            location=self.room1,
        )
        self.guildmaster.guild_class = "warrior"
        self.guildmaster.multi_class_quest_key = "warrior_initiation"

    def test_guild_shows_quest_requirement(self):
        """guild command shows quest requirement."""
        result = self.call(CmdGuild(), "", obj=self.guildmaster)
        self.assertIn("Guild Quest", result)
        self.assertIn("Trial of Arms", result)

    def test_guild_shows_quest_in_progress(self):
        """guild command shows quest in-progress status."""
        self.char1.levels_to_spend = 1
        quest_class = get_quest("warrior_initiation")
        self.char1.quests.add(quest_class)
        result = self.call(CmdGuild(), "", obj=self.guildmaster)
        self.assertIn("In Progress", result)

    def test_guild_shows_quest_completed(self):
        """guild command shows quest completed status."""
        self.char1.levels_to_spend = 1
        quest_class = get_quest("warrior_initiation")
        quest = self.char1.quests.add(quest_class)
        quest.status = "completed"
        result = self.call(CmdGuild(), "", obj=self.guildmaster)
        self.assertIn("Completed", result)


# ═══════════════════════════════════════════════════════
# CmdAdvance level cap tests
# ═══════════════════════════════════════════════════════

class TestCmdAdvanceLevelCap(EvenniaCommandTest):
    """Test guildmaster level cap on CmdAdvance."""

    character_typeclass = "typeclasses.actors.character.FCMCharacter"
    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.guildmaster = create.create_object(
            "typeclasses.actors.npcs.guildmaster.GuildmasterNPC",
            key="Warlord Thane",
            location=self.room1,
        )
        self.guildmaster.guild_class = "warrior"
        self.guildmaster.max_advance_level = 5
        self.guildmaster.next_guildmaster_hint = "the War Marshal in the Capital"
        # Make char1 a warrior with levels to spend
        self.char1.db.classes = {"warrior": {"level": 1, "skill_pts_available": 0}}
        self.char1.levels_to_spend = 3

    def test_advance_within_cap(self):
        """Advance succeeds when under guildmaster's cap."""
        result = self.call(CmdAdvance(), "", obj=self.guildmaster)
        self.assertIn("progressed to level", result.lower())
        classes = self.char1.db.classes
        self.assertEqual(classes["warrior"]["level"], 2)

    def test_advance_blocked_at_cap(self):
        """Advance refused when at guildmaster's max level."""
        self.char1.db.classes = {"warrior": {"level": 5, "skill_pts_available": 0}}
        result = self.call(CmdAdvance(), "", obj=self.guildmaster)
        self.assertIn("surpassed", result.lower())
        # Level should not have changed
        self.assertEqual(self.char1.db.classes["warrior"]["level"], 5)

    def test_advance_blocked_with_hint(self):
        """Blocked message includes next_guildmaster_hint."""
        self.char1.db.classes = {"warrior": {"level": 5, "skill_pts_available": 0}}
        result = self.call(CmdAdvance(), "", obj=self.guildmaster)
        self.assertIn("War Marshal", result)
        self.assertIn("Capital", result)

    def test_advance_blocked_no_hint(self):
        """Blocked message uses generic text when no hint set."""
        self.guildmaster.next_guildmaster_hint = None
        self.char1.db.classes = {"warrior": {"level": 5, "skill_pts_available": 0}}
        result = self.call(CmdAdvance(), "", obj=self.guildmaster)
        self.assertIn("surpassed", result.lower())
        self.assertIn("senior guildmaster", result.lower())

    def test_advance_default_cap_40(self):
        """Guildmaster with default cap (40) allows high levels."""
        self.guildmaster.max_advance_level = 40
        self.char1.db.classes = {"warrior": {"level": 39, "skill_pts_available": 0}}
        result = self.call(CmdAdvance(), "", obj=self.guildmaster)
        self.assertIn("progressed to level", result.lower())
        self.assertEqual(self.char1.db.classes["warrior"]["level"], 40)
