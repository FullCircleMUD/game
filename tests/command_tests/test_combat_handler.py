"""
Tests for CombatHandler script and combat utility functions.

evennia test --settings settings tests.command_tests.test_combat_handler
"""

from unittest.mock import patch, MagicMock
from evennia.utils.test_resources import EvenniaCommandTest
from evennia.utils import create


class TestCombatHandler(EvenniaCommandTest):
    """Test the combat handler script."""

    character_typeclass = "typeclasses.actors.character.FCMCharacter"
    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.room1.allow_combat = True
        self.char1.hp = 20
        self.char1.hp_max = 20
        self.char2.hp = 20
        self.char2.hp_max = 20

    def tearDown(self):
        for char in (self.char1, self.char2):
            handlers = char.scripts.get("combat_handler")
            if handlers:
                for h in handlers:
                    h.stop()
                    h.delete()
        super().tearDown()

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_handler_created_on_combat(self, mock_ticker):
        """Combat handler created when entering combat."""
        from combat.combat_utils import enter_combat
        enter_combat(self.char1, self.char2)
        self.assertTrue(self.char1.scripts.get("combat_handler"))
        self.assertTrue(self.char2.scripts.get("combat_handler"))

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_advantage_tracking(self, mock_ticker):
        """Advantage can be set with round counts and checked."""
        from combat.combat_utils import enter_combat
        enter_combat(self.char1, self.char2)
        handler = self.char1.scripts.get("combat_handler")[0]

        self.assertFalse(handler.has_advantage(self.char2))
        handler.set_advantage(self.char2, rounds=3)
        self.assertTrue(handler.has_advantage(self.char2))
        self.assertEqual(handler.advantage_against[self.char2.id], 3)
        handler.set_advantage(self.char2, rounds=0)
        self.assertFalse(handler.has_advantage(self.char2))

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_advantage_takes_max(self, mock_ticker):
        """set_advantage takes max of existing and new count."""
        from combat.combat_utils import enter_combat
        enter_combat(self.char1, self.char2)
        handler = self.char1.scripts.get("combat_handler")[0]

        handler.set_advantage(self.char2, rounds=3)
        handler.set_advantage(self.char2, rounds=1)
        self.assertEqual(handler.advantage_against[self.char2.id], 3)
        handler.set_advantage(self.char2, rounds=5)
        self.assertEqual(handler.advantage_against[self.char2.id], 5)

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_disadvantage_tracking(self, mock_ticker):
        """Disadvantage can be set with round counts and checked."""
        from combat.combat_utils import enter_combat
        enter_combat(self.char1, self.char2)
        handler = self.char1.scripts.get("combat_handler")[0]

        self.assertFalse(handler.has_disadvantage(self.char2))
        handler.set_disadvantage(self.char2, rounds=2)
        self.assertTrue(handler.has_disadvantage(self.char2))
        self.assertEqual(handler.disadvantage_against[self.char2.id], 2)
        handler.set_disadvantage(self.char2, rounds=0)
        self.assertFalse(handler.has_disadvantage(self.char2))

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_skip_next_action(self, mock_ticker):
        """skip_next_action flag skips one tick then clears."""
        from combat.combat_utils import enter_combat
        self.room1.allow_pvp = True  # PvP so PCs are enemies, combat persists
        enter_combat(self.char1, self.char2)
        handler = self.char1.scripts.get("combat_handler")[0]
        handler.queue_action({
            "key": "attack",
            "target": self.char2,
            "dt": 3,
            "repeat": True,
        })
        handler.skip_next_action = True

        # First tick should skip (no damage dealt)
        hp_before = self.char2.hp
        handler.execute_next_action()
        self.assertEqual(self.char2.hp, hp_before)
        self.assertFalse(handler.skip_next_action)

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_execute_action_attack(self, mock_ticker):
        """execute_next_action resolves attack against target."""
        from combat.combat_utils import enter_combat
        enter_combat(self.char1, self.char2)
        handler = self.char1.scripts.get("combat_handler")[0]
        handler.queue_action({
            "key": "attack",
            "target": self.char2,
            "dt": 3,
            "repeat": True,
        })

        # Patch dice to guarantee hit
        with patch("combat.combat_utils.dice") as mock_dice:
            mock_dice.roll_with_advantage_or_disadvantage.return_value = 20
            mock_dice.roll.return_value = 5
            handler.execute_next_action()

        # char2 should have taken damage
        self.assertLess(self.char2.hp, 20)


