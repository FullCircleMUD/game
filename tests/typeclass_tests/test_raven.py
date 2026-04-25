"""
Tests for the raven flock — 8 ravens that are passive by default but
pull the whole flock into combat when any one is attacked.

evennia test --settings settings tests.typeclass_tests.test_raven
"""

from unittest.mock import patch

from evennia.utils import create
from evennia.utils.test_resources import EvenniaTest


class TestRavenStats(EvenniaTest):
    """Baseline stats for Raven and RavenFlockLeader."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.raven = create.create_object(
            "typeclasses.actors.mobs.raven.Raven",
            key="a raven",
            location=self.room1,
        )
        self.leader = create.create_object(
            "typeclasses.actors.mobs.raven.RavenFlockLeader",
            key="a raven",
            location=self.room1,
        )

    def test_raven_stats(self):
        self.assertEqual(self.raven.hp_max, 12)
        self.assertEqual(self.raven.base_armor_class, 13)
        self.assertEqual(self.raven.dexterity, 16)
        self.assertEqual(self.raven.level, 3)
        self.assertEqual(self.raven.damage_dice, "1d4+1")

    def test_leader_stats_match_follower(self):
        """Leader and follower have identical stats — players can't tell them apart."""
        self.assertEqual(self.leader.hp_max, self.raven.hp_max)
        self.assertEqual(self.leader.level, self.raven.level)
        self.assertEqual(self.leader.damage_dice, self.raven.damage_dice)

    def test_raven_is_passive(self):
        """Raven MRO must not include AggressiveMixin — ravens don't aggro on sight."""
        from typeclasses.mixins.aggressive_mixin import AggressiveMixin
        self.assertNotIn(AggressiveMixin, type(self.raven).__mro__)
        self.assertNotIn(AggressiveMixin, type(self.leader).__mro__)

    def test_squad_leader_typeclass(self):
        """Raven targets RavenFlockLeader as its follow leader."""
        from typeclasses.actors.mobs.raven import RavenFlockLeader
        self.assertIs(type(self.raven).squad_leader_typeclass, RavenFlockLeader)

    def test_base_raven_drops_gold(self):
        """Base Raven and the leader carry up to 3 gold."""
        self.assertEqual(self.raven.loot_gold_max, 3)
        self.assertEqual(self.leader.loot_gold_max, 3)


class TestRavenLootVariants(EvenniaTest):
    """Loot variants — scroll and recipe ravens swap gold for a skilled drop."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def test_scroll_load_drops_skilled_scroll_no_gold(self):
        scroll_raven = create.create_object(
            "typeclasses.actors.mobs.raven.RavenScrollLoad",
            key="a raven",
            location=self.room1,
        )
        self.assertEqual(scroll_raven.loot_gold_max, 0)
        self.assertEqual(scroll_raven.spawn_scrolls_max, {"skilled": 1})
        self.assertFalse(scroll_raven.spawn_recipes_max)

    def test_recipe_load_drops_skilled_recipe_no_gold(self):
        recipe_raven = create.create_object(
            "typeclasses.actors.mobs.raven.RavenRecipeLoad",
            key="a raven",
            location=self.room1,
        )
        self.assertEqual(recipe_raven.loot_gold_max, 0)
        self.assertEqual(recipe_raven.spawn_recipes_max, {"skilled": 1})
        self.assertFalse(recipe_raven.spawn_scrolls_max)

    def test_loot_variants_inherit_follower_behavior(self):
        """Loot variants are still followers — squad_leader_typeclass intact."""
        from typeclasses.actors.mobs.raven import RavenFlockLeader, RavenScrollLoad, RavenRecipeLoad
        self.assertIs(RavenScrollLoad.squad_leader_typeclass, RavenFlockLeader)
        self.assertIs(RavenRecipeLoad.squad_leader_typeclass, RavenFlockLeader)


class TestRavenLeaderAcquisition(EvenniaTest):
    """MobFollowableMixin — Raven locks onto a RavenFlockLeader in the same room."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.leader = create.create_object(
            "typeclasses.actors.mobs.raven.RavenFlockLeader",
            key="a raven",
            location=self.room1,
        )
        self.leader.is_alive = True
        self.raven = create.create_object(
            "typeclasses.actors.mobs.raven.Raven",
            key="a raven",
            location=self.room1,
        )
        self.raven.is_alive = True

    def test_raven_acquires_leader_on_idle_tick(self):
        """When the raven ticks in the idle state, it latches onto the leader."""
        self.assertIsNone(self.raven.following)
        self.raven.ai.set_state("idle")
        self.raven.ai.run()
        self.assertEqual(self.raven.following, self.leader)

    def test_raven_without_leader_stays_unfollowed(self):
        """With no leader in the room, the raven stays unfollowed."""
        self.leader.delete()
        self.raven.ai.set_state("idle")
        self.raven.ai.run()
        self.assertIsNone(self.raven.following)


class TestRavenFlockCombat(EvenniaTest):
    """enter_combat pulls the whole flock onto the defender's side
    via the follow chain."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.room1.allow_combat = True
        self.char1.hp = 40

        self.leader = create.create_object(
            "typeclasses.actors.mobs.raven.RavenFlockLeader",
            key="a raven",
            location=self.room1,
        )
        self.leader.is_alive = True

        self.raven_a = create.create_object(
            "typeclasses.actors.mobs.raven.Raven",
            key="a raven",
            location=self.room1,
        )
        self.raven_a.is_alive = True
        self.raven_a.following = self.leader

        self.raven_b = create.create_object(
            "typeclasses.actors.mobs.raven.Raven",
            key="a raven",
            location=self.room1,
        )
        self.raven_b.is_alive = True
        self.raven_b.following = self.leader

    def tearDown(self):
        # Stop any combat handlers spun up during the test
        for mob in (self.leader, self.raven_a, self.raven_b):
            handlers = mob.scripts.get("combat_handler")
            if handlers:
                for h in handlers:
                    h.stop()
        super().tearDown()

    def test_attack_on_one_raven_pulls_flock(self):
        """Attacking raven_a should put both raven_b AND the leader into combat."""
        from combat.combat_utils import enter_combat
        enter_combat(self.char1, self.raven_a)

        self.assertTrue(self.raven_a.scripts.get("combat_handler"))
        self.assertTrue(self.raven_b.scripts.get("combat_handler"))
        self.assertTrue(self.leader.scripts.get("combat_handler"))

    def test_flock_members_share_defender_side(self):
        """All flock members must land on the same combat side (opposite to the attacker)."""
        from combat.combat_utils import enter_combat, _get_combat_side
        enter_combat(self.char1, self.raven_a)

        attacker_side = _get_combat_side(self.char1)
        for mob in (self.raven_a, self.raven_b, self.leader):
            self.assertNotEqual(_get_combat_side(mob), attacker_side)
            self.assertEqual(_get_combat_side(mob), _get_combat_side(self.raven_a))
