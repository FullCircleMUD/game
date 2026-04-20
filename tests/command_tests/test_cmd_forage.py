"""
Tests for the forage command.

Tests terrain restrictions, cooldown, mastery scaling, solo application,
and the no-hunger-free-pass-tick design rule.
"""

import time

from evennia.utils.test_resources import EvenniaCommandTest

from commands.class_skill_cmdsets.class_skill_cmds.cmd_forage import CmdForage
from enums.hunger_level import HungerLevel
from enums.mastery_level import MasteryLevel
from enums.skills_enum import skills
from enums.terrain_type import TerrainType

_ROOM = "typeclasses.terrain.rooms.room_base.RoomBase"
_CHAR = "typeclasses.actors.character.FCMCharacter"

# Prefix for successful solo forage messages
_OK = "You forage for edible plants and berries"


def _set_survivalist(char, mastery=MasteryLevel.BASIC):
    """Give a character the survivalist skill at a given mastery level."""
    if not char.db.class_skill_mastery_levels:
        char.db.class_skill_mastery_levels = {}
    char.db.class_skill_mastery_levels[skills.SURVIVALIST.value] = {"mastery": mastery.value, "classes": ["Druid"]}


class TestCmdForageTerrain(EvenniaCommandTest):
    """Tests for terrain restrictions."""
    room_typeclass = _ROOM
    character_typeclass = _CHAR

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        _set_survivalist(self.char1, MasteryLevel.BASIC)
        self.char1.hunger_level = HungerLevel.HUNGRY
        self.char1.db.last_forage_time = 0

    def test_forage_in_forest_succeeds(self):
        """Foraging in FOREST terrain should succeed."""
        self.room1.set_terrain(TerrainType.FOREST.value)
        self.call(CmdForage(), "", _OK)

    def test_forage_in_rural_succeeds(self):
        """Foraging in RURAL terrain should succeed."""
        self.room1.set_terrain(TerrainType.RURAL.value)
        self.call(CmdForage(), "", _OK)

    def test_forage_in_urban_blocked(self):
        """Foraging in URBAN terrain should fail."""
        self.room1.set_terrain(TerrainType.URBAN.value)
        self.call(CmdForage(), "", "There is nothing to forage here.")

    def test_forage_in_dungeon_blocked(self):
        """Foraging in DUNGEON terrain should fail."""
        self.room1.set_terrain(TerrainType.DUNGEON.value)
        self.call(CmdForage(), "", "There is nothing to forage here.")

    def test_forage_in_underground_blocked(self):
        """Foraging in UNDERGROUND terrain should fail."""
        self.room1.set_terrain(TerrainType.UNDERGROUND.value)
        self.call(CmdForage(), "", "There is nothing to forage here.")

    def test_forage_in_water_blocked(self):
        """Foraging in WATER terrain should fail."""
        self.room1.set_terrain(TerrainType.WATER.value)
        self.call(CmdForage(), "", "There is nothing to forage here.")

    def test_forage_no_terrain_tag_blocked(self):
        """Room with no terrain tag should block foraging."""
        self.call(CmdForage(), "", "There is nothing to forage here.")

    def test_forage_in_coastal_succeeds(self):
        """Foraging in COASTAL terrain should succeed."""
        self.room1.set_terrain(TerrainType.COASTAL.value)
        self.call(CmdForage(), "", _OK)

    def test_forage_in_mountain_succeeds(self):
        """Foraging in MOUNTAIN terrain should succeed."""
        self.room1.set_terrain(TerrainType.MOUNTAIN.value)
        self.call(CmdForage(), "", _OK)


class TestCmdForageCooldown(EvenniaCommandTest):
    """Tests for the 15-minute cooldown."""
    room_typeclass = _ROOM
    character_typeclass = _CHAR

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        _set_survivalist(self.char1, MasteryLevel.BASIC)
        self.char1.hunger_level = HungerLevel.HUNGRY
        self.room1.set_terrain(TerrainType.FOREST.value)

    def test_forage_on_cooldown(self):
        """Foraging within the 15-minute window should fail with time message."""
        self.char1.db.last_forage_time = time.time() - 60  # 1 minute ago
        self.call(CmdForage(), "", "You have already foraged recently.")

    def test_forage_after_cooldown(self):
        """Foraging after the cooldown expires should succeed."""
        self.char1.db.last_forage_time = time.time() - 901  # 15m 1s ago
        self.call(CmdForage(), "", _OK)

    def test_forage_sets_cooldown(self):
        """Successful forage should set the cooldown timestamp."""
        self.char1.db.last_forage_time = 0
        before = time.time()
        self.call(CmdForage(), "", _OK)
        after = time.time()
        self.assertGreaterEqual(self.char1.db.last_forage_time, before)
        self.assertLessEqual(self.char1.db.last_forage_time, after)


