"""
Tests for follow/group system — follow, unfollow, nofollow, group commands
and auto-follow on exit traversal.

evennia test --settings settings tests.command_tests.test_cmd_follow
"""

from evennia.utils.test_resources import EvenniaCommandTest
from evennia.utils import create

from commands.all_char_cmds.cmd_follow import (
    CmdFollow,
    CmdUnfollow,
    CmdNofollow,
    CmdGroup,
)


class TestCmdFollow(EvenniaCommandTest):
    """Test the follow command."""

    character_typeclass = "typeclasses.actors.character.FCMCharacter"
    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.char1.following = None
        self.char1.nofollow = False
        self.char2.following = None
        self.char2.nofollow = False

    # --- Basic follow ---

    def test_follow_no_args_shows_status(self):
        """follow with no args shows current follow status."""
        result = self.call(CmdFollow(), "")
        self.assertIn("not following", result)

    def test_follow_no_args_when_following(self):
        """follow with no args when following shows who."""
        self.char1.following = self.char2
        result = self.call(CmdFollow(), "")
        self.assertIn(self.char2.key, result)

    def test_follow_target(self):
        """follow <target> sets following attribute."""
        result = self.call(CmdFollow(), self.char2.key)
        self.assertIn("start following", result)
        self.assertEqual(self.char1.following, self.char2)

    def test_follow_self_rejected(self):
        """Can't follow yourself."""
        result = self.call(CmdFollow(), "me")
        self.assertIn("can't follow yourself", result)
        self.assertIsNone(self.char1.following)

    def test_follow_nofollow_target(self):
        """Can't follow someone with nofollow enabled."""
        self.char2.nofollow = True
        result = self.call(CmdFollow(), self.char2.key)
        self.assertIn("not accepting followers", result)
        self.assertIsNone(self.char1.following)

    def test_follow_already_in_group(self):
        """Following someone you already follow (same leader) is rejected."""
        self.char1.following = self.char2
        result = self.call(CmdFollow(), self.char2.key)
        self.assertIn("already in", result)


class TestCmdUnfollow(EvenniaCommandTest):
    """Test the unfollow command."""

    character_typeclass = "typeclasses.actors.character.FCMCharacter"
    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.char1.following = None
        self.char2.following = None

    def test_unfollow_when_not_following(self):
        """Unfollow when not following shows message."""
        result = self.call(CmdUnfollow(), "")
        self.assertIn("not following", result)

    def test_unfollow_clears_following(self):
        """Unfollow clears the following attribute."""
        self.char1.following = self.char2
        result = self.call(CmdUnfollow(), "")
        self.assertIn("stop following", result)
        self.assertIsNone(self.char1.following)


class TestCmdNofollow(EvenniaCommandTest):
    """Test the nofollow toggle (convenience alias for toggle nofollow)."""

    character_typeclass = "typeclasses.actors.character.FCMCharacter"
    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.char1.following = None
        self.char1.nofollow = False
        self.char2.following = None
        self.char2.nofollow = False

    def test_nofollow_toggle_on_no_followers(self):
        """Nofollow toggles on when no followers — no modifier needed."""
        result = self.call(CmdNofollow(), "")
        self.assertIn("ON", result)
        self.assertTrue(self.char1.nofollow)

    def test_nofollow_toggle_off(self):
        """Nofollow toggles off."""
        self.char1.nofollow = True
        result = self.call(CmdNofollow(), "")
        self.assertIn("OFF", result)
        self.assertFalse(self.char1.nofollow)

    def test_nofollow_with_followers_requires_modifier(self):
        """Nofollow with followers and no modifier shows keep/disband prompt."""
        self.char2.following = self.char1
        result = self.call(CmdNofollow(), "")
        self.assertIn("keep", result)
        self.assertIn("disband", result)
        self.assertFalse(self.char1.nofollow)

    def test_nofollow_keep_preserves_followers(self):
        """nofollow keep turns on nofollow but keeps existing followers."""
        self.char2.following = self.char1
        result = self.call(CmdNofollow(), "keep")
        self.assertIn("ON", result)
        self.assertTrue(self.char1.nofollow)
        self.assertEqual(self.char2.following, self.char1)

    def test_nofollow_disband_kicks_followers(self):
        """nofollow disband turns on nofollow and removes followers."""
        self.char2.following = self.char1
        result = self.call(CmdNofollow(), "disband")
        self.assertIn("ON", result)
        self.assertIn("disbanded", result)
        self.assertTrue(self.char1.nofollow)
        self.assertIsNone(self.char2.following)


