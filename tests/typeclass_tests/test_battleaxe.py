"""
Tests for BattleaxeNFTItem — two-handed cleave + stacking sunder weapon.

Validates:
    - No parries, no extra attacks (pure offense)
    - Nerfed cleave cascading on hit via at_post_attack
    - Cleave chain break on failed d100 check
    - Stacking sunder on primary hit via at_hit
    - Stacking sunder on cleave hit
    - Sunder AC floor of 10
    - Sunder extra durability damage to body armour

evennia test --settings settings tests.typeclass_tests.test_battleaxe
"""

from unittest.mock import patch, MagicMock, PropertyMock

from evennia.utils.test_resources import EvenniaTest
from evennia.utils import create

from enums.mastery_level import MasteryLevel


def _make_battleaxe(location=None):
    """Create a BattleaxeNFTItem for testing."""
    obj = create.create_object(
        "typeclasses.items.weapons.battleaxe_nft_item.BattleaxeNFTItem",
        key="Test Battleaxe",
        nohome=True,
    )
    if location:
        obj.move_to(location, quiet=True)
    return obj


def _set_mastery(char, level_int):
    """Set char's battleaxe mastery to the given integer level."""
    char.db.weapon_skill_mastery_levels = {"battleaxe": level_int}


def _mock_enemy(hp=100, name="Enemy", armor_class=15,
                has_sundered=False, sunder_stacks=0):
    """Create a mock enemy for cleave/sunder targets."""
    enemy = MagicMock()
    enemy.hp = hp
    enemy.key = name
    enemy.armor_class = armor_class
    enemy.take_damage.return_value = 5
    enemy.location = MagicMock()
    enemy.has_effect.return_value = has_sundered
    enemy.apply_sundered = MagicMock(return_value=True)
    enemy.db.sunder_stacks = sunder_stacks if has_sundered else 0
    enemy.get_slot.return_value = None
    return enemy


# ================================================================== #
#  Mastery Override Tests
# ================================================================== #

class TestBattleaxeMasteryOverrides(EvenniaTest):
    """Test basic battleaxe properties."""

    def create_script(self):
        pass

    def test_no_parries(self):
        ba = _make_battleaxe()
        for level in range(6):
            _set_mastery(self.char1, level)
            self.assertEqual(ba.get_parries_per_round(self.char1), 0)

    def test_no_extra_attacks(self):
        ba = _make_battleaxe()
        for level in range(6):
            _set_mastery(self.char1, level)
            self.assertEqual(ba.get_extra_attacks(self.char1), 0)

    def test_weapon_type_key(self):
        ba = _make_battleaxe()
        self.assertEqual(ba.weapon_type_key, "battleaxe")

    def test_has_battleaxe_tag(self):
        ba = _make_battleaxe()
        self.assertTrue(ba.tags.has("battleaxe", category="weapon_type"))

    def test_two_handed(self):
        ba = _make_battleaxe()
        self.assertTrue(ba.two_handed)


# ================================================================== #
#  Sunder Tests
# ================================================================== #

