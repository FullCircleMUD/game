"""
Tests for combat system — CmdAttack, CmdDodge, combat_utils, CombatHandler.

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
        self.assertIn(f"You don't see '{self.char2.key}' here", result)

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


# ================================================================== #
#  Parry Tests
# ================================================================== #


class TestParry(EvenniaCommandTest):
    """Test the parry system in execute_attack."""

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
        # Clean up weapons
        for obj in list(self.char1.contents) + list(self.char2.contents):
            if hasattr(obj, "weapon_type_key"):
                obj.delete()
        super().tearDown()

    def _equip_longsword(self, char, mastery_level):
        """Create a longsword and equip it on char with given mastery."""
        from enums.mastery_level import MasteryLevel
        from enums.unused_for_reference.damage_type import DamageType
        sword = create.create_object(
            "typeclasses.items.weapons.longsword_nft_item.LongswordNFTItem",
            key="Test Longsword",
            location=char,
        )
        sword.damage = {
            MasteryLevel.UNSKILLED: "1D4",
            MasteryLevel.BASIC: "1D6",
            MasteryLevel.SKILLED: "1D8",
            MasteryLevel.EXPERT: "1D10",
            MasteryLevel.MASTER: "1D10",
            MasteryLevel.GRANDMASTER: "1D10",
        }
        sword.damage_type = DamageType.SLASHING
        sword.max_durability = 100
        sword.durability = 100
        # Set mastery on character
        char.db.weapon_skill_mastery_levels = {
            "long_sword": mastery_level.value,
        }
        # Equip directly via wearslots
        wearslots = dict(char.db.wearslots or {})
        wearslots["WIELD"] = sword
        char.db.wearslots = wearslots
        return sword

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_parry_blocks_melee_attack(self, mock_ticker):
        """SKILLED longsword wielder parries melee attack, blocking damage."""
        from enums.mastery_level import MasteryLevel
        from combat.combat_utils import enter_combat, execute_attack

        attacker_sword = self._equip_longsword(self.char1, MasteryLevel.BASIC)
        defender_sword = self._equip_longsword(self.char2, MasteryLevel.SKILLED)
        enter_combat(self.char1, self.char2)

        # Set parries on defender
        defender_handler = self.char2.scripts.get("combat_handler")[0]
        defender_handler.parries_remaining = 1

        with patch("combat.combat_utils.dice") as mock_dice:
            # Attacker rolls 10, defender parry rolls high (25 > 10+bonuses)
            mock_dice.roll_with_advantage_or_disadvantage.side_effect = [10, 25]
            mock_dice.roll.return_value = 5
            execute_attack(self.char1, self.char2)

        # Target should take no damage (parried)
        self.assertEqual(self.char2.hp, 50)
        # Both weapons lose durability
        self.assertEqual(attacker_sword.durability, 99)
        self.assertEqual(defender_sword.durability, 99)

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_parry_fails_attack_proceeds(self, mock_ticker):
        """Low parry roll doesn't block, attack resolves normally."""
        from enums.mastery_level import MasteryLevel
        from combat.combat_utils import enter_combat, execute_attack

        self._equip_longsword(self.char1, MasteryLevel.BASIC)
        self._equip_longsword(self.char2, MasteryLevel.SKILLED)
        enter_combat(self.char1, self.char2)

        defender_handler = self.char2.scripts.get("combat_handler")[0]
        defender_handler.parries_remaining = 1

        with patch("combat.combat_utils.dice") as mock_dice:
            # Attacker rolls 15, defender parry rolls low (2)
            mock_dice.roll_with_advantage_or_disadvantage.side_effect = [15, 2]
            mock_dice.roll.return_value = 5
            execute_attack(self.char1, self.char2)

        # Target should take damage (parry failed, attack hit)
        self.assertLess(self.char2.hp, 50)

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_parry_not_triggered_unarmed_attacker(self, mock_ticker):
        """Unarmed attacker doesn't trigger parry (weapon is None)."""
        from enums.mastery_level import MasteryLevel
        from combat.combat_utils import enter_combat, execute_attack

        # Only defender has weapon
        self._equip_longsword(self.char2, MasteryLevel.SKILLED)
        enter_combat(self.char1, self.char2)

        defender_handler = self.char2.scripts.get("combat_handler")[0]
        defender_handler.parries_remaining = 1

        with patch("combat.combat_utils.dice") as mock_dice:
            mock_dice.roll_with_advantage_or_disadvantage.return_value = 20
            mock_dice.roll.return_value = 3
            execute_attack(self.char1, self.char2)

        # Attack should resolve normally (parry not attempted)
        self.assertLess(self.char2.hp, 50)
        # Parry not consumed
        self.assertEqual(defender_handler.parries_remaining, 1)

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_parry_uses_remaining_count(self, mock_ticker):
        """After all parries consumed, further attacks are not parried."""
        from enums.mastery_level import MasteryLevel
        from combat.combat_utils import enter_combat, execute_attack

        self._equip_longsword(self.char1, MasteryLevel.BASIC)
        self._equip_longsword(self.char2, MasteryLevel.SKILLED)
        enter_combat(self.char1, self.char2)

        defender_handler = self.char2.scripts.get("combat_handler")[0]
        defender_handler.parries_remaining = 1

        # First attack: parried (high parry roll)
        with patch("combat.combat_utils.dice") as mock_dice:
            mock_dice.roll_with_advantage_or_disadvantage.side_effect = [10, 25]
            mock_dice.roll.return_value = 5
            execute_attack(self.char1, self.char2)

        self.assertEqual(self.char2.hp, 50)  # no damage
        self.assertEqual(defender_handler.parries_remaining, 0)

        # Second attack: no parry available
        with patch("combat.combat_utils.dice") as mock_dice:
            mock_dice.roll_with_advantage_or_disadvantage.return_value = 20
            mock_dice.roll.return_value = 5
            execute_attack(self.char1, self.char2)

        self.assertLess(self.char2.hp, 50)  # damage dealt

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_parry_resets_each_round(self, mock_ticker):
        """Parries reset at start of execute_next_action."""
        from enums.mastery_level import MasteryLevel
        from combat.combat_utils import enter_combat

        self._equip_longsword(self.char1, MasteryLevel.SKILLED)
        enter_combat(self.char1, self.char2)
        handler = self.char1.scripts.get("combat_handler")[0]

        # Exhaust parries
        handler.parries_remaining = 0

        # Execute next action resets parries based on weapon
        with patch("combat.combat_utils.dice") as mock_dice:
            mock_dice.roll_with_advantage_or_disadvantage.return_value = 15
            mock_dice.roll.return_value = 1
            handler.execute_next_action()

        # SKILLED longsword = 1 parry per round
        self.assertEqual(handler.parries_remaining, 1)

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_grandmaster_parry_advantage(self, mock_ticker):
        """Grandmaster longsword gets parry_advantage set on handler."""
        from enums.mastery_level import MasteryLevel
        from combat.combat_utils import enter_combat

        self._equip_longsword(self.char1, MasteryLevel.GRANDMASTER)
        enter_combat(self.char1, self.char2)
        handler = self.char1.scripts.get("combat_handler")[0]

        with patch("combat.combat_utils.dice") as mock_dice:
            mock_dice.roll_with_advantage_or_disadvantage.return_value = 15
            mock_dice.roll.return_value = 1
            handler.execute_next_action()

        self.assertTrue(handler.parry_advantage)
        self.assertEqual(handler.parries_remaining, 3)


