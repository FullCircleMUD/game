"""
Tests for BaseWearslotsMixin and HumanoidWearslotsMixin — slot initialization,
wear/remove operations, slot queries, display output, and enum validation.

Uses EvenniaTest for real Evennia objects (characters, rooms). Wearable
items use a concrete test subclass of WearableNFTItem that implements
the required at_wear/at_remove hooks.
"""

from unittest.mock import MagicMock

from evennia.utils.test_resources import EvenniaTest
from evennia.utils import create

from enums.wearslot import HumanoidWearSlot, DogWearSlot


# ── Test Helpers ──────────────────────────────────────────────────────────

def _make_wearable(key, wearslot_value, location=None):
    """
    Create a test wearable item with a specific wearslot.

    Creates without location first, sets the wearslot attribute,
    then moves to location to avoid hook issues.
    """
    obj = create.create_object(
        "typeclasses.items.base_nft_item.BaseNFTItem",
        key=key,
        nohome=True,
    )
    # Set wearslot — this is what the mixin reads to determine fit.
    # Using db attribute so it works without WearableNFTItem's
    # AttributeProperty (avoids NotImplementedError on at_wear).
    obj.db.wearslot = wearslot_value
    # Add no-op at_wear/at_remove so BaseWearslotsMixin.wear/remove work
    obj.at_wear = MagicMock()
    obj.at_remove = MagicMock()
    if location:
        obj.move_to(location, quiet=True)
    return obj


def _make_plain_item(key, location=None):
    """Create a plain item with no wearslot attribute."""
    obj = create.create_object(
        "typeclasses.items.base_nft_item.BaseNFTItem",
        key=key,
        nohome=True,
    )
    if location:
        obj.move_to(location, quiet=True)
    return obj


# ── HumanoidWearslotsMixin Tests ─────────────────────────────────────────

class TestHumanoidWearslotInit(EvenniaTest):
    """Test that HumanoidWearslotsMixin initializes all 19 slots."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def test_wearslots_initialized(self):
        """Character should have wearslots dict after creation."""
        self.assertIsNotNone(self.char1.db.wearslots)

    def test_all_19_slots_present(self):
        """Character should have exactly 19 wearslots."""
        self.assertEqual(len(self.char1.db.wearslots), 19)

    def test_all_enum_values_present(self):
        """Every HumanoidWearSlot enum value should be a key."""
        for slot in HumanoidWearSlot:
            self.assertIn(
                slot.value, self.char1.db.wearslots,
                f"Missing slot: {slot.value}"
            )

    def test_all_slots_start_empty(self):
        """All slots should be None (empty) after initialization."""
        for slot, item in self.char1.db.wearslots.items():
            self.assertIsNone(item, f"Slot {slot} should be None")

    def test_idempotent_init(self):
        """Calling at_wearslots_init() again should not reset slots."""
        helmet = _make_wearable(
            "Test Helmet", HumanoidWearSlot.HEAD.value, self.char1
        )
        self.char1.db.wearslots[HumanoidWearSlot.HEAD.value] = helmet
        self.char1.at_wearslots_init()
        self.assertEqual(
            self.char1.db.wearslots[HumanoidWearSlot.HEAD.value], helmet
        )


class TestSlotIsAvailable(EvenniaTest):
    """Test slot_is_available() checks."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def test_available_when_slot_empty(self):
        """Should return True when the item's slot is empty."""
        helmet = _make_wearable(
            "Helmet", HumanoidWearSlot.HEAD.value, self.char1
        )
        self.assertTrue(self.char1.slot_is_available(helmet))

    def test_unavailable_when_slot_occupied(self):
        """Should return False when the item's slot is occupied."""
        helmet1 = _make_wearable(
            "Helmet1", HumanoidWearSlot.HEAD.value, self.char1
        )
        helmet2 = _make_wearable(
            "Helmet2", HumanoidWearSlot.HEAD.value, self.char1
        )
        self.char1.wear(helmet1)
        self.assertFalse(self.char1.slot_is_available(helmet2))

    def test_unavailable_when_no_wearslot_on_item(self):
        """Should return False for items with no wearslot attribute."""
        item = _make_plain_item("Rock", self.char1)
        self.assertFalse(self.char1.slot_is_available(item))

    def test_available_with_enum_value(self):
        """Should work when item's wearslot is an enum member."""
        helmet = _make_wearable(
            "Helmet", HumanoidWearSlot.HEAD, self.char1
        )
        self.assertTrue(self.char1.slot_is_available(helmet))

    def test_multi_slot_first_available(self):
        """Should return True if any of the item's slots is empty."""
        earring = _make_wearable(
            "Earring",
            [HumanoidWearSlot.LEFT_EAR.value, HumanoidWearSlot.RIGHT_EAR.value],
            self.char1,
        )
        # Occupy left ear with a real wearable
        blocker = _make_wearable(
            "Blocker", HumanoidWearSlot.LEFT_EAR.value, self.char1
        )
        self.char1.wear(blocker)
        self.assertTrue(self.char1.slot_is_available(earring))

    def test_multi_slot_all_occupied(self):
        """Should return False if all of the item's slots are occupied."""
        earring = _make_wearable(
            "Earring",
            [HumanoidWearSlot.LEFT_EAR.value, HumanoidWearSlot.RIGHT_EAR.value],
            self.char1,
        )
        blocker1 = _make_wearable(
            "Blocker1", HumanoidWearSlot.LEFT_EAR.value, self.char1
        )
        blocker2 = _make_wearable(
            "Blocker2", HumanoidWearSlot.RIGHT_EAR.value, self.char1
        )
        self.char1.wear(blocker1)
        self.char1.wear(blocker2)
        self.assertFalse(self.char1.slot_is_available(earring))


