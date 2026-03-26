"""
Tests for the stab command (5e-style Sneak Attack for thieves).

evennia test --settings settings tests.command_tests.test_cmd_stab
"""

from unittest.mock import patch, MagicMock, call

from evennia.utils.test_resources import EvenniaCommandTest
from evennia.utils import create

from commands.all_char_cmds.cmd_attack import CmdAttack
from commands.class_skill_cmdsets.class_skill_cmds.cmd_backstab import CmdBackstab, STAB_DICE
from combat.combat_utils import enter_combat, execute_attack
from enums.condition import Condition
from enums.mastery_level import MasteryLevel
from enums.skills_enum import skills


class TestStabGates(EvenniaCommandTest):
    """Test stab command gate checks."""

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
        # Equip a finesse melee weapon so stab's weapon gate passes
        self.dagger = create.create_object(
            "typeclasses.items.weapons.dagger_nft_item.DaggerNFTItem",
            key="test dagger",
        )
        self.char1.db.wearslots["WIELD"] = self.dagger

    def tearDown(self):
        for char in (self.char1, self.char2):
            handlers = char.scripts.get("combat_handler")
            if handlers:
                for h in handlers:
                    h.stop()
                    h.delete()
        if self.dagger:
            self.dagger.delete()
        super().tearDown()

    def _set_stab_mastery(self, char, level):
        if not char.db.class_skill_mastery_levels:
            char.db.class_skill_mastery_levels = {}
        char.db.class_skill_mastery_levels[skills.STAB.value] = {"mastery": level.value, "classes": ["Thief"]}

    def test_no_finesse_weapon(self):
        """Can't stab without a finesse weapon."""
        self._set_stab_mastery(self.char1, MasteryLevel.BASIC)
        self.char1.add_condition(Condition.HIDDEN)
        self.char1.db.wearslots["WIELD"] = None
        result = self.call(CmdBackstab(), self.char2.key)
        self.assertIn("finesse weapon", result)

    def test_ranged_weapon_blocked(self):
        """Can't stab with a ranged finesse weapon."""
        self._set_stab_mastery(self.char1, MasteryLevel.BASIC)
        self.char1.add_condition(Condition.HIDDEN)
        self.dagger.weapon_type = "missile"
        result = self.call(CmdBackstab(), self.char2.key)
        self.assertIn("ranged weapon", result)
        self.dagger.weapon_type = "melee"  # restore

    def test_no_args_no_combat(self):
        """Stab with no args and not in combat → error."""
        self._set_stab_mastery(self.char1, MasteryLevel.BASIC)
        result = self.call(CmdBackstab(), "")
        self.assertIn("Stab who?", result)

    def test_self_target(self):
        """Can't stab yourself."""
        self._set_stab_mastery(self.char1, MasteryLevel.BASIC)
        self.char1.add_condition(Condition.HIDDEN)
        result = self.call(CmdBackstab(), self.char1.key)
        self.assertIn("can't stab yourself", result)

    def test_unskilled_blocked(self):
        """Unskilled characters can't use stab."""
        self._set_stab_mastery(self.char1, MasteryLevel.UNSKILLED)
        self.char1.add_condition(Condition.HIDDEN)
        result = self.call(CmdBackstab(), self.char2.key)
        self.assertIn("need training", result)

    def test_no_mastery_data(self):
        """Characters with no mastery data get mob_func."""
        self.char1.db.class_skill_mastery_levels = None
        result = self.call(CmdBackstab(), self.char2.key)
        self.assertIn("don't know", result)

    def test_target_dead(self):
        """Can't stab a dead target."""
        self._set_stab_mastery(self.char1, MasteryLevel.BASIC)
        self.char1.add_condition(Condition.HIDDEN)
        self.char2.hp = 0
        result = self.call(CmdBackstab(), self.char2.key)
        self.assertIn("already dead", result)

    def test_no_combat_room(self):
        """Can't stab in a non-combat room."""
        self._set_stab_mastery(self.char1, MasteryLevel.BASIC)
        self.char1.add_condition(Condition.HIDDEN)
        self.room1.allow_combat = False
        result = self.call(CmdBackstab(), self.char2.key)
        self.assertIn("not allowed", result)

    def test_no_advantage_no_hidden(self):
        """Can't stab without advantage or hidden."""
        self._set_stab_mastery(self.char1, MasteryLevel.BASIC)
        result = self.call(CmdBackstab(), self.char2.key)
        self.assertIn("need advantage", result)

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_no_advantage_mid_combat(self, mock_ticker):
        """Can't stab mid-combat without advantage."""
        self._set_stab_mastery(self.char1, MasteryLevel.BASIC)
        enter_combat(self.char1, self.char2)
        result = self.call(CmdBackstab(), self.char2.key)
        self.assertIn("need advantage", result)

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_already_used_this_round(self, mock_ticker):
        """Can't stab twice in one round."""
        self._set_stab_mastery(self.char1, MasteryLevel.SKILLED)
        enter_combat(self.char1, self.char2)
        handler = self.char1.scripts.get("combat_handler")[0]
        handler.set_advantage(self.char2, rounds=2)
        # First stab
        self.call(CmdBackstab(), self.char2.key)
        # Second stab — should be blocked
        result = self.call(CmdBackstab(), self.char2.key)
        self.assertIn("already used stab", result)