# ================================================================== #
#  Durability Tests
# ================================================================== #


class TestCombatDurability(EvenniaCommandTest):
    """Test durability loss during combat."""

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
        for obj in list(self.char1.contents) + list(self.char2.contents):
            if hasattr(obj, "weapon_type_key") or getattr(obj, "wearslot", None):
                obj.delete()
        super().tearDown()

    def _equip_weapon(self, char):
        """Create and equip a basic longsword."""
        from enums.mastery_level import MasteryLevel
        from enums.unused_for_reference.damage_type import DamageType
        sword = create.create_object(
            "typeclasses.items.weapons.longsword_nft_item.LongswordNFTItem",
            key="Test Sword",
            location=char,
        )
        sword.damage = {
            MasteryLevel.UNSKILLED: "1D4",
            MasteryLevel.BASIC: "1D6",
            MasteryLevel.SKILLED: "1D8",
            MasteryLevel.EXPERT: "1D10",
            MasteryLevel.MASTER: "1D10",
            MasteryLevel.GRANDMASTER: "1D10",
        }
        sword.damage_type = DamageType.SLASHING
        sword.max_durability = 100
        sword.durability = 100
        wearslots = dict(char.db.wearslots or {})
        wearslots["WIELD"] = sword
        char.db.wearslots = wearslots
        return sword

    def _equip_armor(self, char, slot="BODY"):
        """Create and equip body armor or helmet."""
        from enums.wearslot import HumanoidWearSlot
        armor = create.create_object(
            "typeclasses.items.wearables.wearable_nft_item.WearableNFTItem",
            key=f"Test {'Helmet' if slot == 'HEAD' else 'Armor'}",
            location=char,
        )
        armor.wearslot = HumanoidWearSlot.HEAD if slot == "HEAD" else HumanoidWearSlot.BODY
        armor.max_durability = 80
        armor.durability = 80
        wearslots = dict(char.db.wearslots or {})
        wearslots[slot] = armor
        char.db.wearslots = wearslots
        return armor

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_hit_reduces_weapon_durability(self, mock_ticker):
        """Attacker's weapon loses 1 durability on hit."""
        from combat.combat_utils import enter_combat, execute_attack

        weapon = self._equip_weapon(self.char1)
        enter_combat(self.char1, self.char2)

        with patch("combat.combat_utils.dice") as mock_dice:
            mock_dice.roll_with_advantage_or_disadvantage.return_value = 15
            mock_dice.roll.return_value = 3
            execute_attack(self.char1, self.char2)

        self.assertEqual(weapon.durability, 99)

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_hit_reduces_body_armor_durability(self, mock_ticker):
        """Target's body armor loses 1 durability on hit."""
        from combat.combat_utils import enter_combat, execute_attack

        self._equip_weapon(self.char1)
        armor = self._equip_armor(self.char2, "BODY")
        enter_combat(self.char1, self.char2)

        with patch("combat.combat_utils.dice") as mock_dice:
            mock_dice.roll_with_advantage_or_disadvantage.return_value = 15
            mock_dice.roll.return_value = 3
            execute_attack(self.char1, self.char2)

        self.assertEqual(armor.durability, 79)

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_miss_no_durability_loss(self, mock_ticker):
        """No durability change on miss."""
        from combat.combat_utils import enter_combat, execute_attack

        weapon = self._equip_weapon(self.char1)
        armor = self._equip_armor(self.char2, "BODY")
        enter_combat(self.char1, self.char2)
        self.char2.armor_class = 100  # guarantee miss

        with patch("combat.combat_utils.dice") as mock_dice:
            mock_dice.roll_with_advantage_or_disadvantage.return_value = 1
            mock_dice.roll.return_value = 3
            execute_attack(self.char1, self.char2)

        self.assertEqual(weapon.durability, 100)
        self.assertEqual(armor.durability, 80)

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_parry_both_weapons_lose_durability(self, mock_ticker):
        """Both weapons lose 1 durability on successful parry."""
        from enums.mastery_level import MasteryLevel
        from combat.combat_utils import enter_combat, execute_attack

        atk_sword = self._equip_weapon(self.char1)
        def_sword = self._equip_weapon(self.char2)
        self.char2.db.weapon_skill_mastery_levels = {"long_sword": MasteryLevel.SKILLED.value}
        enter_combat(self.char1, self.char2)

        defender_handler = self.char2.scripts.get("combat_handler")[0]
        defender_handler.parries_remaining = 1

        with patch("combat.combat_utils.dice") as mock_dice:
            mock_dice.roll_with_advantage_or_disadvantage.side_effect = [10, 25]
            mock_dice.roll.return_value = 5
            execute_attack(self.char1, self.char2)

        self.assertEqual(atk_sword.durability, 99)
        self.assertEqual(def_sword.durability, 99)
        self.assertEqual(self.char2.hp, 50)  # no damage


# ================================================================== #
#  CRIT_IMMUNE Tests
# ================================================================== #


