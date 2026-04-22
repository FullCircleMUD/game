"""
Tests for BolaNFTItem — entangle CC weapon.

Validates:
    - Mastery damage override (always 0 bonus)
    - No parries, no extra attacks
    - Entangle on hit via contested DEX roll
    - Entangle miss on lost contested roll
    - HUGE+ targets immune to entangle
    - Save-each-round (STR vs escape DC) success removes entangle
    - Save-each-round failure keeps entangle, decrements duration
    - Max duration safety valve expires entangle
    - Anti-stacking (already entangled → no second entangle)
    - Entangle grants advantage to enemies
    - Entangle causes action denial in combat handler
    - Weapon static attributes

evennia test --settings settings tests.typeclass_tests.test_bola
"""

from unittest.mock import patch, MagicMock

from evennia.utils.test_resources import EvenniaTest
from evennia.utils import create

from enums.mastery_level import MasteryLevel
from enums.named_effect import NamedEffect


def _make_bola(location=None):
    """Create a BolaNFTItem for testing."""
    obj = create.create_object(
        "typeclasses.items.weapons.bola_nft_item.BolaNFTItem",
        key="Test Bola",
        nohome=True,
    )
    if location:
        obj.move_to(location, quiet=True)
    return obj


def _set_mastery(char, level_int):
    """Set char's bola mastery to the given integer level."""
    char.db.weapon_skill_mastery_levels = {"bola": level_int}


# ================================================================== #
#  Mastery Override Tests
# ================================================================== #

class TestBolaMasteryOverrides(EvenniaTest):
    """Test that bola overrides damage bonus, parries, extra attacks."""

    def create_script(self):
        pass

    def test_damage_bonus_always_zero(self):
        """Bola should return 0 mastery damage bonus at all levels."""
        bola = _make_bola()
        for level in range(6):
            _set_mastery(self.char1, level)
            self.assertEqual(bola.get_mastery_damage_bonus(self.char1), 0)

    def test_parries_always_zero(self):
        """Bola should grant 0 parries per round."""
        bola = _make_bola()
        self.assertEqual(bola.get_parries_per_round(self.char1), 0)

    def test_extra_attacks_always_zero(self):
        """Bola should grant 0 extra attacks."""
        bola = _make_bola()
        self.assertEqual(bola.get_extra_attacks(self.char1), 0)

    def test_damage_roll_always_one(self):
        """Bola damage roll should be '1' at all mastery levels."""
        bola = _make_bola()
        for level in MasteryLevel:
            self.assertEqual(bola.get_damage_roll(level), "1")


# ================================================================== #
#  Entangle Application Tests
# ================================================================== #

