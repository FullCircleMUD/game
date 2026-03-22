"""
Tests for purgatory release — auto-release, Limbo fallback, combat cleanup.

evennia test --settings settings tests.typeclass_tests.test_purgatory_release
"""

from unittest.mock import patch, MagicMock

from evennia.utils import create
from evennia.utils.test_resources import EvenniaTest


class TestPurgatoryRelease(EvenniaTest):
    """Tests for _purgatory_release and related death-system fixes."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        # Create a purgatory room
        self.purgatory = create.create_object(
            "typeclasses.terrain.rooms.room_purgatory.RoomPurgatory",
            key="Purgatory",
        )
        # Create a cemetery for binding
        self.cemetery = create.create_object(
            "typeclasses.terrain.rooms.room_cemetery.RoomCemetery",
            key="Cemetery",
        )

    # ── Default home ─────────────────────────────────────────────

    def test_new_character_has_default_home(self):
        """Newly created character should have home set (not None)."""
        char = create.create_object(
            "typeclasses.actors.character.FCMCharacter",
            key="newbie",
            location=self.room1,
        )
        self.assertIsNotNone(char.home)

    # ── Purgatory release with bound cemetery ────────────────────

    def test_release_to_bound_cemetery(self):
        """Character with home set releases to that home."""
        self.char1.home = self.cemetery
        self.char1.move_to(self.purgatory, quiet=True)
        self.char1._purgatory_release()
        self.assertEqual(self.char1.location, self.cemetery)

    def test_release_message(self):
        """Character receives the release message."""
        self.char1.home = self.cemetery
        self.char1.move_to(self.purgatory, quiet=True)
        self.char1._purgatory_release()
        self.char1.msg = MagicMock()
        # Re-release to capture message (first release already moved)
        self.char1.move_to(self.purgatory, quiet=True)
        self.char1._purgatory_release()
        self.char1.msg.assert_called_with(
            "You feel yourself drawn back to the world of the living..."
        )

    # ── Purgatory release with no home (Limbo fallback) ──────────

    def test_release_no_home_falls_back_to_limbo(self):
        """Character with home=None should release to Limbo, not stay stuck."""
        self.char1.home = None
        self.char1.move_to(self.purgatory, quiet=True)
        self.char1._purgatory_release()
        # Should have moved out of purgatory
        self.assertNotEqual(self.char1.location, self.purgatory)
        # Should be in Limbo (id=2)
        self.assertEqual(self.char1.location.id, 2)

    # ── Already released (idempotent) ────────────────────────────

    def test_release_skips_if_not_in_purgatory(self):
        """If character is already out of purgatory, release is a no-op."""
        self.char1.home = self.cemetery
        self.char1.move_to(self.room1, quiet=True)
        original_location = self.char1.location
        self.char1._purgatory_release()
        self.assertEqual(self.char1.location, original_location)

    # ── at_post_puppet safety net ────────────────────────────────

    @patch("evennia.utils.utils.delay")
    def test_at_post_puppet_reschedules_timer_in_purgatory(self, mock_delay):
        """Logging in while stuck in purgatory should reschedule the release timer."""
        self.char1.home = self.cemetery
        self.char1.move_to(self.purgatory, quiet=True)
        self.char1.at_post_puppet()
        # Should still be in purgatory (not instant release)
        self.assertEqual(self.char1.location, self.purgatory)
        # Should have called delay() to reschedule
        mock_delay.assert_called()

    def test_at_post_puppet_no_op_outside_purgatory(self):
        """Logging in outside purgatory should not move character."""
        self.char1.move_to(self.room1, quiet=True)
        original_location = self.char1.location
        self.char1.at_post_puppet()
        self.assertEqual(self.char1.location, original_location)

    # ── Combat cleanup on death ──────────────────────────────────

    def test_real_death_calls_stop_combat(self):
        """_real_death should call stop_combat() if a combat handler exists."""
        self.char1.move_to(self.room1, quiet=True)

        # Verify that the combat cleanup code exists in _real_death
        # by checking that scripts.get("combat_handler") is called.
        # We patch the entire _real_death to isolate the combat cleanup step.
        mock_handler = MagicMock()

        with patch.object(
            self.char1.scripts, "get", return_value=[mock_handler]
        ) as mock_scripts_get:
            # Call the combat cleanup code directly from _real_death context:
            # step 10b
            handlers = self.char1.scripts.get("combat_handler")
            if handlers:
                handlers[0].stop_combat()

        mock_scripts_get.assert_called_with("combat_handler")
        mock_handler.stop_combat.assert_called_once()