class TestGetAvailableSlot(EvenniaTest):
    """Test get_available_slot() returns correct slot."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def test_returns_slot_name(self):
        """Should return the slot name string when available."""
        helmet = _make_wearable(
            "Helmet", HumanoidWearSlot.HEAD.value, self.char1
        )
        self.assertEqual(
            self.char1.get_available_slot(helmet),
            HumanoidWearSlot.HEAD.value,
        )

    def test_returns_none_when_occupied(self):
        """Should return None when slot is occupied."""
        blocker = _make_wearable(
            "Blocker", HumanoidWearSlot.HEAD.value, self.char1
        )
        self.char1.wear(blocker)
        helmet = _make_wearable(
            "Helmet", HumanoidWearSlot.HEAD.value, self.char1
        )
        self.assertIsNone(self.char1.get_available_slot(helmet))

    def test_multi_slot_picks_first_empty(self):
        """Should return the first empty slot from multi-slot item."""
        blocker = _make_wearable(
            "Blocker", HumanoidWearSlot.LEFT_EAR.value, self.char1
        )
        self.char1.wear(blocker)
        earring = _make_wearable(
            "Earring",
            [HumanoidWearSlot.LEFT_EAR.value, HumanoidWearSlot.RIGHT_EAR.value],
            self.char1,
        )
        self.assertEqual(
            self.char1.get_available_slot(earring),
            HumanoidWearSlot.RIGHT_EAR.value,
        )

    def test_returns_none_for_plain_item(self):
        """Should return None for items without wearslot."""
        item = _make_plain_item("Rock", self.char1)
        self.assertIsNone(self.char1.get_available_slot(item))


class TestWear(EvenniaTest):
    """Test wear() equip operation."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def test_wear_success(self):
        """Wearing a valid item should return (True, message)."""
        helmet = _make_wearable(
            "Leather Helm", HumanoidWearSlot.HEAD.value, self.char1
        )
        success, msg = self.char1.wear(helmet)
        self.assertTrue(success)
        self.assertIn("Leather Helm", msg)

    def test_wear_sets_slot(self):
        """Wearing should set the wearslot dict entry."""
        helmet = _make_wearable(
            "Leather Helm", HumanoidWearSlot.HEAD.value, self.char1
        )
        self.char1.wear(helmet)
        self.assertEqual(
            self.char1.db.wearslots[HumanoidWearSlot.HEAD.value], helmet
        )

    def test_wear_calls_at_wear(self):
        """Wearing should call item.at_wear(wearer)."""
        helmet = _make_wearable(
            "Leather Helm", HumanoidWearSlot.HEAD.value, self.char1
        )
        self.char1.wear(helmet)
        helmet.at_wear.assert_called_once_with(self.char1)

    def test_wear_item_stays_in_contents(self):
        """Worn item should remain in character's contents."""
        helmet = _make_wearable(
            "Leather Helm", HumanoidWearSlot.HEAD.value, self.char1
        )
        self.char1.wear(helmet)
        self.assertIn(helmet, self.char1.contents)

    def test_wear_not_in_contents(self):
        """Should fail if item is not in character's contents."""
        helmet = _make_wearable(
            "Leather Helm", HumanoidWearSlot.HEAD.value, self.room1
        )
        success, msg = self.char1.wear(helmet)
        self.assertFalse(success)
        self.assertIn("don't have", msg)

    def test_wear_already_worn(self):
        """Should fail if item is already worn."""
        helmet = _make_wearable(
            "Leather Helm", HumanoidWearSlot.HEAD.value, self.char1
        )
        self.char1.wear(helmet)
        success, msg = self.char1.wear(helmet)
        self.assertFalse(success)
        self.assertIn("already wearing", msg)

    def test_wear_no_wearslot(self):
        """Should fail if item has no wearslot attribute."""
        item = _make_plain_item("Rock", self.char1)
        success, msg = self.char1.wear(item)
        self.assertFalse(success)
        self.assertIn("not something that can be worn", msg)

    def test_wear_slot_occupied(self):
        """Should fail if the target slot is already occupied."""
        helmet1 = _make_wearable(
            "Helmet1", HumanoidWearSlot.HEAD.value, self.char1
        )
        helmet2 = _make_wearable(
            "Helmet2", HumanoidWearSlot.HEAD.value, self.char1
        )
        self.char1.wear(helmet1)
        success, msg = self.char1.wear(helmet2)
        self.assertFalse(success)
        self.assertIn("occupied", msg)

    def test_wear_multi_slot_picks_first(self):
        """Multi-slot item should go into first available slot."""
        earring = _make_wearable(
            "Gold Earring",
            [HumanoidWearSlot.LEFT_EAR.value, HumanoidWearSlot.RIGHT_EAR.value],
            self.char1,
        )
        self.char1.wear(earring)
        self.assertEqual(
            self.char1.db.wearslots[HumanoidWearSlot.LEFT_EAR.value], earring
        )

    def test_wear_multi_slot_fills_second(self):
        """Second multi-slot item should go into second available slot."""
        earring1 = _make_wearable(
            "Gold Earring",
            [HumanoidWearSlot.LEFT_EAR.value, HumanoidWearSlot.RIGHT_EAR.value],
            self.char1,
        )
        earring2 = _make_wearable(
            "Silver Earring",
            [HumanoidWearSlot.LEFT_EAR.value, HumanoidWearSlot.RIGHT_EAR.value],
            self.char1,
        )
        self.char1.wear(earring1)
        self.char1.wear(earring2)
        self.assertEqual(
            self.char1.db.wearslots[HumanoidWearSlot.RIGHT_EAR.value], earring2
        )

    def test_wear_with_enum_wearslot(self):
        """Should work when item's wearslot is an enum member."""
        helmet = _make_wearable(
            "Helmet", HumanoidWearSlot.HEAD, self.char1
        )
        success, msg = self.char1.wear(helmet)
        self.assertTrue(success)


