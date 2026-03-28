"""
Tests for CombatMixin — combat handler accessors, health helpers,
initiate_attack, and CmdSet injection.

evennia test --settings settings tests.typeclass_tests.test_combat_mixin
"""

from unittest.mock import patch, MagicMock

from evennia.utils import create
from evennia.utils.test_resources import EvenniaTest


class TestCombatMixinOnMob(EvenniaTest):
    """Test CombatMixin methods via a CombatMob instance."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.mob = create.create_object(
            "typeclasses.actors.mob.CombatMob",
            key="test mob",
            location=self.room1,
        )
        self.mob.is_alive = True
        self.mob.hp = 10
        self.mob.hp_max = 10

    def tearDown(self):
        if self.mob.pk:
            self.mob.delete()
        super().tearDown()

    # ── get_combat_handler / is_in_combat ──

    def test_get_combat_handler_none(self):
        """Returns None when no combat handler exists."""
        self.assertIsNone(self.mob.get_combat_handler())

    def test_is_in_combat_false(self):
        """is_in_combat is False when no handler."""
        self.assertFalse(self.mob.is_in_combat)

    # ── hp_fraction ──

    def test_hp_fraction_full(self):
        """Full health returns 1.0."""
        max_hp = self.mob.effective_hp_max
        self.mob.hp = max_hp
        self.assertAlmostEqual(self.mob.hp_fraction, 1.0)

    def test_hp_fraction_half(self):
        """Half health returns 0.5."""
        max_hp = self.mob.effective_hp_max
        self.mob.hp = max_hp // 2
        self.assertAlmostEqual(self.mob.hp_fraction, (max_hp // 2) / max_hp)

    def test_hp_fraction_zero_max(self):
        """Zero max HP returns 0."""
        self.mob.hp = 0
        self.mob.hp_max = 0
        self.assertEqual(self.mob.hp_fraction, 0)

    # ── is_low_health ──

    def test_is_low_health_below_threshold(self):
        """Below aggro_hp_threshold returns True."""
        self.mob.hp = 3  # 30% < 50% default threshold
        self.assertTrue(self.mob.is_low_health)

    def test_is_low_health_above_threshold(self):
        """Above aggro_hp_threshold returns False."""
        self.mob.hp = 8  # 80% > 50%
        self.assertFalse(self.mob.is_low_health)

    # ── initiate_attack ──

    def test_initiate_attack_dead_noop(self):
        """Dead mob does nothing."""
        self.mob.is_alive = False
        with patch.object(self.mob, "execute_cmd") as mock:
            self.mob.initiate_attack(self.char1)
            mock.assert_not_called()

    def test_initiate_attack_calls_execute_cmd(self):
        """Living mob executes attack command."""
        self.char1.hp = 10
        with patch.object(self.mob, "execute_cmd") as mock:
            self.mob.initiate_attack(self.char1)
            mock.assert_called_once_with(f"attack {self.char1.key}")

    def test_initiate_attack_dead_target_noop(self):
        """Target with 0 HP is skipped."""
        self.char1.hp = 0
        with patch.object(self.mob, "execute_cmd") as mock:
            self.mob.initiate_attack(self.char1)
            mock.assert_not_called()

    # ── mob_attack backward compat ──

    def test_mob_attack_alias(self):
        """mob_attack still works as backward-compat alias."""
        self.assertTrue(hasattr(self.mob, "mob_attack"))

    # ── exit_combat ──

    def test_exit_combat_no_handler(self):
        """exit_combat is safe when no handler exists."""
        self.mob.exit_combat()  # should not raise


class TestCombatMixinOnCharacter(EvenniaTest):
    """Test CombatMixin methods via FCMCharacter."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def test_character_has_combat_accessors(self):
        """FCMCharacter has CombatMixin methods."""
        self.assertTrue(hasattr(self.char1, "get_combat_handler"))
        self.assertTrue(hasattr(self.char1, "is_in_combat"))
        self.assertTrue(hasattr(self.char1, "hp_fraction"))
        self.assertTrue(hasattr(self.char1, "enter_combat"))
        self.assertTrue(hasattr(self.char1, "exit_combat"))
        self.assertTrue(hasattr(self.char1, "initiate_attack"))

    def test_character_not_in_combat(self):
        """Character starts not in combat."""
        self.assertFalse(self.char1.is_in_combat)
        self.assertIsNone(self.char1.get_combat_handler())
