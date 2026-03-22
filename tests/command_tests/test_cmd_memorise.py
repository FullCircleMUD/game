"""
Tests for CmdMemorise and CmdForget commands.

CmdMemorise validates spell knowledge, school mastery, memorisation state,
and cap before starting a timed delay. CmdForget is instant.

evennia test --settings settings tests.command_tests.test_cmd_memorise
"""

from unittest.mock import patch, MagicMock

from evennia.utils.test_resources import EvenniaCommandTest

from commands.all_char_cmds.cmd_memorise import CmdMemorise, CmdForget


WALLET_A = "0xAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"


def _make_spell(name, school_key, key, min_mastery_value=1):
    """Create a mock spell object."""
    spell = MagicMock()
    spell.name = name
    spell.school_key = school_key
    spell.key = key
    spell.min_mastery = MagicMock()
    spell.min_mastery.value = min_mastery_value
    spell.min_mastery.name = {0: "UNSKILLED", 1: "BASIC", 2: "SKILLED"}.get(
        min_mastery_value, "BASIC"
    )
    spell.aliases = []
    return spell


def _instant_delay(seconds, callback, *args, **kwargs):
    """Mock for utils.delay — executes callback immediately."""
    callback(*args, **kwargs)


# ── Memorise Command — Validation ──────────────────────────────────

class TestCmdMemoriseValidation(EvenniaCommandTest):
    """Test memorise command validation failures."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.char1.db.spellbook = {"magic_missile": True}
        self.char1.db.granted_spells = {}
        self.char1.db.memorised_spells = {}
        self.char1.db.class_skill_mastery_levels = {"evocation": 1}
        self.char1.db.classes = {"mage": {"level": 4}}
        self.char1.intelligence = 14
        self.char1.wisdom = 10

    def test_no_args(self):
        """Memorise with no arguments should show usage."""
        self.call(CmdMemorise(), "", "Memorise what?")

    def test_unknown_spell(self):
        """Memorise with unknown spell name should fail."""
        self.call(CmdMemorise(), "fireball", "You don't know Fireball.")

    def test_spell_not_known(self):
        """Memorise a spell not in spellbook should fail."""
        spell = _make_spell("Cure Wounds", "divine_healing", "cure_wounds")

        with patch(
            "commands.all_char_cmds.cmd_memorise.SPELL_REGISTRY",
            {"cure_wounds": spell},
        ):
            self.call(CmdMemorise(), "cure wounds", "You don't know Cure Wounds")

    def test_mastery_too_low(self):
        """Memorise with insufficient school mastery should fail."""
        # Character has evocation mastery 0 (UNSKILLED), spell requires BASIC (1)
        self.char1.db.class_skill_mastery_levels = {"evocation": 0}
        spell = _make_spell("Magic Missile", "evocation", "magic_missile", 1)

        with patch(
            "commands.all_char_cmds.cmd_memorise.SPELL_REGISTRY",
            {"magic_missile": spell},
        ):
            self.call(CmdMemorise(), "magic missile", "Your mastery of")

    def test_mastery_too_low_nested_dict(self):
        """Memorise with nested dict mastery format (from chargen) should work."""
        # Chargen stores mastery as nested dict
        self.char1.db.class_skill_mastery_levels = {
            "evocation": {"mastery": 0, "classes": ["mage"]}
        }
        spell = _make_spell("Magic Missile", "evocation", "magic_missile", 1)

        with patch(
            "commands.all_char_cmds.cmd_memorise.SPELL_REGISTRY",
            {"magic_missile": spell},
        ):
            self.call(CmdMemorise(), "magic missile", "Your mastery of")

    def test_mastery_sufficient_nested_dict(self):
        """Memorise with sufficient nested dict mastery should proceed."""
        self.char1.db.class_skill_mastery_levels = {
            "evocation": {"mastery": 1, "classes": ["mage"]}
        }
        spell = _make_spell("Magic Missile", "evocation", "magic_missile", 1)

        with patch(
            "commands.all_char_cmds.cmd_memorise.SPELL_REGISTRY",
            {"magic_missile": spell},
        ), patch(
            "commands.all_char_cmds.cmd_memorise.delay",
            side_effect=_instant_delay,
        ):
            result = self.call(CmdMemorise(), "magic missile")
            self.assertIn("memorise", result.lower())

    def test_already_memorised(self):
        """Memorise a spell that's already memorised should fail."""
        self.char1.db.memorised_spells = {"magic_missile": True}
        spell = _make_spell("Magic Missile", "evocation", "magic_missile")

        with patch(
            "commands.all_char_cmds.cmd_memorise.SPELL_REGISTRY",
            {"magic_missile": spell},
        ):
            self.call(CmdMemorise(), "magic missile", "Magic Missile is already memorised")

    def test_already_memorising(self):
        """Memorise while already memorising should fail."""
        self.char1.ndb.is_memorising = True
        self.call(CmdMemorise(), "magic missile", "You are already memorising")


# ── Memorise Command — Granted Spells ──────────────────────────────

class TestCmdMemoriseGranted(EvenniaCommandTest):
    """Test that granted spells can be memorised."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.char1.db.spellbook = {}
        self.char1.db.granted_spells = {"cure_wounds": True}
        self.char1.db.memorised_spells = {}
        self.char1.db.class_skill_mastery_levels = {"divine_healing": 1}
        self.char1.db.classes = {"cleric": {"level": 4}}
        self.char1.wisdom = 14
        self.char1.intelligence = 10

    def test_memorise_granted_spell(self):
        """A granted spell should be memorisable."""
        spell = _make_spell("Cure Wounds", "divine_healing", "cure_wounds")

        with patch(
            "commands.all_char_cmds.cmd_memorise.SPELL_REGISTRY",
            {"cure_wounds": spell},
        ), patch(
            "commands.all_char_cmds.cmd_memorise.delay",
            side_effect=_instant_delay,
        ):
            result = self.call(CmdMemorise(), "cure wounds")
            self.assertIn("memorise", result.lower())


# ── Forget Command ─────────────────────────────────────────────────

class TestCmdForget(EvenniaCommandTest):
    """Test forget command."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.char1.db.spellbook = {"magic_missile": True}
        self.char1.db.granted_spells = {}
        self.char1.db.memorised_spells = {"magic_missile": True}

    def test_no_args(self):
        """Forget with no arguments should show usage."""
        self.call(CmdForget(), "", "Forget what?")

    def test_forget_success(self):
        """Forgetting a memorised spell should succeed."""
        spell = _make_spell("Magic Missile", "evocation", "magic_missile")

        with patch(
            "commands.all_char_cmds.cmd_memorise.SPELL_REGISTRY",
            {"magic_missile": spell},
        ):
            result = self.call(CmdForget(), "magic missile")
            self.assertIn("Magic Missile", result)

    def test_forget_not_memorised(self):
        """Forgetting a spell that isn't memorised should fail."""
        self.char1.db.memorised_spells = {}
        spell = _make_spell("Magic Missile", "evocation", "magic_missile")

        with patch(
            "commands.all_char_cmds.cmd_memorise.SPELL_REGISTRY",
            {"magic_missile": spell},
        ):
            result = self.call(CmdForget(), "magic missile")
            self.assertIn("isn't memorised", result.lower())
