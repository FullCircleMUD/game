"""
Tests for LanceNFTItem — lance with mounted combat mastery.

Validates:
    - Unmounted: no crit bonus, no extra attacks, no prone
    - Mounted: crit threshold scales (0/0/-1/-2/-2/-3)
    - Mounted: extra attacks at MASTER+ only (0/0/0/0/1/1)
    - Mounted: prone chance scales and size-gates correctly
    - Prone only fires on first hit per round
    - Two-handed
    - weapon_type_key and tag set correctly

evennia test --settings settings tests.typeclass_tests.test_lance
"""

from unittest.mock import MagicMock, patch

from evennia.utils.test_resources import EvenniaTest
from evennia.utils import create

from enums.actor_size import ActorSize
from enums.mastery_level import MasteryLevel


def _make_lance(location=None):
    """Create a LanceNFTItem for testing."""
    obj = create.create_object(
        "typeclasses.items.weapons.lance_nft_item.LanceNFTItem",
        key="Test Lance",
        nohome=True,
    )
    if location:
        obj.move_to(location, quiet=True)
    return obj


def _set_mastery(char, level_int):
    """Set char's lance mastery to the given integer level."""
    char.db.weapon_skill_mastery_levels = {"lance": level_int}


def _mock_target(size=ActorSize.MEDIUM):
    """Create a mock target with specific ActorSize."""
    target = MagicMock()
    target.key = "Target"
    target.hp = 100
    target.has_effect = MagicMock(return_value=False)
    target.apply_prone = MagicMock(return_value=True)
    # Store size for get_actor_size patch
    target._test_size = size
    return target


# ================================================================== #
#  Basic Properties
# ================================================================== #

class TestLanceProperties(EvenniaTest):
    """Test basic lance properties."""

    def create_script(self):
        pass

    def test_weapon_type_key(self):
        lance = _make_lance()
        self.assertEqual(lance.weapon_type_key, "lance")

    def test_has_lance_tag(self):
        lance = _make_lance()
        self.assertTrue(lance.tags.has("lance", category="weapon_type"))

    def test_two_handed(self):
        lance = _make_lance()
        self.assertTrue(lance.two_handed)

    def test_no_parries(self):
        lance = _make_lance()
        for level in range(6):
            _set_mastery(self.char1, level)
            self.assertEqual(lance.get_parries_per_round(self.char1), 0)

    def test_no_riposte(self):
        lance = _make_lance()
        for level in range(6):
            _set_mastery(self.char1, level)
            self.assertFalse(lance.has_riposte(self.char1))


# ================================================================== #
#  Unmounted Tests — everything nerfed
# ================================================================== #

class TestLanceUnmounted(EvenniaTest):
    """Test that lance has no special bonuses when unmounted."""

    def create_script(self):
        pass

    def test_no_crit_bonus_unmounted(self):
        """All mastery tiers: 0 crit threshold modifier when unmounted."""
        lance = _make_lance()
        self.char1.db.active_mount = None
        for level in range(6):
            _set_mastery(self.char1, level)
            self.assertEqual(
                lance.get_mastery_crit_threshold_modifier(self.char1), 0,
                f"Expected 0 crit mod at mastery {level} unmounted"
            )

    def test_no_extra_attacks_unmounted(self):
        """All mastery tiers: 0 extra attacks when unmounted."""
        lance = _make_lance()
        self.char1.db.active_mount = None
        for level in range(6):
            _set_mastery(self.char1, level)
            self.assertEqual(
                lance.get_extra_attacks(self.char1), 0,
                f"Expected 0 extra attacks at mastery {level} unmounted"
            )


# ================================================================== #
#  Mounted Crit Threshold Tests
# ================================================================== #

class TestLanceMountedCrit(EvenniaTest):
    """Test crit threshold modifier when mounted."""

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.char1.db.active_mount = 1  # truthy = mounted

    def test_no_crit_unskilled(self):
        lance = _make_lance()
        _set_mastery(self.char1, 0)
        self.assertEqual(lance.get_mastery_crit_threshold_modifier(self.char1), 0)

    def test_no_crit_basic(self):
        lance = _make_lance()
        _set_mastery(self.char1, 1)
        self.assertEqual(lance.get_mastery_crit_threshold_modifier(self.char1), 0)

    def test_crit_minus1_skilled(self):
        lance = _make_lance()
        _set_mastery(self.char1, 2)
        self.assertEqual(lance.get_mastery_crit_threshold_modifier(self.char1), -1)

    def test_crit_minus2_expert(self):
        lance = _make_lance()
        _set_mastery(self.char1, 3)
        self.assertEqual(lance.get_mastery_crit_threshold_modifier(self.char1), -2)

    def test_crit_minus2_master(self):
        lance = _make_lance()
        _set_mastery(self.char1, 4)
        self.assertEqual(lance.get_mastery_crit_threshold_modifier(self.char1), -2)

    def test_crit_minus3_gm(self):
        lance = _make_lance()
        _set_mastery(self.char1, 5)
        self.assertEqual(lance.get_mastery_crit_threshold_modifier(self.char1), -3)


# ================================================================== #
#  Mounted Extra Attacks Tests
# ================================================================== #