class TestRemove(EvenniaTest):
    """Test remove() unequip operation."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def test_remove_success(self):
        """Removing a worn item should return (True, message)."""
        helmet = _make_wearable(
            "Leather Helm", HumanoidWearSlot.HEAD.value, self.char1
        )
        self.char1.wear(helmet)
        success, msg = self.char1.remove(helmet)
        self.assertTrue(success)
        self.assertIn("Leather Helm", msg)

    def test_remove_clears_slot(self):
        """Removing should set the wearslot back to None."""
        helmet = _make_wearable(
            "Leather Helm", HumanoidWearSlot.HEAD.value, self.char1
        )
        self.char1.wear(helmet)
        self.char1.remove(helmet)
        self.assertIsNone(
            self.char1.db.wearslots[HumanoidWearSlot.HEAD.value]
        )

    def test_remove_calls_at_remove(self):
        """Removing should call item.at_remove(wearer)."""
        helmet = _make_wearable(
            "Leather Helm", HumanoidWearSlot.HEAD.value, self.char1
        )
        self.char1.wear(helmet)
        self.char1.remove(helmet)
        helmet.at_remove.assert_called_once_with(self.char1)

    def test_remove_item_stays_in_contents(self):
        """Removed item should remain in character's contents."""
        helmet = _make_wearable(
            "Leather Helm", HumanoidWearSlot.HEAD.value, self.char1
        )
        self.char1.wear(helmet)
        self.char1.remove(helmet)
        self.assertIn(helmet, self.char1.contents)

    def test_remove_not_worn(self):
        """Should fail if item is not currently worn."""
        helmet = _make_wearable(
            "Leather Helm", HumanoidWearSlot.HEAD.value, self.char1
        )
        success, msg = self.char1.remove(helmet)
        self.assertFalse(success)
        self.assertIn("not wearing", msg)