class TestBolaEntangle(EvenniaTest):
    """Test entangle application via at_hit contested DEX roll."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.bola = _make_bola()
        self.char1.dexterity = 14  # +2 mod
        self.char2.dexterity = 10  # +0 mod
        self.char2.strength = 10  # +0 mod
        self.char2.hp = 100
        self.char2.hp_max = 100

    @patch("typeclasses.items.weapons.bola_nft_item.get_actor_size")
    @patch("typeclasses.items.weapons.bola_nft_item.dice")
    def test_entangle_on_hit(self, mock_dice, mock_size):
        """Winning contested roll should apply ENTANGLED effect."""
        from enums.size import Size
        mock_size.return_value = Size.MEDIUM
        # attacker d20=15, defender d20=8
        mock_dice.roll.side_effect = [15, 8]
        _set_mastery(self.char1, 1)  # BASIC: +0 bonus

        self.bola.at_hit(self.char1, self.char2, 1, "bludgeoning")

        self.assertTrue(self.char2.has_effect("entangled"))

    @patch("typeclasses.items.weapons.bola_nft_item.get_actor_size")
    @patch("typeclasses.items.weapons.bola_nft_item.dice")
    def test_entangle_stores_escape_dc(self, mock_dice, mock_size):
        """Escape DC should equal attacker's total roll."""
        from enums.size import Size
        mock_size.return_value = Size.MEDIUM
        # attacker d20=15 + DEX(+2) + mastery(+2) = 19
        mock_dice.roll.side_effect = [15, 5]
        _set_mastery(self.char1, 2)  # SKILLED: +2 bonus

        self.bola.at_hit(self.char1, self.char2, 1, "bludgeoning")

        effect = self.char2.get_named_effect("entangled")
        self.assertIsNotNone(effect)
        self.assertEqual(effect["save_dc"], 19)  # 15 + 2(DEX) + 2(mastery)

    @patch("typeclasses.items.weapons.bola_nft_item.get_actor_size")
    @patch("typeclasses.items.weapons.bola_nft_item.dice")
    def test_entangle_miss(self, mock_dice, mock_size):
        """Losing contested roll should NOT apply entangle."""
        from enums.size import Size
        mock_size.return_value = Size.MEDIUM
        # attacker d20=5, defender d20=18
        mock_dice.roll.side_effect = [5, 18]
        _set_mastery(self.char1, 1)

        self.bola.at_hit(self.char1, self.char2, 1, "bludgeoning")

        self.assertFalse(self.char2.has_effect("entangled"))

    @patch("typeclasses.items.weapons.bola_nft_item.get_actor_size")
    @patch("typeclasses.items.weapons.bola_nft_item.dice")
    def test_entangle_tie_is_miss(self, mock_dice, mock_size):
        """Tie on contested roll should NOT apply entangle (attacker must win)."""
        from enums.size import Size
        mock_size.return_value = Size.MEDIUM
        # attacker d20=10 + DEX(+2) = 12, defender d20=12 + DEX(+0) = 12
        mock_dice.roll.side_effect = [10, 12]
        _set_mastery(self.char1, 1)  # BASIC: +0 bonus

        self.bola.at_hit(self.char1, self.char2, 1, "bludgeoning")

        self.assertFalse(self.char2.has_effect("entangled"))

    @patch("typeclasses.items.weapons.bola_nft_item.get_actor_size")
    @patch("typeclasses.items.weapons.bola_nft_item.dice")
    def test_entangle_max_rounds_basic(self, mock_dice, mock_size):
        """BASIC entangle should have max 2 rounds."""
        from enums.size import Size
        mock_size.return_value = Size.MEDIUM
        mock_dice.roll.side_effect = [20, 3]
        _set_mastery(self.char1, 1)  # BASIC

        self.bola.at_hit(self.char1, self.char2, 1, "bludgeoning")

        effect = self.char2.get_named_effect("entangled")
        self.assertEqual(effect["duration"], 2)

    @patch("typeclasses.items.weapons.bola_nft_item.get_actor_size")
    @patch("typeclasses.items.weapons.bola_nft_item.dice")
    def test_entangle_max_rounds_gm(self, mock_dice, mock_size):
        """GM entangle should have max 6 rounds."""
        from enums.size import Size
        mock_size.return_value = Size.MEDIUM
        mock_dice.roll.side_effect = [20, 3]
        _set_mastery(self.char1, 5)  # GM

        self.bola.at_hit(self.char1, self.char2, 1, "bludgeoning")

        effect = self.char2.get_named_effect("entangled")
        self.assertEqual(effect["duration"], 6)

    @patch("typeclasses.items.weapons.bola_nft_item.get_actor_size")
    @patch("typeclasses.items.weapons.bola_nft_item.dice")
    def test_at_hit_returns_damage_unchanged(self, mock_dice, mock_size):
        """at_hit should return the original damage value."""
        from enums.size import Size
        mock_size.return_value = Size.MEDIUM
        mock_dice.roll.side_effect = [20, 3]
        _set_mastery(self.char1, 1)
        result = self.bola.at_hit(self.char1, self.char2, 1, "bludgeoning")
        self.assertEqual(result, 1)


# ================================================================== #
#  Size Gate Tests
# ================================================================== #

