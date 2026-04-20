"""
Divine Dominion spell tests.

    evennia test --settings settings tests.spell_tests.test_divine_dominion
"""

from unittest.mock import patch, MagicMock

from evennia.utils.test_resources import EvenniaTest

from enums.condition import Condition
from enums.mastery_level import MasteryLevel
from enums.size import Size
from enums.skills_enum import skills
from world.spells.registry import SPELL_REGISTRY, get_spell


class TestCommand(EvenniaTest):
    """Test Command spell execution — divine dominion BASIC."""

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.spell = get_spell("command")
        self.char1.db.class_skill_mastery_levels = {"divine_dominion": 1}
        self.char1.mana = 500
        self.char1.db.spell_cooldowns = {}
        self.char1.wisdom = 14  # +2 mod
        self.char2.wisdom = 10  # +0 mod
        self.char2.hp = 200
        self.char2.hp_max = 200
        # Command is combat-only — mock a combat handler on the target
        self._mock_combat = patch.object(
            self.char2.scripts, "get",
            side_effect=lambda key: [MagicMock()] if key == "combat_handler" else [],
        )
        self._mock_combat.start()

    def tearDown(self):
        self._mock_combat.stop()
        super().tearDown()

    # --- Registration & attributes ---

    def test_registered(self):
        """Command should be in the registry."""
        self.assertIn("command", SPELL_REGISTRY)

    def test_attributes(self):
        """Command should have correct class attributes."""
        self.assertEqual(self.spell.name, "Command")
        self.assertEqual(self.spell.school, skills.DIVINE_DOMINION)
        self.assertEqual(self.spell.min_mastery, MasteryLevel.BASIC)
        self.assertEqual(self.spell.target_type, "actor_hostile")
        self.assertTrue(self.spell.has_spell_arg)
        self.assertEqual(self.spell.cooldown, 0)

    def test_mana_costs(self):
        """Command mana costs should match design."""
        self.assertEqual(
            self.spell.mana_cost, {1: 5, 2: 8, 3: 10, 4: 14, 5: 16}
        )

    # --- Validation gates ---

    def test_invalid_command_word_refunds_mana(self):
        """Invalid command word should refund mana and return error."""
        start_mana = self.char1.mana
        success, result = self.spell.cast(
            self.char1, self.char2, spell_arg="dance",
        )
        self.assertFalse(success)
        self.assertEqual(self.char1.mana, start_mana)
        self.assertIn("Command what?", result["first"])

    def test_missing_command_word_refunds_mana(self):
        """Missing command word should refund mana and return error."""
        start_mana = self.char1.mana
        success, result = self.spell.cast(
            self.char1, self.char2, spell_arg=None,
        )
        self.assertFalse(success)
        self.assertEqual(self.char1.mana, start_mana)

    def test_combat_only_gate(self):
        """Out of combat should refund mana and return error."""
        # Remove combat handler mock
        self._mock_combat.stop()
        start_mana = self.char1.mana
        success, result = self.spell.cast(
            self.char1, self.char2, spell_arg="halt",
        )
        self.assertFalse(success)
        self.assertEqual(self.char1.mana, start_mana)
        self.assertIn("combat", result["first"].lower())
        # Restart mock for tearDown
        self._mock_combat.start()

    def test_size_gate_huge_immune(self):
        """HUGE+ creatures should be immune to Command."""
        self.char2.size = "huge"
        success, result = self.spell.cast(
            self.char1, self.char2, spell_arg="halt",
        )
        self.assertTrue(success)  # spell succeeds (mana spent)
        self.assertIn("massive", result["first"].lower())
        self.assertFalse(self.char2.has_effect("stunned"))

    # --- Contested check ---

    @patch("world.spells.divine_dominion.command.dice")
    def test_contested_check_failure(self, mock_dice):
        """Failed contested check should not apply any effect."""
        # Caster rolls low, target rolls high
        mock_dice.roll.side_effect = [1, 20]
        success, result = self.spell.cast(
            self.char1, self.char2, spell_arg="halt",
        )
        self.assertTrue(success)
        self.assertIn("resist", result["first"].lower())
        self.assertFalse(self.char2.has_effect("stunned"))

    @patch("world.spells.divine_dominion.command.dice")
    def test_contested_check_tie_fails(self, mock_dice):
        """Tie on contested check should fail (caster must beat)."""
        mock_dice.roll.side_effect = [10, 12]  # +2 wis each = 12 vs 12
        self.char2.wisdom = 14  # +2 mod to match caster
        success, result = self.spell.cast(
            self.char1, self.char2, spell_arg="halt",
        )
        self.assertTrue(success)
        self.assertIn("resist", result["first"].lower())

    @patch("world.spells.divine_dominion.command.dice")
    def test_mana_spent_on_failed_contest(self, mock_dice):
        """Mana should be spent even if the contested check fails."""
        mock_dice.roll.side_effect = [1, 20]
        start_mana = self.char1.mana
        self.spell.cast(self.char1, self.char2, spell_arg="halt")
        self.assertEqual(self.char1.mana, start_mana - 5)

    # --- HALT (stun) ---

    @patch("world.spells.divine_dominion.command.dice")
    def test_halt_applies_stunned(self, mock_dice):
        """Halt should apply STUNNED on successful contest."""
        mock_dice.roll.side_effect = [20, 1]
        self.spell.cast(self.char1, self.char2, spell_arg="halt")
        self.assertTrue(self.char2.has_effect("stunned"))

    @patch("world.spells.divine_dominion.command.dice")
    def test_halt_success_message(self, mock_dice):
        """Halt success should show STUNNED in message."""
        mock_dice.roll.side_effect = [20, 1]
        success, result = self.spell.cast(
            self.char1, self.char2, spell_arg="halt",
        )
        self.assertIn("STUNNED", result["first"])
        self.assertIn("HALT", result["first"])

    @patch("world.spells.divine_dominion.command.dice")
    def test_halt_scaling_basic(self, mock_dice):
        """BASIC halt should last 1 round."""
        mock_dice.roll.side_effect = [20, 1]
        self.spell.cast(self.char1, self.char2, spell_arg="halt")
        effect = self.char2.get_named_effect("stunned")
        self.assertEqual(effect["duration"], 1)

    @patch("world.spells.divine_dominion.command.dice")
    def test_halt_scaling_skilled(self, mock_dice):
        """SKILLED halt should last 2 rounds."""
        self.char1.db.class_skill_mastery_levels = {"divine_dominion": 2}
        mock_dice.roll.side_effect = [20, 1]
        self.spell.cast(self.char1, self.char2, spell_arg="halt")
        effect = self.char2.get_named_effect("stunned")
        self.assertEqual(effect["duration"], 2)

    @patch("world.spells.divine_dominion.command.dice")
    def test_halt_scaling_expert(self, mock_dice):
        """EXPERT halt should last 2 rounds."""
        self.char1.db.class_skill_mastery_levels = {"divine_dominion": 3}
        mock_dice.roll.side_effect = [20, 1]
        self.spell.cast(self.char1, self.char2, spell_arg="halt")
        effect = self.char2.get_named_effect("stunned")
        self.assertEqual(effect["duration"], 2)

    @patch("world.spells.divine_dominion.command.dice")
    def test_halt_scaling_master(self, mock_dice):
        """MASTER halt should last 3 rounds."""
        self.char1.db.class_skill_mastery_levels = {"divine_dominion": 4}
        mock_dice.roll.side_effect = [20, 1]
        self.spell.cast(self.char1, self.char2, spell_arg="halt")
        effect = self.char2.get_named_effect("stunned")
        self.assertEqual(effect["duration"], 3)

    @patch("world.spells.divine_dominion.command.dice")
    def test_halt_scaling_gm(self, mock_dice):
        """GM halt should last 3 rounds."""
        self.char1.db.class_skill_mastery_levels = {"divine_dominion": 5}
        mock_dice.roll.side_effect = [20, 1]
        self.spell.cast(self.char1, self.char2, spell_arg="halt")
        effect = self.char2.get_named_effect("stunned")
        self.assertEqual(effect["duration"], 3)

    @patch("world.spells.divine_dominion.command.dice")
    def test_halt_already_stunned(self, mock_dice):
        """Halt on already-stunned target should note it in message."""
        self.char2.apply_stunned(5)
        mock_dice.roll.side_effect = [20, 1]
        success, result = self.spell.cast(
            self.char1, self.char2, spell_arg="halt",
        )
        self.assertIn("already stunned", result["first"].lower())

    # --- GROVEL (prone) ---

    @patch("world.spells.divine_dominion.command.dice")
    def test_grovel_applies_prone(self, mock_dice):
        """Grovel should apply PRONE on successful contest."""
        mock_dice.roll.side_effect = [20, 1]
        self.spell.cast(self.char1, self.char2, spell_arg="grovel")
        self.assertTrue(self.char2.has_effect("prone"))

    @patch("world.spells.divine_dominion.command.dice")
    def test_grovel_success_message(self, mock_dice):
        """Grovel success should show PRONE in message."""
        mock_dice.roll.side_effect = [20, 1]
        success, result = self.spell.cast(
            self.char1, self.char2, spell_arg="grovel",
        )
        self.assertIn("PRONE", result["first"])
        self.assertIn("GROVEL", result["first"])

    @patch("world.spells.divine_dominion.command.dice")
    def test_grovel_scaling_basic(self, mock_dice):
        """BASIC grovel should last 1 round."""
        mock_dice.roll.side_effect = [20, 1]
        self.spell.cast(self.char1, self.char2, spell_arg="grovel")
        effect = self.char2.get_named_effect("prone")
        self.assertEqual(effect["duration"], 1)

    @patch("world.spells.divine_dominion.command.dice")
    def test_grovel_scaling_skilled(self, mock_dice):
        """SKILLED grovel should still last 1 round."""
        self.char1.db.class_skill_mastery_levels = {"divine_dominion": 2}
        mock_dice.roll.side_effect = [20, 1]
        self.spell.cast(self.char1, self.char2, spell_arg="grovel")
        effect = self.char2.get_named_effect("prone")
        self.assertEqual(effect["duration"], 1)

    @patch("world.spells.divine_dominion.command.dice")
    def test_grovel_scaling_expert(self, mock_dice):
        """EXPERT grovel should last 2 rounds."""
        self.char1.db.class_skill_mastery_levels = {"divine_dominion": 3}
        mock_dice.roll.side_effect = [20, 1]
        self.spell.cast(self.char1, self.char2, spell_arg="grovel")
        effect = self.char2.get_named_effect("prone")
        self.assertEqual(effect["duration"], 2)

    @patch("world.spells.divine_dominion.command.dice")
    def test_grovel_scaling_master(self, mock_dice):
        """MASTER grovel should last 2 rounds."""
        self.char1.db.class_skill_mastery_levels = {"divine_dominion": 4}
        mock_dice.roll.side_effect = [20, 1]
        self.spell.cast(self.char1, self.char2, spell_arg="grovel")
        effect = self.char2.get_named_effect("prone")
        self.assertEqual(effect["duration"], 2)

    @patch("world.spells.divine_dominion.command.dice")
    def test_grovel_scaling_gm(self, mock_dice):
        """GM grovel should last 3 rounds."""
        self.char1.db.class_skill_mastery_levels = {"divine_dominion": 5}
        mock_dice.roll.side_effect = [20, 1]
        self.spell.cast(self.char1, self.char2, spell_arg="grovel")
        effect = self.char2.get_named_effect("prone")
        self.assertEqual(effect["duration"], 3)

    @patch("world.spells.divine_dominion.command.dice")
    def test_grovel_already_prone(self, mock_dice):
        """Grovel on already-prone target should note it in message."""
        self.char2.apply_prone(5)
        mock_dice.roll.side_effect = [20, 1]
        success, result = self.spell.cast(
            self.char1, self.char2, spell_arg="grovel",
        )
        self.assertIn("already", result["first"].lower())

    # --- DROP (disarm) ---

    @patch("world.spells.divine_dominion.command.force_drop_weapon")
    @patch("world.spells.divine_dominion.command.dice")
    def test_drop_calls_force_drop(self, mock_dice, mock_drop):
        """Drop should call force_drop_weapon on successful contest."""
        mock_dice.roll.side_effect = [20, 1]
        mock_drop.return_value = (True, "iron sword")
        self.spell.cast(self.char1, self.char2, spell_arg="drop")
        mock_drop.assert_called_once_with(self.char2)

    @patch("world.spells.divine_dominion.command.force_drop_weapon")
    @patch("world.spells.divine_dominion.command.dice")
    def test_drop_success_message(self, mock_dice, mock_drop):
        """Drop success should mention the weapon name."""
        mock_dice.roll.side_effect = [20, 1]
        mock_drop.return_value = (True, "iron sword")
        success, result = self.spell.cast(
            self.char1, self.char2, spell_arg="drop",
        )
        self.assertIn("iron sword", result["first"])
        self.assertIn("DROP", result["first"])

    @patch("world.spells.divine_dominion.command.force_drop_weapon")
    @patch("world.spells.divine_dominion.command.dice")
    def test_drop_no_weapon(self, mock_dice, mock_drop):
        """Drop with no weapon should show appropriate message."""
        mock_dice.roll.side_effect = [20, 1]
        mock_drop.return_value = (False, "")
        success, result = self.spell.cast(
            self.char1, self.char2, spell_arg="drop",
        )
        self.assertIn("nothing to drop", result["first"].lower())

    # --- FLEE ---

    @patch("world.spells.divine_dominion.command.dice")
    def test_flee_executes_command(self, mock_dice):
        """Flee should call target.execute_cmd('flee')."""
        mock_dice.roll.side_effect = [20, 1]
        with patch.object(self.char2, "execute_cmd") as mock_exec:
            self.spell.cast(self.char1, self.char2, spell_arg="flee")
            mock_exec.assert_called_once_with("flee")

    @patch("world.spells.divine_dominion.command.dice")
    def test_flee_success_message(self, mock_dice):
        """Flee success should show FLEE in message."""
        mock_dice.roll.side_effect = [20, 1]
        with patch.object(self.char2, "execute_cmd"):
            success, result = self.spell.cast(
                self.char1, self.char2, spell_arg="flee",
            )
        self.assertIn("FLEE", result["first"])

    # --- Multi-perspective messaging ---

    @patch("world.spells.divine_dominion.command.dice")
    def test_all_perspectives_present(self, mock_dice):
        """All command results should include first/second/third."""
        mock_dice.roll.side_effect = [20, 1]
        success, result = self.spell.cast(
            self.char1, self.char2, spell_arg="halt",
        )
        self.assertTrue(success)
        self.assertIn("first", result)
        self.assertIn("second", result)
        self.assertIn("third", result)

