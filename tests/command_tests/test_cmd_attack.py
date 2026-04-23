"""
Tests for combat commands — CmdAttack, CmdDodge, mastery dispatch.

Other combat tests split into:
    tests.command_tests.test_combat_handler
    tests.command_tests.test_combat_weapons
    tests.command_tests.test_unarmed_combat
    tests.command_tests.test_take_damage

evennia test --settings settings tests.command_tests.test_cmd_attack
"""

from unittest.mock import patch, MagicMock

from evennia.utils.test_resources import EvenniaCommandTest
from evennia.utils import create

from commands.all_char_cmds.cmd_attack import CmdAttack
from commands.class_skill_cmdsets.class_skill_cmds.cmd_dodge import CmdDodge


# ================================================================== #
#  CmdAttack Tests
# ================================================================== #


class TestCmdAttack(EvenniaCommandTest):
    """Test the attack command."""

    character_typeclass = "typeclasses.actors.character.FCMCharacter"
    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        # Enable combat in the room
        self.room1.allow_combat = True
        # Give characters enough HP
        self.char1.hp = 20
        self.char1.hp_max = 20
        self.char2.hp = 20
        self.char2.hp_max = 20

    def tearDown(self):
        """Clean up combat handlers."""
        for char in (self.char1, self.char2):
            handlers = char.scripts.get("combat_handler")
            if handlers:
                for h in handlers:
                    h.stop()
                    h.delete()
        super().tearDown()

    def test_attack_no_args(self):
        """Attack with no target shows error."""
        result = self.call(CmdAttack(), "")
        self.assertIn("Attack what?", result)

    def test_attack_self(self):
        """Attacking 'me' emits the friendly self-error.

        Exercises the self-targeting path via Evennia's direct-match
        shortcut. The resolver lands caller in the 'self' bucket (last
        priority) and the command-layer self-check emits the friendly
        refusal. Typing your own literal key when another actor in the
        room shares a name-prefix honestly resolves to that other
        actor — self-attack-by-literal-key is the rare edge case we
        deliberately don't optimise for.
        """
        result = self.call(CmdAttack(), "me")
        self.assertIn("can't attack yourself", result)

    def test_attack_dead_target(self):
        """A dead target is not distinguishable from 'not here'.

        hp=0 is a microseconds-wide race between actor death and corpse
        creation — not a state players can usefully target. The targeting
        library filters it out via p_living, so the command reports the
        same 'not here' wording as if the target didn't exist at all.
        """
        self.char2.hp = 0
        result = self.call(CmdAttack(), self.char2.key)
        self.assertIn(f"There's no '{self.char2.key}' here", result)

    def test_attack_no_combat_room(self):
        """Can't attack in a non-combat room."""
        self.room1.allow_combat = False
        result = self.call(CmdAttack(), self.char2.key)
        self.assertIn("not allowed", result)

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_attack_success(self, mock_ticker):
        """Successful attack creates combat handlers and queues action."""
        result = self.call(CmdAttack(), self.char2.key)
        self.assertIn("You attack", result)
        # Both should have combat handlers
        self.assertTrue(self.char1.scripts.get("combat_handler"))
        self.assertTrue(self.char2.scripts.get("combat_handler"))

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_attack_queues_repeating_action(self, mock_ticker):
        """Attack queues a repeating attack action on the handler."""
        self.call(CmdAttack(), self.char2.key)
        handler = self.char1.scripts.get("combat_handler")[0]
        action = handler.action_dict
        self.assertEqual(action["key"], "attack")
        self.assertEqual(action["target"], self.char2)
        self.assertTrue(action["repeat"])


# ================================================================== #
#  CmdDodge Tests
# ================================================================== #


class TestCmdDodge(EvenniaCommandTest):
    """Test the dodge command."""

    character_typeclass = "typeclasses.actors.character.FCMCharacter"
    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.room1.allow_combat = True
        self.room1.allow_pvp = True  # PvP needed so PCs can be enemies
        self.char1.hp = 20
        self.char1.hp_max = 20
        self.char2.hp = 20
        self.char2.hp_max = 20
        # Give char1 skill mastery levels so mastery dispatch works
        from enums.skills_enum import skills
        from enums.mastery_level import MasteryLevel
        self.char1.db.general_skill_mastery_levels = {
            skills.BATTLESKILLS.value: MasteryLevel.UNSKILLED.value,
        }

    def tearDown(self):
        for char in (self.char1, self.char2):
            handlers = char.scripts.get("combat_handler")
            if handlers:
                for h in handlers:
                    h.stop()
                    h.delete()
        super().tearDown()

    def test_dodge_not_in_combat(self):
        """Dodge without being in combat shows error."""
        result = self.call(CmdDodge(), "")
        self.assertIn("not in combat", result)

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_dodge_sets_disadvantage(self, mock_ticker):
        """Dodge sets 1 round of disadvantage on enemies against the dodger."""
        # Enter combat (PvP room so PCs are enemies)
        self.call(CmdAttack(), self.char2.key, caller=self.char1)
        # Dodge
        result = self.call(CmdDodge(), "", caller=self.char1)
        self.assertIn("dodge", result.lower())
        # char2 should have 1 round of disadvantage against char1
        enemy_handler = self.char2.scripts.get("combat_handler")
        self.assertTrue(enemy_handler)
        self.assertTrue(enemy_handler[0].has_disadvantage(self.char1))
        self.assertEqual(enemy_handler[0].disadvantage_against[self.char1.id], 1)

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_dodge_sets_skip_flag(self, mock_ticker):
        """Dodge sets skip_next_action on the dodger's handler."""
        self.call(CmdAttack(), self.char2.key, caller=self.char1)
        self.call(CmdDodge(), "", caller=self.char1)
        handler = self.char1.scripts.get("combat_handler")[0]
        self.assertTrue(handler.skip_next_action)

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_dodge_mob_func(self, mock_ticker):
        """Mob without mastery data gets mob_func dodge."""
        mob = create.create_object(
            "typeclasses.actors.mobs.dire_wolf.DireWolf",
            key="dire wolf",
            location=self.room1,
        )
        mob.hp = 30
        mob.hp_max = 30
        try:
            # Enter combat for mob
            from combat.combat_utils import enter_combat
            enter_combat(mob, self.char1)
            # Mob should not have any mastery dicts
            self.assertIsNone(mob.db.general_skill_mastery_levels)
            # Mob dodge — calls mob_func
            result = self.call(CmdDodge(), "", caller=mob)
            self.assertIn("dodges", result)
        finally:
            handlers = mob.scripts.get("combat_handler")
            if handlers:
                for h in handlers:
                    h.stop()
                    h.delete()
            mob.delete()