class TestLanceMountedExtraAttacks(EvenniaTest):
    """Test extra attacks when mounted — MASTER+ only."""

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.char1.db.active_mount = 1  # truthy = mounted

    def test_no_extra_attacks_low_mastery(self):
        lance = _make_lance()
        for level in range(4):  # UNSKILLED through EXPERT
            _set_mastery(self.char1, level)
            self.assertEqual(lance.get_extra_attacks(self.char1), 0)

    def test_one_extra_attack_master(self):
        lance = _make_lance()
        _set_mastery(self.char1, 4)
        self.assertEqual(lance.get_extra_attacks(self.char1), 1)

    def test_one_extra_attack_gm(self):
        lance = _make_lance()
        _set_mastery(self.char1, 5)
        self.assertEqual(lance.get_extra_attacks(self.char1), 1)


# ================================================================== #
#  Prone Mechanic Tests
# ================================================================== #

def _patch_actor_size(target_size):
    """Return a get_actor_size replacement that returns the given ActorSize."""
    def _get_actor_size(actor):
        return getattr(actor, "_test_size", target_size)
    return _get_actor_size


class TestLanceProne(EvenniaTest):
    """Test lance prone mechanic — mounted only, size-gated, first hit/round."""

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.lance = _make_lance()
        self.char1.db.active_mount = 1  # truthy = mounted
        self.char1.ndb.lance_prone_used = False

    def test_no_prone_unmounted(self):
        """Unmounted: at_hit should NOT attempt prone."""
        self.char1.db.active_mount = None
        _set_mastery(self.char1, 5)  # GM
        target = _mock_target()

        result = self.lance.at_hit(self.char1, target, 10, "piercing")
        self.assertEqual(result, 10)
        target.apply_prone.assert_not_called()

    def test_no_prone_unskilled(self):
        """UNSKILLED: 0% chance — no prone even if mounted."""
        _set_mastery(self.char1, 0)
        target = _mock_target()

        self.lance.at_hit(self.char1, target, 10, "piercing")
        target.apply_prone.assert_not_called()

    def test_no_prone_basic(self):
        """BASIC: 0% chance — no prone."""
        _set_mastery(self.char1, 1)
        target = _mock_target()

        self.lance.at_hit(self.char1, target, 10, "piercing")
        target.apply_prone.assert_not_called()

    @patch("typeclasses.items.weapons.lance_nft_item.dice")
    @patch("combat.combat_utils.get_actor_size")
    def test_prone_skilled_medium_target(self, mock_get_size, mock_dice):
        """SKILLED: 15% chance, medium target should prone on low roll."""
        mock_dice.roll.return_value = 10  # under 15% threshold
        mock_get_size.side_effect = _patch_actor_size(ActorSize.MEDIUM)
        _set_mastery(self.char1, 2)
        target = _mock_target(size=ActorSize.MEDIUM)

        self.lance.at_hit(self.char1, target, 10, "piercing")
        target.apply_prone.assert_called_once()
        self.assertTrue(self.char1.ndb.lance_prone_used)

    @patch("typeclasses.items.weapons.lance_nft_item.dice")
    @patch("combat.combat_utils.get_actor_size")
    def test_no_prone_skilled_huge_target(self, mock_get_size, mock_dice):
        """SKILLED: max size LARGE — HUGE target immune."""
        mock_dice.roll.return_value = 1
        mock_get_size.side_effect = _patch_actor_size(ActorSize.HUGE)
        _set_mastery(self.char1, 2)
        target = _mock_target(size=ActorSize.HUGE)

        self.lance.at_hit(self.char1, target, 10, "piercing")
        target.apply_prone.assert_not_called()

    @patch("typeclasses.items.weapons.lance_nft_item.dice")
    @patch("combat.combat_utils.get_actor_size")
    def test_prone_expert_huge_target(self, mock_get_size, mock_dice):
        """EXPERT: max size HUGE — can prone HUGE targets."""
        mock_dice.roll.return_value = 10  # under 20% threshold
        mock_get_size.side_effect = _patch_actor_size(ActorSize.HUGE)
        _set_mastery(self.char1, 3)
        target = _mock_target(size=ActorSize.HUGE)

        self.lance.at_hit(self.char1, target, 10, "piercing")
        target.apply_prone.assert_called_once()

    @patch("typeclasses.items.weapons.lance_nft_item.dice")
    @patch("combat.combat_utils.get_actor_size")
    def test_no_prone_gargantuan(self, mock_get_size, mock_dice):
        """GARGANTUAN always immune, even at GM."""
        mock_dice.roll.return_value = 1
        mock_get_size.side_effect = _patch_actor_size(ActorSize.GARGANTUAN)
        _set_mastery(self.char1, 5)
        target = _mock_target(size=ActorSize.GARGANTUAN)

        self.lance.at_hit(self.char1, target, 10, "piercing")
        target.apply_prone.assert_not_called()

    @patch("typeclasses.items.weapons.lance_nft_item.dice")
    def test_prone_only_first_hit(self, mock_dice):
        """Prone attempt only on first hit per round."""
        mock_dice.roll.return_value = 1
        _set_mastery(self.char1, 5)
        target = _mock_target()
        self.char1.ndb.lance_prone_used = True  # already used this round

        self.lance.at_hit(self.char1, target, 10, "piercing")
        target.apply_prone.assert_not_called()

    @patch("typeclasses.items.weapons.lance_nft_item.dice")
    @patch("combat.combat_utils.get_actor_size")
    def test_no_prone_already_prone(self, mock_get_size, mock_dice):
        """Can't re-prone already prone target."""
        mock_dice.roll.return_value = 1
        mock_get_size.side_effect = _patch_actor_size(ActorSize.MEDIUM)
        _set_mastery(self.char1, 5)
        target = _mock_target()
        target.has_effect = MagicMock(return_value=True)  # already prone

        self.lance.at_hit(self.char1, target, 10, "piercing")
        target.apply_prone.assert_not_called()
