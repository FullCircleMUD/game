"""
Tests for CmdSpells — spellbook display command.

Verifies display of known spells, memorised markers, empty spellbook,
and grouping by school.

evennia test --settings settings tests.command_tests.test_cmd_spells
"""

from unittest.mock import patch, MagicMock

from evennia.utils.test_resources import EvenniaCommandTest

from commands.all_char_cmds.cmd_spells import CmdSpells


WALLET_A = "0xAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"


def _make_spell(name, school_key, mana_cost_dict, tier_for_caster=1):
    """Create a mock spell object."""
    spell = MagicMock()
    spell.name = name
    spell.school_key = school_key
    spell.mana_cost = mana_cost_dict
    spell.get_caster_tier.return_value = tier_for_caster
    return spell


class TestCmdSpells(EvenniaCommandTest):
    """Test the spells command."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)

    def test_no_spells(self):
        """Character with no known spells should see message."""
        self.char1.db.spellbook = []
        self.char1.db.memorised_spells = []
        result = self.call(CmdSpells(), "")
        self.assertIn("don't know any spells", result.lower())

    def test_known_spell_displayed(self):
        """Known spell should appear in output."""
        spell = _make_spell("Magic Missile", "evocation", {1: 5})
        self.char1.db.spellbook = ["magic_missile"]
        self.char1.db.memorised_spells = []

        with patch(
            "commands.all_char_cmds.cmd_spells.SPELL_REGISTRY",
            {"magic_missile": spell},
        ), patch(
            "typeclasses.mixins.spellbook.get_spell",
            side_effect=lambda k: {"magic_missile": spell}.get(k),
        ):
            result = self.call(CmdSpells(), "")
            self.assertIn("Magic Missile", result)
            self.assertIn("Spellbook", result)

    def test_memorised_spell_marked(self):
        """Memorised spells should show [M] marker."""
        spell = _make_spell("Magic Missile", "evocation", {1: 5})
        self.char1.db.spellbook = ["magic_missile"]
        self.char1.db.memorised_spells = ["magic_missile"]

        with patch(
            "commands.all_char_cmds.cmd_spells.SPELL_REGISTRY",
            {"magic_missile": spell},
        ), patch(
            "typeclasses.mixins.spellbook.get_spell",
            side_effect=lambda k: {"magic_missile": spell}.get(k),
        ):
            result = self.call(CmdSpells(), "")
            self.assertIn("[M]", result)

    def test_mana_cost_shown(self):
        """Mana cost should appear in output."""
        spell = _make_spell("Fireball", "evocation", {1: 15})
        self.char1.db.spellbook = ["fireball"]
        self.char1.db.memorised_spells = []

        with patch(
            "commands.all_char_cmds.cmd_spells.SPELL_REGISTRY",
            {"fireball": spell},
        ), patch(
            "typeclasses.mixins.spellbook.get_spell",
            side_effect=lambda k: {"fireball": spell}.get(k),
        ):
            result = self.call(CmdSpells(), "")
            self.assertIn("mana: 15", result)

    def test_memory_slots_shown(self):
        """Memory slot count should appear in output."""
        spell = _make_spell("Magic Missile", "evocation", {1: 5})
        self.char1.db.spellbook = ["magic_missile"]
        self.char1.db.memorised_spells = ["magic_missile"]

        with patch(
            "commands.all_char_cmds.cmd_spells.SPELL_REGISTRY",
            {"magic_missile": spell},
        ), patch(
            "typeclasses.mixins.spellbook.get_spell",
            side_effect=lambda k: {"magic_missile": spell}.get(k),
        ):
            result = self.call(CmdSpells(), "")
            self.assertIn("Memory slots:", result)