class TestCmdGroup(EvenniaCommandTest):
    """Test the group display command."""

    character_typeclass = "typeclasses.actors.character.FCMCharacter"
    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.char1.following = None
        self.char2.following = None

    def test_group_when_solo(self):
        """Group shows 'not in a group' when solo."""
        result = self.call(CmdGroup(), "")
        self.assertIn("not in a group", result)

    def test_group_shows_members(self):
        """Group shows leader and followers."""
        self.char1.following = self.char2
        result = self.call(CmdGroup(), "")
        self.assertIn(self.char2.key, result)
        self.assertIn(self.char1.key, result)


class TestGroupChainResolution(EvenniaCommandTest):
    """Test follow-chain leader resolution."""

    character_typeclass = "typeclasses.actors.character.FCMCharacter"
    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.char3 = create.create_object(
            "typeclasses.actors.character.FCMCharacter",
            key="Char3",
            location=self.room1,
        )
        self.char1.following = None
        self.char2.following = None
        self.char3.following = None

    def test_direct_leader(self):
        """A follows B → A's leader is B."""
        self.char1.following = self.char2
        self.assertEqual(self.char1.get_group_leader(), self.char2)

    def test_chain_leader(self):
        """A follows B follows C → A's leader is C."""
        self.char1.following = self.char2
        self.char2.following = self.char3
        self.assertEqual(self.char1.get_group_leader(), self.char3)

    def test_solo_leader_is_self(self):
        """Character with no following is their own leader."""
        self.assertEqual(self.char1.get_group_leader(), self.char1)

    def test_get_followers(self):
        """Leader's get_followers returns all direct and indirect followers."""
        self.char1.following = self.char2
        self.char3.following = self.char2
        followers = self.char2.get_followers()
        self.assertIn(self.char1, followers)
        self.assertIn(self.char3, followers)

    def test_get_followers_indirect(self):
        """Indirect followers are included."""
        self.char1.following = self.char2
        self.char2.following = self.char3
        # char3 is the leader, char2 and char1 follow
        followers = self.char3.get_followers()
        self.assertIn(self.char2, followers)
        self.assertIn(self.char1, followers)


class TestAutoFollow(EvenniaCommandTest):
    """Test that followers auto-move when the leader moves."""

    character_typeclass = "typeclasses.actors.character.FCMCharacter"
    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.char1.following = None
        self.char2.following = None
        # Create an exit from room1 to room2
        self.exit = create.create_object(
            "evennia.objects.objects.DefaultExit",
            key="north",
            location=self.room1,
            destination=self.room2,
        )

    def test_follower_auto_moves(self):
        """Follower in same room auto-moves when leader traverses exit."""
        self.char1.following = self.char2
        # char2 (leader) moves to room2
        self.char2.move_to(self.room2, move_type="traverse")
        # char1 (follower) should have auto-followed
        self.assertEqual(self.char1.location, self.room2)

    def test_non_follower_stays(self):
        """Non-follower doesn't move when another character moves."""
        # char1 is NOT following char2
        self.char2.move_to(self.room2, move_type="traverse")
        self.assertEqual(self.char1.location, self.room1)

    def test_chain_follow(self):
        """Chain followers auto-move: C follows B follows A, A moves → all follow."""
        char3 = create.create_object(
            "typeclasses.actors.character.FCMCharacter",
            key="Char3",
            location=self.room1,
        )
        # char1 follows char2, char3 follows char1
        # Leader is char2
        self.char1.following = self.char2
        char3.following = self.char1

        # char2 moves
        self.char2.move_to(self.room2, move_type="traverse")

        # Both should follow
        self.assertEqual(self.char1.location, self.room2)
        self.assertEqual(char3.location, self.room2)

    def test_follower_in_different_room_stays(self):
        """Follower in a different room doesn't auto-move."""
        self.char1.following = self.char2
        # Move char1 to room2 first (different room from leader)
        self.char1.move_to(self.room2, quiet=True, move_type="teleport")
        self.char1.following = self.char2  # re-set after move

        # char2 moves from room1 to room2
        self.char2.move_to(self.room2, move_type="traverse")

        # char1 was already in room2 — should stay there
        self.assertEqual(self.char1.location, self.room2)

    def test_follow_move_type_prevents_recursion(self):
        """Follower movement uses move_type='follow' to prevent infinite cascade."""
        self.char1.following = self.char2
        # This should not cause infinite recursion
        self.char2.move_to(self.room2, move_type="traverse")
        self.assertEqual(self.char1.location, self.room2)
        self.assertEqual(self.char2.location, self.room2)
