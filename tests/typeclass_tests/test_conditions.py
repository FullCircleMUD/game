"""
Tests for ConditionsMixin — reference-counted condition flags.

evennia test --settings settings tests.typeclass_tests.test_conditions
"""

from unittest.mock import MagicMock, patch

from evennia.utils.test_resources import EvenniaTest
from evennia.utils import create

from enums.condition import Condition
from enums.wearslot import HumanoidWearSlot


class TestConditionsMixin(EvenniaTest):
    """Core add/remove/has/count tests on FCMCharacter (which mixes in ConditionsMixin)."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    # ── add_condition ──────────────────────────────────────────

    def test_add_condition_newly_gained(self):
        """Adding a condition when count is 0 should return True."""
        result = self.char1.add_condition(Condition.DARKVISION)
        self.assertTrue(result)
        self.assertTrue(self.char1.has_condition(Condition.DARKVISION))

    def test_add_condition_already_present(self):
        """Adding a condition when count > 0 should return False."""
        self.char1.add_condition(Condition.DARKVISION)
        result = self.char1.add_condition(Condition.DARKVISION)
        self.assertFalse(result)
        self.assertEqual(self.char1.get_condition_count(Condition.DARKVISION), 2)

    # ── remove_condition ───────────────────────────────────────

    def test_remove_condition_fully_removed(self):
        """Removing last source should return True."""
        self.char1.add_condition(Condition.HASTED)
        result = self.char1.remove_condition(Condition.HASTED)
        self.assertTrue(result)
        self.assertFalse(self.char1.has_condition(Condition.HASTED))

    def test_remove_condition_still_present(self):
        """Removing one of multiple sources should return False."""
        self.char1.add_condition(Condition.HASTED)
        self.char1.add_condition(Condition.HASTED)
        result = self.char1.remove_condition(Condition.HASTED)
        self.assertFalse(result)
        self.assertTrue(self.char1.has_condition(Condition.HASTED))
        self.assertEqual(self.char1.get_condition_count(Condition.HASTED), 1)

    def test_remove_condition_not_present(self):
        """Removing a condition that was never added should return False and not crash."""
        result = self.char1.remove_condition(Condition.INVISIBLE)
        self.assertFalse(result)
        self.assertFalse(self.char1.has_condition(Condition.INVISIBLE))

    # ── has_condition ──────────────────────────────────────────

    def test_has_condition_true(self):
        """has_condition returns True when count > 0."""
        self.char1.add_condition(Condition.SILENCED)
        self.assertTrue(self.char1.has_condition(Condition.SILENCED))

    def test_has_condition_false(self):
        """has_condition returns False when condition not present."""
        self.assertFalse(self.char1.has_condition(Condition.SILENCED))

    # ── get_condition_count ────────────────────────────────────

    def test_get_condition_count(self):
        """get_condition_count returns the raw ref count."""
        self.assertEqual(self.char1.get_condition_count(Condition.HASTED), 0)
        self.char1.add_condition(Condition.HASTED)
        self.assertEqual(self.char1.get_condition_count(Condition.HASTED), 1)
        self.char1.add_condition(Condition.HASTED)
        self.assertEqual(self.char1.get_condition_count(Condition.HASTED), 2)

    # ── zero cleanup ──────────────────────────────────────────

    def test_zero_cleaned_from_dict(self):
        """After full removal, key should be gone from the dict."""
        self.char1.add_condition(Condition.CRIT_IMMUNE)
        self.char1.remove_condition(Condition.CRIT_IMMUNE)
        self.assertNotIn("crit_immune", self.char1.conditions)

    # ── enum vs string ─────────────────────────────────────────

    def test_accepts_enum_and_string(self):
        """Both Condition enum and raw string should work interchangeably."""
        self.char1.add_condition(Condition.DARKVISION)
        self.assertTrue(self.char1.has_condition("darkvision"))
        self.char1.add_condition("darkvision")
        self.assertEqual(self.char1.get_condition_count(Condition.DARKVISION), 2)

    # ── innate + spell drift ───────────────────────────────────

    def test_innate_plus_spell_no_drift(self):
        """Innate condition should survive spell expiry."""
        # Racial innate
        self.char1.add_condition(Condition.DARKVISION)
        self.assertEqual(self.char1.get_condition_count(Condition.DARKVISION), 1)
        # Friend casts darkvision spell
        self.char1.add_condition(Condition.DARKVISION)
        self.assertEqual(self.char1.get_condition_count(Condition.DARKVISION), 2)
        # Spell expires
        self.char1.remove_condition(Condition.DARKVISION)
        self.assertEqual(self.char1.get_condition_count(Condition.DARKVISION), 1)
        self.assertTrue(self.char1.has_condition(Condition.DARKVISION))


class TestConditionWearEffect(EvenniaTest):
    """Tests for condition effects applied via wear_effects on items."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def _make_condition_item(self, key, wearslot_value, condition_name):
        """Create a wearable with a condition effect."""
        obj = create.create_object(
            "typeclasses.items.wearables.wearable_nft_item.WearableNFTItem",
            key=key,
            nohome=True,
        )
        obj.db.wearslot = wearslot_value
        obj.db.wear_effects = [
            {"type": "condition", "condition": condition_name}
        ]
        obj.move_to(self.char1, quiet=True)
        return obj

    def test_condition_wear_effect(self):
        """Wearing an item with a condition effect should grant the condition."""
        ring = self._make_condition_item(
            "Ring of Invisibility", HumanoidWearSlot.LEFT_RING_FINGER.value, "invisible"
        )
        self.assertFalse(self.char1.has_condition(Condition.INVISIBLE))
        self.char1.wear(ring)
        self.assertTrue(self.char1.has_condition(Condition.INVISIBLE))

    def test_condition_remove_effect(self):
        """Removing the item should remove the condition."""
        ring = self._make_condition_item(
            "Ring of Invisibility", HumanoidWearSlot.LEFT_RING_FINGER.value, "invisible"
        )
        self.char1.wear(ring)
        self.char1.remove(ring)
        self.assertFalse(self.char1.has_condition(Condition.INVISIBLE))

    def test_condition_item_plus_innate(self):
        """Item condition + innate should stack; removing item leaves innate."""
        # Innate darkvision (e.g. elf)
        self.char1.add_condition(Condition.DARKVISION)
        # Wear darkvision goggles
        goggles = self._make_condition_item(
            "Darkvision Goggles", HumanoidWearSlot.FACE.value, "darkvision"
        )
        self.char1.wear(goggles)
        self.assertEqual(self.char1.get_condition_count(Condition.DARKVISION), 2)
        # Remove goggles
        self.char1.remove(goggles)
        self.assertEqual(self.char1.get_condition_count(Condition.DARKVISION), 1)
        self.assertTrue(self.char1.has_condition(Condition.DARKVISION))