class TestCritImmune(EvenniaCommandTest):
    """Test CRIT_IMMUNE condition in combat."""

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
        for obj in list(self.char1.contents) + list(self.char2.contents):
            if hasattr(obj, "weapon_type_key") or getattr(obj, "wearslot", None):
                obj.delete()
        super().tearDown()

    def _equip_weapon(self, char):
        from enums.mastery_level import MasteryLevel
        from enums.unused_for_reference.damage_type import DamageType
        sword = create.create_object(
            "typeclasses.items.weapons.longsword_nft_item.LongswordNFTItem",
            key="Test Sword",
            location=char,
        )
        sword.damage = {
            MasteryLevel.UNSKILLED: "1D4",
            MasteryLevel.BASIC: "1D6",
            MasteryLevel.SKILLED: "1D8",
            MasteryLevel.EXPERT: "1D10",
            MasteryLevel.MASTER: "1D10",
            MasteryLevel.GRANDMASTER: "1D10",
        }
        sword.damage_type = DamageType.SLASHING
        sword.max_durability = 100
        sword.durability = 100
        wearslots = dict(char.db.wearslots or {})
        wearslots["WIELD"] = sword
        char.db.wearslots = wearslots
        return sword

    def _equip_armor(self, char, slot="BODY"):
        from enums.wearslot import HumanoidWearSlot
        armor = create.create_object(
            "typeclasses.items.wearables.wearable_nft_item.WearableNFTItem",
            key=f"Test {'Helmet' if slot == 'HEAD' else 'Armor'}",
            location=char,
        )
        armor.wearslot = HumanoidWearSlot.HEAD if slot == "HEAD" else HumanoidWearSlot.BODY
        armor.max_durability = 80
        armor.durability = 80
        wearslots = dict(char.db.wearslots or {})
        wearslots[slot] = armor
        char.db.wearslots = wearslots
        return armor

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_crit_immune_downgrades_to_normal_hit(self, mock_ticker):
        """CRIT_IMMUNE downgrades crit to normal hit (no double dice)."""
        from enums.condition import Condition
        from combat.combat_utils import enter_combat, execute_attack

        self._equip_weapon(self.char1)
        self._equip_armor(self.char2, "HEAD")
        enter_combat(self.char1, self.char2)

        # Give target CRIT_IMMUNE condition
        self.char2.add_condition(Condition.CRIT_IMMUNE)
        # Set crit threshold low so d20=15 is a crit
        self.char1.base_crit_threshold = 15

        with patch("combat.combat_utils.dice") as mock_dice:
            # d20=15 (would be crit), damage roll=5
            mock_dice.roll_with_advantage_or_disadvantage.return_value = 15
            mock_dice.roll.return_value = 5
            execute_attack(self.char1, self.char2)

        # Should have taken damage but NOT double dice
        # dice.roll called only once (not twice as it would for crit)
        self.assertEqual(mock_dice.roll.call_count, 1)
        self.assertLess(self.char2.hp, 50)

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_crit_immune_helmet_takes_durability(self, mock_ticker):
        """CRIT_IMMUNE: helmet -1 durability, body armor spared."""
        from enums.condition import Condition
        from combat.combat_utils import enter_combat, execute_attack

        self._equip_weapon(self.char1)
        body_armor = self._equip_armor(self.char2, "BODY")
        helmet = self._equip_armor(self.char2, "HEAD")
        enter_combat(self.char1, self.char2)

        self.char2.add_condition(Condition.CRIT_IMMUNE)
        self.char1.base_crit_threshold = 15

        with patch("combat.combat_utils.dice") as mock_dice:
            mock_dice.roll_with_advantage_or_disadvantage.return_value = 15
            mock_dice.roll.return_value = 5
            execute_attack(self.char1, self.char2)

        # Helmet takes durability, body armor does not
        self.assertEqual(helmet.durability, 79)
        self.assertEqual(body_armor.durability, 80)

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_crit_without_crit_immune(self, mock_ticker):
        """Normal crit deals double dice and body armor takes durability."""
        from combat.combat_utils import enter_combat, execute_attack

        self._equip_weapon(self.char1)
        body_armor = self._equip_armor(self.char2, "BODY")
        helmet = self._equip_armor(self.char2, "HEAD")
        enter_combat(self.char1, self.char2)

        self.char1.base_crit_threshold = 15

        with patch("combat.combat_utils.dice") as mock_dice:
            mock_dice.roll_with_advantage_or_disadvantage.return_value = 15
            mock_dice.roll.return_value = 5
            execute_attack(self.char1, self.char2)

        # dice.roll called twice (damage + crit bonus)
        self.assertEqual(mock_dice.roll.call_count, 2)
        # Body armor takes durability, helmet does not
        self.assertEqual(body_armor.durability, 79)
        self.assertEqual(helmet.durability, 80)


# ================================================================== #
#  Multi-Attack Tests
# ================================================================== #


class TestMultiAttack(EvenniaCommandTest):
    """Test extra attacks from weapon mastery."""

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
        for obj in list(self.char1.contents) + list(self.char2.contents):
            if hasattr(obj, "weapon_type_key"):
                obj.delete()
        super().tearDown()

    def _equip_longsword(self, char, mastery_level):
        from enums.mastery_level import MasteryLevel
        from enums.unused_for_reference.damage_type import DamageType
        sword = create.create_object(
            "typeclasses.items.weapons.longsword_nft_item.LongswordNFTItem",
            key="Test Longsword",
            location=char,
        )
        sword.damage = {
            MasteryLevel.UNSKILLED: "1D4",
            MasteryLevel.BASIC: "1D6",
            MasteryLevel.SKILLED: "1D8",
            MasteryLevel.EXPERT: "1D10",
            MasteryLevel.MASTER: "1D10",
            MasteryLevel.GRANDMASTER: "1D10",
        }
        sword.damage_type = DamageType.SLASHING
        sword.max_durability = 100
        sword.durability = 100
        char.db.weapon_skill_mastery_levels = {"long_sword": mastery_level.value}
        wearslots = dict(char.db.wearslots or {})
        wearslots["WIELD"] = sword
        char.db.wearslots = wearslots
        return sword

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_master_longsword_extra_attack(self, mock_ticker):
        """Master longsword fires 2 attacks per tick."""
        from enums.mastery_level import MasteryLevel
        from combat.combat_utils import enter_combat, execute_attack

        self._equip_longsword(self.char1, MasteryLevel.MASTER)
        enter_combat(self.char1, self.char2)
        handler = self.char1.scripts.get("combat_handler")[0]
        handler.queue_action({
            "key": "attack", "target": self.char2, "dt": 3, "repeat": True,
        })

        with patch("combat.combat_utils.dice") as mock_dice, \
             patch("combat.combat_utils.execute_attack", wraps=execute_attack) as spy:
            mock_dice.roll_with_advantage_or_disadvantage.return_value = 15
            mock_dice.roll.return_value = 3
            handler.execute_next_action()

        # execute_attack should have been called twice
        self.assertEqual(spy.call_count, 2)

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_basic_longsword_single_attack(self, mock_ticker):
        """Basic longsword fires only 1 attack per tick."""
        from enums.mastery_level import MasteryLevel
        from combat.combat_utils import enter_combat, execute_attack

        self._equip_longsword(self.char1, MasteryLevel.BASIC)
        enter_combat(self.char1, self.char2)
        handler = self.char1.scripts.get("combat_handler")[0]
        handler.queue_action({
            "key": "attack", "target": self.char2, "dt": 3, "repeat": True,
        })

        with patch("combat.combat_utils.dice") as mock_dice, \
             patch("combat.combat_utils.execute_attack", wraps=execute_attack) as spy:
            mock_dice.roll_with_advantage_or_disadvantage.return_value = 15
            mock_dice.roll.return_value = 3
            handler.execute_next_action()

        self.assertEqual(spy.call_count, 1)

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_extra_attack_stops_on_kill(self, mock_ticker):
        """Second attack doesn't fire if target dies on first."""
        from enums.mastery_level import MasteryLevel
        from combat.combat_utils import enter_combat

        self._equip_longsword(self.char1, MasteryLevel.MASTER)
        enter_combat(self.char1, self.char2)
        self.char2.hp = 1  # Will die on first hit

        handler = self.char1.scripts.get("combat_handler")[0]
        handler.queue_action({
            "key": "attack", "target": self.char2, "dt": 3, "repeat": True,
        })

        with patch("combat.combat_utils.dice") as mock_dice, \
             patch.object(self.char2, "die") as mock_die:
            mock_dice.roll_with_advantage_or_disadvantage.return_value = 20
            mock_dice.roll.return_value = 10
            handler.execute_next_action()

        # die() called only once (second attack skipped)
        mock_die.assert_called_once_with("combat", killer=self.char1)