class TestBolaEntangleSizeGate(EvenniaTest):
    """Test that targets more than 1 size larger than the wielder are immune to entangle."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.bola = _make_bola()
        self.char1.dexterity = 14
        self.char2.dexterity = 10
        self.char2.hp = 100
        self.char2.hp_max = 100

    @patch("typeclasses.items.weapons.bola_nft_item.get_actor_size")
    @patch("typeclasses.items.weapons.bola_nft_item.dice")
    def test_medium_wielder_vs_huge_target_immune(self, mock_dice, mock_size):
        """MEDIUM wielder cannot entangle HUGE target (2 sizes larger)."""
        from enums.size import Size
        mock_size.side_effect = [Size.MEDIUM, Size.HUGE]  # wielder, target
        mock_dice.roll.side_effect = [20, 1]  # would entangle if gate passed
        _set_mastery(self.char1, 1)

        self.bola.at_hit(self.char1, self.char2, 1, "bludgeoning")

        self.assertFalse(self.char2.has_effect("entangled"))

    @patch("typeclasses.items.weapons.bola_nft_item.get_actor_size")
    @patch("typeclasses.items.weapons.bola_nft_item.dice")
    def test_medium_wielder_vs_gargantuan_target_immune(self, mock_dice, mock_size):
        """MEDIUM wielder cannot entangle GARGANTUAN target (3 sizes larger)."""
        from enums.size import Size
        mock_size.side_effect = [Size.MEDIUM, Size.GARGANTUAN]
        mock_dice.roll.side_effect = [20, 1]
        _set_mastery(self.char1, 1)

        self.bola.at_hit(self.char1, self.char2, 1, "bludgeoning")

        self.assertFalse(self.char2.has_effect("entangled"))

    @patch("typeclasses.items.weapons.bola_nft_item.get_actor_size")
    @patch("typeclasses.items.weapons.bola_nft_item.dice")
    def test_medium_wielder_vs_large_target_allowed(self, mock_dice, mock_size):
        """MEDIUM wielder can still entangle LARGE target (only 1 size larger)."""
        from enums.size import Size
        mock_size.side_effect = [Size.MEDIUM, Size.LARGE]
        mock_dice.roll.side_effect = [20, 1]  # attacker wins contest
        _set_mastery(self.char1, 1)

        self.bola.at_hit(self.char1, self.char2, 1, "bludgeoning")

        self.assertTrue(self.char2.has_effect("entangled"))

    @patch("typeclasses.items.weapons.bola_nft_item.get_actor_size")
    @patch("typeclasses.items.weapons.bola_nft_item.dice")
    def test_large_wielder_can_entangle_huge_target(self, mock_dice, mock_size):
        """LARGE wielder (e.g. enlarged) can entangle HUGE target — only 1 size larger."""
        from enums.size import Size
        mock_size.side_effect = [Size.LARGE, Size.HUGE]
        mock_dice.roll.side_effect = [20, 1]  # attacker wins contest
        _set_mastery(self.char1, 1)

        self.bola.at_hit(self.char1, self.char2, 1, "bludgeoning")

        self.assertTrue(self.char2.has_effect("entangled"))


# ================================================================== #
#  Anti-Stacking Tests
# ================================================================== #

class TestBolaAntiStacking(EvenniaTest):
    """Test that entangled target can't be entangled again."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.bola = _make_bola()
        self.char1.dexterity = 14
        self.char2.dexterity = 10
        self.char2.strength = 10
        self.char2.hp = 100
        self.char2.hp_max = 100

    @patch("typeclasses.items.weapons.bola_nft_item.get_actor_size")
    @patch("typeclasses.items.weapons.bola_nft_item.dice")
    def test_already_entangled_no_stack(self, mock_dice, mock_size):
        """Second bola hit should not replace or stack entangle."""
        from enums.size import Size
        mock_size.return_value = Size.MEDIUM

        # First hit: attacker d20=18, defender d20=5 → entangle
        mock_dice.roll.side_effect = [18, 5]
        _set_mastery(self.char1, 2)  # SKILLED
        self.bola.at_hit(self.char1, self.char2, 1, "bludgeoning")
        self.assertTrue(self.char2.has_effect("entangled"))

        # Record original escape DC
        original_dc = self.char2.get_named_effect("entangled")["save_dc"]

        # Second hit: would also win contested roll
        mock_dice.roll.side_effect = [20, 3]
        self.bola.at_hit(self.char1, self.char2, 1, "bludgeoning")

        # Should still have original entangle, not replaced
        effect = self.char2.get_named_effect("entangled")
        self.assertEqual(effect["save_dc"], original_dc)


# ================================================================== #
#  Advantage Grant Tests
# ================================================================== #

