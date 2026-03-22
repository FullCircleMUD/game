"""
Tests for the toggle command and PlayerPreferencesMixin.

evennia test --settings settings tests.command_tests.test_cmd_toggle
"""

from evennia.utils.test_resources import EvenniaCommandTest

from commands.all_char_cmds.cmd_toggle import CmdToggle


WALLET_A = "0xAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"


class TestCmdToggle(EvenniaCommandTest):
    """Test the toggle command and underlying preferences mixin."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)

    # ── Display all preferences ────────────────────────────────────────

    def test_show_all_preferences(self):
        """toggle with no args shows the preference table."""
        result = self.call(CmdToggle(), "")
        self.assertIn("Preferences", result)
        self.assertIn("brief", result)
        self.assertIn("autoexit", result)

    # ── Toggle brief ───────────────────────────────────────────────────

    def test_toggle_brief_on(self):
        """Toggling brief from default OFF should turn it ON."""
        self.assertFalse(self.char1.brief_mode)
        result = self.call(CmdToggle(), "brief")
        self.assertIn("ON", result)
        self.assertTrue(self.char1.brief_mode)

    def test_toggle_brief_off(self):
        """Toggling brief twice returns to OFF."""
        self.call(CmdToggle(), "brief")
        result = self.call(CmdToggle(), "brief")
        self.assertIn("OFF", result)
        self.assertFalse(self.char1.brief_mode)

    # ── Toggle autoexit ────────────────────────────────────────────────

    def test_toggle_autoexit_off(self):
        """Toggling autoexit from default ON should turn it OFF."""
        self.assertTrue(self.char1.auto_exits)
        result = self.call(CmdToggle(), "autoexit")
        self.assertIn("OFF", result)
        self.assertFalse(self.char1.auto_exits)

    def test_toggle_autoexit_on(self):
        """Toggling autoexit twice returns to ON."""
        self.call(CmdToggle(), "autoexit")
        result = self.call(CmdToggle(), "autoexit")
        self.assertIn("ON", result)
        self.assertTrue(self.char1.auto_exits)

    # ── Invalid preference ─────────────────────────────────────────────

    def test_invalid_preference(self):
        """Unknown preference name shows error with valid options."""
        result = self.call(CmdToggle(), "nosuchpref")
        self.assertIn("Unknown preference", result)
        self.assertIn("brief", result)
        self.assertIn("autoexit", result)

    # ── Display reflects current state ─────────────────────────────────

    def test_display_reflects_toggled_state(self):
        """After toggling brief ON, the display table should show ON."""
        self.call(CmdToggle(), "brief")
        result = self.call(CmdToggle(), "")
        self.assertIn("ON", result)

    # ── Mixin direct method tests ──────────────────────────────────────

    def test_toggle_preference_returns_none_for_unknown(self):
        """toggle_preference() returns None for unrecognised names."""
        result = self.char1.toggle_preference("nonexistent")
        self.assertIsNone(result)

    def test_toggle_preference_returns_tuple(self):
        """toggle_preference() returns (name, new_value) on success."""
        result = self.char1.toggle_preference("brief")
        self.assertEqual(result, ("brief", True))

    def test_case_insensitive_toggle(self):
        """Preference names should be case-insensitive."""
        result = self.char1.toggle_preference("BRIEF")
        self.assertEqual(result, ("brief", True))

    # ── Gated preferences (smite) ───────────────────────────────────

    def test_smite_toggle_works_when_memorised(self):
        """toggle smite should work when player has smite memorised."""
        self.char1.db.memorised_spells = {"smite": True}
        self.assertFalse(self.char1.smite_active)
        result = self.call(CmdToggle(), "smite")
        self.assertIn("ON", result)
        self.assertTrue(self.char1.smite_active)

    def test_smite_toggle_blocked_when_not_memorised(self):
        """toggle smite should fail when player hasn't memorised smite."""
        self.char1.db.memorised_spells = {}
        result = self.call(CmdToggle(), "smite")
        self.assertIn("memorised", result.lower())
        self.assertFalse(self.char1.smite_active)

    def test_gated_pref_hidden_from_display(self):
        """Gated prefs should not show in display when gate fails."""
        self.char1.db.memorised_spells = {}
        result = self.call(CmdToggle(), "")
        self.assertNotIn("smite", result)

    def test_gated_pref_shown_in_display_when_gate_passes(self):
        """Gated prefs should show in display when gate passes."""
        self.char1.db.memorised_spells = {"smite": True}
        result = self.call(CmdToggle(), "")
        self.assertIn("smite", result)

    def test_gated_pref_hidden_from_valid_options(self):
        """Invalid pref error should not list gated prefs that fail gate."""
        self.char1.db.memorised_spells = {}
        result = self.call(CmdToggle(), "nosuchpref")
        self.assertNotIn("smite", result)

    # ── Gated preferences (shield) ────────────────────────────────────

    def test_shield_toggle_works_when_memorised(self):
        """toggle shield should work when player has shield memorised."""
        self.char1.db.memorised_spells = {"shield": True}
        self.assertFalse(self.char1.shield_active)
        result = self.call(CmdToggle(), "shield")
        self.assertIn("ON", result)
        self.assertTrue(self.char1.shield_active)

    def test_shield_toggle_blocked_when_not_memorised(self):
        """toggle shield should fail when player hasn't memorised shield."""
        self.char1.db.memorised_spells = {}
        result = self.call(CmdToggle(), "shield")
        self.assertIn("memorised", result.lower())
        self.assertFalse(self.char1.shield_active)

    def test_shield_gated_pref_hidden_from_display(self):
        """Shield should not show in display when not memorised."""
        self.char1.db.memorised_spells = {}
        result = self.call(CmdToggle(), "")
        self.assertNotIn("shield", result)

    def test_shield_gated_pref_shown_in_display_when_gate_passes(self):
        """Shield should show in display when memorised."""
        self.char1.db.memorised_spells = {"shield": True}
        result = self.call(CmdToggle(), "")
        self.assertIn("shield", result)

    # ── Nofollow via toggle command ───────────────────────────────────

    def test_toggle_nofollow_on_no_followers(self):
        """toggle nofollow with no followers just toggles."""
        self.assertFalse(self.char1.nofollow)
        result = self.call(CmdToggle(), "nofollow")
        self.assertIn("ON", result)
        self.assertTrue(self.char1.nofollow)

    def test_toggle_nofollow_off(self):
        """toggle nofollow when already on turns it off."""
        self.char1.nofollow = True
        result = self.call(CmdToggle(), "nofollow")
        self.assertIn("OFF", result)
        self.assertFalse(self.char1.nofollow)

    def test_toggle_nofollow_shown_in_display(self):
        """nofollow should appear in the preferences display."""
        result = self.call(CmdToggle(), "")
        self.assertIn("nofollow", result)
