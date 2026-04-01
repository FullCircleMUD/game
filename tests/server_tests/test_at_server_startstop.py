"""
Tests for at_server_startstop — spawned item cleanup helpers.

Verifies _is_player_owned() correctly identifies player characters and
account banks vs non-player objects.

evennia test --settings settings tests.server_tests.test_at_server_startstop
"""

from unittest import TestCase
from unittest.mock import MagicMock, patch

from utils.spawn_cleanup import _is_player_owned


class TestIsPlayerOwned(TestCase):
    """Test _is_player_owned() helper."""

    def test_none_is_not_player_owned(self):
        """None should not be player-owned."""
        self.assertFalse(_is_player_owned(None))

    def test_mock_character_is_player_owned(self):
        """Object that is instance of FCMCharacter should be player-owned."""
        # Import the real classes for isinstance check
        from typeclasses.actors.character import FCMCharacter
        from typeclasses.accounts.account_bank import AccountBank

        obj = MagicMock(spec=FCMCharacter)
        self.assertTrue(_is_player_owned(obj))

    def test_mock_bank_is_player_owned(self):
        """Object that is instance of AccountBank should be player-owned."""
        from typeclasses.accounts.account_bank import AccountBank

        obj = MagicMock(spec=AccountBank)
        self.assertTrue(_is_player_owned(obj))

    def test_generic_mock_is_not_player_owned(self):
        """Generic object should not be player-owned."""
        obj = MagicMock()
        self.assertFalse(_is_player_owned(obj))
