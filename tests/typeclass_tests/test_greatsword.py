"""
Tests for GreatswordNFTItem — cleave AoE + executioner weapon.

Validates:
    - No parries, no extra attacks (pure offense)
    - Cleave cascading on hit via at_post_attack
    - Cleave chain break on failed d100 check
    - Cleave full damage per target
    - Cleave excludes primary target and dead enemies
    - Executioner GM-only on kill via at_kill
    - Executioner once per round (executioner_used flag)
    - Executioner on cleave kill

evennia test --settings settings tests.typeclass_tests.test_greatsword
"""

from unittest.mock import patch, MagicMock, PropertyMock

from evennia.utils.test_resources import EvenniaTest
from evennia.utils import create

from enums.mastery_level import MasteryLevel


def _make_greatsword(location=None):
    """Create a GreatswordNFTItem for testing."""
    obj = create.create_object(
        "typeclasses.items.weapons.greatsword_nft_item.GreatswordNFTItem",
        key="Test Greatsword",
        nohome=True,
    )
    if location:
        obj.move_to(location, quiet=True)
    return obj


def _set_mastery(char, level_int):
    """Set char's greatsword mastery to the given integer level."""
    char.db.weapon_skill_mastery_levels = {"greatsword": level_int}


def _mock_enemy(hp=100, name="Enemy"):
    """Create a mock enemy for cleave targets."""
    enemy = MagicMock()
    enemy.hp = hp
    enemy.key = name
    enemy.take_damage.return_value = 5
    enemy.location = MagicMock()
    return enemy


def _mock_dying_enemy(name="DyingEnemy"):
    """Create a mock enemy that dies when take_damage is called."""
    enemy = MagicMock()
    enemy.hp = 100
    enemy.key = name
    enemy.location = MagicMock()

    def take_damage_and_die(*args, **kwargs):
        enemy.hp = 0
        return 10

    enemy.take_damage.side_effect = take_damage_and_die
    return enemy


# ================================================================== #
#  Mastery Override Tests
# ================================================================== #

class TestGreatswordMasteryOverrides(EvenniaTest):
    """Test that greatsword returns 0 parries and 0 extra attacks."""

    def create_script(self):
        pass

    def test_no_parries(self):
        """Greatsword should grant 0 parries per round at all levels."""
        gs = _make_greatsword()
        for level in range(6):
            _set_mastery(self.char1, level)
            self.assertEqual(gs.get_parries_per_round(self.char1), 0)

    def test_no_extra_attacks(self):
        """Greatsword should grant 0 extra attacks at all levels."""
        gs = _make_greatsword()
        for level in range(6):
            _set_mastery(self.char1, level)
            self.assertEqual(gs.get_extra_attacks(self.char1), 0)

    def test_weapon_type_key(self):
        gs = _make_greatsword()
        self.assertEqual(gs.weapon_type_key, "greatsword")

    def test_has_greatsword_tag(self):
        gs = _make_greatsword()
        self.assertTrue(gs.tags.has("greatsword", category="weapon_type"))


# ================================================================== #
#  Cleave Tests
# ================================================================== #

