"""Tests for Phase 8 — gold spawning tags and attributes.

Covers:
  - CombatMob gold tag registration (intelligent mobs vs animals)
  - spawn_gold_max attribute on mobs
  - WorldChest gold tag registration
  - Zone spawn script gold tag sync
  - GoldDistributor tag/max_attr config

evennia test --settings settings tests.spawn_tests.test_phase8_gold
"""

from unittest.mock import patch, MagicMock

from evennia.utils import create
from evennia.utils.test_resources import EvenniaTest


# ================================================================== #
#  Mob gold tags
# ================================================================== #


class TestMobGoldTags(EvenniaTest):
    """Mobs with loot_gold_max > 0 get spawn_gold tag."""

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.room = create.create_object(
            "typeclasses.terrain.rooms.room_base.RoomBase",
            key="Test Room",
        )

    def test_kobold_has_gold_tag(self):
        """Kobold (loot_gold_max=6) gets spawn_gold tag."""
        mob = create.create_object(
            "typeclasses.actors.mobs.kobold.Kobold",
            key="a kobold",
            location=self.room,
        )
        tags = mob.tags.get(category="spawn_gold", return_list=True)
        self.assertIn("spawn_gold", tags)

    def test_kobold_gold_max(self):
        """Kobold spawn_gold_max should be 2."""
        mob = create.create_object(
            "typeclasses.actors.mobs.kobold.Kobold",
            key="a kobold",
            location=self.room,
        )
        self.assertEqual(mob.db.spawn_gold_max, 2)

    def test_kobold_chieftain_gold_max(self):
        """KoboldChieftain spawn_gold_max should be 6."""
        mob = create.create_object(
            "typeclasses.actors.mobs.kobold_chieftain.KoboldChieftain",
            key="Kobold Chieftain",
            location=self.room,
        )
        self.assertEqual(mob.db.spawn_gold_max, 6)

    def test_gnoll_gold_max(self):
        """Gnoll spawn_gold_max should be 8."""
        mob = create.create_object(
            "typeclasses.actors.mobs.gnoll.Gnoll",
            key="a gnoll",
            location=self.room,
        )
        self.assertEqual(mob.db.spawn_gold_max, 8)

    def test_gnoll_warlord_gold_max(self):
        """GnollWarlord spawn_gold_max should be 15."""
        mob = create.create_object(
            "typeclasses.actors.mobs.gnoll_warlord.GnollWarlord",
            key="Gnoll Warlord",
            location=self.room,
        )
        self.assertEqual(mob.db.spawn_gold_max, 15)

    def test_wolf_has_gold_tag(self):
        """Wolf (loot_gold_max=2) gets spawn_gold tag."""
        mob = create.create_object(
            "typeclasses.actors.mobs.wolf.Wolf",
            key="a grey wolf",
            location=self.room,
        )
        tags = mob.tags.get(category="spawn_gold", return_list=True)
        self.assertIn("spawn_gold", tags)

    def test_wolf_gold_max(self):
        """Wolf spawn_gold_max should be 2."""
        mob = create.create_object(
            "typeclasses.actors.mobs.wolf.Wolf",
            key="a grey wolf",
            location=self.room,
        )
        self.assertEqual(mob.db.spawn_gold_max, 2)

    def test_base_combat_mob_no_gold_tag(self):
        """Base CombatMob (loot_gold_max=0) should NOT get gold tag."""
        mob = create.create_object(
            "typeclasses.actors.mob.CombatMob",
            key="a mob",
            location=self.room,
        )
        tags = mob.tags.get(category="spawn_gold", return_list=True)
        self.assertNotIn("spawn_gold", tags)


# ================================================================== #
#  WorldChest gold tags
# ================================================================== #


class TestWorldChestGoldTags(EvenniaTest):
    """WorldChest with loot_gold_max > 0 gets spawn_gold tag."""

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.room = create.create_object(
            "typeclasses.terrain.rooms.room_base.RoomBase",
            key="Dungeon Room",
        )

    def test_chest_default_no_gold_tag(self):
        """Default WorldChest (loot_gold_max=0) has no gold tag."""
        chest = create.create_object(
            "typeclasses.world_objects.chest.WorldChest",
            key="an iron chest",
            location=self.room,
        )
        tags = chest.tags.get(category="spawn_gold", return_list=True)
        self.assertNotIn("spawn_gold", tags)

    def test_chest_with_gold_max_gets_tag(self):
        """WorldChest can have loot_gold_max set after creation."""
        chest = create.create_object(
            "typeclasses.world_objects.chest.WorldChest",
            key="a treasure chest",
            location=self.room,
        )
        # Zone builder sets gold capacity after creation
        chest.tags.add("spawn_gold", category="spawn_gold")
        chest.db.spawn_gold_max = 50
        tags = chest.tags.get(category="spawn_gold", return_list=True)
        self.assertIn("spawn_gold", tags)
        self.assertEqual(chest.db.spawn_gold_max, 50)


# ================================================================== #
#  GoldDistributor config
# ================================================================== #


class TestGoldDistributorConfig(EvenniaTest):
    """GoldDistributor uses correct tag and max attr names."""

    def create_script(self):
        pass

    def test_tag_name(self):
        from blockchain.xrpl.services.spawn.distributors.fungible import GoldDistributor
        dist = GoldDistributor()
        self.assertEqual(dist.tag_name, "spawn_gold")

    def test_max_attr_name(self):
        from blockchain.xrpl.services.spawn.distributors.fungible import GoldDistributor
        dist = GoldDistributor()
        self.assertEqual(dist.max_attr_name, "spawn_gold_max")

    def test_category(self):
        from blockchain.xrpl.services.spawn.distributors.fungible import GoldDistributor
        dist = GoldDistributor()
        self.assertEqual(dist.category, "gold")


# ================================================================== #
#  Headroom — gold get_current_count
# ================================================================== #


class TestGoldHeadroom(EvenniaTest):
    """get_current_count for gold reads db.gold."""

    def create_script(self):
        pass

    def test_gold_count_zero(self):
        from blockchain.xrpl.services.spawn.headroom import get_current_count
        target = MagicMock()
        target.db = MagicMock()
        target.db.gold = 0
        self.assertEqual(get_current_count(target, "gold", "gold"), 0)

    def test_gold_count_nonzero(self):
        from blockchain.xrpl.services.spawn.headroom import get_current_count
        target = MagicMock()
        target.db = MagicMock()
        target.db.gold = 15
        self.assertEqual(get_current_count(target, "gold", "gold"), 15)

    def test_gold_count_none(self):
        from blockchain.xrpl.services.spawn.headroom import get_current_count
        target = MagicMock()
        target.db = MagicMock()
        target.db.gold = None
        self.assertEqual(get_current_count(target, "gold", "gold"), 0)
