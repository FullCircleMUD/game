"""Tests for spawn/executor.py — carrying out planned placements.

The executor receives placement dicts, which in a sharded deployment arrive
over the message bus from a different process. It picks a distributor by
category, resolves the target, clamps to current headroom, and places.

Real objects throughout. Placement itself is patched at class level in most
tests, because actually placing would draw from the RESERVE or mint an NFT —
what is under test is the routing, resolution and clamping around it.

evennia test --settings settings tests.spawn_tests.test_executor
"""

from unittest.mock import patch

from evennia.utils import create
from evennia.utils.test_resources import EvenniaTest

from blockchain.xrpl.services.spawn.distributors.fungible import (
    GoldDistributor,
    ResourceDistributor,
)
from blockchain.xrpl.services.spawn.distributors.nft import ScrollDistributor
from blockchain.xrpl.services.spawn.executor import execute

RESOURCE_ID = 1


def _make_target(key="Target", **attrs):
    obj = create.create_object(
        "evennia.objects.objects.DefaultObject", key=key, nohome=True,
    )
    for name, value in attrs.items():
        obj.attributes.add(name, value)
    return obj


def _placement(category, type_key, target_pk, amount):
    return {
        "category": category,
        "type_key": type_key,
        "target_pk": target_pk,
        "amount": amount,
    }


# ================================================================== #
#  Routing by category
# ================================================================== #


class TestCategoryRouting(EvenniaTest):
    """Category is the dispatch key — placing gold, a resource and a scroll
    are entirely different operations."""

    databases = "__all__"

    def create_script(self):
        pass

    def test_resources_route_to_resource_distributor(self):
        t = _make_target(spawn_resources_max={RESOURCE_ID: 10})
        with patch.object(ResourceDistributor, "_place") as mock_place:
            execute([_placement("resources", RESOURCE_ID, t.pk, 3)])
        mock_place.assert_called_once()
        target, type_key, amount = mock_place.call_args[0]
        self.assertEqual(target.pk, t.pk)
        self.assertEqual(type_key, RESOURCE_ID)
        self.assertEqual(amount, 3)

    def test_gold_routes_to_gold_distributor(self):
        t = _make_target(spawn_gold_max=20)
        with patch.object(GoldDistributor, "_place") as mock_place:
            execute([_placement("gold", "gold", t.pk, 5)])
        mock_place.assert_called_once()
        self.assertEqual(mock_place.call_args[0][2], 5)

    def test_scrolls_route_to_scroll_distributor(self):
        t = _make_target(spawn_scrolls_max={"basic": 1})
        with patch.object(ScrollDistributor, "_place") as mock_place:
            execute([_placement("scrolls", "scroll_x", t.pk, 1)])
        mock_place.assert_called_once()

    def test_unknown_category_is_skipped(self):
        t = _make_target(spawn_gold_max=20)
        with patch.object(GoldDistributor, "_place") as mock_place:
            placed = execute([_placement("bogus", "x", t.pk, 5)])
        mock_place.assert_not_called()
        self.assertEqual(placed, 0)

    def test_mixed_categories_in_one_call(self):
        """A message may carry placements for different items."""
        gold_target = _make_target("Chest", spawn_gold_max=20)
        res_target = _make_target(
            "Node", spawn_resources_max={RESOURCE_ID: 10},
        )
        with patch.object(GoldDistributor, "_place") as mock_gold, \
                patch.object(ResourceDistributor, "_place") as mock_res:
            execute([
                _placement("gold", "gold", gold_target.pk, 5),
                _placement("resources", RESOURCE_ID, res_target.pk, 3),
            ])
        mock_gold.assert_called_once()
        mock_res.assert_called_once()


# ================================================================== #
#  Target resolution
# ================================================================== #


class TestTargetResolution(EvenniaTest):

    databases = "__all__"

    def create_script(self):
        pass

    def test_missing_target_is_skipped(self):
        """The target died between planning and placing."""
        t = _make_target(spawn_gold_max=20)
        pk = t.pk
        t.delete()
        with patch.object(GoldDistributor, "_place") as mock_place:
            placed = execute([_placement("gold", "gold", pk, 5)])
        mock_place.assert_not_called()
        self.assertEqual(placed, 0)

    def test_one_missing_target_does_not_stop_the_others(self):
        alive = _make_target("Alive", spawn_gold_max=20)
        dead = _make_target("Dead", spawn_gold_max=20)
        dead_pk = dead.pk
        dead.delete()
        with patch.object(GoldDistributor, "_place") as mock_place:
            execute([
                _placement("gold", "gold", dead_pk, 5),
                _placement("gold", "gold", alive.pk, 5),
            ])
        mock_place.assert_called_once()
        self.assertEqual(mock_place.call_args[0][0].pk, alive.pk)


# ================================================================== #
#  The clamp
# ================================================================== #