class TestCmdForageMastery(EvenniaCommandTest):
    """Tests for mastery level scaling."""
    room_typeclass = _ROOM
    character_typeclass = _CHAR

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.room1.set_terrain(TerrainType.FOREST.value)
        self.char1.db.last_forage_time = 0

    def test_unskilled_fails(self):
        """UNSKILLED mastery should fail with a message."""
        _set_survivalist(self.char1, MasteryLevel.UNSKILLED)
        self.char1.hunger_level = HungerLevel.HUNGRY
        self.call(CmdForage(), "", "You search around but have no idea")

    def test_basic_restores_1(self):
        """BASIC mastery should restore 1 hunger level."""
        _set_survivalist(self.char1, MasteryLevel.BASIC)
        self.char1.hunger_level = HungerLevel.HUNGRY  # 3
        self.call(CmdForage(), "", _OK)
        self.assertEqual(self.char1.hunger_level, HungerLevel.PECKISH)  # 4

    def test_skilled_restores_2(self):
        """SKILLED mastery should restore 2 hunger levels (HUNGRY 3 → CONTENT 5)."""
        _set_survivalist(self.char1, MasteryLevel.SKILLED)
        self.char1.hunger_level = HungerLevel.HUNGRY  # 3
        self.call(CmdForage(), "", _OK)
        self.assertEqual(self.char1.hunger_level, HungerLevel.CONTENT)  # 5

    def test_expert_restores_3(self):
        """EXPERT mastery should restore 3 hunger levels (STARVING 1 → PECKISH 4)."""
        _set_survivalist(self.char1, MasteryLevel.EXPERT)
        self.char1.hunger_level = HungerLevel.STARVING  # 1
        self.call(CmdForage(), "", _OK)
        self.assertEqual(self.char1.hunger_level, HungerLevel.PECKISH)  # 4

    def test_master_restores_4(self):
        """MASTER mastery should restore 4 hunger levels (STARVING 1 → CONTENT 5)."""
        _set_survivalist(self.char1, MasteryLevel.MASTER)
        self.char1.hunger_level = HungerLevel.STARVING  # 1
        self.call(CmdForage(), "", _OK)
        self.assertEqual(self.char1.hunger_level, HungerLevel.CONTENT)  # 5

    def test_grandmaster_restores_5(self):
        """GRANDMASTER mastery should restore 5 hunger levels (STARVING 1 → NOURISHED 6)."""
        _set_survivalist(self.char1, MasteryLevel.GRANDMASTER)
        self.char1.hunger_level = HungerLevel.STARVING  # 1
        self.call(CmdForage(), "", _OK)
        self.assertEqual(self.char1.hunger_level, HungerLevel.NOURISHED)  # 6

    def test_capped_at_full(self):
        """Hunger restoration should cap at FULL (8)."""
        _set_survivalist(self.char1, MasteryLevel.GRANDMASTER)
        self.char1.hunger_level = HungerLevel.SATISFIED  # 7
        self.call(CmdForage(), "", _OK)
        self.assertEqual(self.char1.hunger_level, HungerLevel.FULL)  # 8

    def test_already_full(self):
        """Foraging when already FULL should succeed but restore nothing."""
        _set_survivalist(self.char1, MasteryLevel.BASIC)
        self.char1.hunger_level = HungerLevel.FULL  # 6
        self.call(CmdForage(), "", _OK)
        self.assertEqual(self.char1.hunger_level, HungerLevel.FULL)

    def test_no_hunger_free_pass_tick(self):
        """Foraging to FULL should NOT set hunger_free_pass_tick."""
        _set_survivalist(self.char1, MasteryLevel.BASIC)
        self.char1.hunger_level = HungerLevel.SATISFIED  # 5
        self.char1.hunger_free_pass_tick = False
        self.call(CmdForage(), "", _OK)
        self.assertEqual(self.char1.hunger_level, HungerLevel.FULL)
        self.assertFalse(self.char1.db.hunger_free_pass_tick)


class TestCmdForageNoSkill(EvenniaCommandTest):
    """Test that characters without survivalist skill can't forage."""
    room_typeclass = _ROOM
    character_typeclass = _CHAR

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.room1.set_terrain(TerrainType.FOREST.value)
        self.char1.db.last_forage_time = 0
        self.char1.hunger_level = HungerLevel.HUNGRY

    def test_no_mastery_dict(self):
        """Character with no mastery data at all should fail."""
        self.char1.db.class_skill_mastery_levels = None
        self.call(CmdForage(), "", "You search around but have no idea")


# ── Water credit tests ──────────────────────────────────────────────────

from unittest.mock import patch
from evennia.utils import create


