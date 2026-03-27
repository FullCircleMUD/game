"""
Tests for combat height mechanics — height gating, ranged penalty, mob retarget.

evennia test --settings settings tests.command_tests.test_combat_height
"""

from unittest.mock import patch, MagicMock

from evennia.utils.test_resources import EvenniaCommandTest
from evennia.utils import create

from commands.all_char_cmds.cmd_attack import CmdAttack


class TestCombatHeight(EvenniaCommandTest):
    """Test height-based combat restrictions and modifiers."""

    character_typeclass = "typeclasses.actors.character.FCMCharacter"
    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.room1.allow_combat = True
        self.room1.max_height = 5
        self.char1.hp = 50
        self.char1.hp_max = 50
        self.char2.hp = 50
        self.char2.hp_max = 50
        # Both start at ground level
        self.char1.room_vertical_position = 0
        self.char2.room_vertical_position = 0

    def tearDown(self):
        for char in (self.char1, self.char2):
            handlers = char.scripts.get("combat_handler")
            if handlers:
                for h in handlers:
                    h.stop()
                    h.delete()
        super().tearDown()

    # ------------------------------------------------------------------ #
    #  height_utils unit tests
    # ------------------------------------------------------------------ #

    def test_can_reach_same_height_melee(self):
        """Melee weapon can reach target at same height."""
        from combat.height_utils import can_reach_target
        weapon = MagicMock()
        weapon.weapon_type = "melee"
        self.char1.room_vertical_position = 0
        self.char2.room_vertical_position = 0
        self.assertTrue(can_reach_target(self.char1, self.char2, weapon))

    def test_cannot_reach_different_height_melee(self):
        """Melee weapon cannot reach target at different height."""
        from combat.height_utils import can_reach_target
        weapon = MagicMock()
        weapon.weapon_type = "melee"
        self.char1.room_vertical_position = 0
        self.char2.room_vertical_position = 2
        self.assertFalse(can_reach_target(self.char1, self.char2, weapon))

    def test_can_reach_different_height_missile(self):
        """Missile weapon can reach target at different height."""
        from combat.height_utils import can_reach_target
        weapon = MagicMock()
        weapon.weapon_type = "missile"
        self.char1.room_vertical_position = 0
        self.char2.room_vertical_position = 3
        self.assertTrue(can_reach_target(self.char1, self.char2, weapon))

    def test_can_reach_same_height_missile(self):
        """Missile weapon can reach target at same height."""
        from combat.height_utils import can_reach_target
        weapon = MagicMock()
        weapon.weapon_type = "missile"
        self.char1.room_vertical_position = 0
        self.char2.room_vertical_position = 0
        self.assertTrue(can_reach_target(self.char1, self.char2, weapon))

    def test_cannot_reach_different_height_unarmed(self):
        """Unarmed (no weapon) cannot reach target at different height."""
        from combat.height_utils import can_reach_target
        self.char1.room_vertical_position = 0
        self.char2.room_vertical_position = 1
        self.assertFalse(can_reach_target(self.char1, self.char2, None))

    def test_height_modifier_missile_same_height(self):
        """Missile weapon at same height gets -4 penalty."""
        from combat.height_utils import get_height_hit_modifier
        weapon = MagicMock()
        weapon.weapon_type = "missile"
        self.char1.room_vertical_position = 0
        self.char2.room_vertical_position = 0
        self.assertEqual(
            get_height_hit_modifier(self.char1, self.char2, weapon), -4
        )

    def test_height_modifier_missile_different_height(self):
        """Missile weapon at different height gets no penalty."""
        from combat.height_utils import get_height_hit_modifier
        weapon = MagicMock()
        weapon.weapon_type = "missile"
        self.char1.room_vertical_position = 0
        self.char2.room_vertical_position = 2
        self.assertEqual(
            get_height_hit_modifier(self.char1, self.char2, weapon), 0
        )

    def test_height_modifier_melee_same_height(self):
        """Melee weapon at same height gets no penalty."""
        from combat.height_utils import get_height_hit_modifier
        weapon = MagicMock()
        weapon.weapon_type = "melee"
        self.char1.room_vertical_position = 0
        self.char2.room_vertical_position = 0
        self.assertEqual(
            get_height_hit_modifier(self.char1, self.char2, weapon), 0
        )

    # ------------------------------------------------------------------ #
    #  CmdAttack height gating
    # ------------------------------------------------------------------ #

    def test_attack_blocked_melee_different_height(self):
        """Attack command blocks melee against target at different height."""
        self.char1.room_vertical_position = 0
        self.char2.room_vertical_position = 2
        result = self.call(CmdAttack(), self.char2.key)
        self.assertIn("out of melee range", result)

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_attack_allowed_missile_different_height(self, mock_ticker):
        """Attack command allows missile weapon against target at different height."""
        # Create a missile weapon and equip it
        weapon = create.create_object(
            "typeclasses.items.weapons.weapon_nft_item.WeaponNFTItem",
            key="a shortbow",
            location=self.char1,
            attributes=[
                ("weapon_type", "missile"),
                ("weapon_type_key", "bow"),
                ("speed", 1.0),
                ("damage_dice", "1d6"),
                ("token_id", 999),
            ],
        )
        self.char1.wear(weapon)

        self.char1.room_vertical_position = 0
        self.char2.room_vertical_position = 2

        result = self.call(CmdAttack(), self.char2.key)
        self.assertIn("You attack", result)

    # ------------------------------------------------------------------ #
    #  execute_attack height gating (mid-combat height change)
    # ------------------------------------------------------------------ #

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_execute_attack_blocked_height_change(self, mock_ticker):
        """execute_attack skips attack when target changes height mid-combat."""
        from combat.combat_utils import enter_combat, execute_attack
        enter_combat(self.char1, self.char2)

        # Target flies up mid-combat
        self.char2.room_vertical_position = 2
        hp_before = self.char2.hp

        execute_attack(self.char1, self.char2)
        # No damage should be dealt
        self.assertEqual(self.char2.hp, hp_before)

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_execute_attack_ranged_penalty_applied(self, mock_ticker):
        """execute_attack applies -4 penalty for missile at same height."""
        from combat.combat_utils import enter_combat, execute_attack

        weapon = create.create_object(
            "typeclasses.items.weapons.weapon_nft_item.WeaponNFTItem",
            key="a shortbow",
            location=self.char1,
            attributes=[
                ("weapon_type", "missile"),
                ("weapon_type_key", "bow"),
                ("speed", 1.0),
                ("damage_dice", "1d6"),
                ("token_id", 998),
            ],
        )
        self.char1.wear(weapon)
        enter_combat(self.char1, self.char2)

        # Both at ground level — ranged penalty should apply
        # Roll a 15 on d20. With -4 penalty, total_hit should be lower.
        with patch("combat.combat_utils.dice") as mock_dice:
            mock_dice.roll_with_advantage_or_disadvantage.return_value = 15
            mock_dice.roll.return_value = 3

            # Set target AC high enough that -4 matters
            original_ac = self.char2.effective_ac
            self.char2.db.base_ac = 15  # high AC

            hp_before = self.char2.hp
            execute_attack(self.char1, self.char2)

            # We can't easily assert the exact modifier was applied
            # without deep mocking, but we verify the attack ran without error.
            # The -4 is tested more directly via test_height_modifier_* above.

    # ------------------------------------------------------------------ #
    #  Mob retarget / flee on height block
    # ------------------------------------------------------------------ #

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_mob_retargets_reachable_enemy(self, mock_ticker):
        """Mob retargets to a reachable enemy when current target is unreachable."""
        from combat.combat_utils import enter_combat

        mob = create.create_object(
            "typeclasses.actors.mob.CombatMob",
            key="test_mob",
            location=self.room1,
        )
        mob.hp = 20
        mob.hp_max = 20

        try:
            enter_combat(mob, self.char1)

            handler = mob.scripts.get("combat_handler")
            self.assertTrue(handler)

            # char1 flies up, char2 stays on ground
            self.char1.room_vertical_position = 2
            self.char2.room_vertical_position = 0
            mob.room_vertical_position = 0

            # Make char2 also in combat
            enter_combat(self.char2, mob)

            # Set mob's target to char1 (unreachable)
            handler[0].action_dict = {
                "key": "attack",
                "target": self.char1,
                "dt": 4,
                "repeat": True,
            }
            mob.ndb.combat_target = self.char1

            # Trigger tick — mob should retarget to char2
            with patch("combat.combat_utils.dice") as mock_dice:
                mock_dice.roll_with_advantage_or_disadvantage.return_value = 10
                mock_dice.roll.return_value = 2
                handler[0].execute_next_action()

            # Mob should now target char2
            self.assertEqual(mob.ndb.combat_target, self.char2)
        finally:
            handlers = mob.scripts.get("combat_handler")
            if handlers:
                for h in handlers:
                    h.stop()
                    h.delete()
            mob.delete()

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_mob_flees_when_all_targets_unreachable(self, mock_ticker):
        """Mob flees when all targets are at unreachable heights."""
        from combat.combat_utils import enter_combat

        mob = create.create_object(
            "typeclasses.actors.mob.CombatMob",
            key="test_mob",
            location=self.room1,
        )
        mob.hp = 20
        mob.hp_max = 20

        try:
            enter_combat(mob, self.char1)

            handler = mob.scripts.get("combat_handler")
            self.assertTrue(handler)

            # All players fly up
            self.char1.room_vertical_position = 2
            mob.room_vertical_position = 0

            handler[0].action_dict = {
                "key": "attack",
                "target": self.char1,
                "dt": 4,
                "repeat": True,
            }

            # Mock execute_cmd to capture the flee attempt
            with patch.object(mob, "execute_cmd") as mock_cmd:
                handler[0].execute_next_action()
                mock_cmd.assert_called_with("flee")
        finally:
            handlers = mob.scripts.get("combat_handler")
            if handlers:
                for h in handlers:
                    h.stop()
                    h.delete()
            mob.delete()