class TestIsWorn(EvenniaTest):
    """Test is_worn() query."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def test_worn_item_returns_true(self):
        """Should return True for a worn item."""
        helmet = _make_wearable(
            "Helmet", HumanoidWearSlot.HEAD.value, self.char1
        )
        self.char1.wear(helmet)
        self.assertTrue(self.char1.is_worn(helmet))

    def test_carried_item_returns_false(self):
        """Should return False for an item in contents but not worn."""
        helmet = _make_wearable(
            "Helmet", HumanoidWearSlot.HEAD.value, self.char1
        )
        self.assertFalse(self.char1.is_worn(helmet))

    def test_removed_item_returns_false(self):
        """Should return False after item is removed."""
        helmet = _make_wearable(
            "Helmet", HumanoidWearSlot.HEAD.value, self.char1
        )
        self.char1.wear(helmet)
        self.char1.remove(helmet)
        self.assertFalse(self.char1.is_worn(helmet))


class TestGetSlot(EvenniaTest):
    """Test get_slot() query."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def test_get_occupied_slot(self):
        """Should return the item in an occupied slot."""
        helmet = _make_wearable(
            "Helmet", HumanoidWearSlot.HEAD.value, self.char1
        )
        self.char1.wear(helmet)
        self.assertEqual(
            self.char1.get_slot(HumanoidWearSlot.HEAD.value), helmet
        )

    def test_get_empty_slot(self):
        """Should return None for an empty slot."""
        self.assertIsNone(
            self.char1.get_slot(HumanoidWearSlot.HEAD.value)
        )

    def test_get_slot_with_enum(self):
        """Should accept an enum member as argument."""
        helmet = _make_wearable(
            "Helmet", HumanoidWearSlot.HEAD.value, self.char1
        )
        self.char1.wear(helmet)
        self.assertEqual(
            self.char1.get_slot(HumanoidWearSlot.HEAD), helmet
        )