# ================================================================== #
#  CombatHandler Tests
# ================================================================== #


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


# ================================================================== #
#  Combat Utility Tests
# ================================================================== #


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
    def test_enter_combat_one_shot_kill_does_not_store_deleted_target(self, mock_ticker):
        """Free attack that one-shots the target must not store a stale
        reference in action_dict.

        Regression: pickling action_dict for persistence reads db_sessid
        on the target, which raises ObjectDoesNotExist if the mob was
        deleted by the free attack.
        """
        from combat.combat_utils import enter_combat
        mob = create.create_object(
            "typeclasses.actors.mob.CombatMob",
            key="test_mob",
            location=self.room1,
        )
        mob.hp = 1
        mob.hp_max = 1
        mob.is_unique = False  # common mob → deleted on death

        try:
            with patch("combat.combat_utils.dice") as mock_dice:
                mock_dice.roll_with_advantage_or_disadvantage.return_value = 20
                mock_dice.roll.return_value = 99
                # Should not raise
                enter_combat(self.char1, mob, instigator=self.char1)

            # Mob was deleted
            self.assertIsNone(mob.pk)

            # char1's action_dict must not carry the deleted reference
            handlers = self.char1.scripts.get("combat_handler")
            if handlers:
                action = handlers[0].action_dict
                if action:
                    self.assertNotEqual(action.get("target"), mob)
        finally:
            if mob.pk:
                mob.delete()


# ================================================================== #
#  CmdSkillBase Mastery Branch Tests
# ================================================================== #


class TestCmdSkillBaseMasteryBranch(EvenniaCommandTest):
    """Test CmdSkillBase mastery dispatch vs mob_func branching."""

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
    def test_player_with_mastery_uses_dispatch(self, mock_ticker):
        """Player with skill_mastery_levels gets mastery dispatch (unskilled)."""
        from combat.combat_utils import enter_combat
        from enums.skills_enum import skills
        from enums.mastery_level import MasteryLevel
        self.room1.allow_pvp = True  # PvP so PCs are enemies for dodge
        self.char1.db.general_skill_mastery_levels = {
            skills.BATTLESKILLS.value: MasteryLevel.UNSKILLED.value,
        }
        enter_combat(self.char1, self.char2)
        result = self.call(CmdDodge(), "", caller=self.char1)
        # Unskilled dodge message
        self.assertIn("clumsily", result)

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_player_basic_mastery_dodge(self, mock_ticker):
        """Player with basic mastery gets basic dodge message."""
        from enums.skills_enum import skills
        from enums.mastery_level import MasteryLevel
        from combat.combat_utils import enter_combat

        self.room1.allow_pvp = True
        if not self.char1.db.general_skill_mastery_levels:
            self.char1.db.general_skill_mastery_levels = {}
        self.char1.db.general_skill_mastery_levels[skills.BATTLESKILLS.value] = MasteryLevel.BASIC.value
        enter_combat(self.char1, self.char2)
        result = self.call(CmdDodge(), "", caller=self.char1)
        self.assertIn("weaving defensively", result)

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_caller_without_mastery_gets_mob_func(self, mock_ticker):
        """Caller without skill_mastery_levels gets mob_func."""
        mob = create.create_object(
            "typeclasses.actors.mob.CombatMob",
            key="test_mob",
            location=self.room1,
        )
        mob.hp = 20
        mob.hp_max = 20
        try:
            from combat.combat_utils import enter_combat
            enter_combat(mob, self.char1)
            # mob should not have any mastery dicts
            self.assertIsNone(mob.db.general_skill_mastery_levels)
            result = self.call(CmdDodge(), "", caller=mob)
            # mob_func for dodge shows leaping/twisting message
            self.assertIn("dodges", result)
        finally:
            handlers = mob.scripts.get("combat_handler")
            if handlers:
                for h in handlers:
                    h.stop()
                    h.delete()
            mob.delete()