class TestGreatswordCleave(EvenniaTest):
    """Test cleave cascading AoE mechanic."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.gs = _make_greatsword()
        # effective_damage_bonus is a read-only @property — mock it
        patcher = patch.object(
            type(self.char1), 'effective_damage_bonus',
            new_callable=PropertyMock, return_value=4
        )
        self.mock_dmg_bonus = patcher.start()
        self.addCleanup(patcher.stop)

    @patch("typeclasses.items.weapons.greatsword_nft_item.get_sides")
    @patch("typeclasses.items.weapons.greatsword_nft_item.dice")
    def test_no_cleave_on_miss(self, mock_dice, mock_sides):
        """Cleave should not trigger when primary attack misses."""
        _set_mastery(self.char1, 3)  # EXPERT
        enemy = _mock_enemy()
        mock_sides.return_value = ([], [enemy])

        self.gs.at_post_attack(self.char1, self.char2, False, 0)

        enemy.take_damage.assert_not_called()

    @patch("typeclasses.items.weapons.greatsword_nft_item.get_sides")
    @patch("typeclasses.items.weapons.greatsword_nft_item.dice")
    def test_no_cleave_unskilled(self, mock_dice, mock_sides):
        """UNSKILLED should have no cleave chances."""
        _set_mastery(self.char1, 0)

        self.gs.at_post_attack(self.char1, self.char2, True, 5)

        # get_sides should never be called — early return
        mock_sides.assert_not_called()

    @patch("typeclasses.items.weapons.greatsword_nft_item.get_sides")
    @patch("typeclasses.items.weapons.greatsword_nft_item.dice")
    def test_no_cleave_basic(self, mock_dice, mock_sides):
        """BASIC should have no cleave chances."""
        _set_mastery(self.char1, 1)

        self.gs.at_post_attack(self.char1, self.char2, True, 5)

        mock_sides.assert_not_called()

    @patch("typeclasses.items.weapons.greatsword_nft_item.get_sides")
    @patch("typeclasses.items.weapons.greatsword_nft_item.dice")
    def test_cleave_skilled_hit(self, mock_dice, mock_sides):
        """SKILLED: 25% chance passes → 2nd enemy takes damage."""
        _set_mastery(self.char1, 2)
        enemy = _mock_enemy()
        mock_sides.return_value = ([], [enemy])
        # d100=20 passes 25%, damage roll=8
        mock_dice.roll.side_effect = [20, 8]

        self.gs.at_post_attack(self.char1, self.char2, True, 5)

        # damage = 8 + 4 (effective_damage_bonus) = 12
        enemy.take_damage.assert_called_once()
        self.assertEqual(enemy.take_damage.call_args[0][0], 12)

    @patch("typeclasses.items.weapons.greatsword_nft_item.get_sides")
    @patch("typeclasses.items.weapons.greatsword_nft_item.dice")
    def test_cleave_skilled_miss(self, mock_dice, mock_sides):
        """SKILLED: d100 > 25 → no cleave."""
        _set_mastery(self.char1, 2)
        enemy = _mock_enemy()
        mock_sides.return_value = ([], [enemy])
        mock_dice.roll.side_effect = [30]  # fails 25%

        self.gs.at_post_attack(self.char1, self.char2, True, 5)

        enemy.take_damage.assert_not_called()

    @patch("typeclasses.items.weapons.greatsword_nft_item.get_sides")
    @patch("typeclasses.items.weapons.greatsword_nft_item.dice")
    def test_cleave_expert_cascade_both(self, mock_dice, mock_sides):
        """EXPERT: 50%/25%, both pass → 2 extra enemies hit."""
        _set_mastery(self.char1, 3)
        enemy1 = _mock_enemy(name="Enemy1")
        enemy2 = _mock_enemy(name="Enemy2")
        mock_sides.return_value = ([], [enemy1, enemy2])
        # d100=40 passes 50%, dmg=6, d100=20 passes 25%, dmg=8
        mock_dice.roll.side_effect = [40, 6, 20, 8]

        self.gs.at_post_attack(self.char1, self.char2, True, 5)

        enemy1.take_damage.assert_called_once()
        enemy2.take_damage.assert_called_once()

    @patch("typeclasses.items.weapons.greatsword_nft_item.get_sides")
    @patch("typeclasses.items.weapons.greatsword_nft_item.dice")
    def test_cleave_expert_chain_break(self, mock_dice, mock_sides):
        """EXPERT: 1st passes 50%, 2nd fails 25% → only 1 extra hit."""
        _set_mastery(self.char1, 3)
        enemy1 = _mock_enemy(name="Enemy1")
        enemy2 = _mock_enemy(name="Enemy2")
        mock_sides.return_value = ([], [enemy1, enemy2])
        # d100=40 passes 50%, dmg=6, d100=30 fails 25%
        mock_dice.roll.side_effect = [40, 6, 30]

        self.gs.at_post_attack(self.char1, self.char2, True, 5)

        enemy1.take_damage.assert_called_once()
        enemy2.take_damage.assert_not_called()

    @patch("typeclasses.items.weapons.greatsword_nft_item.get_sides")
    @patch("typeclasses.items.weapons.greatsword_nft_item.dice")
    def test_cleave_master_three_targets(self, mock_dice, mock_sides):
        """MASTER: 75%/50%/25%, all pass → 3 extra enemies hit."""
        _set_mastery(self.char1, 4)
        enemy1 = _mock_enemy(name="E1")
        enemy2 = _mock_enemy(name="E2")
        enemy3 = _mock_enemy(name="E3")
        mock_sides.return_value = ([], [enemy1, enemy2, enemy3])
        # d100=70/45/20, dmg=6/8/10
        mock_dice.roll.side_effect = [70, 6, 45, 8, 20, 10]

        self.gs.at_post_attack(self.char1, self.char2, True, 5)

        enemy1.take_damage.assert_called_once()
        enemy2.take_damage.assert_called_once()
        enemy3.take_damage.assert_called_once()

    @patch("typeclasses.items.weapons.greatsword_nft_item.get_sides")
    @patch("typeclasses.items.weapons.greatsword_nft_item.dice")
    def test_cleave_full_damage(self, mock_dice, mock_sides):
        """Cleave damage should be dice roll + effective_damage_bonus."""
        _set_mastery(self.char1, 2)
        self.mock_dmg_bonus.return_value = 3
        enemy = _mock_enemy()
        mock_sides.return_value = ([], [enemy])
        mock_dice.roll.side_effect = [20, 7]  # d100 passes, dmg=7

        self.gs.at_post_attack(self.char1, self.char2, True, 5)

        # damage = 7 + 3 = 10
        self.assertEqual(enemy.take_damage.call_args[0][0], 10)

    @patch("typeclasses.items.weapons.greatsword_nft_item.get_sides")
    @patch("typeclasses.items.weapons.greatsword_nft_item.dice")
    def test_cleave_minimum_damage_one(self, mock_dice, mock_sides):
        """Cleave damage should be at least 1 even with negative bonus."""
        _set_mastery(self.char1, 2)
        self.mock_dmg_bonus.return_value = -5
        enemy = _mock_enemy()
        mock_sides.return_value = ([], [enemy])
        mock_dice.roll.side_effect = [20, 1]

        self.gs.at_post_attack(self.char1, self.char2, True, 5)

        self.assertEqual(enemy.take_damage.call_args[0][0], 1)

    @patch("typeclasses.items.weapons.greatsword_nft_item.get_sides")
    @patch("typeclasses.items.weapons.greatsword_nft_item.dice")
    def test_cleave_excludes_primary_target(self, mock_dice, mock_sides):
        """Primary target should not be hit by cleave."""
        _set_mastery(self.char1, 2)
        primary = _mock_enemy(name="Primary")
        other = _mock_enemy(name="Other")
        mock_sides.return_value = ([], [primary, other])
        mock_dice.roll.side_effect = [20, 6]

        self.gs.at_post_attack(self.char1, primary, True, 5)

        primary.take_damage.assert_not_called()
        other.take_damage.assert_called_once()

    @patch("typeclasses.items.weapons.greatsword_nft_item.get_sides")
    @patch("typeclasses.items.weapons.greatsword_nft_item.dice")
    def test_cleave_skips_dead_enemies(self, mock_dice, mock_sides):
        """Dead enemies should not be cleave targets."""
        _set_mastery(self.char1, 3)  # EXPERT: 50%/25%
        dead_enemy = _mock_enemy(hp=0, name="Dead")
        alive_enemy = _mock_enemy(hp=50, name="Alive")
        mock_sides.return_value = ([], [dead_enemy, alive_enemy])
        # Dead filtered out, only alive in list. d100=40 passes 50%, dmg=6
        mock_dice.roll.side_effect = [40, 6]

        self.gs.at_post_attack(self.char1, self.char2, True, 5)

        dead_enemy.take_damage.assert_not_called()
        alive_enemy.take_damage.assert_called_once()

    @patch("typeclasses.items.weapons.greatsword_nft_item.get_sides")
    @patch("typeclasses.items.weapons.greatsword_nft_item.dice")
    def test_cleave_no_enemies_left(self, mock_dice, mock_sides):
        """No cleave if no other enemies besides primary target."""
        _set_mastery(self.char1, 4)
        mock_sides.return_value = ([], [])

        self.gs.at_post_attack(self.char1, self.char2, True, 5)

        mock_dice.roll.assert_not_called()

    @patch("typeclasses.items.weapons.greatsword_nft_item.get_sides")
    @patch("typeclasses.items.weapons.greatsword_nft_item.dice")
    def test_cleave_fewer_enemies_than_chances(self, mock_dice, mock_sides):
        """If fewer enemies than cascade levels, stop after last enemy."""
        _set_mastery(self.char1, 4)  # MASTER: 3 cascade levels
        enemy = _mock_enemy()
        mock_sides.return_value = ([], [enemy])  # only 1 extra enemy
        mock_dice.roll.side_effect = [70, 6]  # passes 75%, dmg=6

        self.gs.at_post_attack(self.char1, self.char2, True, 5)

        enemy.take_damage.assert_called_once()

    @patch("typeclasses.items.weapons.greatsword_nft_item.get_sides")
    @patch("typeclasses.items.weapons.greatsword_nft_item.dice")
    def test_cleave_boundary_roll_passes(self, mock_dice, mock_sides):
        """d100 roll exactly equal to chance should pass (roll <= chance)."""
        _set_mastery(self.char1, 2)  # SKILLED: 25%
        enemy = _mock_enemy()
        mock_sides.return_value = ([], [enemy])
        mock_dice.roll.side_effect = [25, 6]  # exactly 25

        self.gs.at_post_attack(self.char1, self.char2, True, 5)

        enemy.take_damage.assert_called_once()

    @patch("typeclasses.items.weapons.greatsword_nft_item.get_sides")
    @patch("typeclasses.items.weapons.greatsword_nft_item.dice")
    def test_cleave_boundary_roll_fails(self, mock_dice, mock_sides):
        """d100 roll one above chance should fail."""
        _set_mastery(self.char1, 2)  # SKILLED: 25%
        enemy = _mock_enemy()
        mock_sides.return_value = ([], [enemy])
        mock_dice.roll.side_effect = [26]

        self.gs.at_post_attack(self.char1, self.char2, True, 5)

        enemy.take_damage.assert_not_called()


# ================================================================== #
#  Executioner Tests
# ================================================================== #

class TestGreatswordExecutioner(EvenniaTest):
    """Test executioner mechanic (GM-only bonus attack on kill)."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.gs = _make_greatsword()
        patcher = patch.object(
            type(self.char1), 'effective_damage_bonus',
            new_callable=PropertyMock, return_value=4
        )
        self.mock_dmg_bonus = patcher.start()
        self.addCleanup(patcher.stop)

    def _setup_handler(self, executioner_used=False):
        """Create a real CombatHandler on char1."""
        from combat.combat_handler import CombatHandler
        from evennia.utils.create import create_script

        # Remove any existing handler
        existing = self.char1.scripts.get("combat_handler")
        if existing:
            existing[0].delete()

        handler = create_script(
            CombatHandler,
            obj=self.char1,
            key="combat_handler",
            autostart=False,
        )
        handler.start()
        handler.executioner_used = executioner_used
        return handler

    @patch("typeclasses.items.weapons.greatsword_nft_item.execute_attack")
    @patch("typeclasses.items.weapons.greatsword_nft_item.get_sides")
    def test_executioner_gm_only(self, mock_sides, mock_exec):
        """Non-GM mastery should not trigger executioner."""
        _set_mastery(self.char1, 4)  # MASTER, not GM
        self._setup_handler()
        mock_sides.return_value = ([], [_mock_enemy()])

        self.gs.at_kill(self.char1, self.char2)

        mock_exec.assert_not_called()

    @patch("typeclasses.items.weapons.greatsword_nft_item.execute_attack")
    @patch("typeclasses.items.weapons.greatsword_nft_item.get_sides")
    def test_executioner_on_primary_kill(self, mock_sides, mock_exec):
        """GM: at_kill should trigger execute_attack on another enemy."""
        _set_mastery(self.char1, 5)  # GM
        handler = self._setup_handler()
        enemy = _mock_enemy(name="NextTarget")
        mock_sides.return_value = ([], [enemy])

        self.gs.at_kill(self.char1, self.char2)

        mock_exec.assert_called_once_with(self.char1, enemy)
        self.assertTrue(handler.executioner_used)

    @patch("typeclasses.items.weapons.greatsword_nft_item.execute_attack")
    @patch("typeclasses.items.weapons.greatsword_nft_item.get_sides")
    def test_executioner_once_per_round(self, mock_sides, mock_exec):
        """Second kill should not trigger executioner again."""
        _set_mastery(self.char1, 5)
        self._setup_handler(executioner_used=True)  # already used
        mock_sides.return_value = ([], [_mock_enemy()])

        self.gs.at_kill(self.char1, self.char2)

        mock_exec.assert_not_called()

    @patch("typeclasses.items.weapons.greatsword_nft_item.execute_attack")
    @patch("typeclasses.items.weapons.greatsword_nft_item.get_sides")
    def test_executioner_no_living_enemies(self, mock_sides, mock_exec):
        """Executioner should not fire if no living enemies remain."""
        _set_mastery(self.char1, 5)
        handler = self._setup_handler()
        mock_sides.return_value = ([], [])

        self.gs.at_kill(self.char1, self.char2)

        mock_exec.assert_not_called()
        self.assertFalse(handler.executioner_used)

    @patch("typeclasses.items.weapons.greatsword_nft_item.execute_attack")
    @patch("typeclasses.items.weapons.greatsword_nft_item.get_sides")
    @patch("typeclasses.items.weapons.greatsword_nft_item.dice")
    def test_executioner_on_cleave_kill(self, mock_dice, mock_sides, mock_exec):
        """Cleave kill should trigger executioner for GM."""
        _set_mastery(self.char1, 5)  # GM
        handler = self._setup_handler()

        dying = _mock_dying_enemy()
        exec_target = _mock_enemy(hp=50, name="NextTarget")

        # First get_sides for cleave, second for executioner
        mock_sides.side_effect = [
            ([], [dying]),
            ([], [exec_target]),
        ]
        # d100=70 passes 75%, dmg=10
        mock_dice.roll.side_effect = [70, 10]

        self.gs.at_post_attack(self.char1, self.char2, True, 5)

        mock_exec.assert_called_once_with(self.char1, exec_target)
        self.assertTrue(handler.executioner_used)

    @patch("typeclasses.items.weapons.greatsword_nft_item.execute_attack")
    @patch("typeclasses.items.weapons.greatsword_nft_item.get_sides")
    @patch("typeclasses.items.weapons.greatsword_nft_item.dice")
    def test_no_executioner_cleave_no_kill(self, mock_dice, mock_sides, mock_exec):
        """Cleave hit that doesn't kill should not trigger executioner."""
        _set_mastery(self.char1, 5)  # GM
        self._setup_handler()

        enemy = _mock_enemy(hp=100)  # survives
        mock_sides.return_value = ([], [enemy])
        mock_dice.roll.side_effect = [70, 6]

        self.gs.at_post_attack(self.char1, self.char2, True, 5)

        mock_exec.assert_not_called()

    def test_executioner_used_default_false(self):
        """executioner_used should default to False on new handler."""
        from combat.combat_handler import CombatHandler
        from evennia.utils.create import create_script

        handler = create_script(
            CombatHandler,
            obj=self.char1,
            key="combat_handler",
            autostart=False,
        )
        handler.start()
        self.assertFalse(handler.executioner_used)