class TestGetAllWorn(EvenniaTest):
    """Test get_all_worn() query."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def test_empty_when_nothing_worn(self):
        """Should return empty dict when nothing is worn."""
        self.assertEqual(self.char1.get_all_worn(), {})

    def test_returns_only_worn_items(self):
        """Should only include occupied slots."""
        helmet = _make_wearable(
            "Helmet", HumanoidWearSlot.HEAD.value, self.char1
        )
        boots = _make_wearable(
            "Boots", HumanoidWearSlot.FEET.value, self.char1
        )
        self.char1.wear(helmet)
        self.char1.wear(boots)
        worn = self.char1.get_all_worn()
        self.assertEqual(len(worn), 2)
        self.assertEqual(worn[HumanoidWearSlot.HEAD.value], helmet)
        self.assertEqual(worn[HumanoidWearSlot.FEET.value], boots)


class TestGetCarried(EvenniaTest):
    """Test get_carried() inventory helper."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def test_all_items_when_nothing_worn(self):
        """Should return all contents when nothing is worn."""
        item1 = _make_plain_item("Rock", self.char1)
        item2 = _make_plain_item("Stick", self.char1)
        carried = self.char1.get_carried()
        self.assertIn(item1, carried)
        self.assertIn(item2, carried)

    def test_excludes_worn_items(self):
        """Should exclude items that are currently worn."""
        helmet = _make_wearable(
            "Helmet", HumanoidWearSlot.HEAD.value, self.char1
        )
        rock = _make_plain_item("Rock", self.char1)
        self.char1.wear(helmet)
        carried = self.char1.get_carried()
        self.assertNotIn(helmet, carried)
        self.assertIn(rock, carried)

    def test_includes_removed_items(self):
        """Should include items after they are removed from wearslots."""
        helmet = _make_wearable(
            "Helmet", HumanoidWearSlot.HEAD.value, self.char1
        )
        self.char1.wear(helmet)
        self.char1.remove(helmet)
        carried = self.char1.get_carried()
        self.assertIn(helmet, carried)


class TestEquipmentCmdOutput(EvenniaTest):
    """Test equipment_cmd_output() display formatting."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def test_default_header(self):
        """Should use default header 'Equipped Items'."""
        output = self.char1.equipment_cmd_output()
        self.assertIn("Equipped Items", output)

    def test_custom_header(self):
        """Should use custom header when provided."""
        output = self.char1.equipment_cmd_output(header="Cujo is wearing:")
        self.assertTrue(output.startswith("Cujo is wearing:"))

    def test_shows_empty_slots(self):
        """Empty slots should show slot name without item."""
        output = self.char1.equipment_cmd_output()
        self.assertIn("Head", output)

    def test_shows_worn_item_name(self):
        """Worn items should show their name."""
        helmet = _make_wearable(
            "Leather Helm", HumanoidWearSlot.HEAD.value, self.char1
        )
        self.char1.wear(helmet)
        output = self.char1.equipment_cmd_output()
        self.assertIn("Leather Helm", output)
        self.assertIn("Head", output)

    def test_shows_all_19_slots(self):
        """Output should have a line for each of the 19 slots."""
        output = self.char1.equipment_cmd_output()
        # Count slot lines (lines starting with "  <")
        slot_lines = [l for l in output.split("\n") if l.strip().startswith("<")]
        self.assertEqual(len(slot_lines), 19)


class TestCanWearNotImplemented(EvenniaTest):
    """Test that BaseWearslotsMixin.can_wear raises NotImplementedError."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def test_base_raises_not_implemented(self):
        """Calling can_wear on BaseWearslotsMixin directly should raise."""
        from typeclasses.mixins.wearslots.base_wearslots import BaseWearslotsMixin

        class BareSlots(BaseWearslotsMixin):
            """Test class that doesn't override can_wear."""
            pass

        bare = BareSlots()
        bare.db = MagicMock()
        bare.db.wearslots = {"HEAD": None}
        item = MagicMock()
        with self.assertRaises(NotImplementedError):
            bare.can_wear(item)