class TestHold(EvenniaTest):
    """Test Hold spell execution — divine dominion EXPERT."""

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.spell = get_spell("hold")
        self.char1.db.class_skill_mastery_levels = {"divine_dominion": 3}
        self.char1.mana = 500
        self.char1.db.spell_cooldowns = {}
        self.char1.wisdom = 14  # +2 mod
        self.char2.wisdom = 10  # +0 mod
        self.char2.hp = 200
        self.char2.hp_max = 200

    # --- Registration & attributes ---

    def test_registered(self):
        """Hold should be in the registry."""
        self.assertIn("hold", SPELL_REGISTRY)

    def test_hold_person_not_registered(self):
        """Old hold_person key should not be in the registry."""
        self.assertNotIn("hold_person", SPELL_REGISTRY)

    def test_attributes(self):
        """Hold should have correct class attributes."""
        self.assertEqual(self.spell.name, "Hold")
        self.assertEqual(self.spell.school, skills.DIVINE_DOMINION)
        self.assertEqual(self.spell.min_mastery, MasteryLevel.EXPERT)
        self.assertEqual(self.spell.target_type, "actor_hostile")

    def test_mana_costs(self):
        """Hold mana costs should match design."""
        self.assertEqual(self.spell.mana_cost, {3: 28, 4: 39, 5: 49})

    def test_deducts_mana(self):
        """Hold should deduct 28 mana at EXPERT tier."""
        start_mana = self.char1.mana
        self.spell.cast(self.char1, self.char2)
        self.assertEqual(self.char1.mana, start_mana - 28)

    # --- Size gate ---

    def test_expert_can_hold_medium(self):
        """EXPERT should be able to hold MEDIUM targets."""
        self.char2.size = "medium"
        success, result = self.spell.cast(self.char1, self.char2)
        self.assertTrue(success)
        self.assertNotIn("too powerful", result["first"].lower())

    def test_expert_cannot_hold_large(self):
        """EXPERT should NOT be able to hold LARGE targets."""
        self.char2.size = "large"
        success, result = self.spell.cast(self.char1, self.char2)
        self.assertTrue(success)
        self.assertIn("too powerful", result["first"].lower())
        self.assertFalse(self.char2.has_effect("paralysed"))

    def test_master_can_hold_large(self):
        """MASTER should be able to hold LARGE targets."""
        self.char1.db.class_skill_mastery_levels = {"divine_dominion": 4}
        self.char2.size = "large"
        success, result = self.spell.cast(self.char1, self.char2)
        self.assertTrue(success)
        self.assertNotIn("too powerful", result["first"].lower())

    def test_master_cannot_hold_huge(self):
        """MASTER should NOT be able to hold HUGE targets."""
        self.char1.db.class_skill_mastery_levels = {"divine_dominion": 4}
        self.char2.size = "huge"
        success, result = self.spell.cast(self.char1, self.char2)
        self.assertTrue(success)
        self.assertIn("too powerful", result["first"].lower())
        self.assertFalse(self.char2.has_effect("paralysed"))

    def test_gm_can_hold_huge(self):
        """GM should be able to hold HUGE targets."""
        self.char1.db.class_skill_mastery_levels = {"divine_dominion": 5}
        self.char2.size = "huge"
        success, result = self.spell.cast(self.char1, self.char2)
        self.assertTrue(success)
        self.assertNotIn("too powerful", result["first"].lower())

    def test_gm_cannot_hold_gargantuan(self):
        """GM should NOT be able to hold GARGANTUAN targets."""
        self.char1.db.class_skill_mastery_levels = {"divine_dominion": 5}
        self.char2.size = "gargantuan"
        success, result = self.spell.cast(self.char1, self.char2)
        self.assertTrue(success)
        self.assertIn("too powerful", result["first"].lower())
        self.assertFalse(self.char2.has_effect("paralysed"))

    # --- Contested check ---

    @patch("world.spells.divine_dominion.hold.dice")
    def test_contested_check_success(self, mock_dice):
        """Successful contest should apply PARALYSED."""
        mock_dice.roll.side_effect = [20, 1]
        self.spell.cast(self.char1, self.char2)
        self.assertTrue(self.char2.has_effect("paralysed"))

    @patch("world.spells.divine_dominion.hold.dice")
    def test_contested_check_failure(self, mock_dice):
        """Failed contest should not apply any effect."""
        mock_dice.roll.side_effect = [1, 20]
        success, result = self.spell.cast(self.char1, self.char2)
        self.assertTrue(success)
        self.assertIn("resist", result["first"].lower())
        self.assertFalse(self.char2.has_effect("paralysed"))

    @patch("world.spells.divine_dominion.hold.dice")
    def test_contested_check_tie_fails(self, mock_dice):
        """Tie should fail (caster must beat)."""
        # Caster: d20=10 + WIS(+2) + mastery(+4) = 16
        # Target: d20=16 + WIS(+0) = 16  → tie → fail
        mock_dice.roll.side_effect = [10, 16]
        success, result = self.spell.cast(self.char1, self.char2)
        self.assertIn("resist", result["first"].lower())

    @patch("world.spells.divine_dominion.hold.dice")
    def test_mana_spent_on_failed_contest(self, mock_dice):
        """Mana should be spent even on failed contest."""
        mock_dice.roll.side_effect = [1, 20]
        start_mana = self.char1.mana
        self.spell.cast(self.char1, self.char2)
        self.assertEqual(self.char1.mana, start_mana - 28)

    # --- Duration scaling ---

    @patch("world.spells.divine_dominion.hold.dice")
    def test_duration_expert(self, mock_dice):
        """EXPERT hold should last 3 rounds."""
        mock_dice.roll.side_effect = [20, 1]
        self.spell.cast(self.char1, self.char2)
        effect = self.char2.get_named_effect("paralysed")
        self.assertEqual(effect["duration"], 3)

    @patch("world.spells.divine_dominion.hold.dice")
    def test_duration_master(self, mock_dice):
        """MASTER hold should last 4 rounds."""
        self.char1.db.class_skill_mastery_levels = {"divine_dominion": 4}
        mock_dice.roll.side_effect = [20, 1]
        self.spell.cast(self.char1, self.char2)
        effect = self.char2.get_named_effect("paralysed")
        self.assertEqual(effect["duration"], 4)

    @patch("world.spells.divine_dominion.hold.dice")
    def test_duration_gm(self, mock_dice):
        """GM hold should last 5 rounds."""
        self.char1.db.class_skill_mastery_levels = {"divine_dominion": 5}
        mock_dice.roll.side_effect = [20, 1]
        self.spell.cast(self.char1, self.char2)
        effect = self.char2.get_named_effect("paralysed")
        self.assertEqual(effect["duration"], 5)

    # --- Save DC ---

    @patch("world.spells.divine_dominion.hold.dice")
    def test_save_dc_is_full_caster_total(self, mock_dice):
        """Save DC should be caster's d20 + WIS + mastery, not raw d20."""
        # Caster: d20=15, WIS bonus=+2, mastery bonus=+4 (EXPERT) → total 21
        mock_dice.roll.side_effect = [15, 1]
        self.spell.cast(self.char1, self.char2)
        effect = self.char2.get_named_effect("paralysed")
        self.assertIsNotNone(effect)
        # 15 + 2 (WIS bonus for 14) + 4 (EXPERT mastery bonus) = 21
        self.assertEqual(effect["save_dc"], 21)

    @patch("world.spells.divine_dominion.hold.dice")
    def test_save_stat_is_wisdom(self, mock_dice):
        """Per-round save should use wisdom."""
        mock_dice.roll.side_effect = [20, 1]
        self.spell.cast(self.char1, self.char2)
        effect = self.char2.get_named_effect("paralysed")
        self.assertEqual(effect["save_stat"], "wisdom")

    # --- Anti-stacking ---

    @patch("world.spells.divine_dominion.hold.dice")
    def test_already_paralysed(self, mock_dice):
        """Hold on already-paralysed target should note it in message."""
        self.char2.apply_paralysed(5)
        mock_dice.roll.side_effect = [20, 1]
        success, result = self.spell.cast(self.char1, self.char2)
        self.assertIn("already", result["first"].lower())

    # --- Multi-perspective messaging ---

    @patch("world.spells.divine_dominion.hold.dice")
    def test_all_perspectives_present(self, mock_dice):
        """All results should include first/second/third."""
        mock_dice.roll.side_effect = [20, 1]
        success, result = self.spell.cast(self.char1, self.char2)
        self.assertTrue(success)
        self.assertIn("first", result)
        self.assertIn("second", result)
        self.assertIn("third", result)

    @patch("world.spells.divine_dominion.hold.dice")
    def test_success_message(self, mock_dice):
        """Success message should mention PARALYSED."""
        mock_dice.roll.side_effect = [20, 1]
        success, result = self.spell.cast(self.char1, self.char2)
        self.assertIn("PARALYSED", result["first"])
        self.assertIn("HOLD", result["first"])