class TestCombatUtils(EvenniaCommandTest):
    """Test combat utility functions."""

    character_typeclass = "typeclasses.actors.character.FCMCharacter"
    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.room1.allow_combat = True
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

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_enter_combat_creates_handlers(self, mock_ticker):
        """enter_combat creates handlers on both combatants."""
        from combat.combat_utils import enter_combat
        result = enter_combat(self.char1, self.char2)
        self.assertTrue(result)
        self.assertTrue(self.char1.scripts.get("combat_handler"))
        self.assertTrue(self.char2.scripts.get("combat_handler"))

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_enter_combat_no_combat_room(self, mock_ticker):
        """enter_combat fails if room doesn't allow combat."""
        from combat.combat_utils import enter_combat
        self.room1.allow_combat = False
        result = enter_combat(self.char1, self.char2)
        self.assertFalse(result)

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_get_sides_pcs_vs_npcs(self, mock_ticker):
        """get_sides groups PCs together vs NPCs."""
        from combat.combat_utils import enter_combat, get_sides
        mob = create.create_object(
            "typeclasses.actors.mob.CombatMob",
            key="test_mob",
            location=self.room1,
        )
        mob.hp = 10
        mob.hp_max = 10

        try:
            enter_combat(self.char1, mob)
            allies, enemies = get_sides(self.char1)
            self.assertIn(self.char1, allies)
            self.assertIn(mob, enemies)

            # From mob's perspective
            allies_m, enemies_m = get_sides(mob)
            self.assertIn(mob, allies_m)
            self.assertIn(self.char1, enemies_m)
        finally:
            handlers = mob.scripts.get("combat_handler")
            if handlers:
                for h in handlers:
                    h.stop()
                    h.delete()
            mob.delete()

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_execute_attack_hit(self, mock_ticker):
        """execute_attack deals damage on a hit."""
        from combat.combat_utils import enter_combat, execute_attack
        enter_combat(self.char1, self.char2)

        with patch("combat.combat_utils.dice") as mock_dice:
            mock_dice.roll_with_advantage_or_disadvantage.return_value = 20
            mock_dice.roll.return_value = 3
            execute_attack(self.char1, self.char2)

        self.assertLess(self.char2.hp, 50)

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_execute_attack_miss(self, mock_ticker):
        """execute_attack on a miss doesn't deal damage."""
        from combat.combat_utils import enter_combat, execute_attack
        enter_combat(self.char1, self.char2)
        # Set very high AC so the attack misses
        self.char2.armor_class = 100

        with patch("combat.combat_utils.dice") as mock_dice:
            mock_dice.roll_with_advantage_or_disadvantage.return_value = 1
            mock_dice.roll.return_value = 3
            execute_attack(self.char1, self.char2)

        self.assertEqual(self.char2.hp, 50)

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_execute_attack_consumes_one_disadvantage(self, mock_ticker):
        """Attack consumes 1 round of disadvantage, leaving remainder."""
        from combat.combat_utils import enter_combat, execute_attack
        enter_combat(self.char1, self.char2)
        handler = self.char1.scripts.get("combat_handler")[0]
        handler.set_disadvantage(self.char2, rounds=3)

        with patch("combat.combat_utils.dice") as mock_dice:
            mock_dice.roll_with_advantage_or_disadvantage.return_value = 15
            mock_dice.roll.return_value = 3
            execute_attack(self.char1, self.char2)

        # Should have 2 rounds left
        self.assertTrue(handler.has_disadvantage(self.char2))
        self.assertEqual(handler.disadvantage_against[self.char2.id], 2)

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_execute_attack_consumes_last_disadvantage(self, mock_ticker):
        """Attack consuming last round of disadvantage removes entry."""
        from combat.combat_utils import enter_combat, execute_attack
        enter_combat(self.char1, self.char2)
        handler = self.char1.scripts.get("combat_handler")[0]
        handler.set_disadvantage(self.char2, rounds=1)

        with patch("combat.combat_utils.dice") as mock_dice:
            mock_dice.roll_with_advantage_or_disadvantage.return_value = 15
            mock_dice.roll.return_value = 3
            execute_attack(self.char1, self.char2)

        self.assertFalse(handler.has_disadvantage(self.char2))

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_execute_attack_consumes_one_advantage(self, mock_ticker):
        """Attack consumes 1 round of advantage, leaving remainder."""
        from combat.combat_utils import enter_combat, execute_attack
        enter_combat(self.char1, self.char2)
        handler = self.char1.scripts.get("combat_handler")[0]
        handler.set_advantage(self.char2, rounds=3)

        with patch("combat.combat_utils.dice") as mock_dice:
            mock_dice.roll_with_advantage_or_disadvantage.return_value = 15
            mock_dice.roll.return_value = 3
            execute_attack(self.char1, self.char2)

        self.assertTrue(handler.has_advantage(self.char2))
        self.assertEqual(handler.advantage_against[self.char2.id], 2)

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_execute_attack_consumes_last_advantage(self, mock_ticker):
        """Attack consuming last round of advantage removes entry."""
        from combat.combat_utils import enter_combat, execute_attack
        enter_combat(self.char1, self.char2)
        handler = self.char1.scripts.get("combat_handler")[0]
        handler.set_advantage(self.char2, rounds=1)

        with patch("combat.combat_utils.dice") as mock_dice:
            mock_dice.roll_with_advantage_or_disadvantage.return_value = 15
            mock_dice.roll.return_value = 3
            execute_attack(self.char1, self.char2)

        self.assertFalse(handler.has_advantage(self.char2))

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_decrement_unused_advantage_end_of_round(self, mock_ticker):
        """Unused advantage decrements by 1 at end of tick (minimum rule)."""
        from combat.combat_utils import enter_combat
        self.room1.allow_pvp = True  # PvP so PCs are enemies, combat persists
        enter_combat(self.char1, self.char2)
        handler = self.char1.scripts.get("combat_handler")[0]
        handler.set_advantage(self.char2, rounds=3)

        # Call decrement_advantages directly — simulates end-of-tick
        # without an attack consuming the advantage
        handler.decrement_advantages()

        # Should have decremented by 1 (minimum rule)
        self.assertEqual(handler.advantage_against[self.char2.id], 2)

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_advantage_not_double_decremented(self, mock_ticker):
        """Advantage consumed by attack is NOT also decremented at end of tick."""
        from combat.combat_utils import enter_combat
        self.room1.allow_pvp = True  # PvP so PCs are enemies, combat persists
        enter_combat(self.char1, self.char2)
        handler = self.char1.scripts.get("combat_handler")[0]
        handler.set_advantage(self.char2, rounds=3)
        handler.queue_action({
            "key": "attack", "target": self.char2, "dt": 3, "repeat": True,
        })

        with patch("combat.combat_utils.dice") as mock_dice:
            mock_dice.roll_with_advantage_or_disadvantage.return_value = 15
            mock_dice.roll.return_value = 3
            handler.execute_next_action()

        # Attack consumed 1 (3→2), end-of-round should NOT decrement further
        self.assertEqual(handler.advantage_against[self.char2.id], 2)

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_execute_attack_dead_target_skipped(self, mock_ticker):
        """execute_attack does nothing if target is dead."""
        from combat.combat_utils import enter_combat, execute_attack
        enter_combat(self.char1, self.char2)
        self.char2.hp = 0

        with patch("combat.combat_utils.dice") as mock_dice:
            execute_attack(self.char1, self.char2)
            mock_dice.roll_with_advantage_or_disadvantage.assert_not_called()

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_execute_attack_different_rooms_skipped(self, mock_ticker):
        """execute_attack does nothing if attacker and target in different rooms."""
        from combat.combat_utils import enter_combat, execute_attack
        enter_combat(self.char1, self.char2)
        self.char2.location = self.room2

        with patch("combat.combat_utils.dice") as mock_dice:
            execute_attack(self.char1, self.char2)
            mock_dice.roll_with_advantage_or_disadvantage.assert_not_called()

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_execute_attack_kill_triggers_die(self, mock_ticker):
        """execute_attack calls target.die() when HP reaches 0."""
        from combat.combat_utils import enter_combat, execute_attack
        enter_combat(self.char1, self.char2)
        self.char2.hp = 1  # Will die on any hit

        with patch("combat.combat_utils.dice") as mock_dice, \
             patch.object(self.char2, "die") as mock_die:
            mock_dice.roll_with_advantage_or_disadvantage.return_value = 20
            mock_dice.roll.return_value = 10
            execute_attack(self.char1, self.char2)
            mock_die.assert_called_once_with("combat", killer=self.char1)

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_offhand_skipped_when_target_deleted_mid_tick(self, mock_ticker):
        """Off-hand check short-circuits if main-hand attack deleted the mob.

        Regression test for ValueError raised by AttributeProperty write-on-miss
        when ``getattr(target, "hp", 0)`` runs against a deleted mob (pk=None)
        in the off-hand gate at combat_handler.py line 268. Common mobs are
        deleted by mob.die() → self.delete() the moment HP hits 0, so a fatal
        main-hand blow can leave the off-hand check operating on a dead
        Django reference within the same tick.
        """
        from combat.combat_utils import enter_combat
        mob = create.create_object(
            "typeclasses.actors.mob.CombatMob",
            key="a rabbit",
            location=self.room1,
        )
        mob.hp = 1
        mob.hp_max = 1

        try:
            enter_combat(self.char1, mob)
            handler = self.char1.scripts.get("combat_handler")[0]
            handler.queue_action({
                "key": "attack",
                "target": mob,
                "dt": 3,
                "repeat": True,
            })

            # Simulate mob.die() → self.delete() during the main-hand attack:
            # execute_attack is mocked to delete the target, mirroring what
            # happens when a common mob takes a fatal blow.
            def _kill_and_delete(*args, **kwargs):
                mob.delete()

            with patch("combat.combat_utils.execute_attack",
                       side_effect=_kill_and_delete):
                # Must not raise ValueError("...needs to have a value for
                # field 'id' before this many-to-many relationship...")
                handler.execute_next_action()

            # Mob is gone — pk has been cleared by .delete()
            self.assertIsNone(mob.pk)
        finally:
            handlers = mob.scripts.get("combat_handler") if mob.pk else None
            if handlers:
                for h in handlers:
                    h.stop()
                    h.delete()
            if mob.pk:
                mob.delete()