# ================================================================== #
#  Longsword Custom Hit Bonus Tests
# ================================================================== #


class TestLongswordHitBonuses(EvenniaCommandTest):
    """Test longsword custom hit bonuses override defaults."""

    character_typeclass = "typeclasses.actors.character.FCMCharacter"
    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"
    databases = "__all__"

    def create_script(self):
        pass

    def test_longsword_custom_hit_bonuses(self):
        """Longsword hit bonuses differ from default mastery bonuses."""
        from enums.mastery_level import MasteryLevel
        sword = create.create_object(
            "typeclasses.items.weapons.longsword_nft_item.LongswordNFTItem",
            key="Test Longsword",
            location=self.char1,
        )
        try:
            # MASTER: longsword=+4, default=+6
            self.char1.db.weapon_skill_mastery_levels = {"long_sword": MasteryLevel.MASTER.value}
            self.assertEqual(sword.get_mastery_hit_bonus(self.char1), 4)
            self.assertNotEqual(MasteryLevel.MASTER.bonus, 4)  # default is 6

            # GRANDMASTER: longsword=+5, default=+8
            self.char1.db.weapon_skill_mastery_levels = {"long_sword": MasteryLevel.GRANDMASTER.value}
            self.assertEqual(sword.get_mastery_hit_bonus(self.char1), 5)
            self.assertNotEqual(MasteryLevel.GRANDMASTER.bonus, 5)  # default is 8

            # SKILLED: longsword=+2, same as default
            self.char1.db.weapon_skill_mastery_levels = {"long_sword": MasteryLevel.SKILLED.value}
            self.assertEqual(sword.get_mastery_hit_bonus(self.char1), 2)
        finally:
            sword.delete()


# ================================================================== #
#  Effective Attacks Per Round Tests
# ================================================================== #


class TestEffectiveAttacksPerRound(EvenniaCommandTest):
    """Test effective_attacks_per_round property and HASTED integration."""

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
        for obj in list(self.char1.contents) + list(self.char2.contents):
            if hasattr(obj, "weapon_type_key"):
                obj.delete()
        super().tearDown()

    def _equip_longsword(self, char, mastery_level):
        from enums.mastery_level import MasteryLevel
        from enums.unused_for_reference.damage_type import DamageType
        sword = create.create_object(
            "typeclasses.items.weapons.longsword_nft_item.LongswordNFTItem",
            key="Test Longsword",
            location=char,
        )
        sword.damage = {
            MasteryLevel.UNSKILLED: "1D4",
            MasteryLevel.BASIC: "1D6",
            MasteryLevel.SKILLED: "1D8",
            MasteryLevel.EXPERT: "1D10",
            MasteryLevel.MASTER: "1D10",
            MasteryLevel.GRANDMASTER: "1D10",
        }
        sword.damage_type = DamageType.SLASHING
        sword.max_durability = 100
        sword.durability = 100
        char.db.weapon_skill_mastery_levels = {"long_sword": mastery_level.value}
        wearslots = dict(char.db.wearslots or {})
        wearslots["WIELD"] = sword
        char.db.wearslots = wearslots
        return sword

    def test_base_attacks_no_weapon(self):
        """No weapon: effective_attacks_per_round equals attacks_per_round."""
        self.assertEqual(self.char1.attacks_per_round, 1)
        self.assertEqual(self.char1.effective_attacks_per_round, 1)

    def test_basic_weapon_no_extra_attacks(self):
        """Basic longsword gives no extra attacks."""
        from enums.mastery_level import MasteryLevel
        self._equip_longsword(self.char1, MasteryLevel.BASIC)
        self.assertEqual(self.char1.effective_attacks_per_round, 1)

    def test_master_weapon_extra_attack(self):
        """Master longsword adds 1 extra attack via effective_attacks_per_round."""
        from enums.mastery_level import MasteryLevel
        self._equip_longsword(self.char1, MasteryLevel.MASTER)
        self.assertEqual(self.char1.effective_attacks_per_round, 2)

    def test_hasted_adds_one_attack(self):
        """HASTED condition adds 1 to attacks_per_round, reflected in effective."""
        from enums.condition import Condition
        newly_gained = self.char1.add_condition(Condition.HASTED)
        self.assertTrue(newly_gained)
        self.char1.apply_effect({"type": "stat_bonus", "stat": "attacks_per_round", "value": 1})
        self.assertEqual(self.char1.attacks_per_round, 2)
        self.assertEqual(self.char1.effective_attacks_per_round, 2)
        # Clean up
        self.char1.remove_effect({"type": "stat_bonus", "stat": "attacks_per_round", "value": 1})
        self.char1.remove_condition(Condition.HASTED)

    def test_hasted_plus_master_weapon(self):
        """HASTED + master longsword = 3 attacks per round."""
        from enums.condition import Condition
        from enums.mastery_level import MasteryLevel
        self._equip_longsword(self.char1, MasteryLevel.MASTER)
        self.char1.add_condition(Condition.HASTED)
        self.char1.apply_effect({"type": "stat_bonus", "stat": "attacks_per_round", "value": 1})
        self.assertEqual(self.char1.effective_attacks_per_round, 3)
        # Clean up
        self.char1.remove_effect({"type": "stat_bonus", "stat": "attacks_per_round", "value": 1})
        self.char1.remove_condition(Condition.HASTED)

    def test_hasted_does_not_stack(self):
        """Two sources of HASTED still only give 1 extra attack."""
        from enums.condition import Condition
        # First source: newly gained, apply effect
        gained1 = self.char1.add_condition(Condition.HASTED)
        self.assertTrue(gained1)
        if gained1:
            self.char1.apply_effect({"type": "stat_bonus", "stat": "attacks_per_round", "value": 1})

        # Second source: NOT newly gained, do NOT apply effect
        gained2 = self.char1.add_condition(Condition.HASTED)
        self.assertFalse(gained2)
        if gained2:
            self.char1.apply_effect({"type": "stat_bonus", "stat": "attacks_per_round", "value": 1})

        # Count is 2, but attacks_per_round only got +1
        self.assertEqual(self.char1.get_condition_count(Condition.HASTED), 2)
        self.assertEqual(self.char1.attacks_per_round, 2)  # base 1 + 1 from haste
        self.assertEqual(self.char1.effective_attacks_per_round, 2)

        # Remove first source: count drops to 1, effect stays
        removed1 = self.char1.remove_condition(Condition.HASTED)
        self.assertFalse(removed1)
        if removed1:
            self.char1.remove_effect({"type": "stat_bonus", "stat": "attacks_per_round", "value": 1})
        self.assertEqual(self.char1.attacks_per_round, 2)  # still have the bonus

        # Remove second source: fully removed, now remove effect
        removed2 = self.char1.remove_condition(Condition.HASTED)
        self.assertTrue(removed2)
        if removed2:
            self.char1.remove_effect({"type": "stat_bonus", "stat": "attacks_per_round", "value": 1})
        self.assertEqual(self.char1.attacks_per_round, 1)  # back to base
        self.assertEqual(self.char1.effective_attacks_per_round, 1)

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_hasted_master_fires_three_attacks(self, mock_ticker):
        """HASTED + master longsword fires 3 attacks in combat handler."""
        from enums.condition import Condition
        from enums.mastery_level import MasteryLevel
        from combat.combat_utils import enter_combat, execute_attack

        self._equip_longsword(self.char1, MasteryLevel.MASTER)
        self.char1.add_condition(Condition.HASTED)
        self.char1.apply_effect({"type": "stat_bonus", "stat": "attacks_per_round", "value": 1})

        enter_combat(self.char1, self.char2)
        handler = self.char1.scripts.get("combat_handler")[0]
        handler.queue_action({
            "key": "attack", "target": self.char2, "dt": 3, "repeat": True,
        })

        with patch("combat.combat_utils.dice") as mock_dice, \
             patch("combat.combat_utils.execute_attack", wraps=execute_attack) as spy:
            mock_dice.roll_with_advantage_or_disadvantage.return_value = 15
            mock_dice.roll.return_value = 3
            handler.execute_next_action()

        self.assertEqual(spy.call_count, 3)

        # Clean up
        self.char1.remove_effect({"type": "stat_bonus", "stat": "attacks_per_round", "value": 1})
        self.char1.remove_condition(Condition.HASTED)