class TestMsgContentsVisibility(EvenniaTest):
    """Tests for visibility filtering in RoomBase.msg_contents override."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    # ── HIDDEN ──────────────────────────────────────────────────

    def test_hidden_actor_suppresses_room_message(self):
        """A HIDDEN actor's msg_contents should reach nobody."""
        self.char1.add_condition(Condition.HIDDEN)
        with patch.object(self.char2, "msg") as mock_msg:
            self.room1.msg_contents(
                "Char does something.", from_obj=self.char1, exclude=[self.char1]
            )
            mock_msg.assert_not_called()

    def test_hidden_does_not_affect_other_actors(self):
        """A non-hidden actor's messages should still reach the room normally."""
        self.char2.add_condition(Condition.HIDDEN)  # char2 is hidden, not char1
        with patch.object(self.char2, "msg") as mock_msg:
            self.room1.msg_contents(
                "Char does something.", from_obj=self.char1, exclude=[self.char1]
            )
            mock_msg.assert_called_once()

    # ── INVISIBLE ───────────────────────────────────────────────

    def test_invisible_actor_excluded_without_detect(self):
        """An INVISIBLE actor's msg_contents should not reach char2 without DETECT_INVIS."""
        self.char1.add_condition(Condition.INVISIBLE)
        with patch.object(self.char2, "msg") as mock_msg:
            self.room1.msg_contents(
                "Char shimmers.", from_obj=self.char1, exclude=[self.char1]
            )
            mock_msg.assert_not_called()

    def test_invisible_actor_seen_with_detect_invis(self):
        """An INVISIBLE actor's msg_contents should reach char2 who has DETECT_INVIS."""
        self.char1.add_condition(Condition.INVISIBLE)
        self.char2.add_condition(Condition.DETECT_INVIS)
        with patch.object(self.char2, "msg") as mock_msg:
            self.room1.msg_contents(
                "Char shimmers.", from_obj=self.char1, exclude=[self.char1]
            )
            mock_msg.assert_called_once()

    def test_invisible_mixed_room(self):
        """Only recipients with DETECT_INVIS should see an invisible actor's messages."""
        char3 = create.create_object(
            "typeclasses.actors.character.FCMCharacter",
            key="Char3", location=self.room1, home=self.room1, nohome=False,
        )
        self.char1.add_condition(Condition.INVISIBLE)
        self.char2.add_condition(Condition.DETECT_INVIS)
        # char3 has no DETECT_INVIS
        with patch.object(self.char2, "msg") as mock_msg2, \
             patch.object(char3, "msg") as mock_msg3:
            self.room1.msg_contents(
                "Char shimmers.", from_obj=self.char1, exclude=[self.char1]
            )
            mock_msg2.assert_called_once()
            mock_msg3.assert_not_called()

    # ── NORMAL (regression) ─────────────────────────────────────

    def test_normal_actor_no_filtering(self):
        """A normal (visible) actor's messages should reach everyone as before."""
        with patch.object(self.char2, "msg") as mock_msg:
            self.room1.msg_contents(
                "Char does something.", from_obj=self.char1, exclude=[self.char1]
            )
            mock_msg.assert_called_once()

    def test_invisible_preserves_existing_exclude(self):
        """Existing exclude list should be preserved alongside invisibility filtering."""
        char3 = create.create_object(
            "typeclasses.actors.character.FCMCharacter",
            key="Char3", location=self.room1, home=self.room1, nohome=False,
        )
        self.char1.add_condition(Condition.INVISIBLE)
        char3.add_condition(Condition.DETECT_INVIS)
        # char3 has DETECT_INVIS but is explicitly excluded
        with patch.object(self.char2, "msg") as mock_msg2, \
             patch.object(char3, "msg") as mock_msg3:
            self.room1.msg_contents(
                "Char shimmers.", from_obj=self.char1, exclude=[self.char1, char3]
            )
            mock_msg2.assert_not_called()  # no DETECT_INVIS
            mock_msg3.assert_not_called()  # explicitly excluded