class TestBattleaxeSunder(EvenniaTest):
    """Test stacking sunder mechanic on battleaxe."""

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.ba = _make_battleaxe()

    @patch("typeclasses.items.weapons.battleaxe_nft_item.dice")
    def test_no_sunder_unskilled(self, mock_dice):
        """UNSKILLED should never attempt sunder."""
        _set_mastery(self.char1, 0)
        target = _mock_enemy()

        self.ba.at_hit(self.char1, target, 5, "slashing")

        mock_dice.roll.assert_not_called()

    @patch("typeclasses.items.weapons.battleaxe_nft_item.dice")
    def test_sunder_skilled_hit(self, mock_dice):
        """SKILLED: d100=15 <= 20% → sunder applied with -1 AC."""
        _set_mastery(self.char1, 2)
        target = _mock_enemy(armor_class=15)
        mock_dice.roll.return_value = 15

        self.ba.at_hit(self.char1, target, 5, "slashing")

        target.apply_sundered.assert_called_once()
        args, kwargs = target.apply_sundered.call_args
        self.assertEqual(args[0], -1)  # ac_penalty
        self.assertEqual(args[1], 99)  # duration_rounds
        self.assertEqual(kwargs["source"], self.char1)

    @patch("typeclasses.items.weapons.battleaxe_nft_item.dice")
    def test_sunder_skilled_miss(self, mock_dice):
        """SKILLED: d100=25 > 20% → no sunder."""
        _set_mastery(self.char1, 2)
        target = _mock_enemy()
        mock_dice.roll.return_value = 25

        self.ba.at_hit(self.char1, target, 5, "slashing")

        target.apply_sundered.assert_not_called()

    @patch("typeclasses.items.weapons.battleaxe_nft_item.dice")
    def test_sunder_stacks(self, mock_dice):
        """Second sunder should stack to -2 AC total."""
        _set_mastery(self.char1, 2)  # SKILLED: -1 per hit
        target = _mock_enemy(armor_class=14, has_sundered=True, sunder_stacks=1)
        mock_dice.roll.return_value = 15

        self.ba.at_hit(self.char1, target, 5, "slashing")

        target.remove_named_effect.assert_called_once_with("sundered")
        args, kwargs = target.apply_sundered.call_args
        self.assertEqual(args[0], -2)  # ac_penalty (stacked)

    @patch("typeclasses.items.weapons.battleaxe_nft_item.dice")
    def test_sunder_gm_penalty(self, mock_dice):
        """GM: sunder should apply -2 AC per hit with 30% chance."""
        _set_mastery(self.char1, 5)
        target = _mock_enemy(armor_class=20)
        mock_dice.roll.return_value = 25

        self.ba.at_hit(self.char1, target, 5, "slashing")

        args, kwargs = target.apply_sundered.call_args
        self.assertEqual(args[0], -2)  # ac_penalty

    @patch("typeclasses.items.weapons.battleaxe_nft_item.dice")
    def test_sunder_ac_floor(self, mock_dice):
        """Sunder should not reduce armor_class below 10."""
        _set_mastery(self.char1, 2)
        target = _mock_enemy(armor_class=10)
        mock_dice.roll.return_value = 15

        self.ba.at_hit(self.char1, target, 5, "slashing")

        target.apply_sundered.assert_not_called()

    @patch("typeclasses.items.weapons.battleaxe_nft_item.dice")
    def test_sunder_ac_floor_partial(self, mock_dice):
        """MASTER sunder (-2) on AC 11 should only apply -1."""
        _set_mastery(self.char1, 4)
        target = _mock_enemy(armor_class=11)
        mock_dice.roll.return_value = 20

        self.ba.at_hit(self.char1, target, 5, "slashing")

        args, kwargs = target.apply_sundered.call_args
        self.assertEqual(args[0], -1)  # ac_penalty (clamped by floor)

    @patch("typeclasses.items.weapons.battleaxe_nft_item.dice")
    def test_sunder_extra_durability(self, mock_dice):
        """Sunder should deal extra durability damage to body armour."""
        _set_mastery(self.char1, 2)  # SKILLED: +1 extra durability
        body_armor = MagicMock()
        body_armor.reduce_durability = MagicMock()
        target = _mock_enemy(armor_class=15)
        target.get_slot.return_value = body_armor
        mock_dice.roll.return_value = 15

        self.ba.at_hit(self.char1, target, 5, "slashing")

        body_armor.reduce_durability.assert_called_once_with(1)

    @patch("typeclasses.items.weapons.battleaxe_nft_item.dice")
    def test_sunder_master_extra_durability(self, mock_dice):
        """MASTER sunder should deal +2 extra durability damage."""
        _set_mastery(self.char1, 4)
        body_armor = MagicMock()
        body_armor.reduce_durability = MagicMock()
        target = _mock_enemy(armor_class=20)
        target.get_slot.return_value = body_armor
        mock_dice.roll.return_value = 20

        self.ba.at_hit(self.char1, target, 5, "slashing")

        body_armor.reduce_durability.assert_called_once_with(2)

    @patch("typeclasses.items.weapons.battleaxe_nft_item.dice")
    def test_sunder_returns_damage_unchanged(self, mock_dice):
        """at_hit should return damage unchanged regardless of sunder."""
        _set_mastery(self.char1, 5)
        target = _mock_enemy()
        mock_dice.roll.return_value = 1

        result = self.ba.at_hit(self.char1, target, 42, "slashing")

        self.assertEqual(result, 42)

    @patch("typeclasses.items.weapons.battleaxe_nft_item.dice")
    def test_sunder_stores_stacks(self, mock_dice):
        """Sunder should store cumulative stacks on target.db.sunder_stacks."""
        _set_mastery(self.char1, 2)
        target = _mock_enemy(armor_class=15)
        mock_dice.roll.return_value = 15

        self.ba.at_hit(self.char1, target, 5, "slashing")

        self.assertEqual(target.db.sunder_stacks, 1)


# ================================================================== #
#  Cleave Tests
# ================================================================== #