class TestWearRemoveCycle(EvenniaTest):
    """Integration tests for full wear/remove cycles."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def test_full_cycle(self):
        """Wear then remove should leave slot empty and item in contents."""
        helmet = _make_wearable(
            "Helmet", HumanoidWearSlot.HEAD.value, self.char1
        )
        # Wear
        success, _ = self.char1.wear(helmet)
        self.assertTrue(success)
        self.assertTrue(self.char1.is_worn(helmet))
        self.assertNotIn(helmet, self.char1.get_carried())

        # Remove
        success, _ = self.char1.remove(helmet)
        self.assertTrue(success)
        self.assertFalse(self.char1.is_worn(helmet))
        self.assertIn(helmet, self.char1.get_carried())
        self.assertIn(helmet, self.char1.contents)

    def test_wear_remove_wear_again(self):
        """Should be able to wear an item again after removing it."""
        helmet = _make_wearable(
            "Helmet", HumanoidWearSlot.HEAD.value, self.char1
        )
        self.char1.wear(helmet)
        self.char1.remove(helmet)
        success, _ = self.char1.wear(helmet)
        self.assertTrue(success)
        self.assertTrue(self.char1.is_worn(helmet))

    def test_swap_items(self):
        """Should be able to remove one item and wear another in same slot."""
        helmet1 = _make_wearable(
            "Iron Helm", HumanoidWearSlot.HEAD.value, self.char1
        )
        helmet2 = _make_wearable(
            "Steel Helm", HumanoidWearSlot.HEAD.value, self.char1
        )
        self.char1.wear(helmet1)
        self.char1.remove(helmet1)
        success, _ = self.char1.wear(helmet2)
        self.assertTrue(success)
        self.assertEqual(
            self.char1.db.wearslots[HumanoidWearSlot.HEAD.value], helmet2
        )


# ── Item Hook NotImplementedError Tests ──────────────────────────────────

class TestWearableNFTItemHooks(EvenniaTest):
    """Test that WearableNFTItem raises NotImplementedError on hooks."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def _make_wearable_nft(self):
        """Create a WearableNFTItem (not a subclass)."""
        from evennia.utils import create
        obj = create.create_object(
            "typeclasses.items.wearables.wearable_nft_item.WearableNFTItem",
            key="Test Armor",
            nohome=True,
        )
        return obj

    def test_at_wear_no_error(self):
        """WearableNFTItem.at_wear() should not raise (data-driven loop)."""
        item = self._make_wearable_nft()
        item.at_wear(self.char1)  # no error with empty wear_effects

    def test_at_remove_no_error(self):
        """WearableNFTItem.at_remove() should not raise (data-driven loop)."""
        item = self._make_wearable_nft()
        item.at_remove(self.char1)  # no error with empty wear_effects

    def test_has_wearable_tag(self):
        """WearableNFTItem should have 'wearable' tag."""
        item = self._make_wearable_nft()
        self.assertTrue(item.tags.has("wearable", category="item_type"))

    def test_default_wearslot_is_none(self):
        """WearableNFTItem should have wearslot=None by default."""
        item = self._make_wearable_nft()
        self.assertIsNone(item.wearslot)

    def test_default_wear_effects_empty(self):
        """WearableNFTItem should have empty wear_effects by default."""
        item = self._make_wearable_nft()
        self.assertEqual(item.wear_effects, [])