class TestStabOpener(EvenniaCommandTest):
    """Test stab as a combat opener from stealth."""

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
        self.dagger = create.create_object(
            "typeclasses.items.weapons.dagger_nft_item.DaggerNFTItem",
            key="test dagger",
        )
        self.char1.db.wearslots["WIELD"] = self.dagger

    def tearDown(self):
        for char in (self.char1, self.char2):
            handlers = char.scripts.get("combat_handler")
            if handlers:
                for h in handlers:
                    h.stop()
                    h.delete()
        if self.dagger:
            self.dagger.delete()
        super().tearDown()

    def _set_stab_mastery(self, char, level):
        if not char.db.class_skill_mastery_levels:
            char.db.class_skill_mastery_levels = {}
        char.db.class_skill_mastery_levels[skills.STAB.value] = {"mastery": level.value, "classes": ["Thief"]}

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_opener_from_hidden(self, mock_ticker):
        """Stab from hidden enters combat, sets advantage and bonus dice, breaks hidden."""
        self._set_stab_mastery(self.char1, MasteryLevel.EXPERT)
        self.char1.add_condition(Condition.HIDDEN)

        result = self.call(CmdBackstab(), self.char2.key)

        # Hidden is broken
        self.assertFalse(self.char1.has_condition(Condition.HIDDEN))
        # Combat started
        handler = self.char1.scripts.get("combat_handler")
        self.assertTrue(handler)
        # Advantage set
        self.assertTrue(handler[0].has_advantage(self.char2))
        # Bonus dice set
        self.assertEqual(handler[0].bonus_attack_dice, "6d6")
        # Stab used flag set
        self.assertTrue(handler[0].stab_used)
        # Message
        self.assertIn("shadows", result)
        self.assertIn("+6d6", result)

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_opener_queues_attack(self, mock_ticker):
        """Opener from hidden queues repeating attack."""
        self._set_stab_mastery(self.char1, MasteryLevel.BASIC)
        self.char1.add_condition(Condition.HIDDEN)

        self.call(CmdBackstab(), self.char2.key)

        handler = self.char1.scripts.get("combat_handler")[0]
        action = handler.action_dict
        self.assertEqual(action["key"], "attack")
        self.assertEqual(action["target"], self.char2)
        self.assertTrue(action["repeat"])

    def test_opener_not_hidden_fails(self):
        """Not in combat and not hidden → blocked."""
        self._set_stab_mastery(self.char1, MasteryLevel.BASIC)
        result = self.call(CmdBackstab(), self.char2.key)
        self.assertIn("need advantage", result)

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_opener_correct_dice_per_mastery(self, mock_ticker):
        """Each mastery level sets the correct bonus dice."""
        for mastery, expected_dice in STAB_DICE.items():
            # Clean up from previous iteration
            for char in (self.char1, self.char2):
                handlers = char.scripts.get("combat_handler")
                if handlers:
                    for h in handlers:
                        h.stop()
                        h.delete()
            self.char2.hp = 20

            self._set_stab_mastery(self.char1, mastery)
            self.char1.add_condition(Condition.HIDDEN)

            self.call(CmdBackstab(), self.char2.key)

            handler = self.char1.scripts.get("combat_handler")[0]
            self.assertEqual(
                handler.bonus_attack_dice, expected_dice,
                f"Mastery {mastery.name} should set {expected_dice}"
            )


