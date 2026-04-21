"""
Tests for the score command (consolidated character sheet).

evennia test --settings settings tests.command_tests.test_cmd_score
"""

from evennia.utils.test_resources import EvenniaCommandTest

from commands.all_char_cmds.cmd_score import CmdScore
from enums.condition import Condition


WALLET_A = "0xAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"


class TestCmdScoreIdentity(EvenniaCommandTest):
    """Test the header section: name, race, alignment, class, level, XP."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)

    def test_score_shows_name(self):
        """Score header should contain the character's name."""
        result = self.call(CmdScore(), "")
        self.assertIn(self.char1.key, result)

    def test_score_shows_race(self):
        """Score header should show the race."""
        result = self.call(CmdScore(), "")
        self.assertIn("Human", result)

    def test_score_shows_alignment(self):
        """Score header should show alignment label."""
        result = self.call(CmdScore(), "")
        self.assertIn("Neutral", result)

    def test_score_shows_xp(self):
        """Score header should show XP fraction."""
        result = self.call(CmdScore(), "")
        self.assertIn("XP", result)

    def test_score_shows_level(self):
        """Score header should show total level."""
        result = self.call(CmdScore(), "")
        self.assertIn("Lvl 1", result)

    def test_score_shows_class_when_set(self):
        """Score should display class name and level in header."""
        self.char1.db.classes = {"warrior": {"level": 5}}
        result = self.call(CmdScore(), "")
        self.assertIn("Warrior 5", result)

    def test_score_shows_multiclass(self):
        """Score should show multiple classes joined with /."""
        self.char1.db.classes = {
            "warrior": {"level": 3},
            "mage": {"level": 2},
        }
        result = self.call(CmdScore(), "")
        self.assertIn("Warrior 3", result)
        self.assertIn("Mage 2", result)

    def test_score_no_class_message(self):
        """Score should show guidance when no class chosen."""
        result = self.call(CmdScore(), "")
        self.assertIn("No class", result)
        self.assertIn("guildmaster", result)


class TestCmdScoreVitals(EvenniaCommandTest):
    """Test the vitals section: HP, MP, MV."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)

    def test_score_shows_hp(self):
        """Score body should contain HP values."""
        result = self.call(CmdScore(), "")
        self.assertIn("HP:", result)

    def test_score_shows_mp(self):
        """Score body should contain MP values."""
        result = self.call(CmdScore(), "")
        self.assertIn("MP:", result)

    def test_score_shows_mv(self):
        """Score body should contain MV values."""
        result = self.call(CmdScore(), "")
        self.assertIn("MV:", result)


class TestCmdScoreAbilities(EvenniaCommandTest):
    """Test the ability scores section."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)

    def test_score_shows_all_abilities(self):
        """Score body should show all 6 ability scores."""
        result = self.call(CmdScore(), "")
        for ab in ("STR", "DEX", "CON", "INT", "WIS", "CHA"):
            self.assertIn(f"{ab}:", result)


