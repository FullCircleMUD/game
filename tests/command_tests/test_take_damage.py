"""
Tests for the take_damage() pipeline — resistances, vulnerability,
minimum damage, death triggers, ignore_resistance.

evennia test --settings settings tests.command_tests.test_take_damage
"""

from unittest.mock import patch
from evennia.utils.test_resources import EvenniaCommandTest
from evennia.utils import create


class TestTakeDamage(EvenniaCommandTest):
    """Test the central take_damage() method on BaseActor."""

    character_typeclass = "typeclasses.actors.character.FCMCharacter"
    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.char1.hp = 100
        self.char1.hp_max = 100

    # ------------------------------------------------------------------ #
    #  Basic damage
    # ------------------------------------------------------------------ #

    def test_take_damage_basic(self):
        """Raw damage subtracted from HP."""
        dealt = self.char1.take_damage(10)
        self.assertEqual(dealt, 10)
        self.assertEqual(self.char1.hp, 90)

    def test_take_damage_no_resistance_type(self):
        """No damage_type means no resistance check."""
        self.char1.damage_resistances = {"fire": 50}
        dealt = self.char1.take_damage(10)
        self.assertEqual(dealt, 10)
        self.assertEqual(self.char1.hp, 90)

    # ------------------------------------------------------------------ #
    #  Resistance
    # ------------------------------------------------------------------ #

    def test_take_damage_resistance_reduces(self):
        """50% fire resistance halves fire damage."""
        self.char1.damage_resistances = {"fire": 50}
        dealt = self.char1.take_damage(20, damage_type="fire")
        self.assertEqual(dealt, 10)
        self.assertEqual(self.char1.hp, 90)

    def test_take_damage_resistance_min_1_saved(self):
        """Even 1% resistance saves at least 1 HP."""
        self.char1.damage_resistances = {"fire": 1}
        dealt = self.char1.take_damage(10, damage_type="fire")
        # 1% of 10 = 0.1 → int(0.1) = 0 → max(1, 0) = 1 reduction
        self.assertEqual(dealt, 9)
        self.assertEqual(self.char1.hp, 91)

    def test_take_damage_high_resistance_min_1_damage(self):
        """Even with 75% resistance, at least 1 HP damage dealt."""
        self.char1.damage_resistances = {"fire": 75}
        dealt = self.char1.take_damage(2, damage_type="fire")
        # 75% of 2 = 1.5 → int(1.5) = 1 → max(1, 1) = 1 reduction
        # damage = 2 - 1 = 1 → max(1, 1) = 1
        self.assertEqual(dealt, 1)
        self.assertEqual(self.char1.hp, 99)

    def test_take_damage_75_pct_resistance_large(self):
        """75% resistance on large damage."""
        self.char1.damage_resistances = {"fire": 75}
        dealt = self.char1.take_damage(100, damage_type="fire")
        # 75% of 100 = 75 reduction → damage = 100 - 75 = 25
        self.assertEqual(dealt, 25)
        self.assertEqual(self.char1.hp, 75)

    # ------------------------------------------------------------------ #
    #  Vulnerability (negative resistance)
    # ------------------------------------------------------------------ #

    def test_take_damage_vulnerability_amplifies(self):
        """Negative resistance (vulnerability) amplifies damage."""
        self.char1.damage_resistances = {"fire": -25}
        dealt = self.char1.take_damage(20, damage_type="fire")
        # 25% of 20 = 5 extra → damage = 20 + 5 = 25
        self.assertEqual(dealt, 25)
        self.assertEqual(self.char1.hp, 75)

    def test_take_damage_vulnerability_min_1_added(self):
        """Even -1% vulnerability adds at least 1 HP extra."""
        self.char1.damage_resistances = {"fire": -1}
        dealt = self.char1.take_damage(10, damage_type="fire")
        # 1% of 10 = 0.1 → int(0.1) = 0 → max(1, 0) = 1 extra
        self.assertEqual(dealt, 11)
        self.assertEqual(self.char1.hp, 89)

    # ------------------------------------------------------------------ #
    #  Minimum damage
    # ------------------------------------------------------------------ #

    def test_take_damage_min_1_damage(self):
        """Minimum 1 HP damage always dealt."""
        self.char1.damage_resistances = {"fire": 75}
        dealt = self.char1.take_damage(1, damage_type="fire")
        # 75% of 1 = 0.75 → int(0.75) = 0 → max(1, 0) = 1 reduction
        # damage = 1 - 1 = 0 → max(1, 0) = 1
        self.assertEqual(dealt, 1)
        self.assertEqual(self.char1.hp, 99)

    # ------------------------------------------------------------------ #
    #  Death
    # ------------------------------------------------------------------ #

    def test_take_damage_kills_at_zero(self):
        """die() called when HP reaches 0."""
        self.char1.hp = 5
        with patch.object(self.char1, "die") as mock_die:
            dealt = self.char1.take_damage(10)
            mock_die.assert_called_once_with("combat", killer=None)
        self.assertEqual(self.char1.hp, 0)
        self.assertEqual(dealt, 10)

    def test_take_damage_custom_cause(self):
        """Custom cause passed to die()."""
        self.char1.hp = 3
        with patch.object(self.char1, "die") as mock_die:
            self.char1.take_damage(10, cause="spell")
            mock_die.assert_called_once_with("spell", killer=None)

    def test_take_damage_no_death_if_alive(self):
        """die() NOT called if HP stays above 0."""
        with patch.object(self.char1, "die") as mock_die:
            self.char1.take_damage(5)
            mock_die.assert_not_called()
        self.assertEqual(self.char1.hp, 95)

    # ------------------------------------------------------------------ #
    #  ignore_resistance
    # ------------------------------------------------------------------ #

    def test_take_damage_ignore_resistance(self):
        """Environmental damage bypasses resistance entirely."""
        self.char1.damage_resistances = {"fire": 75}
        dealt = self.char1.take_damage(
            20, damage_type="fire", ignore_resistance=True
        )
        self.assertEqual(dealt, 20)
        self.assertEqual(self.char1.hp, 80)

    def test_take_damage_ignore_resistance_no_type(self):
        """ignore_resistance with no damage type still works."""
        dealt = self.char1.take_damage(
            15, cause="fall", ignore_resistance=True
        )
        self.assertEqual(dealt, 15)
        self.assertEqual(self.char1.hp, 85)

    # ------------------------------------------------------------------ #
    #  Integration: mob take_damage uses base class
    # ------------------------------------------------------------------ #

    def test_mob_take_damage_uses_base(self):
        """CombatMob inherits take_damage from BaseActor."""
        mob = create.create_object(
            "typeclasses.actors.mob.CombatMob",
            key="test mob",
            location=self.room1,
        )
        mob.hp = 50
        mob.hp_max = 50
        mob.damage_resistances = {"piercing": 50}
        try:
            dealt = mob.take_damage(20, damage_type="piercing")
            self.assertEqual(dealt, 10)
            self.assertEqual(mob.hp, 40)
        finally:
            mob.delete()