class TestStabMidCombat(EvenniaCommandTest):
    """Test stab used mid-combat with existing advantage."""

    character_typeclass = "typeclasses.actors.character.FCMCharacter"
    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.room1.allow_combat = True
        self.room1.allow_pvp = True  # PvP needed so PCs are enemies
        self.char1.hp = 20
        self.char1.hp_max = 20
        self.char2.hp = 20
        self.char2.hp_max = 20
        self.dagger = create.create_object(
            "typeclasses.items.weapons.dagger_nft_item.DaggerNFTItem",
            key="test dagger",
        )
        self.char1.db.wearslots["WIELD"] = self.dagger

    def tearDown(self):
        for char in (self.char1, self.char2):
            handlers = char.scripts.get("combat_handler")
            if handlers:
                for h in handlers:
                    h.stop()
                    h.delete()
        if self.dagger:
            self.dagger.delete()
        super().tearDown()

    def _set_stab_mastery(self, char, level):
        if not char.db.class_skill_mastery_levels:
            char.db.class_skill_mastery_levels = {}
        char.db.class_skill_mastery_levels[skills.STAB.value] = {"mastery": level.value, "classes": ["Thief"]}

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_mid_combat_with_advantage(self, mock_ticker):
        """Mid-combat stab with advantage sets bonus dice and stab_used."""
        self._set_stab_mastery(self.char1, MasteryLevel.MASTER)
        enter_combat(self.char1, self.char2)
        handler = self.char1.scripts.get("combat_handler")[0]
        handler.set_advantage(self.char2, rounds=1)

        result = self.call(CmdBackstab(), self.char2.key)

        self.assertEqual(handler.bonus_attack_dice, "8d6")
        self.assertTrue(handler.stab_used)
        self.assertIn("+8d6", result)

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_no_args_defaults_to_target(self, mock_ticker):
        """Stab with no args in combat defaults to current attack target."""
        self._set_stab_mastery(self.char1, MasteryLevel.BASIC)
        enter_combat(self.char1, self.char2)
        handler = self.char1.scripts.get("combat_handler")[0]
        handler.queue_action({
            "key": "attack", "target": self.char2, "dt": 4, "repeat": True,
        })
        handler.set_advantage(self.char2, rounds=1)

        result = self.call(CmdBackstab(), "")

        self.assertEqual(handler.bonus_attack_dice, "2d6")
        self.assertTrue(handler.stab_used)

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_stab_used_resets_each_tick(self, mock_ticker):
        """stab_used is reset to False at the start of each tick."""
        self._set_stab_mastery(self.char1, MasteryLevel.BASIC)
        enter_combat(self.char1, self.char2)
        handler = self.char1.scripts.get("combat_handler")[0]
        handler.stab_used = True

        # Simulate tick — execute_next_action resets per-round flags
        handler.queue_action({
            "key": "attack", "target": self.char2, "dt": 4, "repeat": True,
        })
        handler.execute_next_action()

        self.assertFalse(handler.stab_used)

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_hidden_mid_combat_grants_advantage(self, mock_ticker):
        """If hidden mid-combat, stab breaks hidden and grants advantage."""
        self._set_stab_mastery(self.char1, MasteryLevel.SKILLED)
        enter_combat(self.char1, self.char2)
        handler = self.char1.scripts.get("combat_handler")[0]
        # Somehow hidden mid-combat (quaff invis potion, etc.)
        self.char1.add_condition(Condition.HIDDEN)

        result = self.call(CmdBackstab(), self.char2.key)

        self.assertFalse(self.char1.has_condition(Condition.HIDDEN))
        self.assertEqual(handler.bonus_attack_dice, "4d6")
        self.assertTrue(handler.stab_used)