class TestCmdScoreCombat(EvenniaCommandTest):
    """Test combat modifier display."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)

    def test_score_shows_ac(self):
        """Score body should show Armor Class."""
        result = self.call(CmdScore(), "")
        self.assertIn("AC:", result)

    def test_score_shows_crit(self):
        """Score body should show crit threshold."""
        result = self.call(CmdScore(), "")
        self.assertIn("Crit:", result)

    def test_score_shows_initiative(self):
        """Score body should show initiative bonus."""
        result = self.call(CmdScore(), "")
        self.assertIn("Init:", result)

    def test_score_shows_attacks(self):
        """Score body should show attacks per round."""
        result = self.call(CmdScore(), "")
        self.assertIn("Att:", result)


class TestCmdScoreFooter(EvenniaCommandTest):
    """Test footer: conditions and levels to spend."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)

    def test_levels_to_spend_shown(self):
        """Footer should show levels-to-spend message when > 0."""
        self.char1.levels_to_spend = 3
        result = self.call(CmdScore(), "")
        self.assertIn("3 levels to spend", result)
        self.assertIn("guildmaster", result)

    def test_levels_to_spend_hidden_when_zero(self):
        """Footer should not show levels message when 0."""
        self.char1.levels_to_spend = 0
        result = self.call(CmdScore(), "")
        self.assertNotIn("levels to spend", result)

    def test_conditions_shown(self):
        """Footer should list active conditions."""
        conds = dict(self.char1.conditions)
        conds[Condition.FLY.value] = 1
        self.char1.conditions = conds
        result = self.call(CmdScore(), "")
        self.assertIn("Conditions:", result)
        self.assertIn("Fly", result)

    def test_no_conditions_shows_none(self):
        """Footer should show 'Conditions: None' when none active."""
        result = self.call(CmdScore(), "")
        self.assertIn("Conditions:", result)
        self.assertIn("None", result)

    def test_active_effects_none_shows_none(self):
        """Footer should show 'Active Effects: None' when no effects active."""
        result = self.call(CmdScore(), "")
        self.assertIn("Active Effects:", result)
        idx = result.find("Active Effects:")
        self.assertIn("None", result[idx:idx + 40])

    def test_active_effects_combat_rounds(self):
        """Footer should render round-based effects as 'Name (Nr)'."""
        self.char1.active_effects = {
            "stunned": {
                "duration": 3,
                "duration_type": "combat_rounds",
                "effects": [],
                "messages": {},
            }
        }
        result = self.call(CmdScore(), "")
        self.assertIn("Stunned (3r)", result)

    def test_active_effects_permanent(self):
        """Footer should render permanent (duration_type=None) effects without suffix."""
        self.char1.active_effects = {
            "darkvision": {
                "duration": None,
                "duration_type": None,
                "effects": [],
                "messages": {},
            }
        }
        result = self.call(CmdScore(), "")
        idx = result.find("Active Effects:")
        self.assertGreaterEqual(idx, 0)
        self.assertIn("Darkvision", result[idx:idx + 60])
        self.assertNotIn("Darkvision (", result)

    def test_active_effects_seconds(self):
        """Seconds-based effects should render remaining duration in minutes."""
        self.char1.active_effects = {
            "mage_armor": {
                "duration": 3600,
                "duration_type": "seconds",
                "effects": [],
                "messages": {},
            }
        }
        # Stub the remaining-seconds helper so we don't depend on real timer scripts.
        self.char1.get_effect_remaining_seconds = lambda key: 3540
        result = self.call(CmdScore(), "")
        self.assertIn("Mage Armor (59m)", result)

    def test_active_effects_multiple_sorted(self):
        """Multiple effects should be sorted alphabetically."""
        self.char1.active_effects = {
            "shield": {
                "duration": 2,
                "duration_type": "combat_rounds",
                "effects": [],
                "messages": {},
            },
            "barkskin": {
                "duration": 5,
                "duration_type": "combat_rounds",
                "effects": [],
                "messages": {},
            },
        }
        result = self.call(CmdScore(), "")
        bark_idx = result.find("Barkskin")
        shield_idx = result.find("Shield")
        self.assertGreaterEqual(bark_idx, 0)
        self.assertGreaterEqual(shield_idx, 0)
        self.assertLess(bark_idx, shield_idx)


class TestCmdScoreStructure(EvenniaCommandTest):
    """Test overall visual structure."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)

    def test_has_border(self):
        """Output should have box borders."""
        result = self.call(CmdScore(), "")
        self.assertIn("+====", result)

    def test_has_hunger(self):
        """Output should show hunger status."""
        result = self.call(CmdScore(), "")
        self.assertIn("Full", result)

    def test_resist_vulner_headers_always_shown(self):
        """Right column should always show Resist and Vulner headers."""
        result = self.call(CmdScore(), "")
        self.assertIn("Resist:", result)
        self.assertIn("Vulner:", result)

    def test_has_carry_weight(self):
        """Output should show carry weight."""
        result = self.call(CmdScore(), "")
        self.assertIn("kg", result)
