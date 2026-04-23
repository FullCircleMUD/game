"""
Tests for the movement-gating system added alongside the kobold-flees-while-stunned
fix:

  - NamedEffect.get_block_message() accessor
  - INCAPACITATING_EFFECTS / MOVEMENT_BLOCKING_EFFECTS tuples
  - EffectsManagerMixin.get_incapacitating_effect()
  - EffectsManagerMixin.get_movement_blocking_effect()
  - BaseActor.at_pre_move() gate
  - ENTANGLED demotion regression coverage (movement-blocking, NOT incapacitating)

evennia test --settings settings tests.typeclass_tests.test_movement_gates
"""

from unittest.mock import MagicMock

from evennia.utils.test_resources import EvenniaTest

from enums.named_effect import (
    NamedEffect,
    INCAPACITATING_EFFECTS,
    MOVEMENT_BLOCKING_EFFECTS,
)


# ====================================================================== #
#  Registry / Tuple Membership
# ====================================================================== #


class TestBlockMessageRegistry(EvenniaTest):
    """get_block_message() returns specific text for each gating effect."""

    def create_script(self):
        pass

    def test_stunned_block_message(self):
        msg = NamedEffect.STUNNED.get_block_message()
        self.assertIn("stunned", msg.lower())

    def test_prone_block_message(self):
        msg = NamedEffect.PRONE.get_block_message()
        self.assertIn("prone", msg.lower())

    def test_paralysed_block_message(self):
        msg = NamedEffect.PARALYSED.get_block_message()
        self.assertIn("paralysed", msg.lower())

    def test_entangled_block_message(self):
        msg = NamedEffect.ENTANGLED.get_block_message()
        self.assertIn("entangled", msg.lower())

    def test_thorn_whip_block_message(self):
        msg = NamedEffect.THORN_WHIP_HELD.get_block_message()
        self.assertIn("vines", msg.lower())

    def test_unmapped_effect_falls_back(self):
        """Effects without a registry entry get a default message string."""
        # SHIELD has no block message — it's not a gating effect.
        msg = NamedEffect.SHIELD.get_block_message()
        self.assertIn("shield", msg.lower())


class TestIncapacitatingEffectsMembership(EvenniaTest):
    """INCAPACITATING_EFFECTS contains action-denying effects only."""

    def create_script(self):
        pass

    def test_stunned_is_incapacitating(self):
        self.assertIn(NamedEffect.STUNNED, INCAPACITATING_EFFECTS)

    def test_prone_is_incapacitating(self):
        self.assertIn(NamedEffect.PRONE, INCAPACITATING_EFFECTS)

    def test_paralysed_is_incapacitating(self):
        self.assertIn(NamedEffect.PARALYSED, INCAPACITATING_EFFECTS)

    def test_entangled_is_NOT_incapacitating(self):
        """Demotion regression: ENTANGLED no longer denies actions."""
        self.assertNotIn(NamedEffect.ENTANGLED, INCAPACITATING_EFFECTS)

    def test_thorn_whip_is_NOT_incapacitating(self):
        """Movement-only effects must not appear here."""
        self.assertNotIn(NamedEffect.THORN_WHIP_HELD, INCAPACITATING_EFFECTS)


class TestMovementBlockingEffectsMembership(EvenniaTest):
    """MOVEMENT_BLOCKING_EFFECTS is a strict superset of INCAPACITATING_EFFECTS."""

    def create_script(self):
        pass

    def test_is_superset_of_incapacitating(self):
        for effect in INCAPACITATING_EFFECTS:
            self.assertIn(effect, MOVEMENT_BLOCKING_EFFECTS)

    def test_includes_thorn_whip(self):
        self.assertIn(NamedEffect.THORN_WHIP_HELD, MOVEMENT_BLOCKING_EFFECTS)

    def test_includes_entangled(self):
        """Demotion regression: ENTANGLED still blocks movement."""
        self.assertIn(NamedEffect.ENTANGLED, MOVEMENT_BLOCKING_EFFECTS)


# ====================================================================== #
#  EffectsManagerMixin Helpers
# ====================================================================== #


