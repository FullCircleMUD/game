"""
Tests for ``world.spells.spell_utils.resolve_item_target``.

The helper drives target resolution for spells whose ``target_type`` is
``"inventory_item"``, ``"world_item"``, or ``"any_item"``. It is called
by both ``cmd_cast`` and ``cmd_zap`` and must respect the canonical
visibility rules (HiddenObjectMixin / InvisibleObjectMixin) for room
targets while always finding inventory items the caster is carrying.

evennia test --settings settings tests.typeclass_tests.test_spell_target_resolution
"""

from evennia.utils.test_resources import EvenniaTest
from evennia.utils import create

from world.spells.spell_utils import resolve_item_target


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
        result = resolve_item_target(self.char1, "training wand", "inventory_item")
        self.assertEqual(result, wand)

    def test_returns_none_for_unknown_inventory_name(self):
        result = resolve_item_target(self.char1, "phantom item", "inventory_item")
        self.assertIsNone(result)

    def test_does_not_match_room_objects(self):
        """A WorldChest in the room must not satisfy an inventory_item lookup."""
        chest = create.create_object(
            "typeclasses.world_objects.chest.WorldChest",
            key="iron chest",
            location=self.room1,
        )
        result = resolve_item_target(self.char1, "iron chest", "inventory_item")
        self.assertIsNone(result)

    def test_empty_target_str_returns_none(self):
        result = resolve_item_target(self.char1, "", "inventory_item")
        self.assertIsNone(result)

    def test_whitespace_only_target_str_returns_none(self):
        result = resolve_item_target(self.char1, "   ", "inventory_item")
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
        result = resolve_item_target(self.char1, "iron chest", "world_item")
        self.assertEqual(result, chest)

    def test_returns_none_when_target_hidden(self):
        chest = self._spawn_room_object("hidden chest")
        chest.is_hidden = True   # HiddenObjectMixin attribute
        result = resolve_item_target(self.char1, "hidden chest", "world_item")
        self.assertIsNone(result)

    def test_finds_hidden_chest_after_discovery(self):
        """A hidden chest discovered by the character is then visible."""
        chest = self._spawn_room_object("hidden chest")
        chest.is_hidden = True
        chest.discovered_by.add(self.char1.key)
        result = resolve_item_target(self.char1, "hidden chest", "world_item")
        self.assertEqual(result, chest)

    def test_empty_target_str_returns_none(self):
        result = resolve_item_target(self.char1, "", "world_item")
        self.assertIsNone(result)


class TestResolveAnyItem(EvenniaTest):
    """any_item — try room first, fall through to inventory."""

    databases = "__all__"

    def create_script(self):
        pass

    def test_room_object_takes_precedence_over_inventory(self):
        """When both exist, the room target wins."""
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
        result = resolve_item_target(self.char1, "iron chest", "any_item")
        self.assertEqual(result, chest)
        self.assertNotEqual(result, carried)

    def test_falls_through_to_inventory_when_room_empty(self):
        """If nothing in the room matches, search inventory."""
        wand = create.create_object(
            "typeclasses.items.base_nft_item.BaseNFTItem",
            key="dusty wand",
            location=self.char1,
        )
        result = resolve_item_target(self.char1, "dusty wand", "any_item")
        self.assertEqual(result, wand)

    def test_returns_none_when_neither_matches(self):
        result = resolve_item_target(self.char1, "phantom thing", "any_item")
        self.assertIsNone(result)


class TestResolveUnknownTargetType(EvenniaTest):
    """Defensive — unknown target_type values fail gracefully."""

    databases = "__all__"

    def create_script(self):
        pass

    def test_unknown_target_type_returns_none(self):
        result = resolve_item_target(self.char1, "anything", "bogus_type")
        self.assertIsNone(result)