class TestBolaAdvantageGrant(EvenniaTest):
    """Test that entangle grants advantage to enemies."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.bola = _make_bola()
        self.char1.dexterity = 14
        self.char2.dexterity = 10
        self.char2.strength = 10
        self.char2.hp = 100
        self.char2.hp_max = 100

    @patch("combat.combat_utils.get_sides")
    @patch("typeclasses.items.weapons.bola_nft_item.get_actor_size")
    @patch("typeclasses.items.weapons.bola_nft_item.dice")
    def test_entangle_grants_advantage(self, mock_dice, mock_size, mock_sides):
        """Entangle should grant advantage to all enemies of the target."""
        from enums.size import Size
        mock_size.return_value = Size.MEDIUM
        mock_dice.roll.side_effect = [18, 5]
        _set_mastery(self.char1, 2)  # SKILLED: max 3 rounds

        mock_handler = MagicMock()
        mock_enemy = MagicMock()
        mock_enemy.scripts.get.return_value = [mock_handler]
        mock_sides.return_value = ([], [mock_enemy])

        self.bola.at_hit(self.char1, self.char2, 1, "bludgeoning")

        mock_handler.set_advantage.assert_called_once_with(self.char2, 3)


# ================================================================== #
#  Save-Each-Round Tests
# ================================================================== #

class TestSaveEachRound(EvenniaTest):
    """Test the save-each-round escape mechanic in tick_combat_round."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.char1.strength = 10  # +0 mod

    def _apply_entangle(self, target, save_dc=15, max_rounds=3):
        """Apply entangled effect directly for testing."""
        target.apply_named_effect(
            key="entangled",
            duration=max_rounds,
            duration_type="combat_rounds",
            messages={
                "start": NamedEffect.ENTANGLED.get_start_message(),
                "end": NamedEffect.ENTANGLED.get_end_message(),
                "start_third": NamedEffect.ENTANGLED.get_start_message_third_person("{name}"),
                "end_third": NamedEffect.ENTANGLED.get_end_message_third_person("{name}"),
            },
            save_dc=save_dc,
            save_stat="strength",
            save_messages={
                "success": "You strain and tear free! (rolled {roll} vs DC {dc})",
                "fail": "You struggle but cannot break free! (rolled {roll} vs DC {dc})",
                "success_third": "{name} strains and tears free!",
                "fail_third": "{name} struggles but cannot break free!",
            },
        )

    @patch("utils.dice_roller.dice")
    def test_save_success_removes_entangle(self, mock_dice):
        """Rolling >= save_dc should remove entangle immediately."""
        self._apply_entangle(self.char1, save_dc=12, max_rounds=4)
        self.assertTrue(self.char1.has_effect("entangled"))

        # STR save: d20=15 + 0(STR mod) = 15 >= DC 12
        mock_dice.roll.return_value = 15
        self.char1.tick_combat_round()

        self.assertFalse(self.char1.has_effect("entangled"))

    @patch("utils.dice_roller.dice")
    def test_save_fail_keeps_entangle(self, mock_dice):
        """Rolling < save_dc should keep entangle and decrement duration."""
        self._apply_entangle(self.char1, save_dc=15, max_rounds=4)

        # STR save: d20=8 + 0 = 8 < DC 15
        mock_dice.roll.return_value = 8
        self.char1.tick_combat_round()

        self.assertTrue(self.char1.has_effect("entangled"))
        effect = self.char1.get_named_effect("entangled")
        self.assertEqual(effect["duration"], 3)  # 4 - 1 = 3

    @patch("utils.dice_roller.dice")
    def test_max_duration_expires(self, mock_dice):
        """Entangle should auto-remove when max duration runs out."""
        self._apply_entangle(self.char1, save_dc=99, max_rounds=2)  # impossible DC

        # First tick: fail save, duration 2→1
        mock_dice.roll.return_value = 5
        self.char1.tick_combat_round()
        self.assertTrue(self.char1.has_effect("entangled"))
        self.assertEqual(self.char1.get_named_effect("entangled")["duration"], 1)

        # Second tick: fail save again, duration 1→0 → expired
        mock_dice.roll.return_value = 5
        self.char1.tick_combat_round()
        self.assertFalse(self.char1.has_effect("entangled"))

    @patch("utils.dice_roller.dice")
    def test_save_with_high_str(self, mock_dice):
        """High STR bonus should help escape."""
        self.char1.strength = 18  # +4 mod
        self._apply_entangle(self.char1, save_dc=15, max_rounds=4)

        # STR save: d20=12 + 4(STR mod) = 16 >= DC 15
        mock_dice.roll.return_value = 12
        self.char1.tick_combat_round()

        self.assertFalse(self.char1.has_effect("entangled"))

    @patch("utils.dice_roller.dice")
    def test_save_does_not_affect_other_effects(self, mock_dice):
        """Non-save effects should tick down normally alongside save effects."""
        # Apply a normal stunned effect (no save_dc)
        self.char1.apply_named_effect(
            key="stunned",
            duration=2,
            duration_type="combat_rounds",
            messages={
                "start": "Stunned!",
                "end": "Recovered!",
            },
        )
        # Apply entangled with save
        self._apply_entangle(self.char1, save_dc=99, max_rounds=3)

        # Tick — save fails for entangle, both should decrement
        mock_dice.roll.return_value = 5
        self.char1.tick_combat_round()

        # Stunned decrements normally (no save involved)
        stun_effect = self.char1.get_named_effect("stunned")
        self.assertIsNotNone(stun_effect)
        self.assertEqual(stun_effect["duration"], 1)

        # Entangled also decrements (save failed)
        entangle_effect = self.char1.get_named_effect("entangled")
        self.assertIsNotNone(entangle_effect)
        self.assertEqual(entangle_effect["duration"], 2)