class TestGetIncapacitatingEffect(EvenniaTest):
    """get_incapacitating_effect() returns (key, msg) or (None, None)."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def test_clean_actor_returns_none(self):
        key, msg = self.char1.get_incapacitating_effect()
        self.assertIsNone(key)
        self.assertIsNone(msg)

    def test_stunned_returns_tuple(self):
        self.char1.apply_stunned(2)
        key, msg = self.char1.get_incapacitating_effect()
        self.assertEqual(key, "stunned")
        self.assertIn("stunned", msg.lower())

    def test_prone_returns_tuple(self):
        self.char1.apply_prone(1)
        key, msg = self.char1.get_incapacitating_effect()
        self.assertEqual(key, "prone")

    def test_paralysed_returns_tuple(self):
        self.char1.apply_paralysed(1)
        key, msg = self.char1.get_incapacitating_effect()
        self.assertEqual(key, "paralysed")

    def test_entangled_does_NOT_incapacitate(self):
        """Demotion regression: entangled actor is NOT considered incapacitated."""
        self.char1.apply_entangled(3, save_dc=15)
        key, msg = self.char1.get_incapacitating_effect()
        self.assertIsNone(key)
        self.assertIsNone(msg)

    def test_thorn_whip_does_NOT_incapacitate(self):
        self.char1.apply_named_effect(
            key="thorn_whip_held", duration=3, duration_type="combat_rounds",
            messages={"start": "...", "end": "..."},
        )
        key, _ = self.char1.get_incapacitating_effect()
        self.assertIsNone(key)


class TestGetMovementBlockingEffect(EvenniaTest):
    """get_movement_blocking_effect() catches incapacitation + restraints."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def test_clean_actor_returns_none(self):
        key, msg = self.char1.get_movement_blocking_effect()
        self.assertIsNone(key)
        self.assertIsNone(msg)

    def test_stunned_blocks_movement(self):
        self.char1.apply_stunned(2)
        key, _ = self.char1.get_movement_blocking_effect()
        self.assertEqual(key, "stunned")

    def test_entangled_blocks_movement(self):
        """Demotion regression: entangled still prevents leaving the room."""
        self.char1.apply_entangled(3, save_dc=15)
        key, msg = self.char1.get_movement_blocking_effect()
        self.assertEqual(key, "entangled")
        self.assertIn("entangled", msg.lower())

    def test_thorn_whip_blocks_movement(self):
        self.char1.apply_named_effect(
            key="thorn_whip_held", duration=3, duration_type="combat_rounds",
            messages={"start": "...", "end": "..."},
        )
        key, _ = self.char1.get_movement_blocking_effect()
        self.assertEqual(key, "thorn_whip_held")


# ====================================================================== #
#  BaseActor.at_pre_move Gate
# ====================================================================== #


class TestAtPreMoveMovementGate(EvenniaTest):
    """BaseActor.at_pre_move blocks movement when a movement-blocking effect is active."""

    character_typeclass = "typeclasses.actors.character.FCMCharacter"
    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        # Capture msg() output without requiring a real session.
        self.char1.msg = MagicMock()

    def test_clean_actor_can_move(self):
        """No effects → at_pre_move returns True."""
        self.assertTrue(self.char1.at_pre_move(self.room2, move_type="move"))

    def test_stunned_blocks_walk(self):
        self.char1.apply_stunned(2)
        self.assertFalse(self.char1.at_pre_move(self.room2, move_type="move"))
        self.char1.msg.assert_called()

    def test_entangled_blocks_walk(self):
        """Demotion regression: entangled blocks walking out of the room."""
        self.char1.apply_entangled(3, save_dc=15)
        self.assertFalse(self.char1.at_pre_move(self.room2, move_type="move"))

    def test_entangled_blocks_flee(self):
        self.char1.apply_entangled(3, save_dc=15)
        self.assertFalse(self.char1.at_pre_move(self.room2, move_type="flee"))

    def test_entangled_blocks_follow(self):
        self.char1.apply_entangled(3, save_dc=15)
        self.assertFalse(self.char1.at_pre_move(self.room2, move_type="follow"))

    def test_thorn_whip_blocks_walk(self):
        self.char1.apply_named_effect(
            key="thorn_whip_held", duration=3, duration_type="combat_rounds",
            messages={"start": "...", "end": "..."},
        )
        self.assertFalse(self.char1.at_pre_move(self.room2, move_type="move"))

    def test_teleport_bypasses_gate(self):
        """Magical relocation should bypass physical restraints."""
        self.char1.apply_stunned(2)
        # at_pre_move should NOT return False for teleport — Character's other
        # checks may apply, but the new movement-blocking gate must not fire.
        # We assert that the msg() does not get the block message.
        self.char1.at_pre_move(self.room2, move_type="teleport")
        for call_args in self.char1.msg.call_args_list:
            sent = call_args.args[0] if call_args.args else ""
            self.assertNotIn("stunned", sent.lower())

    def test_block_message_sent_to_actor(self):
        """The actor sees the effect-specific block message on the move attempt."""
        self.char1.apply_stunned(2)
        # Reset mock to ignore the on-apply start message — we only care about
        # what the move-attempt sends.
        self.char1.msg.reset_mock()
        self.char1.at_pre_move(self.room2, move_type="move")
        sent_messages = [c.args[0] for c in self.char1.msg.call_args_list if c.args]
        self.assertTrue(
            any("stunned" in m.lower() for m in sent_messages),
            f"Expected 'stunned' in one of: {sent_messages}",
        )