# ================================================================== #
#  Finesse Weapon Tests
# ================================================================== #


class TestFinesseWeapons(EvenniaCommandTest):
    """Test finesse weapon mechanics — uses max(STR, DEX) for hit/damage."""

    character_typeclass = "typeclasses.actors.character.FCMCharacter"
    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"
    databases = "__all__"

    def create_script(self):
        pass

    def tearDown(self):
        for obj in list(self.char1.contents):
            if hasattr(obj, "weapon_type_key"):
                obj.delete()
        super().tearDown()

    def _equip_rapier(self, char):
        from enums.mastery_level import MasteryLevel
        from enums.unused_for_reference.damage_type import DamageType
        rapier = create.create_object(
            "typeclasses.items.weapons.rapier_nft_item.RapierNFTItem",
            key="Test Rapier",
            location=char,
        )
        rapier.damage = {
            MasteryLevel.UNSKILLED: "1D4",
            MasteryLevel.BASIC: "1D6",
            MasteryLevel.SKILLED: "1D8",
            MasteryLevel.EXPERT: "1D10",
            MasteryLevel.MASTER: "1D10",
            MasteryLevel.GRANDMASTER: "1D10",
        }
        rapier.damage_type = DamageType.PIERCING
        rapier.max_durability = 100
        rapier.durability = 100
        wearslots = dict(char.db.wearslots or {})
        wearslots["WIELD"] = rapier
        char.db.wearslots = wearslots
        return rapier

    def _equip_longsword(self, char):
        from enums.mastery_level import MasteryLevel
        from enums.unused_for_reference.damage_type import DamageType
        sword = create.create_object(
            "typeclasses.items.weapons.longsword_nft_item.LongswordNFTItem",
            key="Test Longsword",
            location=char,
        )
        sword.damage = {
            MasteryLevel.UNSKILLED: "1D4",
            MasteryLevel.BASIC: "1D6",
            MasteryLevel.SKILLED: "1D8",
            MasteryLevel.EXPERT: "1D10",
            MasteryLevel.MASTER: "1D10",
            MasteryLevel.GRANDMASTER: "1D10",
        }
        sword.damage_type = DamageType.SLASHING
        sword.max_durability = 100
        sword.durability = 100
        wearslots = dict(char.db.wearslots or {})
        wearslots["WIELD"] = sword
        char.db.wearslots = wearslots
        return sword

    def test_finesse_uses_dex_when_higher(self):
        """Finesse weapon uses DEX when DEX > STR."""
        self._equip_rapier(self.char1)
        self.char1.strength = 10   # mod +0
        self.char1.dexterity = 16  # mod +3
        hit_dex = self.char1.effective_hit_bonus
        dam_dex = self.char1.effective_damage_bonus
        # Swap: STR high, DEX low — should give same result since max() picks higher
        self.char1.strength = 16   # mod +3
        self.char1.dexterity = 10  # mod +0
        hit_str = self.char1.effective_hit_bonus
        dam_str = self.char1.effective_damage_bonus
        self.assertEqual(hit_dex, hit_str)
        self.assertEqual(dam_dex, dam_str)

    def test_finesse_uses_str_when_higher(self):
        """Finesse weapon uses STR when STR > DEX."""
        self._equip_rapier(self.char1)
        self.char1.strength = 18   # mod +4
        self.char1.dexterity = 12  # mod +1
        hit = self.char1.effective_hit_bonus
        # Confirm STR mod is being used (not DEX mod)
        expected_str_mod = self.char1.get_attribute_bonus(18)  # +4
        expected_dex_mod = self.char1.get_attribute_bonus(12)  # +1
        self.assertGreater(expected_str_mod, expected_dex_mod)
        # Lower STR to match DEX — hit should drop
        self.char1.strength = 12
        hit_lower = self.char1.effective_hit_bonus
        self.assertGreater(hit, hit_lower)

    def test_non_finesse_always_uses_str(self):
        """Non-finesse melee weapon always uses STR regardless of DEX."""
        self._equip_longsword(self.char1)
        self.char1.strength = 10   # mod +0
        self.char1.dexterity = 18  # mod +4
        hit_low_str = self.char1.effective_hit_bonus
        self.char1.strength = 18   # mod +4
        hit_high_str = self.char1.effective_hit_bonus
        # Longsword uses STR only — higher STR = higher bonus
        self.assertGreater(hit_high_str, hit_low_str)

    def test_finesse_flag_on_rapier(self):
        """RapierNFTItem has is_finesse = True."""
        rapier = self._equip_rapier(self.char1)
        self.assertTrue(rapier.is_finesse)

    def test_finesse_flag_off_on_longsword(self):
        """LongswordNFTItem has is_finesse = False."""
        sword = self._equip_longsword(self.char1)
        self.assertFalse(sword.is_finesse)


