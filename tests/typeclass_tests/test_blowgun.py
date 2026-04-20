"""
Tests for BlowgunNFTItem — poison DoT + paralysis weapon.

Validates:
    - Mastery damage override (always 0 bonus)
    - Melee penalty (UNSKILLED/BASIC get -2, SKILLED+ get 0)
    - Poison application (BASIC+ applies poison, UNSKILLED does not)
    - Poison DoT script ticking + expiry
    - Poison anti-stacking (new hit replaces old poison)
    - Paralysis on failed CON save
    - Paralysis grants advantage to enemies
    - Paralysis size gate (HUGE+ immune)
    - Paralysis skips action in combat handler

evennia test --settings settings tests.typeclass_tests.test_blowgun
"""

from unittest.mock import patch, MagicMock, PropertyMock

from evennia.utils.test_resources import EvenniaTest
from evennia.utils import create

from enums.condition import Condition
from enums.mastery_level import MasteryLevel
from enums.named_effect import NamedEffect


def _make_blowgun(location=None):
    """Create a BlowgunNFTItem for testing."""
    obj = create.create_object(
        "typeclasses.items.weapons.blowgun_nft_item.BlowgunNFTItem",
        key="Test Blowgun",
        nohome=True,
    )
    if location:
        obj.move_to(location, quiet=True)
    return obj


def _set_mastery(char, level_int):
    """Set char's blowgun mastery to the given integer level."""
    char.db.weapon_skill_mastery_levels = {"blowgun": level_int}


# ================================================================== #
#  Mastery Override Tests
# ================================================================== #

class TestBlowgunMasteryOverrides(EvenniaTest):
    """Test that blowgun overrides damage bonus, parries, extra attacks."""

    def create_script(self):
        pass

    def test_damage_bonus_always_zero(self):
        """Blowgun should return 0 mastery damage bonus at all levels."""
        blowgun = _make_blowgun()
        for level in range(6):
            _set_mastery(self.char1, level)
            self.assertEqual(blowgun.get_mastery_damage_bonus(self.char1), 0)

    def test_parries_always_zero(self):
        """Blowgun should grant 0 parries per round."""
        blowgun = _make_blowgun()
        self.assertEqual(blowgun.get_parries_per_round(self.char1), 0)

    def test_extra_attacks_always_zero(self):
        """Blowgun should grant 0 extra attacks."""
        blowgun = _make_blowgun()
        self.assertEqual(blowgun.get_extra_attacks(self.char1), 0)

    def test_damage_roll_always_one(self):
        """Blowgun damage roll should be '1' at all mastery levels."""
        blowgun = _make_blowgun()
        for level in MasteryLevel:
            self.assertEqual(blowgun.get_damage_roll(level), "1")


# ================================================================== #
#  Melee Penalty Tests
# ================================================================== #

class TestBlowgunMeleePenalty(EvenniaTest):
    """Test at_pre_attack melee penalty for low mastery."""

    def create_script(self):
        pass

    def test_unskilled_gets_penalty(self):
        """UNSKILLED blowgun wielder should get -2 melee penalty."""
        blowgun = _make_blowgun()
        _set_mastery(self.char1, 0)
        self.assertEqual(blowgun.at_pre_attack(self.char1, self.char2), -2)

    def test_basic_gets_penalty(self):
        """BASIC blowgun wielder should get -2 melee penalty."""
        blowgun = _make_blowgun()
        _set_mastery(self.char1, 1)
        self.assertEqual(blowgun.at_pre_attack(self.char1, self.char2), -2)

    def test_skilled_no_penalty(self):
        """SKILLED blowgun wielder should get no melee penalty."""
        blowgun = _make_blowgun()
        _set_mastery(self.char1, 2)
        self.assertEqual(blowgun.at_pre_attack(self.char1, self.char2), 0)

    def test_expert_no_penalty(self):
        """EXPERT blowgun wielder should get no melee penalty."""
        blowgun = _make_blowgun()
        _set_mastery(self.char1, 3)
        self.assertEqual(blowgun.at_pre_attack(self.char1, self.char2), 0)

    def test_master_no_penalty(self):
        """MASTER blowgun wielder should get no melee penalty."""
        blowgun = _make_blowgun()
        _set_mastery(self.char1, 4)
        self.assertEqual(blowgun.at_pre_attack(self.char1, self.char2), 0)

    def test_gm_no_penalty(self):
        """GM blowgun wielder should get no melee penalty."""
        blowgun = _make_blowgun()
        _set_mastery(self.char1, 5)
        self.assertEqual(blowgun.at_pre_attack(self.char1, self.char2), 0)


