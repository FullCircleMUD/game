"""
Tests for session-end telemetry when a character is unpuppeted.

Evennia's maintenance loop runs a link-dead sweep once a minute: it
finds objects still tagged ``puppeted`` that have no sessions left — a
crash, a closed browser tab, a dropped connection — and runs the
unpuppet hooks for them. It has no account to hand, so it passes
``None``.

The account is still recoverable. A clean quit clears ``db_account``
and *then* passes the account as the argument; the sweep fires because
that clean path never ran, so ``db_account`` survives. Reading whichever
one is present closes the ``PlayerSession`` row either way.

Closing it matters rather than skipping the telemetry: an unclosed row
keeps that character inside ``get_active_player_count_7d`` forever, and
that count is the denominator saturation divides by — so a character who
played once and dropped would inflate the active population, and the
spawner reads a low saturation as scarcity.

evennia test --settings settings tests.typeclass_tests.test_session_end_telemetry
"""

from evennia.utils.test_resources import EvenniaTest

from telemetry.models import PlayerSession
from telemetry.services import TelemetryWriteService


class SessionEndTest(EvenniaTest):
    """A character with one open session row."""

    character_typeclass = "typeclasses.actors.character.FCMCharacter"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.char1.account = self.account
        TelemetryWriteService.record_session_start(self.account.id, self.char1.key)

    def _open_rows(self):
        return PlayerSession.objects.filter(
            character_key=self.char1.key, ended_at__isnull=True
        )

    def _closed_rows(self):
        return PlayerSession.objects.filter(
            character_key=self.char1.key, ended_at__isnull=False
        )


class TestACleanQuitClosesTheSession(SessionEndTest):
    """The account arrives as the argument, as it always did."""

    def test_the_row_is_closed(self):
        self.char1.at_post_unpuppet(self.account)
        self.assertEqual(self._open_rows().count(), 0)

    def test_an_end_time_is_stamped(self):
        self.char1.at_post_unpuppet(self.account)
        self.assertIsNotNone(self._closed_rows().first().ended_at)


class TestTheLinkDeadSweepClosesItToo(SessionEndTest):
    """
    The sweep passes ``None``. Reading ``account.id`` off that argument
    raised ``AttributeError``, which killed the sweep before it could
    clear the ``puppeted`` tag — and left the session row open.
    """

    def test_no_account_argument_does_not_raise(self):
        self.char1.at_post_unpuppet(None)

    def test_the_row_is_still_closed(self):
        self.char1.at_post_unpuppet(None)
        self.assertEqual(self._open_rows().count(), 0)

    def test_the_account_comes_off_the_character(self):
        """db_account survives precisely because the clean path never ran."""
        self.assertEqual(self.char1.account, self.account)
        self.char1.at_post_unpuppet(None)
        self.assertIsNotNone(self._closed_rows().first().ended_at)

    def test_the_argument_is_optional(self):
        """Evennia's base declares it optional; ours has to accept that."""
        self.char1.at_post_unpuppet()
        self.assertEqual(self._open_rows().count(), 0)


class TestWithNoAccountAnywhere(SessionEndTest):
    """
    Both sources gone. Nothing can be closed, and nothing may crash —
    the sweep still has a tag to clear after this hook returns.
    """

    def setUp(self):
        super().setUp()
        del self.char1.account

    def test_it_does_not_raise(self):
        self.char1.at_post_unpuppet(None)

    def test_the_row_is_left_open(self):
        self.char1.at_post_unpuppet(None)
        self.assertEqual(self._open_rows().count(), 1)