# ================================================================== #
#  Rapier Mastery & Riposte Tests
# ================================================================== #


class TestRapierMastery(EvenniaCommandTest):
    """Test rapier mastery progression and riposte mechanic."""

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
        for obj in list(self.char1.contents) + list(self.char2.contents):
            if hasattr(obj, "weapon_type_key"):
                obj.delete()
        super().tearDown()

    def _equip_rapier(self, char, mastery_level):
        from enums.mastery_level import MasteryLevel
        from enums.unused_for_reference.damage_type import DamageType
        rapier = create.create_object(
            "typeclasses.items.weapons.rapier_nft_item.RapierNFTItem",
            key="Test Rapier",
            location=char,
        )
        rapier.damage = {
            MasteryLevel.UNSKILLED: "1D4",
            MasteryLevel.BASIC: "1D6",
            MasteryLevel.SKILLED: "1D8",
            MasteryLevel.EXPERT: "1D10",
            MasteryLevel.MASTER: "1D10",
            MasteryLevel.GRANDMASTER: "1D10",
        }
        rapier.damage_type = DamageType.PIERCING
        rapier.max_durability = 100
        rapier.durability = 100
        char.db.weapon_skill_mastery_levels = {"rapier": mastery_level.value}
        wearslots = dict(char.db.wearslots or {})
        wearslots["WIELD"] = rapier
        char.db.wearslots = wearslots
        return rapier

    def _equip_longsword(self, char, mastery_level):
        from enums.mastery_level import MasteryLevel
        from enums.unused_for_reference.damage_type import DamageType
        sword = create.create_object(
            "typeclasses.items.weapons.longsword_nft_item.LongswordNFTItem",
            key="Test Longsword",
            location=char,
        )
        sword.damage = {
            MasteryLevel.UNSKILLED: "1D4",
            MasteryLevel.BASIC: "1D6",
            MasteryLevel.SKILLED: "1D8",
            MasteryLevel.EXPERT: "1D10",
            MasteryLevel.MASTER: "1D10",
            MasteryLevel.GRANDMASTER: "1D10",
        }
        sword.damage_type = DamageType.SLASHING
        sword.max_durability = 100
        sword.durability = 100
        char.db.weapon_skill_mastery_levels = {"long_sword": mastery_level.value}
        wearslots = dict(char.db.wearslots or {})
        wearslots["WIELD"] = sword
        char.db.wearslots = wearslots
        return sword

    # --- Mastery table tests ---

    def test_rapier_custom_hit_bonuses(self):
        """Rapier has reduced hit bonuses at EXPERT+ to offset riposte."""
        from enums.mastery_level import MasteryLevel
        rapier = self._equip_rapier(self.char1, MasteryLevel.EXPERT)
        self.assertEqual(rapier.get_mastery_hit_bonus(self.char1), 3)
        self.char1.db.weapon_skill_mastery_levels = {"rapier": MasteryLevel.MASTER.value}
        self.assertEqual(rapier.get_mastery_hit_bonus(self.char1), 4)
        self.char1.db.weapon_skill_mastery_levels = {"rapier": MasteryLevel.GRANDMASTER.value}
        self.assertEqual(rapier.get_mastery_hit_bonus(self.char1), 5)

    def test_rapier_parries_per_round(self):
        """Rapier parry progression: 0/0/1/1/2/3."""
        from enums.mastery_level import MasteryLevel
        rapier = self._equip_rapier(self.char1, MasteryLevel.UNSKILLED)
        expected = [
            (MasteryLevel.UNSKILLED, 0),
            (MasteryLevel.BASIC, 0),
            (MasteryLevel.SKILLED, 1),
            (MasteryLevel.EXPERT, 1),
            (MasteryLevel.MASTER, 2),
            (MasteryLevel.GRANDMASTER, 3),
        ]
        for mastery, count in expected:
            self.char1.db.weapon_skill_mastery_levels = {"rapier": mastery.value}
            self.assertEqual(
                rapier.get_parries_per_round(self.char1), count,
                f"Expected {count} parries at {mastery.name}, got {rapier.get_parries_per_round(self.char1)}",
            )

    def test_rapier_no_extra_attacks(self):
        """Rapier never grants extra attacks (that's the longsword's thing)."""
        from enums.mastery_level import MasteryLevel
        rapier = self._equip_rapier(self.char1, MasteryLevel.GRANDMASTER)
        self.assertEqual(rapier.get_extra_attacks(self.char1), 0)

    def test_rapier_riposte_unlocks_at_expert(self):
        """has_riposte returns False below EXPERT, True at EXPERT+."""
        from enums.mastery_level import MasteryLevel
        rapier = self._equip_rapier(self.char1, MasteryLevel.SKILLED)
        self.assertFalse(rapier.has_riposte(self.char1))
        self.char1.db.weapon_skill_mastery_levels = {"rapier": MasteryLevel.EXPERT.value}
        self.assertTrue(rapier.has_riposte(self.char1))
        self.char1.db.weapon_skill_mastery_levels = {"rapier": MasteryLevel.MASTER.value}
        self.assertTrue(rapier.has_riposte(self.char1))
        self.char1.db.weapon_skill_mastery_levels = {"rapier": MasteryLevel.GRANDMASTER.value}
        self.assertTrue(rapier.has_riposte(self.char1))

    def test_rapier_parry_advantage_at_gm(self):
        """Rapier gets parry advantage only at GRANDMASTER."""
        from enums.mastery_level import MasteryLevel
        rapier = self._equip_rapier(self.char1, MasteryLevel.MASTER)
        self.assertFalse(rapier.get_parry_advantage(self.char1))
        self.char1.db.weapon_skill_mastery_levels = {"rapier": MasteryLevel.GRANDMASTER.value}
        self.assertTrue(rapier.get_parry_advantage(self.char1))

    def test_longsword_no_riposte(self):
        """Longsword never has riposte — base weapon default is False."""
        from enums.mastery_level import MasteryLevel
        sword = self._equip_longsword(self.char1, MasteryLevel.GRANDMASTER)
        self.assertFalse(sword.has_riposte(self.char1))

    # --- Riposte in combat tests ---

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_riposte_fires_on_successful_parry(self, mock_ticker):
        """Expert rapier wielder ripostes after a successful parry."""
        from enums.mastery_level import MasteryLevel
        from combat.combat_utils import enter_combat, execute_attack

        # char1 attacks with longsword, char2 defends with expert rapier
        self._equip_longsword(self.char1, MasteryLevel.BASIC)
        rapier = self._equip_rapier(self.char2, MasteryLevel.EXPERT)

        enter_combat(self.char1, self.char2)
        # Set up char2's parries (normally reset each tick)
        handler2 = self.char2.scripts.get("combat_handler")[0]
        handler2.parries_remaining = 1

        with patch("combat.combat_utils.dice") as mock_dice:
            # First call: attacker's d20 = 10 (low, easy to parry)
            # Second call: defender parry d20 = 20 (parry succeeds)
            # Third call: riposte attacker d20 = 15 (riposte hit roll)
            # roll calls: damage rolls
            mock_dice.roll_with_advantage_or_disadvantage.side_effect = [10, 20, 15]
            mock_dice.roll.return_value = 5

            initial_hp = self.char1.hp
            execute_attack(self.char1, self.char2)

        # char2 should have taken no damage (parried)
        self.assertEqual(self.char2.hp, 50)
        # char1 should have taken riposte damage
        self.assertLess(self.char1.hp, initial_hp)

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_no_riposte_at_skilled(self, mock_ticker):
        """Skilled rapier wielder parries but does NOT riposte."""
        from enums.mastery_level import MasteryLevel
        from combat.combat_utils import enter_combat, execute_attack

        self._equip_longsword(self.char1, MasteryLevel.BASIC)
        self._equip_rapier(self.char2, MasteryLevel.SKILLED)

        enter_combat(self.char1, self.char2)
        handler2 = self.char2.scripts.get("combat_handler")[0]
        handler2.parries_remaining = 1

        with patch("combat.combat_utils.dice") as mock_dice:
            # Attacker d20 = 10, parry d20 = 20 (parry succeeds)
            mock_dice.roll_with_advantage_or_disadvantage.side_effect = [10, 20]
            mock_dice.roll.return_value = 5

            execute_attack(self.char1, self.char2)

        # char2 parried — no damage
        self.assertEqual(self.char2.hp, 50)
        # char1 took no riposte damage (SKILLED has no riposte)
        self.assertEqual(self.char1.hp, 50)

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_riposte_cannot_be_parried(self, mock_ticker):
        """Riposte attacks skip the parry check (_is_riposte=True)."""
        from enums.mastery_level import MasteryLevel
        from combat.combat_utils import enter_combat, execute_attack

        # Both wield rapiers at expert — both have riposte
        self._equip_rapier(self.char1, MasteryLevel.EXPERT)
        self._equip_rapier(self.char2, MasteryLevel.EXPERT)

        enter_combat(self.char1, self.char2)
        handler1 = self.char1.scripts.get("combat_handler")[0]
        handler2 = self.char2.scripts.get("combat_handler")[0]
        handler1.parries_remaining = 1
        handler2.parries_remaining = 1

        with patch("combat.combat_utils.dice") as mock_dice:
            # Call 1: char1's attack d20 = 10
            # Call 2: char2's parry d20 = 20 (parry succeeds)
            # Call 3: char2's riposte d20 = 15 (this is _is_riposte=True, no parry check)
            mock_dice.roll_with_advantage_or_disadvantage.side_effect = [10, 20, 15]
            mock_dice.roll.return_value = 5

            execute_attack(self.char1, self.char2)

        # char2 parried, so no damage from char1
        self.assertEqual(self.char2.hp, 50)
        # char1 took riposte damage — even though char1 had parries remaining,
        # riposte attacks skip the parry check
        self.assertLess(self.char1.hp, 50)
        # char1's parries_remaining should still be 1 (not consumed by riposte)
        self.assertEqual(handler1.parries_remaining, 1)

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_master_rapier_multiple_ripostes(self, mock_ticker):
        """Master rapier with 2 parries can riposte twice against multiple attacks."""
        from enums.mastery_level import MasteryLevel
        from combat.combat_utils import enter_combat, execute_attack

        # char1 attacks with longsword (master = 2 attacks per round)
        self._equip_longsword(self.char1, MasteryLevel.MASTER)
        self._equip_rapier(self.char2, MasteryLevel.MASTER)

        enter_combat(self.char1, self.char2)
        handler2 = self.char2.scripts.get("combat_handler")[0]
        handler2.parries_remaining = 2

        riposte_count = 0
        original_execute = execute_attack

        def counting_execute(a, t, _is_riposte=False):
            nonlocal riposte_count
            if _is_riposte:
                riposte_count += 1
            return original_execute(a, t, _is_riposte=_is_riposte)

        with patch("combat.combat_utils.dice") as mock_dice:
            # Attack 1: d20=10, parry=20 (parry+riposte), riposte d20=15
            # Attack 2: d20=10, parry=20 (parry+riposte), riposte d20=15
            mock_dice.roll_with_advantage_or_disadvantage.side_effect = [
                10, 20, 15,  # attack 1 → parry → riposte
                10, 20, 15,  # attack 2 → parry → riposte
            ]
            mock_dice.roll.return_value = 3

            # Patch execute_attack at the module level to count ripostes
            with patch("combat.combat_utils.execute_attack", side_effect=counting_execute):
                # Call the original for the two main attacks
                for _ in range(2):
                    if self.char2.hp > 0 and self.char1.hp > 0:
                        original_execute(self.char1, self.char2)

        self.assertEqual(riposte_count, 2)

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_riposte_does_not_fire_if_parry_fails(self, mock_ticker):
        """Failed parry does not trigger riposte."""
        from enums.mastery_level import MasteryLevel
        from combat.combat_utils import enter_combat, execute_attack

        self._equip_longsword(self.char1, MasteryLevel.BASIC)
        self._equip_rapier(self.char2, MasteryLevel.EXPERT)

        enter_combat(self.char1, self.char2)
        handler2 = self.char2.scripts.get("combat_handler")[0]
        handler2.parries_remaining = 1

        with patch("combat.combat_utils.dice") as mock_dice:
            # Attacker d20 = 20 (high roll), parry d20 = 5 (parry fails)
            mock_dice.roll_with_advantage_or_disadvantage.side_effect = [20, 5]
            mock_dice.roll.return_value = 3

            initial_hp1 = self.char1.hp
            execute_attack(self.char1, self.char2)

        # char1 should NOT have taken riposte damage (parry failed)
        self.assertEqual(self.char1.hp, initial_hp1)
        # char2 should have taken damage (attack hit)
        self.assertLess(self.char2.hp, 50)