# ================================================================== #
#  Poison Application Tests
# ================================================================== #

class TestBlowgunPoison(EvenniaTest):
    """Test poison DoT application via at_hit."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.blowgun = _make_blowgun()
        self.char2.hp = 100
        self.char2.hp_max = 100

    def test_unskilled_no_poison(self):
        """UNSKILLED hit should return damage without applying poison."""
        _set_mastery(self.char1, 0)
        result = self.blowgun.at_hit(self.char1, self.char2, 1, "piercing")
        self.assertEqual(result, 1)
        self.assertFalse(self.char2.has_effect("poisoned"))

    @patch("typeclasses.items.weapons.blowgun_nft_item.dice")
    def test_basic_applies_poison(self, mock_dice):
        """BASIC hit should apply poisoned named effect."""
        mock_dice.roll.return_value = 3  # poison duration = 3 ticks
        _set_mastery(self.char1, 1)
        self.blowgun.at_hit(self.char1, self.char2, 1, "piercing")
        self.assertTrue(self.char2.has_effect("poisoned"))

    @patch("typeclasses.items.weapons.blowgun_nft_item.dice")
    def test_basic_creates_poison_script(self, mock_dice):
        """BASIC hit should create PoisonDoTScript on target."""
        mock_dice.roll.return_value = 3
        _set_mastery(self.char1, 1)
        self.blowgun.at_hit(self.char1, self.char2, 1, "piercing")
        scripts = self.char2.scripts.get("poison_dot")
        self.assertTrue(scripts)
        self.assertEqual(scripts[0].db.remaining_ticks, 3)
        self.assertEqual(scripts[0].db.damage_dice, "1d2")

    @patch("typeclasses.items.weapons.blowgun_nft_item.dice")
    def test_skilled_poison_uses_correct_dice(self, mock_dice):
        """SKILLED hit should use 1d4 duration and 1d3 damage dice."""
        mock_dice.roll.return_value = 4
        _set_mastery(self.char1, 2)
        self.blowgun.at_hit(self.char1, self.char2, 1, "piercing")
        scripts = self.char2.scripts.get("poison_dot")
        self.assertTrue(scripts)
        self.assertEqual(scripts[0].db.remaining_ticks, 4)
        self.assertEqual(scripts[0].db.damage_dice, "1d3")

    @patch("typeclasses.items.weapons.blowgun_nft_item.dice")
    def test_poison_replaces_existing(self, mock_dice):
        """Second poison hit should replace the first."""
        mock_dice.roll.return_value = 2
        _set_mastery(self.char1, 1)

        # First hit
        self.blowgun.at_hit(self.char1, self.char2, 1, "piercing")
        scripts_before = self.char2.scripts.get("poison_dot")
        self.assertEqual(len(scripts_before), 1)

        # Second hit (replaces)
        mock_dice.roll.return_value = 3
        _set_mastery(self.char1, 2)  # upgrade mastery for different dice
        self.blowgun.at_hit(self.char1, self.char2, 1, "piercing")
        scripts_after = self.char2.scripts.get("poison_dot")
        self.assertEqual(len(scripts_after), 1)
        self.assertEqual(scripts_after[0].db.remaining_ticks, 3)
        self.assertEqual(scripts_after[0].db.damage_dice, "1d3")

    @patch("typeclasses.items.weapons.blowgun_nft_item.dice")
    def test_at_hit_returns_damage_unchanged(self, mock_dice):
        """at_hit should return the original damage value."""
        mock_dice.roll.return_value = 2
        _set_mastery(self.char1, 1)
        result = self.blowgun.at_hit(self.char1, self.char2, 1, "piercing")
        self.assertEqual(result, 1)


# ================================================================== #
#  Poison DoT Script Tests
# ================================================================== #

class TestPoisonDoTScript(EvenniaTest):
    """Test PoisonDoTScript ticking and expiry."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.char2.hp = 100
        self.char2.hp_max = 100

    def _create_poison_script(self, target, remaining=3, damage_dice="1d2"):
        """Create a PoisonDoTScript on target with given params."""
        from evennia.utils.create import create_script
        from typeclasses.scripts.poison_dot_script import PoisonDoTScript

        # Apply the named effect first (like blowgun does)
        target.apply_named_effect(
            key="poisoned",
            duration=remaining,
            duration_type=None,
            messages={
                "start": NamedEffect.POISONED.get_start_message(),
                "end": NamedEffect.POISONED.get_end_message(),
            },
        )

        script = create_script(
            PoisonDoTScript,
            obj=target,
            key="poison_dot",
            autostart=False,
        )
        script.db.remaining_ticks = remaining
        script.db.damage_dice = damage_dice
        script.db.source_name = "TestPoisoner"
        script.start()
        return script

    @patch("typeclasses.scripts.poison_dot_script.dice")
    def test_tick_deals_damage(self, mock_dice):
        """Poison tick should deal damage to the target."""
        mock_dice.roll.return_value = 2
        script = self._create_poison_script(self.char2, remaining=3, damage_dice="1d2")
        script.tick_poison()
        self.assertEqual(self.char2.hp, 98)

    @patch("typeclasses.scripts.poison_dot_script.dice")
    def test_tick_decrements_remaining(self, mock_dice):
        """Each tick should decrement remaining_ticks."""
        mock_dice.roll.return_value = 1
        script = self._create_poison_script(self.char2, remaining=3)
        script.tick_poison()
        self.assertEqual(script.db.remaining_ticks, 2)

    @patch("typeclasses.scripts.poison_dot_script.dice")
    def test_tick_expires_at_zero(self, mock_dice):
        """Script should delete itself when remaining_ticks hits 0."""
        mock_dice.roll.return_value = 1
        script = self._create_poison_script(self.char2, remaining=1)
        script.tick_poison()
        # Script should have deleted itself
        scripts = self.char2.scripts.get("poison_dot")
        self.assertFalse(scripts)
        # Named effect should be removed
        self.assertFalse(self.char2.has_effect("poisoned"))

    @patch("typeclasses.scripts.poison_dot_script.dice")
    def test_tick_expires_on_death(self, mock_dice):
        """Script should expire if target dies."""
        mock_dice.roll.return_value = 1
        self.char2.hp = 1
        script = self._create_poison_script(self.char2, remaining=5)
        with patch.object(self.char2, "die", MagicMock()):
            script.tick_poison()
        # Target should be at 0 HP and script should expire
        scripts = self.char2.scripts.get("poison_dot")
        self.assertFalse(scripts)

    @patch("typeclasses.scripts.poison_dot_script.dice")
    def test_at_repeat_skips_in_combat(self, mock_dice):
        """at_repeat should skip ticking if target has combat_handler."""
        mock_dice.roll.return_value = 2
        script = self._create_poison_script(self.char2, remaining=3)

        # Mock combat handler existence
        mock_handler = MagicMock()
        with patch.object(self.char2.scripts, "get", return_value=[mock_handler]):
            script.at_repeat()

        # HP should be unchanged (skipped)
        self.assertEqual(self.char2.hp, 100)

    @patch("typeclasses.scripts.poison_dot_script.dice")
    def test_at_repeat_ticks_out_of_combat(self, mock_dice):
        """at_repeat should tick when target is NOT in combat."""
        mock_dice.roll.return_value = 2
        script = self._create_poison_script(self.char2, remaining=3)
        script.at_repeat()
        self.assertEqual(self.char2.hp, 98)