class TestHeadroomClamp(EvenniaTest):
    """Re-checked immediately before placing, covering the gap between the
    planner reading the world and this running."""

    databases = "__all__"

    def create_script(self):
        pass

    def test_amount_within_headroom_placed_unchanged(self):
        t = _make_target(spawn_gold_max=20)
        with patch.object(GoldDistributor, "_place") as mock_place:
            placed = execute([_placement("gold", "gold", t.pk, 5)])
        self.assertEqual(mock_place.call_args[0][2], 5)
        self.assertEqual(placed, 5)

    def test_amount_exceeding_headroom_is_clamped(self):
        """Room for 4 of a requested 10 — place 4, not 10."""
        t = _make_target(spawn_gold_max=10, gold=6)
        with patch.object(GoldDistributor, "_place") as mock_place:
            placed = execute([_placement("gold", "gold", t.pk, 10)])
        self.assertEqual(mock_place.call_args[0][2], 4)
        self.assertEqual(placed, 4)

    def test_full_target_places_nothing(self):
        t = _make_target(spawn_gold_max=10, gold=10)
        with patch.object(GoldDistributor, "_place") as mock_place:
            placed = execute([_placement("gold", "gold", t.pk, 5)])
        mock_place.assert_not_called()
        self.assertEqual(placed, 0)

    def test_target_with_no_capacity_places_nothing(self):
        t = _make_target()
        with patch.object(GoldDistributor, "_place") as mock_place:
            placed = execute([_placement("gold", "gold", t.pk, 5)])
        mock_place.assert_not_called()
        self.assertEqual(placed, 0)

    def test_duplicate_delivery_places_nothing_the_second_time(self):
        """Why no dedup record is needed: at-least-once delivery is made
        safe by the clamp, because the first placement closes the headroom."""
        t = _make_target(spawn_gold_max=5)
        placement = _placement("gold", "gold", t.pk, 5)

        with patch.object(GoldDistributor, "_place"):
            first = execute([placement])
        # The first placement really landed, so headroom is now closed.
        t.attributes.add("gold", 5)
        with patch.object(GoldDistributor, "_place") as mock_place:
            second = execute([placement])

        self.assertEqual(first, 5)
        self.assertEqual(second, 0)
        mock_place.assert_not_called()

    def test_zero_amount_is_skipped(self):
        t = _make_target(spawn_gold_max=20)
        with patch.object(GoldDistributor, "_place") as mock_place:
            execute([_placement("gold", "gold", t.pk, 0)])
        mock_place.assert_not_called()


# ================================================================== #
#  Isolation — one bad entry must not cost the others
# ================================================================== #


class TestEntryIsolation(EvenniaTest):

    databases = "__all__"

    def create_script(self):
        pass

    def test_malformed_entry_skipped(self):
        t = _make_target(spawn_gold_max=20)
        with patch.object(GoldDistributor, "_place") as mock_place:
            placed = execute([
                {"category": "gold", "amount": 5},          # no target_pk
                _placement("gold", "gold", t.pk, 5),
            ])
        mock_place.assert_called_once()
        self.assertEqual(placed, 5)

    def test_non_dict_entry_skipped(self):
        t = _make_target(spawn_gold_max=20)
        with patch.object(GoldDistributor, "_place") as mock_place:
            execute(["nonsense", _placement("gold", "gold", t.pk, 5)])
        mock_place.assert_called_once()

    def test_failed_placement_does_not_stop_the_rest(self):
        a = _make_target("A", spawn_gold_max=20)
        b = _make_target("B", spawn_gold_max=20)

        def _boom(target, type_key, amount):
            if target.pk == a.pk:
                raise RuntimeError("reserve exhausted")

        with patch.object(GoldDistributor, "_place", side_effect=_boom) as m:
            placed = execute([
                _placement("gold", "gold", a.pk, 5),
                _placement("gold", "gold", b.pk, 5),
            ])
        self.assertEqual(m.call_count, 2)
        self.assertEqual(placed, 5)

    def test_failed_placement_is_not_counted(self):
        t = _make_target(spawn_gold_max=20)
        with patch.object(
            GoldDistributor, "_place", side_effect=RuntimeError("nope"),
        ):
            placed = execute([_placement("gold", "gold", t.pk, 5)])
        self.assertEqual(placed, 0)

    def test_empty_list(self):
        self.assertEqual(execute([]), 0)


# ================================================================== #
#  Placement actually reaches the world
# ================================================================== #


class TestRealPlacement(EvenniaTest):
    """One test that does not patch _place, so the whole path runs — the
    resource route is used because it needs no NFT minting."""

    databases = "__all__"

    def create_script(self):
        pass

    def test_harvest_room_resource_count_increases(self):
        """A harvest room tracks a single int rather than the fungible dict,
        and the distributor increments it directly."""
        room = _make_target(
            "Vein",
            spawn_resources_max={RESOURCE_ID: 20},
            resource_count=4,
        )
        placed = execute([_placement("resources", RESOURCE_ID, room.pk, 6)])
        self.assertEqual(placed, 6)
        self.assertEqual(room.attributes.get("resource_count"), 10)

    def test_clamped_amount_is_what_lands(self):
        room = _make_target(
            "Vein",
            spawn_resources_max={RESOURCE_ID: 10},
            resource_count=8,
        )
        placed = execute([_placement("resources", RESOURCE_ID, room.pk, 50)])
        self.assertEqual(placed, 2)
        self.assertEqual(room.attributes.get("resource_count"), 10)
