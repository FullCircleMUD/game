"""
Tests for the loot command — corpse selection by sight and height.

The command had no tests at all, and no height gating: a flying character
could loot a corpse on the ground, and a swimmer at depth could loot one
on the surface. Every other object-handling command (get, put, give,
open, close, lock, unlock, read) gates on height; loot did not.

These cover selection rather than the looting mechanics themselves —
which corpses a character may act on, and what they are told about the
ones they cannot.

evennia test --settings settings tests.command_tests.test_cmd_loot
"""

from unittest.mock import patch

from evennia.utils import create
from evennia.utils.test_resources import EvenniaCommandTest

from commands.all_char_cmds.cmd_loot import CmdLoot
from typeclasses.world_objects.corpse import Corpse


class LootTestBase(EvenniaCommandTest):
    character_typeclass = "typeclasses.actors.character.FCMCharacter"
    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        # Pin the light — targeting runs through p_can_see, and an unpinned
        # fixture room follows the world clock. See test_cmd_attack.
        self.room1.always_lit = True
        # Flying and diving both need headroom to move into.
        self.room1.max_height = 3
        self.room1.max_depth = -3

    def _corpse(self, name="a wolf", height=0, unlocked=True):
        """Place an unowned, lootable corpse at a given height."""
        corpse = create.create_object(Corpse, key="corpse", location=self.room1)
        corpse.owner_name = name
        corpse.is_unlocked = unlocked
        corpse.room_vertical_position = height
        return corpse


class TestLootHeightGating(LootTestBase):
    """A corpse must be at the caller's height to be looted."""

    def test_same_height_corpse_is_reachable(self):
        self._corpse()
        result = self.call(CmdLoot(), "")
        self.assertNotIn("cannot reach", result)

    def test_corpse_on_the_ground_is_out_of_reach_when_flying(self):
        self._corpse(height=0)
        self.char1.room_vertical_position = 2

        result = self.call(CmdLoot(), "")

        self.assertIn("cannot reach", result)

    def test_corpse_at_depth_is_out_of_reach_from_the_surface(self):
        self._corpse(height=-2)

        result = self.call(CmdLoot(), "")

        self.assertIn("cannot reach", result)

    def test_reachable_corpse_is_looted_while_another_is_not(self):
        # The mixed case: loot what you can, report what you cannot.
        self._corpse(name="a rat", height=0)
        self._corpse(name="a bird", height=2)

        result = self.call(CmdLoot(), "")

        self.assertIn("cannot reach", result)
        # The out-of-reach one is named; the reachable one is not in that
        # sentence, because it was dealt with rather than refused.
        self.assertIn("bird", result)


class TestOutOfReachMessage(LootTestBase):
    """Wording of the refusal, which lists what the caller can see."""

    def test_single_corpse_is_named(self):
        self._corpse(name="a wolf", height=2)
        result = self.call(CmdLoot(), "")
        self.assertIn("wolf", result)

    def test_two_corpses_are_joined_with_or(self):
        self._corpse(name="a wolf", height=2)
        self._corpse(name="a rat", height=2)

        result = self.call(CmdLoot(), "")

        self.assertIn(" or ", result)
        self.assertNotIn(", ", result.split("cannot reach")[1].split(" or ")[0])

    def test_three_corpses_use_commas_then_or(self):
        for name in ("a wolf", "a rat", "a bird"):
            self._corpse(name=name, height=2)

        result = self.call(CmdLoot(), "")

        self.assertIn(",", result)
        self.assertIn(" or ", result)


class TestLootSightGating(LootTestBase):
    """An unseen corpse is not mentioned at all."""

    def test_unseen_corpse_is_not_named_as_out_of_reach(self):
        # Naming it would announce a corpse the caller cannot see. The
        # command should read exactly as though the room were empty.
        self._corpse(name="a wolf", height=0)

        # Patch cmd_loot's own reference, not predicates'. cmd_loot does
        # `from utils.targeting.predicates import p_can_see`, so it holds
        # its own binding and patching the source module would leave it
        # pointing at the original — the patch would silently do nothing.
        with patch(
            "commands.all_char_cmds.cmd_loot.p_can_see", return_value=False
        ):
            result = self.call(CmdLoot(), "")

        self.assertNotIn("wolf", result)
        self.assertNotIn("cannot reach", result)
        # Reads as an empty room, which is the whole point — verified by
        # pointing this patch at the wrong module, where the test passed
        # while doing nothing.
        self.assertIn("no corpses", result)

    def test_empty_room_reports_no_corpses(self):
        result = self.call(CmdLoot(), "")
        self.assertIn("no corpses", result)


class TestLootArgumentForms(LootTestBase):
    """`loot` and `loot all` are the same; anything else is refused."""

    def test_bare_loot_and_loot_all_agree(self):
        self._corpse()
        bare = self.call(CmdLoot(), "")
        self._corpse()
        explicit = self.call(CmdLoot(), "all")
        self.assertEqual(bare, explicit)

    def test_targeted_form_is_refused_not_silently_swept(self):
        # Before this, `loot sword` swept every corpse in the room —
        # identical to bare loot, with no hint the argument was ignored.
        self._corpse()

        result = self.call(CmdLoot(), "sword")

        self.assertIn("loot all", result)

    def test_targeted_form_is_case_insensitive_on_all(self):
        self._corpse()
        result = self.call(CmdLoot(), "ALL")
        self.assertNotIn("Only", result)