# ================================================================== #
#  Paralysis Tests
# ================================================================== #

class TestBlowgunParalysis(EvenniaTest):
    """Test paralysis CON save and application."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.blowgun = _make_blowgun()
        self.char2.hp = 100
        self.char2.hp_max = 100
        self.char2.constitution = 10  # +0 mod

    @patch("typeclasses.items.weapons.blowgun_nft_item.get_actor_size")
    @patch("typeclasses.items.weapons.blowgun_nft_item.dice")
    def test_paralysis_on_failed_save(self, mock_dice, mock_size):
        """Failed CON save should apply PARALYSED condition."""
        from enums.size import Size
        mock_size.return_value = Size.MEDIUM
        # First dice.roll = poison duration, second = CON save d20
        mock_dice.roll.side_effect = [2, 5]  # poison ticks=2, save roll=5
        _set_mastery(self.char1, 1)  # BASIC: DC 10

        self.blowgun.at_hit(self.char1, self.char2, 1, "piercing")

        # 5 + 0(CON mod) = 5 < DC 10 → paralysed
        self.assertTrue(self.char2.has_condition(Condition.PARALYSED))
        self.assertTrue(self.char2.has_effect("paralysed"))

    @patch("typeclasses.items.weapons.blowgun_nft_item.get_actor_size")
    @patch("typeclasses.items.weapons.blowgun_nft_item.dice")
    def test_paralysis_resisted_on_passed_save(self, mock_dice, mock_size):
        """Passed CON save should NOT apply PARALYSED."""
        from enums.size import Size
        mock_size.return_value = Size.MEDIUM
        # poison ticks=2, save roll=15
        mock_dice.roll.side_effect = [2, 15]
        _set_mastery(self.char1, 1)  # BASIC: DC 10

        self.blowgun.at_hit(self.char1, self.char2, 1, "piercing")

        # 15 + 0 = 15 >= DC 10 → saved
        self.assertFalse(self.char2.has_condition(Condition.PARALYSED))

    @patch("typeclasses.items.weapons.blowgun_nft_item.get_actor_size")
    @patch("typeclasses.items.weapons.blowgun_nft_item.dice")
    def test_paralysis_huge_immune(self, mock_dice, mock_size):
        """HUGE targets should be immune to paralysis."""
        from enums.size import Size
        mock_size.return_value = Size.HUGE
        mock_dice.roll.side_effect = [2, 1]  # poison ticks=2, save roll=1 (nat 1, would fail)
        _set_mastery(self.char1, 1)

        self.blowgun.at_hit(self.char1, self.char2, 1, "piercing")

        # HUGE = immune, no paralysis even on natural 1
        self.assertFalse(self.char2.has_condition(Condition.PARALYSED))

    @patch("typeclasses.items.weapons.blowgun_nft_item.get_actor_size")
    @patch("typeclasses.items.weapons.blowgun_nft_item.dice")
    def test_paralysis_gargantuan_immune(self, mock_dice, mock_size):
        """GARGANTUAN targets should be immune to paralysis."""
        from enums.size import Size
        mock_size.return_value = Size.GARGANTUAN
        mock_dice.roll.side_effect = [2, 1]
        _set_mastery(self.char1, 1)

        self.blowgun.at_hit(self.char1, self.char2, 1, "piercing")
        self.assertFalse(self.char2.has_condition(Condition.PARALYSED))

    @patch("combat.combat_utils.get_sides")
    @patch("typeclasses.items.weapons.blowgun_nft_item.get_actor_size")
    @patch("typeclasses.items.weapons.blowgun_nft_item.dice")
    def test_paralysis_grants_advantage(self, mock_dice, mock_size, mock_sides):
        """Paralysis should grant advantage to all enemies of the target."""
        from enums.size import Size
        mock_size.return_value = Size.MEDIUM
        mock_dice.roll.side_effect = [2, 3]  # poison ticks=2, save=3 (fail DC 10)
        _set_mastery(self.char1, 1)

        # Mock enemy with combat handler that has set_advantage
        mock_handler = MagicMock()
        mock_enemy = MagicMock()
        mock_enemy.scripts.get.return_value = [mock_handler]
        mock_sides.return_value = ([], [mock_enemy])

        self.blowgun.at_hit(self.char1, self.char2, 1, "piercing")

        # Enemy's combat handler should have set_advantage called
        mock_handler.set_advantage.assert_called_once_with(self.char2, 1)

    @patch("typeclasses.items.weapons.blowgun_nft_item.get_actor_size")
    @patch("typeclasses.items.weapons.blowgun_nft_item.dice")
    def test_expert_paralysis_two_rounds(self, mock_dice, mock_size):
        """EXPERT paralysis should last 2 rounds."""
        from enums.size import Size
        mock_size.return_value = Size.MEDIUM
        mock_dice.roll.side_effect = [3, 1]  # poison ticks=3, save=1 (fail DC 14)
        _set_mastery(self.char1, 3)  # EXPERT

        self.blowgun.at_hit(self.char1, self.char2, 1, "piercing")

        effect = self.char2.get_named_effect("paralysed")
        self.assertIsNotNone(effect)
        self.assertEqual(effect["duration"], 2)

    @patch("typeclasses.items.weapons.blowgun_nft_item.get_actor_size")
    @patch("typeclasses.items.weapons.blowgun_nft_item.dice")
    def test_gm_paralysis_three_rounds(self, mock_dice, mock_size):
        """GM paralysis should last 3 rounds."""
        from enums.size import Size
        mock_size.return_value = Size.MEDIUM
        mock_dice.roll.side_effect = [5, 1]  # poison ticks=5, save=1 (fail DC 20)
        _set_mastery(self.char1, 5)  # GM

        self.blowgun.at_hit(self.char1, self.char2, 1, "piercing")

        effect = self.char2.get_named_effect("paralysed")
        self.assertIsNotNone(effect)
        self.assertEqual(effect["duration"], 3)

    def test_unskilled_no_paralysis(self):
        """UNSKILLED should not attempt paralysis at all."""
        _set_mastery(self.char1, 0)
        self.blowgun.at_hit(self.char1, self.char2, 1, "piercing")
        self.assertFalse(self.char2.has_condition(Condition.PARALYSED))


# ================================================================== #
#  Paralysis Action Denial (combat handler integration)
# ================================================================== #

class TestParalysisActionDenial(EvenniaTest):
    """Test that paralysed targets skip their combat action."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def test_paralysed_target_has_effect(self):
        """Applying paralysed named effect should make has_effect return True."""
        self.char1.apply_named_effect(
            key="paralysed",
            condition=Condition.PARALYSED,
            duration=2,
            duration_type="combat_rounds",
            messages={
                "start": NamedEffect.PARALYSED.get_start_message(),
                "end": NamedEffect.PARALYSED.get_end_message(),
            },
        )
        self.assertTrue(self.char1.has_effect("paralysed"))
        self.assertTrue(self.char1.has_condition(Condition.PARALYSED))


# ================================================================== #
#  Weapon Attributes Tests
# ================================================================== #

class TestBlowgunAttributes(EvenniaTest):
    """Test BlowgunNFTItem static attributes."""

    def create_script(self):
        pass

    def test_weapon_type_key(self):
        """weapon_type_key should be 'blowgun'."""
        blowgun = _make_blowgun()
        self.assertEqual(blowgun.weapon_type_key, "blowgun")

    def test_weapon_type_ranged(self):
        """weapon_type should be 'ranged'."""
        blowgun = _make_blowgun()
        self.assertEqual(blowgun.weapon_type, "ranged")

    def test_is_finesse(self):
        """Blowgun should be finesse."""
        blowgun = _make_blowgun()
        self.assertTrue(blowgun.is_finesse)

    def test_not_two_handed(self):
        """Blowgun should be one-handed."""
        blowgun = _make_blowgun()
        self.assertFalse(blowgun.two_handed)

    def test_has_blowgun_tag(self):
        """Blowgun should have 'blowgun' weapon_type tag."""
        blowgun = _make_blowgun()
        self.assertTrue(blowgun.tags.has("blowgun", category="weapon_type"))
