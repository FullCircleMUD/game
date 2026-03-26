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
        """SKILLED mastery should restore 2 hunger levels."""
        _set_survivalist(self.char1, MasteryLevel.SKILLED)
        self.char1.hunger_level = HungerLevel.HUNGRY  # 3
        self.call(CmdForage(), "", _OK)
        self.assertEqual(self.char1.hunger_level, HungerLevel.SATISFIED)  # 5

    def test_expert_restores_3(self):
        """EXPERT mastery should restore 3 hunger levels."""
        _set_survivalist(self.char1, MasteryLevel.EXPERT)
        self.char1.hunger_level = HungerLevel.STARVING  # 1
        self.call(CmdForage(), "", _OK)
        self.assertEqual(self.char1.hunger_level, HungerLevel.PECKISH)  # 4

    def test_master_restores_4(self):
        """MASTER mastery should restore 4 hunger levels."""
        _set_survivalist(self.char1, MasteryLevel.MASTER)
        self.char1.hunger_level = HungerLevel.STARVING  # 1
        self.call(CmdForage(), "", _OK)
        self.assertEqual(self.char1.hunger_level, HungerLevel.SATISFIED)  # 5

    def test_grandmaster_restores_5(self):
        """GRANDMASTER mastery should restore 5 hunger levels."""
        _set_survivalist(self.char1, MasteryLevel.GRANDMASTER)
        self.char1.hunger_level = HungerLevel.STARVING  # 1
        self.call(CmdForage(), "", _OK)
        self.assertEqual(self.char1.hunger_level, HungerLevel.FULL)  # 6

    def test_capped_at_full(self):
        """Hunger restoration should cap at FULL (6)."""
        _set_survivalist(self.char1, MasteryLevel.GRANDMASTER)
        self.char1.hunger_level = HungerLevel.SATISFIED  # 5
        self.call(CmdForage(), "", _OK)
        self.assertEqual(self.char1.hunger_level, HungerLevel.FULL)  # 6

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