class TestBattleaxeCleave(EvenniaTest):
    """Test nerfed cleave cascading AoE mechanic."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.ba = _make_battleaxe()
        patcher = patch.object(
            type(self.char1), 'effective_damage_bonus',
            new_callable=PropertyMock, return_value=4
        )
        self.mock_dmg_bonus = patcher.start()
        self.addCleanup(patcher.stop)

    @patch("typeclasses.items.weapons.battleaxe_nft_item.get_sides")
    @patch("typeclasses.items.weapons.battleaxe_nft_item.dice")
    def test_no_cleave_on_miss(self, mock_dice, mock_sides):
        """Cleave should not trigger when primary attack misses."""
        _set_mastery(self.char1, 3)
        enemy = _mock_enemy()
        mock_sides.return_value = ([], [enemy])

        self.ba.at_post_attack(self.char1, self.char2, False, 0)

        enemy.take_damage.assert_not_called()

    @patch("typeclasses.items.weapons.battleaxe_nft_item.get_sides")
    @patch("typeclasses.items.weapons.battleaxe_nft_item.dice")
    def test_no_cleave_unskilled(self, mock_dice, mock_sides):
        """UNSKILLED should have no cleave chances."""
        _set_mastery(self.char1, 0)

        self.ba.at_post_attack(self.char1, self.char2, True, 5)

        mock_sides.assert_not_called()

    @patch("typeclasses.items.weapons.battleaxe_nft_item.get_sides")
    @patch("typeclasses.items.weapons.battleaxe_nft_item.dice")
    def test_cleave_skilled_hit(self, mock_dice, mock_sides):
        """SKILLED: 20% chance passes → 2nd enemy takes damage."""
        _set_mastery(self.char1, 2)
        enemy = _mock_enemy()
        mock_sides.return_value = ([], [enemy])
        # d100=15 passes 20% cleave, dmg=8, d100=99 sunder fails
        mock_dice.roll.side_effect = [15, 8, 99]

        self.ba.at_post_attack(self.char1, self.char2, True, 5)

        enemy.take_damage.assert_called_once()
        self.assertEqual(enemy.take_damage.call_args[0][0], 12)

    @patch("typeclasses.items.weapons.battleaxe_nft_item.get_sides")
    @patch("typeclasses.items.weapons.battleaxe_nft_item.dice")
    def test_cleave_skilled_miss(self, mock_dice, mock_sides):
        """SKILLED: d100 > 20 → no cleave."""
        _set_mastery(self.char1, 2)
        enemy = _mock_enemy()
        mock_sides.return_value = ([], [enemy])
        mock_dice.roll.side_effect = [25]

        self.ba.at_post_attack(self.char1, self.char2, True, 5)

        enemy.take_damage.assert_not_called()

    @patch("typeclasses.items.weapons.battleaxe_nft_item.get_sides")
    @patch("typeclasses.items.weapons.battleaxe_nft_item.dice")
    def test_cleave_expert_cascade_both(self, mock_dice, mock_sides):
        """EXPERT: 40%/20%, both pass → 2 extra enemies hit."""
        _set_mastery(self.char1, 3)
        enemy1 = _mock_enemy(name="Enemy1")
        enemy2 = _mock_enemy(name="Enemy2")
        mock_sides.return_value = ([], [enemy1, enemy2])
        # d100=35 cleave1, dmg=6, d100=99 sunder1 fails,
        # d100=15 cleave2, dmg=8, d100=99 sunder2 fails
        mock_dice.roll.side_effect = [35, 6, 99, 15, 8, 99]

        self.ba.at_post_attack(self.char1, self.char2, True, 5)

        enemy1.take_damage.assert_called_once()
        enemy2.take_damage.assert_called_once()

    @patch("typeclasses.items.weapons.battleaxe_nft_item.get_sides")
    @patch("typeclasses.items.weapons.battleaxe_nft_item.dice")
    def test_cleave_chain_break(self, mock_dice, mock_sides):
        """EXPERT: 1st passes 40%, 2nd fails 20% → only 1 extra hit."""
        _set_mastery(self.char1, 3)
        enemy1 = _mock_enemy(name="Enemy1")
        enemy2 = _mock_enemy(name="Enemy2")
        mock_sides.return_value = ([], [enemy1, enemy2])
        # d100=35 cleave1, dmg=6, d100=99 sunder1 fails, d100=25 cleave2 fails
        mock_dice.roll.side_effect = [35, 6, 99, 25]

        self.ba.at_post_attack(self.char1, self.char2, True, 5)

        enemy1.take_damage.assert_called_once()
        enemy2.take_damage.assert_not_called()

    @patch("typeclasses.items.weapons.battleaxe_nft_item.get_sides")
    @patch("typeclasses.items.weapons.battleaxe_nft_item.dice")
    def test_cleave_excludes_primary(self, mock_dice, mock_sides):
        """Primary target should not be hit by cleave."""
        _set_mastery(self.char1, 2)
        primary = _mock_enemy(name="Primary")
        other = _mock_enemy(name="Other")
        mock_sides.return_value = ([], [primary, other])
        # d100=15 cleave, dmg=6, d100=99 sunder fails
        mock_dice.roll.side_effect = [15, 6, 99]

        self.ba.at_post_attack(self.char1, primary, True, 5)

        primary.take_damage.assert_not_called()
        other.take_damage.assert_called_once()

    @patch("typeclasses.items.weapons.battleaxe_nft_item.get_sides")
    @patch("typeclasses.items.weapons.battleaxe_nft_item.dice")
    def test_cleave_skips_dead(self, mock_dice, mock_sides):
        """Dead enemies should not be cleave targets."""
        _set_mastery(self.char1, 3)
        dead = _mock_enemy(hp=0, name="Dead")
        alive = _mock_enemy(hp=50, name="Alive")
        mock_sides.return_value = ([], [dead, alive])
        # d100=35 cleave, dmg=6, d100=99 sunder fails
        mock_dice.roll.side_effect = [35, 6, 99]

        self.ba.at_post_attack(self.char1, self.char2, True, 5)

        dead.take_damage.assert_not_called()
        alive.take_damage.assert_called_once()

    @patch("typeclasses.items.weapons.battleaxe_nft_item.get_sides")
    @patch("typeclasses.items.weapons.battleaxe_nft_item.dice")
    def test_cleave_triggers_sunder(self, mock_dice, mock_sides):
        """Cleave hits should also attempt sunder on the target."""
        _set_mastery(self.char1, 2)  # SKILLED: 20% cleave, 20% sunder
        enemy = _mock_enemy(name="CleaveTarget", armor_class=15)
        mock_sides.return_value = ([], [enemy])
        # d100=15 passes 20% cleave, dmg=6, d100=15 passes 20% sunder
        mock_dice.roll.side_effect = [15, 6, 15]

        self.ba.at_post_attack(self.char1, self.char2, True, 5)

        enemy.take_damage.assert_called_once()
        enemy.apply_sundered.assert_called_once()
        args, kwargs = enemy.apply_sundered.call_args
        self.assertEqual(args[0], -1)  # ac_penalty

    @patch("typeclasses.items.weapons.battleaxe_nft_item.get_sides")
    @patch("typeclasses.items.weapons.battleaxe_nft_item.dice")
    def test_cleave_minimum_damage(self, mock_dice, mock_sides):
        """Cleave damage should be at least 1."""
        _set_mastery(self.char1, 2)
        self.mock_dmg_bonus.return_value = -5
        enemy = _mock_enemy()
        mock_sides.return_value = ([], [enemy])
        # d100=15 cleave, dmg=1, d100=99 sunder fails
        mock_dice.roll.side_effect = [15, 1, 99]

        self.ba.at_post_attack(self.char1, self.char2, True, 5)

        self.assertEqual(enemy.take_damage.call_args[0][0], 1)

    @patch("typeclasses.items.weapons.battleaxe_nft_item.get_sides")
    @patch("typeclasses.items.weapons.battleaxe_nft_item.dice")
    def test_cleave_master_three_targets(self, mock_dice, mock_sides):
        """MASTER: 60%/40%/20%, all pass → 3 extra enemies hit."""
        _set_mastery(self.char1, 4)
        e1 = _mock_enemy(name="E1")
        e2 = _mock_enemy(name="E2")
        e3 = _mock_enemy(name="E3")
        mock_sides.return_value = ([], [e1, e2, e3])
        # d100=55 cleave1, dmg=6, d100=99 sunder1 fails,
        # d100=35 cleave2, dmg=8, d100=99 sunder2 fails,
        # d100=15 cleave3, dmg=10, d100=99 sunder3 fails
        mock_dice.roll.side_effect = [55, 6, 99, 35, 8, 99, 15, 10, 99]

        self.ba.at_post_attack(self.char1, self.char2, True, 5)

        e1.take_damage.assert_called_once()
        e2.take_damage.assert_called_once()
        e3.take_damage.assert_called_once()
