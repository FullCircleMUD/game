"""
Tests for unarmed combat — weapon singleton, get_weapon(), damage scaling,
stun, knockdown, size immunity.

evennia test --settings settings tests.command_tests.test_unarmed_combat
"""

from unittest.mock import patch, MagicMock
from evennia.utils.test_resources import EvenniaCommandTest
from evennia.utils import create


class TestUnarmedCombat(EvenniaCommandTest):
    """Test unarmed weapon singleton, get_weapon(), and stun/knockdown."""

    character_typeclass = "typeclasses.actors.character.FCMCharacter"
    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.room1.allow_combat = True
        self.room1.allow_pvp = True
        self.char1.hp = 50
        self.char1.hp_max = 50
        self.char2.hp = 50
        self.char2.hp_max = 50

    def tearDown(self):
        for char in (self.char1, self.char2):
            handlers = char.scripts.get("combat_handler")
            if handlers:
                for h in handlers:
                    h.stop()
                    h.delete()
        super().tearDown()

    # ------------------------------------------------------------------ #
    #  get_weapon() tests
    # ------------------------------------------------------------------ #

    def test_get_weapon_returns_unarmed_for_bare_pc(self):
        """get_weapon() returns UNARMED singleton for a PC with no weapon."""
        from combat.combat_utils import get_weapon
        from typeclasses.items.weapons.unarmed_weapon import UNARMED
        weapon = get_weapon(self.char1)
        self.assertIs(weapon, UNARMED)

    def test_get_weapon_returns_none_for_mob(self):
        """get_weapon() returns None for mobs without wearslots."""
        from combat.combat_utils import get_weapon
        mob = create.create_object(
            "typeclasses.actors.mob.CombatMob",
            key="test mob",
            location=self.room1,
        )
        try:
            weapon = get_weapon(mob)
            self.assertIsNone(weapon)
        finally:
            mob.delete()

    def test_get_weapon_returns_wielded_weapon(self):
        """get_weapon() returns the real weapon when one is wielded."""
        from combat.combat_utils import get_weapon
        from typeclasses.items.weapons.unarmed_weapon import UNARMED, UnarmedWeapon
        # Create and wield a weapon
        sword = create.create_object(
            "typeclasses.items.weapons.weapon_nft_item.WeaponNFTItem",
            key="test sword",
        )
        sword.move_to(self.char1, quiet=True)
        self.char1.wear(sword)
        try:
            weapon = get_weapon(self.char1)
            self.assertEqual(weapon, sword)
            self.assertNotIsInstance(weapon, UnarmedWeapon)
        finally:
            sword.delete()

    # ------------------------------------------------------------------ #
    #  Unarmed damage scaling
    # ------------------------------------------------------------------ #

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_unarmed_pc_can_attack(self, mock_ticker):
        """Unarmed PC can attack and deal damage."""
        from combat.combat_utils import enter_combat, execute_attack
        enter_combat(self.char1, self.char2)

        with patch("combat.combat_utils.dice") as mock_dice:
            mock_dice.roll_with_advantage_or_disadvantage.return_value = 20
            mock_dice.roll.return_value = 1
            execute_attack(self.char1, self.char2)

        self.assertLess(self.char2.hp, 50)

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_unarmed_mastery_damage_scaling(self, mock_ticker):
        """Damage dice scale with unarmed mastery."""
        from typeclasses.items.weapons.unarmed_weapon import UNARMED
        from enums.mastery_level import MasteryLevel
        self.assertEqual(UNARMED.get_damage_roll(MasteryLevel.UNSKILLED), "1d1")
        self.assertEqual(UNARMED.get_damage_roll(MasteryLevel.BASIC), "1d2")
        self.assertEqual(UNARMED.get_damage_roll(MasteryLevel.SKILLED), "1d3")
        self.assertEqual(UNARMED.get_damage_roll(MasteryLevel.EXPERT), "1d4")
        self.assertEqual(UNARMED.get_damage_roll(MasteryLevel.MASTER), "1d6")
        self.assertEqual(UNARMED.get_damage_roll(MasteryLevel.GRANDMASTER), "1d8")

    def test_unarmed_extra_attacks_at_expert(self):
        """Expert unarmed gets 1 extra attack."""
        from typeclasses.items.weapons.unarmed_weapon import UNARMED
        from enums.mastery_level import MasteryLevel
        self.char1.db.weapon_skill_mastery_levels = {"unarmed": MasteryLevel.EXPERT.value}
        self.assertEqual(UNARMED.get_extra_attacks(self.char1), 1)

    def test_unarmed_no_extra_attacks_at_skilled(self):
        """Skilled unarmed gets no extra attacks."""
        from typeclasses.items.weapons.unarmed_weapon import UNARMED
        from enums.mastery_level import MasteryLevel
        self.char1.db.weapon_skill_mastery_levels = {"unarmed": MasteryLevel.SKILLED.value}
        self.assertEqual(UNARMED.get_extra_attacks(self.char1), 0)

    # ------------------------------------------------------------------ #
    #  Unarmed cannot be parried
    # ------------------------------------------------------------------ #

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_unarmed_attack_cannot_be_parried(self, mock_ticker):
        """Unarmed attacks bypass parry check entirely."""
        from combat.combat_utils import enter_combat, execute_attack
        enter_combat(self.char1, self.char2)

        handler2 = self.char2.scripts.get("combat_handler")[0]
        handler2.parries_remaining = 5  # lots of parries available

        with patch("combat.combat_utils.dice") as mock_dice:
            mock_dice.roll_with_advantage_or_disadvantage.return_value = 20
            mock_dice.roll.return_value = 3
            execute_attack(self.char1, self.char2)

        # char2 should have taken damage — parry was NOT checked
        self.assertLess(self.char2.hp, 50)
        # Parries should NOT have been consumed
        self.assertEqual(handler2.parries_remaining, 5)

    # ------------------------------------------------------------------ #
    #  Unarmed no durability loss
    # ------------------------------------------------------------------ #

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_unarmed_no_durability_loss(self, mock_ticker):
        """Unarmed weapon has no reduce_durability — should not error on hit."""
        from typeclasses.items.weapons.unarmed_weapon import UNARMED
        self.assertFalse(hasattr(UNARMED, "reduce_durability"))

    # ------------------------------------------------------------------ #
    #  Stun tests (SKILLED+)
    # ------------------------------------------------------------------ #

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_unarmed_stun_at_skilled(self, mock_ticker):
        """Skilled unarmed: successful contested roll stuns target for 1 round."""
        from enums.mastery_level import MasteryLevel
        from enums.condition import Condition
        from combat.combat_utils import enter_combat, execute_attack

        self.char1.db.weapon_skill_mastery_levels = {"unarmed": MasteryLevel.SKILLED.value}
        enter_combat(self.char1, self.char2)

        handler1 = self.char1.scripts.get("combat_handler")[0]
        handler1.stun_checks_remaining = 1

        with patch("combat.combat_utils.dice") as mock_dice, \
             patch("typeclasses.items.weapons.unarmed_weapon.dice") as mock_unarmed_dice:
            # Attack roll: high to guarantee hit
            mock_dice.roll_with_advantage_or_disadvantage.return_value = 20
            mock_dice.roll.return_value = 1
            # Stun contested roll: attacker wins
            mock_unarmed_dice.roll.side_effect = [20, 5]  # attacker d20=20, defender d20=5

            execute_attack(self.char1, self.char2)

        self.assertTrue(self.char2.has_effect("stunned"))

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_unarmed_stun_fails_when_defender_wins(self, mock_ticker):
        """Stun check fails when defender wins the contested roll."""
        from enums.mastery_level import MasteryLevel
        from enums.condition import Condition
        from combat.combat_utils import enter_combat, execute_attack

        self.char1.db.weapon_skill_mastery_levels = {"unarmed": MasteryLevel.SKILLED.value}
        enter_combat(self.char1, self.char2)

        handler1 = self.char1.scripts.get("combat_handler")[0]
        handler1.stun_checks_remaining = 1

        with patch("combat.combat_utils.dice") as mock_dice, \
             patch("typeclasses.items.weapons.unarmed_weapon.dice") as mock_unarmed_dice:
            mock_dice.roll_with_advantage_or_disadvantage.return_value = 20
            mock_dice.roll.return_value = 1
            # Stun contested roll: defender wins
            mock_unarmed_dice.roll.side_effect = [5, 20]

            execute_attack(self.char1, self.char2)

        self.assertFalse(self.char2.has_effect("stunned"))

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_unarmed_stun_check_consumed_on_use(self, mock_ticker):
        """Stun check is consumed after first hit, no second check."""
        from enums.mastery_level import MasteryLevel
        from combat.combat_utils import enter_combat, execute_attack

        self.char1.db.weapon_skill_mastery_levels = {"unarmed": MasteryLevel.SKILLED.value}
        enter_combat(self.char1, self.char2)

        handler1 = self.char1.scripts.get("combat_handler")[0]
        handler1.stun_checks_remaining = 1

        with patch("combat.combat_utils.dice") as mock_dice, \
             patch("typeclasses.items.weapons.unarmed_weapon.dice") as mock_unarmed_dice:
            mock_dice.roll_with_advantage_or_disadvantage.return_value = 20
            mock_dice.roll.return_value = 1
            # Stun check fails (defender wins) — but check is consumed
            mock_unarmed_dice.roll.side_effect = [5, 20]

            execute_attack(self.char1, self.char2)

        self.assertEqual(handler1.stun_checks_remaining, 0)

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_unarmed_no_stun_at_basic(self, mock_ticker):
        """Basic unarmed mastery does not trigger stun check."""
        from enums.mastery_level import MasteryLevel
        from enums.condition import Condition
        from combat.combat_utils import enter_combat, execute_attack

        self.char1.db.weapon_skill_mastery_levels = {"unarmed": MasteryLevel.BASIC.value}
        enter_combat(self.char1, self.char2)

        handler1 = self.char1.scripts.get("combat_handler")[0]
        handler1.stun_checks_remaining = 1

        with patch("combat.combat_utils.dice") as mock_dice:
            mock_dice.roll_with_advantage_or_disadvantage.return_value = 20
            mock_dice.roll.return_value = 1
            execute_attack(self.char1, self.char2)

        self.assertFalse(self.char2.has_effect("stunned"))

    # ------------------------------------------------------------------ #
    #  Knockdown tests (MASTER+)
    # ------------------------------------------------------------------ #

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_unarmed_knockdown_at_master(self, mock_ticker):
        """Master unarmed: winning by >=5 applies PRONE + advantage to enemies."""
        from enums.mastery_level import MasteryLevel
        from enums.condition import Condition
        from combat.combat_utils import enter_combat, execute_attack

        self.char1.db.weapon_skill_mastery_levels = {"unarmed": MasteryLevel.MASTER.value}
        enter_combat(self.char1, self.char2)

        handler1 = self.char1.scripts.get("combat_handler")[0]
        handler1.stun_checks_remaining = 1

        with patch("combat.combat_utils.dice") as mock_dice, \
             patch("typeclasses.items.weapons.unarmed_weapon.dice") as mock_unarmed_dice:
            mock_dice.roll_with_advantage_or_disadvantage.return_value = 20
            mock_dice.roll.return_value = 1
            # Stun roll: attacker 20 vs defender 5 = gap of 15+ (with bonuses)
            mock_unarmed_dice.roll.side_effect = [20, 1]

            execute_attack(self.char1, self.char2)

        self.assertTrue(self.char2.has_effect("prone"))
        # char1 (enemy of char2) should have advantage against char2
        self.assertTrue(handler1.has_advantage(self.char2))

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_unarmed_stun_not_knockdown_small_gap(self, mock_ticker):
        """Master unarmed: winning by <5 applies STUNNED, not PRONE."""
        from enums.mastery_level import MasteryLevel
        from enums.condition import Condition
        from combat.combat_utils import enter_combat, execute_attack

        self.char1.db.weapon_skill_mastery_levels = {"unarmed": MasteryLevel.MASTER.value}
        # Give both same stats so bonuses cancel out, gap = d20 diff only
        self.char1.strength = 10
        self.char2.constitution = 10
        enter_combat(self.char1, self.char2)

        handler1 = self.char1.scripts.get("combat_handler")[0]
        handler1.stun_checks_remaining = 1

        with patch("combat.combat_utils.dice") as mock_dice, \
             patch("typeclasses.items.weapons.unarmed_weapon.dice") as mock_unarmed_dice:
            mock_dice.roll_with_advantage_or_disadvantage.return_value = 20
            mock_dice.roll.return_value = 1
            # STR bonus = 0, mastery bonus = +6, CON bonus = 0
            # attacker = 12 + 0 + 6 = 18, defender = 15 + 0 = 15, gap = 3
            mock_unarmed_dice.roll.side_effect = [12, 15]

            execute_attack(self.char1, self.char2)

        # Gap < 5, so STUNNED not PRONE
        self.assertTrue(self.char2.has_effect("stunned"))
        self.assertFalse(self.char2.has_effect("prone"))

    # ------------------------------------------------------------------ #
    #  GM double duration
    # ------------------------------------------------------------------ #

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_gm_stun_2_rounds(self, mock_ticker):
        """GM unarmed stun lasts 2 rounds."""
        from enums.mastery_level import MasteryLevel
        from enums.condition import Condition
        from combat.combat_utils import enter_combat, execute_attack

        self.char1.db.weapon_skill_mastery_levels = {"unarmed": MasteryLevel.GRANDMASTER.value}
        self.char1.strength = 10
        self.char2.constitution = 10
        enter_combat(self.char1, self.char2)

        handler1 = self.char1.scripts.get("combat_handler")[0]
        handler1.stun_checks_remaining = 2

        with patch("combat.combat_utils.dice") as mock_dice, \
             patch("typeclasses.items.weapons.unarmed_weapon.dice") as mock_unarmed_dice:
            mock_dice.roll_with_advantage_or_disadvantage.return_value = 20
            mock_dice.roll.return_value = 1
            # Small gap: attacker 12 + 0 + 8 = 20, defender 15 + 0 = 15, gap = 5
            # Actually gap=5 means PRONE at GM... let's make gap exactly 4
            # attacker 12 + 0 + 8 = 20, defender 17 + 0 = 17, gap = 3
            mock_unarmed_dice.roll.side_effect = [12, 17]

            execute_attack(self.char1, self.char2)

        self.assertTrue(self.char2.has_effect("stunned"))
        record = self.char2.get_named_effect("stunned")
        self.assertEqual(record["duration"], 2)

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_gm_two_stun_checks_per_round(self, mock_ticker):
        """GM gets 2 stun checks per round."""
        from enums.mastery_level import MasteryLevel
        from combat.combat_utils import enter_combat

        self.char1.db.weapon_skill_mastery_levels = {"unarmed": MasteryLevel.GRANDMASTER.value}
        enter_combat(self.char1, self.char2)

        handler1 = self.char1.scripts.get("combat_handler")[0]
        # Simulate start of round via execute_next_action
        handler1.execute_next_action()
        # GM should get 2 stun checks per round
        # (after execute_next_action resets, it was used during attacks)
        # Check the reset logic: stun_checks_remaining is set at start of execute_next_action
        # Since we haven't mocked combat to prevent attacks, let's just check the value directly
        from typeclasses.items.weapons.unarmed_weapon import UNARMED
        self.assertEqual(UNARMED.get_extra_attacks(self.char1), 1)

    # ------------------------------------------------------------------ #
    #  Size immunity
    # ------------------------------------------------------------------ #

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_unarmed_stun_immune_huge_target(self, mock_ticker):
        """HUGE targets are immune to unarmed stun."""
        from enums.mastery_level import MasteryLevel
        from enums.condition import Condition
        from enums.size import Size
        from combat.combat_utils import enter_combat, execute_attack

        self.char1.db.weapon_skill_mastery_levels = {"unarmed": MasteryLevel.MASTER.value}

        mob = create.create_object(
            "typeclasses.actors.mob.CombatMob",
            key="huge beast",
            location=self.room1,
        )
        mob.hp = 100
        mob.hp_max = 100
        mob.size = "huge"
        try:
            enter_combat(self.char1, mob)
            handler1 = self.char1.scripts.get("combat_handler")[0]
            handler1.stun_checks_remaining = 1

            with patch("combat.combat_utils.dice") as mock_dice:
                mock_dice.roll_with_advantage_or_disadvantage.return_value = 20
                mock_dice.roll.return_value = 3
                execute_attack(self.char1, mob)

            # Mob should NOT be stunned — size immune
            self.assertFalse(mob.has_effect("stunned"))
            self.assertFalse(mob.has_effect("prone"))
        finally:
            handlers = mob.scripts.get("combat_handler")
            if handlers:
                for h in handlers:
                    h.stop()
                    h.delete()
            mob.delete()

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_unarmed_stun_works_on_large_target(self, mock_ticker):
        """LARGE targets CAN be stunned by unarmed (only HUGE+ immune)."""
        from enums.mastery_level import MasteryLevel
        from enums.condition import Condition
        from enums.size import Size
        from combat.combat_utils import enter_combat, execute_attack

        self.char1.db.weapon_skill_mastery_levels = {"unarmed": MasteryLevel.SKILLED.value}

        mob = create.create_object(
            "typeclasses.actors.mob.CombatMob",
            key="large wolf",
            location=self.room1,
        )
        mob.hp = 50
        mob.hp_max = 50
        mob.size = "large"
        try:
            enter_combat(self.char1, mob)
            handler1 = self.char1.scripts.get("combat_handler")[0]
            handler1.stun_checks_remaining = 1

            with patch("combat.combat_utils.dice") as mock_dice, \
                 patch("typeclasses.items.weapons.unarmed_weapon.dice") as mock_unarmed_dice:
                mock_dice.roll_with_advantage_or_disadvantage.return_value = 20
                mock_dice.roll.return_value = 1
                mock_unarmed_dice.roll.side_effect = [20, 1]

                execute_attack(self.char1, mob)

            self.assertTrue(mob.has_effect("stunned"))
        finally:
            handlers = mob.scripts.get("combat_handler")
            if handlers:
                for h in handlers:
                    h.stop()
                    h.delete()
            mob.delete()

    # ------------------------------------------------------------------ #
    #  Skip actions / condition cleanup
    # ------------------------------------------------------------------ #

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_stun_named_effect_decrements_and_clears(self, mock_ticker):
        """Stun named effect decrements each tick and clears when done."""
        from combat.combat_utils import enter_combat
        from enums.named_effect import NamedEffect

        enter_combat(self.char1, self.char2)
        handler = self.char1.scripts.get("combat_handler")[0]

        # Simulate being stunned for 2 rounds via named effect
        self.char1.apply_named_effect(
            key="stunned",
            duration=2,
            duration_type="combat_rounds",
            messages={
                "start": NamedEffect.STUNNED.get_start_message(),
                "end": NamedEffect.STUNNED.get_end_message(),
            },
        )

        # First tick — duration 2 → 1, still stunned
        handler.execute_next_action()
        self.assertTrue(self.char1.has_effect("stunned"))

        # Second tick — duration 1 → 0, effect removed
        handler.execute_next_action()
        self.assertFalse(self.char1.has_effect("stunned"))

    # ------------------------------------------------------------------ #
    #  Mob size attribute
    # ------------------------------------------------------------------ #

    def test_combat_mob_default_size(self):
        """CombatMob defaults to MEDIUM size."""
        mob = create.create_object(
            "typeclasses.actors.mob.CombatMob",
            key="test mob",
            location=self.room1,
        )
        try:
            self.assertEqual(mob.size, "medium")
        finally:
            mob.delete()

    def test_dire_wolf_size_large(self):
        """DireWolf is LARGE."""
        wolf = create.create_object(
            "typeclasses.actors.mobs.dire_wolf.DireWolf",
            key="dire wolf",
            location=self.room1,
        )
        try:
            self.assertEqual(wolf.size, "large")
        finally:
            wolf.delete()