class TestStabDamage(EvenniaCommandTest):
    """Test bonus_attack_dice integration in execute_attack."""

    character_typeclass = "typeclasses.actors.character.FCMCharacter"
    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.room1.allow_combat = True
        self.room1.allow_pvp = True
        self.char1.hp = 100
        self.char1.hp_max = 100
        self.char2.hp = 100
        self.char2.hp_max = 100

    def tearDown(self):
        for char in (self.char1, self.char2):
            handlers = char.scripts.get("combat_handler")
            if handlers:
                for h in handlers:
                    h.stop()
                    h.delete()
        super().tearDown()

    @patch("combat.combat_handler.TICKER_HANDLER")
    @patch("combat.combat_utils.dice")
    def test_bonus_dice_applied_on_hit(self, mock_dice, mock_ticker):
        """Bonus attack dice are rolled and added to damage on hit."""
        enter_combat(self.char1, self.char2)
        handler = self.char1.scripts.get("combat_handler")[0]
        handler.bonus_attack_dice = "4d6"

        # d20 roll = 19 (hit), weapon damage = 5, bonus dice = 12
        mock_dice.roll_with_advantage_or_disadvantage.return_value = 19
        mock_dice.roll.side_effect = [5, 12]  # weapon damage, bonus dice

        execute_attack(self.char1, self.char2)

        # bonus_attack_dice should be consumed
        self.assertEqual(handler.bonus_attack_dice, "")
        # dice.roll should have been called with bonus dice string
        calls = mock_dice.roll.call_args_list
        self.assertEqual(calls[1], call("4d6"))

    @patch("combat.combat_handler.TICKER_HANDLER")
    @patch("combat.combat_utils.dice")
    def test_bonus_dice_doubled_on_crit(self, mock_dice, mock_ticker):
        """Critical hit doubles both weapon dice and bonus attack dice."""
        enter_combat(self.char1, self.char2)
        handler = self.char1.scripts.get("combat_handler")[0]
        handler.bonus_attack_dice = "6d6"

        # d20 = 20 (crit), weapon base = 5, bonus = 15, crit weapon = 5, crit bonus = 15
        mock_dice.roll_with_advantage_or_disadvantage.return_value = 20
        mock_dice.roll.side_effect = [5, 15, 5, 15]  # base, bonus, crit weapon, crit bonus

        execute_attack(self.char1, self.char2)

        # Should have 4 dice.roll calls: base weapon, bonus, crit weapon, crit bonus
        roll_calls = mock_dice.roll.call_args_list
        self.assertTrue(len(roll_calls) >= 4)
        # The bonus dice string should appear twice (base + crit)
        bonus_calls = [c for c in roll_calls if c == call("6d6")]
        self.assertEqual(len(bonus_calls), 2)

    @patch("combat.combat_handler.TICKER_HANDLER")
    @patch("combat.combat_utils.dice")
    def test_bonus_dice_wasted_on_miss(self, mock_dice, mock_ticker):
        """On a miss, bonus dice are consumed but not applied."""
        enter_combat(self.char1, self.char2)
        handler = self.char1.scripts.get("combat_handler")[0]
        handler.bonus_attack_dice = "4d6"

        # d20 = 1 (miss)
        mock_dice.roll_with_advantage_or_disadvantage.return_value = 1

        hp_before = self.char2.hp
        execute_attack(self.char1, self.char2)

        # Bonus consumed
        self.assertEqual(handler.bonus_attack_dice, "")
        # No bonus dice rolled (no dice.roll calls for bonus since it was a miss)
        # The miss path doesn't call dice.roll at all for damage
        bonus_calls = [c for c in mock_dice.roll.call_args_list if c == call("4d6")]
        self.assertEqual(len(bonus_calls), 0)

    @patch("combat.combat_handler.TICKER_HANDLER")
    def test_bonus_dice_cleared_on_stun(self, mock_ticker):
        """Pending bonus dice are cleared when action is skipped (stunned)."""
        enter_combat(self.char1, self.char2)
        handler = self.char1.scripts.get("combat_handler")[0]
        handler.bonus_attack_dice = "6d6"
        handler.queue_action({
            "key": "attack", "target": self.char2, "dt": 4, "repeat": True,
        })

        # Simulate being stunned
        self.char1.apply_named_effect("stunned", duration=1, duration_type="combat_rounds")

        handler.execute_next_action()

        # Bonus dice should be cleared
        self.assertEqual(handler.bonus_attack_dice, "")
