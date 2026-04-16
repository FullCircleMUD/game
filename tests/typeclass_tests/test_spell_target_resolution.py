"""
Tests for ``world.spells.spell_utils.resolve_target``.

The helper drives target resolution for all spell target_types. Item-
target tests cover ``"items_inventory"``, ``"items_all_room_then_inventory"``, and
``"items_inventory_then_all_room"``. It is called by both ``cmd_cast`` and ``cmd_zap`` and
must respect the canonical visibility rules (HiddenObjectMixin /
InvisibleObjectMixin) for room targets while always finding inventory
items the caster is carrying.

evennia test --settings settings tests.typeclass_tests.test_spell_target_resolution
"""

from evennia.utils.test_resources import EvenniaTest
from evennia.utils import create

from utils.targeting.helpers import resolve_target


class TestResolveInventoryItem(EvenniaTest):
    """inventory_item — search the caster's own contents only."""

    databases = "__all__"

    def create_script(self):
        pass

    def _spawn_inv_item(self, key):
        obj = create.create_object(
            "typeclasses.items.base_nft_item.BaseNFTItem",
            key=key,
            location=self.char1,
        )
        return obj

    def test_finds_carried_item_by_name(self):
        wand = self._spawn_inv_item("training wand")
        result, _secondaries = resolve_target(self.char1, "training wand", "items_inventory")
        self.assertEqual(result, wand)

    def test_returns_none_for_unknown_inventory_name(self):
        result, _secondaries = resolve_target(self.char1, "phantom item", "items_inventory")
        self.assertIsNone(result)

    def test_does_not_match_room_objects(self):
        """A WorldChest in the room must not satisfy an inventory_item lookup."""
        chest = create.create_object(
            "typeclasses.world_objects.chest.WorldChest",
            key="iron chest",
            location=self.room1,
        )
        result, _secondaries = resolve_target(self.char1, "iron chest", "items_inventory")
        self.assertIsNone(result)

    def test_empty_target_str_returns_none(self):
        result, _secondaries = resolve_target(self.char1, "", "items_inventory")
        self.assertIsNone(result)

    def test_whitespace_only_target_str_returns_none(self):
        result, _secondaries = resolve_target(self.char1, "   ", "items_inventory")
        self.assertIsNone(result)


class TestResolveWorldItem(EvenniaTest):
    """world_item — search caster.location.contents + exits, visibility-filtered."""

    databases = "__all__"

    def create_script(self):
        pass

    def _spawn_room_object(self, key, typeclass="typeclasses.world_objects.chest.WorldChest"):
        return create.create_object(typeclass, key=key, location=self.room1)

    def test_finds_room_chest_by_name(self):
        chest = self._spawn_room_object("iron chest")
        result, _secondaries = resolve_target(self.char1, "iron chest", "items_all_room_then_inventory")
        self.assertEqual(result, chest)

    def test_returns_none_when_target_hidden(self):
        chest = self._spawn_room_object("hidden chest")
        chest.is_hidden = True   # HiddenObjectMixin attribute
        result, _secondaries = resolve_target(self.char1, "hidden chest", "items_all_room_then_inventory")
        self.assertIsNone(result)

    def test_finds_hidden_chest_after_discovery(self):
        """A hidden chest discovered by the character is then visible."""
        chest = self._spawn_room_object("hidden chest")
        chest.is_hidden = True
        chest.discovered_by.add(self.char1.key)
        result, _secondaries = resolve_target(self.char1, "hidden chest", "items_all_room_then_inventory")
        self.assertEqual(result, chest)

    def test_empty_target_str_returns_none(self):
        result, _secondaries = resolve_target(self.char1, "", "items_all_room_then_inventory")
        self.assertIsNone(result)


class TestResolveAnyItem(EvenniaTest):
    """any_item — try inventory first, fall through to room."""

    databases = "__all__"

    def create_script(self):
        pass

    def test_inventory_takes_precedence_over_room(self):
        """When both exist, the inventory item wins.

        Reversed from the old room-first order. Players most often
        identify items they just picked up — inventory-first is the
        correct default for any_item.
        """
        chest = create.create_object(
            "typeclasses.world_objects.chest.WorldChest",
            key="iron chest",
            location=self.room1,
        )
        carried = create.create_object(
            "typeclasses.items.base_nft_item.BaseNFTItem",
            key="iron chest",
            location=self.char1,
        )
        result, _secondaries = resolve_target(self.char1, "iron chest", "items_inventory_then_all_room")
        self.assertEqual(result, carried)
        self.assertNotEqual(result, chest)

    def test_falls_through_to_inventory_when_room_empty(self):
        """If nothing in the room matches, search inventory."""
        wand = create.create_object(
            "typeclasses.items.base_nft_item.BaseNFTItem",
            key="dusty wand",
            location=self.char1,
        )
        result, _secondaries = resolve_target(self.char1, "dusty wand", "items_inventory_then_all_room")
        self.assertEqual(result, wand)

    def test_returns_none_when_neither_matches(self):
        result, _secondaries = resolve_target(self.char1, "phantom thing", "items_inventory_then_all_room")
        self.assertIsNone(result)


class TestResolveUnknownTargetType(EvenniaTest):
    """Defensive — unknown target_type values fail gracefully."""

    databases = "__all__"

    def create_script(self):
        pass

    def test_unknown_target_type_returns_none(self):
        result, _secondaries = resolve_target(self.char1, "anything", "bogus_type")
        self.assertIsNone(result)