class TestConditionMessaging(EvenniaTest):
    """Tests for automatic condition start/end messages on FCMCharacter."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    # ── First-person messages ────────────────────────────────────

    def test_gain_sends_first_person_message(self):
        """Gaining a condition should send the start message to the character."""
        with patch.object(self.char1, "msg") as mock_msg:
            self.char1.add_condition(Condition.HASTED)
            mock_msg.assert_called_once_with(Condition.HASTED.get_start_message())

    def test_loss_sends_first_person_message(self):
        """Losing a condition should send the end message to the character."""
        self.char1.add_condition(Condition.HASTED)
        with patch.object(self.char1, "msg") as mock_msg:
            self.char1.remove_condition(Condition.HASTED)
            mock_msg.assert_called_once_with(Condition.HASTED.get_end_message())

    def test_no_message_on_duplicate_add(self):
        """Adding a condition that's already present should not send a message."""
        self.char1.add_condition(Condition.HASTED)
        with patch.object(self.char1, "msg") as mock_msg:
            self.char1.add_condition(Condition.HASTED)
            mock_msg.assert_not_called()

    def test_no_message_on_partial_remove(self):
        """Removing one of multiple sources should not send a message."""
        self.char1.add_condition(Condition.HASTED)
        self.char1.add_condition(Condition.HASTED)
        with patch.object(self.char1, "msg") as mock_msg:
            self.char1.remove_condition(Condition.HASTED)
            mock_msg.assert_not_called()

    # ── Third-person messages ────────────────────────────────────

    def test_gain_sends_third_person_to_room(self):
        """Gaining a condition should broadcast the third-person message to the room."""
        with patch.object(self.char2, "msg") as mock_msg:
            self.char1.add_condition(Condition.HASTED)
            mock_msg.assert_called_once()
            # Evennia's msg_contents passes text=(message, kwargs) as keyword arg
            msg_text = mock_msg.call_args[1].get("text", ("",))[0]
            self.assertIn("Char", msg_text)

    def test_loss_sends_third_person_to_room(self):
        """Losing a condition should broadcast the third-person end message to the room."""
        self.char1.add_condition(Condition.HASTED)
        with patch.object(self.char2, "msg") as mock_msg:
            self.char1.remove_condition(Condition.HASTED)
            mock_msg.assert_called_once()

    # ── Hidden suppression ───────────────────────────────────────

    def test_gain_while_hidden_suppresses_third_person(self):
        """Gaining a condition while HIDDEN should not broadcast to the room."""
        self.char1.add_condition(Condition.HIDDEN)
        with patch.object(self.char2, "msg") as mock_msg:
            self.char1.add_condition(Condition.HASTED)
            mock_msg.assert_not_called()

    def test_gain_while_hidden_still_sends_first_person(self):
        """Gaining a condition while HIDDEN should still message the character."""
        self.char1.add_condition(Condition.HIDDEN)
        with patch.object(self.char1, "msg") as mock_msg:
            self.char1.add_condition(Condition.HASTED)
            mock_msg.assert_called_once_with(Condition.HASTED.get_start_message())

    # ── Invisible filtering on condition messages ────────────────

    def test_gain_while_invisible_filters_room(self):
        """Gaining a condition while INVISIBLE should only reach DETECT_INVIS recipients."""
        self.char1.add_condition(Condition.INVISIBLE)
        # char2 has no DETECT_INVIS
        with patch.object(self.char2, "msg") as mock_msg:
            self.char1.add_condition(Condition.HASTED)
            mock_msg.assert_not_called()

    def test_gain_while_invisible_reaches_detect_invis(self):
        """Gaining a condition while INVISIBLE should reach recipients with DETECT_INVIS."""
        self.char1.add_condition(Condition.INVISIBLE)
        self.char2.add_condition(Condition.DETECT_INVIS)
        with patch.object(self.char2, "msg") as mock_msg:
            self.char1.add_condition(Condition.HASTED)
            mock_msg.assert_called_once()

    # ── Gaining INVISIBLE/HIDDEN itself ──────────────────────────

    def test_gaining_invisible_seen_by_everyone(self):
        """Gaining INVISIBLE itself should be seen by everyone (not filtered)."""
        with patch.object(self.char2, "msg") as mock_msg:
            self.char1.add_condition(Condition.INVISIBLE)
            mock_msg.assert_called_once()

    def test_losing_invisible_seen_by_everyone(self):
        """Losing INVISIBLE should be seen by everyone (character is now visible)."""
        self.char1.add_condition(Condition.INVISIBLE)
        with patch.object(self.char2, "msg") as mock_msg:
            self.char1.remove_condition(Condition.INVISIBLE)
            mock_msg.assert_called_once()

    def test_gaining_hidden_seen_by_everyone(self):
        """Gaining HIDDEN itself should be seen by everyone (they see you duck into shadows)."""
        with patch.object(self.char2, "msg") as mock_msg:
            self.char1.add_condition(Condition.HIDDEN)
            mock_msg.assert_called_once()

    def test_losing_hidden_seen_by_everyone(self):
        """Losing HIDDEN should be seen by everyone (character steps out of shadows)."""
        self.char1.add_condition(Condition.HIDDEN)
        with patch.object(self.char2, "msg") as mock_msg:
            self.char1.remove_condition(Condition.HIDDEN)
            mock_msg.assert_called_once()