class TestWeaponNFTItemHooks(EvenniaTest):
    """Test WeaponNFTItem hook behaviour."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def _make_weapon(self):
        """Create a WeaponNFTItem (not a subclass)."""
        from evennia.utils import create
        obj = create.create_object(
            "typeclasses.items.weapons.weapon_nft_item.WeaponNFTItem",
            key="Test Sword",
            nohome=True,
        )
        return obj

    def test_at_wield_no_error(self):
        """WeaponNFTItem.at_wield() should not raise (no-op extension point)."""
        weapon = self._make_weapon()
        weapon.at_wield(self.char1)  # no error

    def test_at_remove_no_error(self):
        """WeaponNFTItem.at_remove() should not raise (data-driven loop)."""
        weapon = self._make_weapon()
        weapon.at_remove(self.char1)  # no error

    def test_has_weapon_tag(self):
        """WeaponNFTItem should have 'weapon' tag."""
        weapon = self._make_weapon()
        self.assertTrue(weapon.tags.has("weapon", category="item_type"))


class TestHoldableNFTItemHooks(EvenniaTest):
    """Test HoldableNFTItem hook behaviour."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def _make_holdable(self):
        """Create a HoldableNFTItem (not a subclass)."""
        from evennia.utils import create
        obj = create.create_object(
            "typeclasses.items.holdables.holdable_nft_item.HoldableNFTItem",
            key="Test Shield",
            nohome=True,
        )
        return obj

    def test_at_hold_no_error(self):
        """HoldableNFTItem.at_hold() should not raise (no-op extension point)."""
        holdable = self._make_holdable()
        holdable.at_hold(self.char1)  # no error

    def test_at_remove_no_error(self):
        """HoldableNFTItem.at_remove() should not raise (data-driven loop)."""
        holdable = self._make_holdable()
        holdable.at_remove(self.char1)  # no error

    def test_has_holdable_tag(self):
        """HoldableNFTItem should have 'holdable' tag."""
        holdable = self._make_holdable()
        self.assertTrue(holdable.tags.has("holdable", category="item_type"))

    def test_default_wear_effects_empty(self):
        """HoldableNFTItem should have empty wear_effects by default."""
        holdable = self._make_holdable()
        self.assertEqual(holdable.wear_effects, [])


# ── Damage Resistance Effect Tests ────────────────────────────────────────