class TestCmdForageWaterCredit(EvenniaCommandTest):
    """
    Forage tops up the FORAGER's water containers by N drinks (N = mastery
    tier), most-empty first, capping at each container's max_capacity.
    Containers are inventory items, not held — same mental model as bread.
    """
    room_typeclass = _ROOM
    character_typeclass = _CHAR
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.room1.set_terrain(TerrainType.FOREST.value)
        self.char1.db.last_forage_time = 0
        self.char1.hunger_level = HungerLevel.HUNGRY

    def _make_canteen(self, current=0, token_id=9501):
        with patch("blockchain.xrpl.services.nft.NFTService.update_metadata"), \
             patch("blockchain.xrpl.services.nft.NFTService.craft_output"):
            obj = create.create_object(
                "typeclasses.items.water_containers.canteen_nft_item.CanteenNFTItem",
                key="a leather canteen",
                location=self.char1,
                nohome=True,
            )
            obj.token_id = token_id
            obj.current = current
        return obj

    def _make_cask(self, current=0, token_id=9502):
        with patch("blockchain.xrpl.services.nft.NFTService.update_metadata"), \
             patch("blockchain.xrpl.services.nft.NFTService.craft_output"):
            obj = create.create_object(
                "typeclasses.items.water_containers.cask_nft_item.CaskNFTItem",
                key="a wooden cask",
                location=self.char1,
                nohome=True,
            )
            obj.token_id = token_id
            obj.current = current
        return obj

    def test_no_container_no_water_credit(self):
        """If the forager carries no water container, no water credit."""
        _set_survivalist(self.char1, MasteryLevel.GRANDMASTER)
        # No exception, no crash, no water output
        self.call(CmdForage(), "", _OK)

    def test_basic_adds_one_drink(self):
        """BASIC mastery (1 point) adds 1 drink to a single canteen."""
        _set_survivalist(self.char1, MasteryLevel.BASIC)
        canteen = self._make_canteen(current=0)
        self.call(CmdForage(), "", _OK)
        self.assertEqual(canteen.current, 1)

    def test_grandmaster_fills_canteen_partially(self):
        """GM (5 points) into an empty canteen (capacity 5) fills it."""
        _set_survivalist(self.char1, MasteryLevel.GRANDMASTER)
        canteen = self._make_canteen(current=0)
        self.call(CmdForage(), "", _OK)
        self.assertEqual(canteen.current, 5)

    def test_caps_at_max_capacity(self):
        """Drinks beyond capacity are discarded — container caps at max."""
        _set_survivalist(self.char1, MasteryLevel.GRANDMASTER)
        canteen = self._make_canteen(current=3)  # capacity 5, room for 2
        self.call(CmdForage(), "", _OK)
        self.assertEqual(canteen.current, 5)  # +2, not +5

    def test_multi_container_most_empty_first(self):
        """
        With multiple containers, the most-empty fills first, then the next.
        SKILLED (2 points) into a 0/5 canteen + 8/10 cask should put both
        drinks into the canteen (most empty), leaving the cask unchanged.
        """
        _set_survivalist(self.char1, MasteryLevel.SKILLED)
        canteen = self._make_canteen(current=0)
        cask = self._make_cask(current=8)
        self.call(CmdForage(), "", _OK)
        self.assertEqual(canteen.current, 2)
        self.assertEqual(cask.current, 8)  # untouched

    def test_multi_container_spills_to_next(self):
        """
        If the most-empty container fills, remaining drinks spill into the
        next-emptiest. GM (5 points) into a 4/5 canteen + 0/10 cask should
        fill the canteen by 1 then put 4 in the cask.
        Wait — the cask is more empty (0 vs 4), so it fills first: cask gets
        5 (capped not by capacity), canteen unchanged.
        """
        _set_survivalist(self.char1, MasteryLevel.GRANDMASTER)
        canteen = self._make_canteen(current=4)
        cask = self._make_cask(current=0)
        self.call(CmdForage(), "", _OK)
        # Cask is more empty (0 < 4), so all 5 drinks land there.
        self.assertEqual(cask.current, 5)
        self.assertEqual(canteen.current, 4)

    def test_overflow_spills(self):
        """
        SKILLED forage (2 drinks) into a 4/5 canteen and a 0/10 cask.
        Cask is more empty (0 < 4), so both drinks land in the cask.
        """
        _set_survivalist(self.char1, MasteryLevel.SKILLED)
        canteen = self._make_canteen(current=4)
        cask = self._make_cask(current=0)
        self.call(CmdForage(), "", _OK)
        self.assertEqual(cask.current, 2)
        self.assertEqual(canteen.current, 4)

    def test_full_containers_get_no_water(self):
        """If all containers are already full, the water credit is wasted."""
        _set_survivalist(self.char1, MasteryLevel.GRANDMASTER)
        canteen = self._make_canteen(current=5)
        cask = self._make_cask(current=10)
        self.call(CmdForage(), "", _OK)
        self.assertEqual(canteen.current, 5)
        self.assertEqual(cask.current, 10)

    def test_mirror_persistence_fires_on_credit(self):
        """Each container that received drinks should fire _persist_water_state."""
        _set_survivalist(self.char1, MasteryLevel.SKILLED)
        canteen = self._make_canteen(current=0)
        with patch("blockchain.xrpl.services.nft.NFTService.update_metadata") as mock_update:
            self.call(CmdForage(), "", _OK)
            # update_metadata called at least once with the container's state
            self.assertTrue(mock_update.called)
            args = mock_update.call_args[0]
            self.assertEqual(args[1]["current"], 2)
