"""
Tests for CmdMemorise and CmdForget commands.

CmdMemorise validates spell knowledge, school mastery, memorisation state,
and cap before starting a timed delay. CmdForget is instant.

evennia test --settings settings tests.command_tests.test_cmd_memorise
"""

from unittest.mock import patch

from evennia.utils.test_resources import EvenniaCommandTest

from commands.all_char_cmds.cmd_memorise import CmdMemorise, CmdForget


WALLET_A = "0xAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"


def _instant_delay(seconds, callback, *args, **kwargs):
    """Mock for utils.delay — executes callback immediately."""
    callback(*args, **kwargs)


def _stand_up_then_tick(char):
    """Mock for utils.delay that stands the character up mid-memorisation."""
    def _delay(seconds, callback, *args, **kwargs):
        char.position = "standing"
        callback(*args, **kwargs)
    return _delay


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
        self.char1.position = "sitting"

    def test_no_args(self):
        """Memorise with no arguments should show usage."""
        self.call(CmdMemorise(), "", "Memorise what?")

    def test_unknown_spell(self):
        """Memorise with unknown spell name should fail."""
        self.call(CmdMemorise(), "fireball", "You don't know Fireball.")

    def test_spell_not_known(self):
        """Memorise a spell not in spellbook should fail."""
        self.call(CmdMemorise(), "cure wounds", "You don't know Cure Wounds")

    def test_mastery_too_low(self):
        """Memorise with insufficient school mastery should fail."""
        # Character has evocation mastery 0 (UNSKILLED), spell requires BASIC (1)
        self.char1.db.class_skill_mastery_levels = {"evocation": 0}

        self.call(CmdMemorise(), "magic missile", "Your mastery of")

    def test_mastery_too_low_nested_dict(self):
        """Memorise with nested dict mastery format (from chargen) should work."""
        # Chargen stores mastery as nested dict
        self.char1.db.class_skill_mastery_levels = {
            "evocation": {"mastery": 0, "classes": ["mage"]}
        }

        self.call(CmdMemorise(), "magic missile", "Your mastery of")

    def test_mastery_sufficient_nested_dict(self):
        """Memorise with sufficient nested dict mastery should proceed."""
        self.char1.db.class_skill_mastery_levels = {
            "evocation": {"mastery": 1, "classes": ["mage"]}
        }

        with patch(
            "utils.busy.delay",
            side_effect=_instant_delay,
        ):
            result = self.call(CmdMemorise(), "magic missile")
            self.assertIn("memorise", result.lower())

    def test_already_memorised(self):
        """Memorise a spell that's already memorised should fail."""
        self.char1.db.memorised_spells = {"magic_missile": True}

        self.call(CmdMemorise(), "magic missile", "Magic Missile is already memorised")

    def test_cap_reached(self):
        """Memorise with every slot full should fail before the delay."""
        with patch.object(
            type(self.char1), "get_memorisation_cap", return_value=1,
        ):
            self.char1.db.memorised_spells = {"cure_wounds": True}
            self.call(CmdMemorise(), "magic missile", "You can only memorise 1 spell")

    def test_already_busy(self):
        """Memorise while busy with another action should fail."""
        self.char1.ndb.is_processing = True
        self.call(CmdMemorise(), "magic missile", "You are busy")

    def test_must_be_sitting(self):
        """Standing, resting and fighting are all refused."""
        for position in ("standing", "resting", "fighting"):
            self.char1.position = position
            self.call(CmdMemorise(), "magic missile", "You must sit down")

    def test_refused_while_asleep(self):
        """A sleeping character is turned away by the sleep gate."""
        self.char1.position = "sleeping"
        self.call(CmdMemorise(), "magic missile", "In your dreams")

    def test_memorising_holds_the_busy_lock(self):
        """A memorising character reads as busy to other commands."""
        with patch("utils.busy.delay"):
            self.call(CmdMemorise(), "magic missile")
        self.assertTrue(self.char1.ndb.is_processing)

    def test_standing_up_loses_the_spell(self):
        """Getting up before the last tick abandons the memorisation."""
        with patch(
            "utils.busy.delay",
            side_effect=_stand_up_then_tick(self.char1),
        ):
            result = self.call(CmdMemorise(), "magic missile")
        self.assertIn("lost your place", result)
        self.assertEqual(self.char1.db.memorised_spells, {})


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
        self.char1.position = "sitting"

    def test_memorise_granted_spell(self):
        """A granted spell should be memorisable."""
        with patch(
            "utils.busy.delay",
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
        result = self.call(CmdForget(), "magic missile")
        self.assertIn("Magic Missile", result)

    def test_forget_not_memorised(self):
        """Forgetting a spell that isn't memorised should fail."""
        self.char1.db.memorised_spells = {}

        result = self.call(CmdForget(), "magic missile")
        self.assertIn("don't have magic missile memorised", result.lower())