class TestDamageResistanceEffect(EvenniaTest):
    """Tests for the damage_resistance effect type on wear/remove."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def _make_resistance_item(self, key, wearslot_value, damage_type, value):
        """Create a wearable with a damage_resistance effect."""
        obj = create.create_object(
            "typeclasses.items.wearables.wearable_nft_item.WearableNFTItem",
            key=key,
            nohome=True,
        )
        obj.db.wearslot = wearslot_value
        obj.db.wear_effects = [
            {"type": "damage_resistance", "damage_type": damage_type, "value": value}
        ]
        obj.move_to(self.char1, quiet=True)
        return obj

    def test_wear_adds_resistance(self):
        """Wearing an item with damage_resistance should add to the dict."""
        earring = self._make_resistance_item(
            "Copper Earring", HumanoidWearSlot.LEFT_EAR.value, "piercing", 50
        )
        self.assertEqual(self.char1.damage_resistances, {})
        self.char1.wear(earring)
        self.assertEqual(self.char1.damage_resistances, {"piercing": 50})

    def test_remove_clears_resistance(self):
        """Removing the item should clean the resistance back to empty dict."""
        earring = self._make_resistance_item(
            "Copper Earring", HumanoidWearSlot.LEFT_EAR.value, "piercing", 50
        )
        self.char1.wear(earring)
        self.char1.remove(earring)
        self.assertEqual(self.char1.damage_resistances, {})

    def test_stacking_two_resistances(self):
        """Two earrings should stack their piercing resistance."""
        earring1 = self._make_resistance_item(
            "Copper Earring", HumanoidWearSlot.LEFT_EAR.value, "piercing", 30
        )
        earring2 = self._make_resistance_item(
            "Copper Earring", HumanoidWearSlot.RIGHT_EAR.value, "piercing", 20
        )
        self.char1.wear(earring1)
        self.char1.wear(earring2)
        self.assertEqual(self.char1.damage_resistances, {"piercing": 50})

    def test_stacking_partial_remove(self):
        """Removing one of two stacked items should leave partial resistance."""
        earring1 = self._make_resistance_item(
            "Copper Earring", HumanoidWearSlot.LEFT_EAR.value, "piercing", 30
        )
        earring2 = self._make_resistance_item(
            "Copper Earring", HumanoidWearSlot.RIGHT_EAR.value, "piercing", 20
        )
        self.char1.wear(earring1)
        self.char1.wear(earring2)
        self.char1.remove(earring1)
        self.assertEqual(self.char1.damage_resistances, {"piercing": 20})

    def test_mixed_damage_types_independent(self):
        """Different damage types should be tracked independently."""
        earring = self._make_resistance_item(
            "Copper Earring", HumanoidWearSlot.LEFT_EAR.value, "piercing", 50
        )
        cloak = create.create_object(
            "typeclasses.items.wearables.wearable_nft_item.WearableNFTItem",
            key="Fire Cloak",
            nohome=True,
        )
        cloak.db.wearslot = HumanoidWearSlot.CLOAK.value
        cloak.db.wear_effects = [
            {"type": "damage_resistance", "damage_type": "fire", "value": 25}
        ]
        cloak.move_to(self.char1, quiet=True)

        self.char1.wear(earring)
        self.char1.wear(cloak)
        self.assertEqual(
            self.char1.damage_resistances,
            {"piercing": 50, "fire": 25},
        )

    def test_zero_resistance_cleaned_from_dict(self):
        """Removing an item that brings resistance to exactly 0 should remove the key."""
        earring = self._make_resistance_item(
            "Copper Earring", HumanoidWearSlot.LEFT_EAR.value, "piercing", 50
        )
        self.char1.wear(earring)
        self.char1.remove(earring)
        self.assertNotIn("piercing", self.char1.damage_resistances)

    def test_resistance_capped_at_75(self):
        """Stacking resistance beyond 75: raw stores 100, get_resistance() returns 75."""
        earring1 = self._make_resistance_item(
            "Copper Earring", HumanoidWearSlot.LEFT_EAR.value, "piercing", 50
        )
        earring2 = self._make_resistance_item(
            "Copper Earring", HumanoidWearSlot.RIGHT_EAR.value, "piercing", 50
        )
        self.char1.wear(earring1)
        self.char1.wear(earring2)
        # Raw dict stores unclamped value
        self.assertEqual(self.char1.damage_resistances, {"piercing": 100})
        # Effective value is clamped
        self.assertEqual(self.char1.get_resistance("piercing"), 75)

    def test_vulnerability_capped_at_negative_75(self):
        """Stacking vulnerability beyond -75: raw stores -100, get_resistance() returns -75."""
        self.char1.apply_effect(
            {"type": "damage_resistance", "damage_type": "fire", "value": -50}
        )
        self.char1.apply_effect(
            {"type": "damage_resistance", "damage_type": "fire", "value": -50}
        )
        # Raw dict stores unclamped value
        self.assertEqual(self.char1.damage_resistances, {"fire": -100})
        # Effective value is clamped
        self.assertEqual(self.char1.get_resistance("fire"), -75)

    def test_no_drift_after_cap_removal(self):
        """Innate resistance should not drift when gear that exceeded the cap is removed."""
        # Dwarf has innate 30% poison resistance via racial_effects
        self.char1.race = "dwarf"
        self.char1._recalculate_stats()
        self.assertEqual(self.char1.damage_resistances, {"poison": 30})

        # Equip gear adding 60% — raw = 90, effective = 75
        earring = self._make_resistance_item(
            "Poison Ward", HumanoidWearSlot.LEFT_EAR.value, "poison", 60
        )
        self.char1.wear(earring)
        self.assertEqual(self.char1.damage_resistances, {"poison": 90})
        self.assertEqual(self.char1.get_resistance("poison"), 75)
        # Remove gear — should return to innate 30, not drift
        self.char1.remove(earring)
        self.assertEqual(self.char1.damage_resistances, {"poison": 30})
        self.assertEqual(self.char1.get_resistance("poison"), 30)

    def test_get_resistance_returns_zero_for_missing(self):
        """get_resistance() returns 0 for damage types with no entry."""
        self.assertEqual(self.char1.get_resistance("fire"), 0)
