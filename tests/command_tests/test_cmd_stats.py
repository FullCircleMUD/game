"""
Tests for the stats command (base vs effective breakdown).

evennia test --settings settings tests.command_tests.test_cmd_stats
"""

from evennia.utils.test_resources import EvenniaCommandTest

from commands.all_char_cmds.cmd_stats import CmdStats


WALLET_A = "0xAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"


class TestCmdStatsAbilities(EvenniaCommandTest):
    """Test ability scores section."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)

    def test_shows_all_abilities(self):
        """Stats should display all six ability scores."""
        result = self.call(CmdStats(), "")
        for ab in ("Strength", "Dexterity", "Constitution",
                    "Intelligence", "Wisdom", "Charisma"):
            self.assertIn(ab, result)

    def test_shows_ability_modifier(self):
        """Stats should show ability modifier notes."""
        result = self.call(CmdStats(), "")
        self.assertIn("mod", result)

    def test_shows_base_and_eff_headers(self):
        """Stats should show Base and Eff. column headers."""
        result = self.call(CmdStats(), "")
        self.assertIn("Base", result)
        self.assertIn("Eff.", result)


class TestCmdStatsVitals(EvenniaCommandTest):
    """Test vitals section."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)

    def test_shows_hp_max(self):
        """Stats should display HP Max."""
        result = self.call(CmdStats(), "")
        self.assertIn("HP Max", result)

    def test_shows_mana_max(self):
        """Stats should display Mana Max."""
        result = self.call(CmdStats(), "")
        self.assertIn("Mana Max", result)

    def test_shows_move_max(self):
        """Stats should display Move Max."""
        result = self.call(CmdStats(), "")
        self.assertIn("Move Max", result)

    def test_hp_shows_con_note(self):
        """HP Max should show CON modifier breakdown."""
        result = self.call(CmdStats(), "")
        self.assertIn("CON mod", result)


class TestCmdStatsCombat(EvenniaCommandTest):
    """Test combat section."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)

    def test_shows_armor_class(self):
        """Stats should display Armor Class."""
        result = self.call(CmdStats(), "")
        self.assertIn("Armor Class", result)

    def test_shows_crit_threshold(self):
        """Stats should display Crit Threshold."""
        result = self.call(CmdStats(), "")
        self.assertIn("Crit Threshold", result)

    def test_shows_initiative(self):
        """Stats should display Initiative with DEX note."""
        result = self.call(CmdStats(), "")
        self.assertIn("Initiative", result)
        self.assertIn("DEX mod", result)

    def test_shows_attacks(self):
        """Stats should display Attacks/Round."""
        result = self.call(CmdStats(), "")
        self.assertIn("Attacks/Round", result)

    def test_shows_perception(self):
        """Stats should display Perception with a WIS note."""
        result = self.call(CmdStats(), "")
        self.assertIn("Perception", result)
        self.assertIn("WIS mod", result)

    def test_shows_hit_bonus(self):
        """Stats should display the hit bonus."""
        result = self.call(CmdStats(), "")
        self.assertIn("Hit Bonus", result)

    def test_shows_damage_bonus(self):
        """Stats should display the damage bonus."""
        result = self.call(CmdStats(), "")
        self.assertIn("Damage Bonus", result)


class TestCmdStatsStructure(EvenniaCommandTest):
    """Test overall structure."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)

    def test_has_border(self):
        """Output should have box borders."""
        result = self.call(CmdStats(), "")
        self.assertIn("+====", result)

    def test_has_section_headers(self):
        """Output should have section headers."""
        result = self.call(CmdStats(), "")
        self.assertIn("Ability Scores", result)
        self.assertIn("Vitals", result)
        self.assertIn("Combat", result)

    def test_delta_shown_when_base_differs(self):
        """A row whose effective value differs from base shows the delta."""
        self.char1.total_hit_bonus = 3
        result = self.call(CmdStats(), "")
        self.assertIn("(-3)", result)

    def test_no_delta_when_values_match(self):
        """Mana Max has no effective modifier, so no delta is shown."""
        result = self.call(CmdStats(), "")
        mana_row = next(ln for ln in result.split("\n") if "Mana Max" in ln)
        self.assertNotIn("(", mana_row)

    def test_no_resistances_or_conditions(self):
        """Stats should NOT show resistances or conditions (moved to score)."""
        result = self.call(CmdStats(), "")
        self.assertNotIn("Resist", result)
        self.assertNotIn("Conditions", result)
        self.assertNotIn("Hunger", result)