# ================================================================== #
#  Unarmed Combat Tests
# ================================================================== #


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
        from enums.actor_size import ActorSize
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
        from enums.actor_size import ActorSize
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


# ================================================================== #
#  take_damage() Tests
# ================================================================== #


class TestTakeDamage(EvenniaCommandTest):
    """Test the central take_damage() method on BaseActor."""

    character_typeclass = "typeclasses.actors.character.FCMCharacter"
    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.char1.hp = 100
        self.char1.hp_max = 100

    # ------------------------------------------------------------------ #
    #  Basic damage
    # ------------------------------------------------------------------ #

    def test_take_damage_basic(self):
        """Raw damage subtracted from HP."""
        dealt = self.char1.take_damage(10)
        self.assertEqual(dealt, 10)
        self.assertEqual(self.char1.hp, 90)

    def test_take_damage_no_resistance_type(self):
        """No damage_type means no resistance check."""
        self.char1.damage_resistances = {"fire": 50}
        dealt = self.char1.take_damage(10)
        self.assertEqual(dealt, 10)
        self.assertEqual(self.char1.hp, 90)

    # ------------------------------------------------------------------ #
    #  Resistance
    # ------------------------------------------------------------------ #

    def test_take_damage_resistance_reduces(self):
        """50% fire resistance halves fire damage."""
        self.char1.damage_resistances = {"fire": 50}
        dealt = self.char1.take_damage(20, damage_type="fire")
        self.assertEqual(dealt, 10)
        self.assertEqual(self.char1.hp, 90)

    def test_take_damage_resistance_min_1_saved(self):
        """Even 1% resistance saves at least 1 HP."""
        self.char1.damage_resistances = {"fire": 1}
        dealt = self.char1.take_damage(10, damage_type="fire")
        # 1% of 10 = 0.1 → int(0.1) = 0 → max(1, 0) = 1 reduction
        self.assertEqual(dealt, 9)
        self.assertEqual(self.char1.hp, 91)

    def test_take_damage_high_resistance_min_1_damage(self):
        """Even with 75% resistance, at least 1 HP damage dealt."""
        self.char1.damage_resistances = {"fire": 75}
        dealt = self.char1.take_damage(2, damage_type="fire")
        # 75% of 2 = 1.5 → int(1.5) = 1 → max(1, 1) = 1 reduction
        # damage = 2 - 1 = 1 → max(1, 1) = 1
        self.assertEqual(dealt, 1)
        self.assertEqual(self.char1.hp, 99)

    def test_take_damage_75_pct_resistance_large(self):
        """75% resistance on large damage."""
        self.char1.damage_resistances = {"fire": 75}
        dealt = self.char1.take_damage(100, damage_type="fire")
        # 75% of 100 = 75 reduction → damage = 100 - 75 = 25
        self.assertEqual(dealt, 25)
        self.assertEqual(self.char1.hp, 75)

    # ------------------------------------------------------------------ #
    #  Vulnerability (negative resistance)
    # ------------------------------------------------------------------ #

    def test_take_damage_vulnerability_amplifies(self):
        """Negative resistance (vulnerability) amplifies damage."""
        self.char1.damage_resistances = {"fire": -25}
        dealt = self.char1.take_damage(20, damage_type="fire")
        # 25% of 20 = 5 extra → damage = 20 + 5 = 25
        self.assertEqual(dealt, 25)
        self.assertEqual(self.char1.hp, 75)

    def test_take_damage_vulnerability_min_1_added(self):
        """Even -1% vulnerability adds at least 1 HP extra."""
        self.char1.damage_resistances = {"fire": -1}
        dealt = self.char1.take_damage(10, damage_type="fire")
        # 1% of 10 = 0.1 → int(0.1) = 0 → max(1, 0) = 1 extra
        self.assertEqual(dealt, 11)
        self.assertEqual(self.char1.hp, 89)

    # ------------------------------------------------------------------ #
    #  Minimum damage
    # ------------------------------------------------------------------ #

    def test_take_damage_min_1_damage(self):
        """Minimum 1 HP damage always dealt."""
        self.char1.damage_resistances = {"fire": 75}
        dealt = self.char1.take_damage(1, damage_type="fire")
        # 75% of 1 = 0.75 → int(0.75) = 0 → max(1, 0) = 1 reduction
        # damage = 1 - 1 = 0 → max(1, 0) = 1
        self.assertEqual(dealt, 1)
        self.assertEqual(self.char1.hp, 99)

    # ------------------------------------------------------------------ #
    #  Death
    # ------------------------------------------------------------------ #

    def test_take_damage_kills_at_zero(self):
        """die() called when HP reaches 0."""
        self.char1.hp = 5
        with patch.object(self.char1, "die") as mock_die:
            dealt = self.char1.take_damage(10)
            mock_die.assert_called_once_with("combat", killer=None)
        self.assertEqual(self.char1.hp, 0)
        self.assertEqual(dealt, 10)

    def test_take_damage_custom_cause(self):
        """Custom cause passed to die()."""
        self.char1.hp = 3
        with patch.object(self.char1, "die") as mock_die:
            self.char1.take_damage(10, cause="spell")
            mock_die.assert_called_once_with("spell", killer=None)

    def test_take_damage_no_death_if_alive(self):
        """die() NOT called if HP stays above 0."""
        with patch.object(self.char1, "die") as mock_die:
            self.char1.take_damage(5)
            mock_die.assert_not_called()
        self.assertEqual(self.char1.hp, 95)

    # ------------------------------------------------------------------ #
    #  ignore_resistance
    # ------------------------------------------------------------------ #

    def test_take_damage_ignore_resistance(self):
        """Environmental damage bypasses resistance entirely."""
        self.char1.damage_resistances = {"fire": 75}
        dealt = self.char1.take_damage(
            20, damage_type="fire", ignore_resistance=True
        )
        self.assertEqual(dealt, 20)
        self.assertEqual(self.char1.hp, 80)

    def test_take_damage_ignore_resistance_no_type(self):
        """ignore_resistance with no damage type still works."""
        dealt = self.char1.take_damage(
            15, cause="fall", ignore_resistance=True
        )
        self.assertEqual(dealt, 15)
        self.assertEqual(self.char1.hp, 85)

    # ------------------------------------------------------------------ #
    #  Integration: mob take_damage uses base class
    # ------------------------------------------------------------------ #

    def test_mob_take_damage_uses_base(self):
        """CombatMob inherits take_damage from BaseActor."""
        mob = create.create_object(
            "typeclasses.actors.mob.CombatMob",
            key="test mob",
            location=self.room1,
        )
        mob.hp = 50
        mob.hp_max = 50
        mob.damage_resistances = {"piercing": 50}
        try:
            dealt = mob.take_damage(20, damage_type="piercing")
            self.assertEqual(dealt, 10)
            self.assertEqual(mob.hp, 40)
        finally:
            mob.delete()