# ================================================================== #
#  Action Denial Tests (combat handler integration)
# ================================================================== #

class TestEntangleActionDenial(EvenniaTest):
    """Test that entangled targets skip their combat action."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def test_entangled_has_effect(self):
        """Applying entangled named effect should make has_effect return True."""
        self.char1.apply_named_effect(
            key="entangled",
            duration=3,
            duration_type="combat_rounds",
            messages={
                "start": NamedEffect.ENTANGLED.get_start_message(),
                "end": NamedEffect.ENTANGLED.get_end_message(),
            },
            save_dc=15,
            save_stat="strength",
            save_messages={},
        )
        self.assertTrue(self.char1.has_effect("entangled"))

    def test_entangled_cleared_on_combat_end(self):
        """Entangled effect should be cleared by clear_combat_effects."""
        self.char1.apply_named_effect(
            key="entangled",
            duration=3,
            duration_type="combat_rounds",
            messages={
                "start": NamedEffect.ENTANGLED.get_start_message(),
                "end": NamedEffect.ENTANGLED.get_end_message(),
            },
            save_dc=15,
            save_stat="strength",
            save_messages={},
        )
        self.assertTrue(self.char1.has_effect("entangled"))

        self.char1.clear_combat_effects()
        self.assertFalse(self.char1.has_effect("entangled"))


# ================================================================== #
#  Weapon Attributes Tests
# ================================================================== #

class TestBolaAttributes(EvenniaTest):
    """Test BolaNFTItem static attributes."""

    def create_script(self):
        pass

    def test_weapon_type_key(self):
        """weapon_type_key should be 'bola'."""
        bola = _make_bola()
        self.assertEqual(bola.weapon_type_key, "bola")

    def test_weapon_type_ranged(self):
        """weapon_type should be 'ranged'."""
        bola = _make_bola()
        self.assertEqual(bola.weapon_type, "ranged")

    def test_damage_type_bludgeoning(self):
        """damage_type should be BLUDGEONING."""
        from enums.unused_for_reference.damage_type import DamageType
        bola = _make_bola()
        self.assertEqual(bola.damage_type, DamageType.BLUDGEONING)

    def test_is_finesse(self):
        """Bola should be finesse."""
        bola = _make_bola()
        self.assertTrue(bola.is_finesse)

    def test_not_two_handed(self):
        """Bola should be one-handed."""
        bola = _make_bola()
        self.assertFalse(bola.two_handed)

    def test_has_bola_tag(self):
        """Bola should have 'bola' weapon_type tag."""
        bola = _make_bola()
        self.assertTrue(bola.tags.has("bola", category="weapon_type"))
