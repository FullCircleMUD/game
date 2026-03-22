"""
Tests for the Day/Night cycle system.

Covers:
    - TimeOfDay enum (hour → phase mapping)
    - DayNightService (phase transitions, broadcasts)
    - Room darkness (natural_light, is_dark, dark rendering)
    - LightSourceMixin (light, extinguish, fuel)
    - LightBurnScript (fuel decrement, exhaustion)
    - TorchNFTItem (consumable, destroyed on empty)
    - LanternNFTItem (reusable, kept on empty)
    - LitFixture (infinite, always lit)
"""

from unittest.mock import patch, PropertyMock, MagicMock

from evennia.utils.test_resources import EvenniaTest
from evennia.utils import create

from enums.time_of_day import TimeOfDay
from enums.condition import Condition
from enums.terrain_type import TerrainType


class TestTimeOfDay(EvenniaTest):
    """Test TimeOfDay enum and hour-to-phase mapping."""

    def create_script(self):
        pass

    def test_dawn_hours(self):
        for hour in (5, 6, 7):
            self.assertEqual(TimeOfDay.from_hour(hour), TimeOfDay.DAWN)

    def test_day_hours(self):
        for hour in (8, 12, 17):
            self.assertEqual(TimeOfDay.from_hour(hour), TimeOfDay.DAY)

    def test_dusk_hours(self):
        for hour in (18, 19, 20):
            self.assertEqual(TimeOfDay.from_hour(hour), TimeOfDay.DUSK)

    def test_night_hours(self):
        for hour in (21, 23, 0, 1, 4):
            self.assertEqual(TimeOfDay.from_hour(hour), TimeOfDay.NIGHT)

    def test_dawn_is_light(self):
        self.assertTrue(TimeOfDay.DAWN.is_light)

    def test_day_is_light(self):
        self.assertTrue(TimeOfDay.DAY.is_light)

    def test_dusk_is_light(self):
        self.assertTrue(TimeOfDay.DUSK.is_light)

    def test_night_is_not_light(self):
        self.assertFalse(TimeOfDay.NIGHT.is_light)


class TestRoomNaturalLight(EvenniaTest):
    """Test room natural_light attribute and terrain-based defaults."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def test_default_has_natural_light_true(self):
        """Rooms with no terrain tag default to natural light."""
        self.assertTrue(self.room1.has_natural_light)

    def test_underground_no_natural_light(self):
        """Underground rooms are dark by default."""
        self.room1.set_terrain(TerrainType.UNDERGROUND.value)
        self.assertFalse(self.room1.has_natural_light)

    def test_dungeon_no_natural_light(self):
        """Dungeon rooms are dark by default."""
        self.room1.set_terrain(TerrainType.DUNGEON.value)
        self.assertFalse(self.room1.has_natural_light)

    def test_forest_has_natural_light(self):
        """Forest rooms have natural light."""
        self.room1.set_terrain(TerrainType.FOREST.value)
        self.assertTrue(self.room1.has_natural_light)

    def test_urban_has_natural_light(self):
        """Urban rooms have natural light."""
        self.room1.set_terrain(TerrainType.URBAN.value)
        self.assertTrue(self.room1.has_natural_light)

    def test_explicit_true_overrides_terrain(self):
        """Explicitly set natural_light=True overrides dark terrain."""
        self.room1.set_terrain(TerrainType.UNDERGROUND.value)
        self.room1.natural_light = True
        self.assertTrue(self.room1.has_natural_light)

    def test_explicit_false_overrides_terrain(self):
        """Explicitly set natural_light=False makes outdoor room dark."""
        self.room1.set_terrain(TerrainType.FOREST.value)
        self.room1.natural_light = False
        self.assertFalse(self.room1.has_natural_light)


class TestRoomIsDark(EvenniaTest):
    """Test room is_dark() logic."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    @patch("typeclasses.scripts.day_night_service.get_time_of_day")
    def test_natural_light_room_during_day_not_dark(self, mock_tod):
        """Room with natural light during DAY is not dark."""
        mock_tod.return_value = TimeOfDay.DAY
        self.assertFalse(self.room1.is_dark(self.char1))

    @patch("typeclasses.scripts.day_night_service.get_time_of_day")
    def test_natural_light_room_during_night_is_dark(self, mock_tod):
        """Room with natural light during NIGHT is dark."""
        mock_tod.return_value = TimeOfDay.NIGHT
        self.assertTrue(self.room1.is_dark(self.char1))

    @patch("typeclasses.scripts.day_night_service.get_time_of_day")
    def test_natural_light_room_during_dawn_not_dark(self, mock_tod):
        """Room with natural light during DAWN is not dark."""
        mock_tod.return_value = TimeOfDay.DAWN
        self.assertFalse(self.room1.is_dark(self.char1))

    @patch("typeclasses.scripts.day_night_service.get_time_of_day")
    def test_underground_room_always_dark(self, mock_tod):
        """Underground room is dark even during DAY."""
        mock_tod.return_value = TimeOfDay.DAY
        self.room1.set_terrain(TerrainType.UNDERGROUND.value)
        self.assertTrue(self.room1.is_dark(self.char1))

    @patch("typeclasses.scripts.day_night_service.get_time_of_day")
    def test_darkvision_sees_in_dark(self, mock_tod):
        """Character with DARKVISION can see in a dark room."""
        mock_tod.return_value = TimeOfDay.NIGHT
        self.char1.add_condition(Condition.DARKVISION)
        self.assertFalse(self.room1.is_dark(self.char1))

    @patch("typeclasses.scripts.day_night_service.get_time_of_day")
    def test_lit_fixture_in_room_prevents_dark(self, mock_tod):
        """A lit light source in the room prevents darkness."""
        mock_tod.return_value = TimeOfDay.NIGHT
        # Create a mock light source in the room
        fixture = create.create_object(
            "typeclasses.world_objects.lit_fixture.LitFixture",
            key="lamppost",
            location=self.room1,
            nohome=True,
        )
        self.assertFalse(self.room1.is_dark(self.char1))

    @patch("typeclasses.scripts.day_night_service.get_time_of_day")
    def test_unlit_fixture_doesnt_prevent_dark(self, mock_tod):
        """An unlit light source in the room doesn't prevent darkness."""
        mock_tod.return_value = TimeOfDay.NIGHT
        fixture = create.create_object(
            "typeclasses.world_objects.lit_fixture.LitFixture",
            key="lamppost",
            location=self.room1,
            nohome=True,
        )
        fixture.is_lit = False
        self.assertTrue(self.room1.is_dark(self.char1))

    @patch("typeclasses.scripts.day_night_service.get_time_of_day")
    def test_carried_light_prevents_dark(self, mock_tod):
        """A lit light source carried by the looker prevents darkness."""
        mock_tod.return_value = TimeOfDay.NIGHT
        # Create a simple object with light source attributes
        light = create.create_object(
            key="torch",
            location=self.char1,
            nohome=True,
        )
        light.db.is_light_source = True
        light.is_light_source = True
        light.db.is_lit = True
        light.is_lit = True
        self.assertFalse(self.room1.is_dark(self.char1))


class TestDarkRoomRendering(EvenniaTest):
    """Test that dark rooms show limited information."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    @patch("typeclasses.scripts.day_night_service.get_time_of_day")
    def test_dark_room_desc_shows_pitch_black(self, mock_tod):
        """Dark room description shows pitch black message."""
        mock_tod.return_value = TimeOfDay.NIGHT
        desc = self.room1.get_display_desc(self.char1)
        self.assertIn("pitch black", desc)

    @patch("typeclasses.scripts.day_night_service.get_time_of_day")
    def test_dark_room_characters_empty(self, mock_tod):
        """Dark room doesn't show characters."""
        mock_tod.return_value = TimeOfDay.NIGHT
        result = self.room1.get_display_characters(self.char1)
        self.assertEqual(result, "")

    @patch("typeclasses.scripts.day_night_service.get_time_of_day")
    def test_dark_room_things_empty(self, mock_tod):
        """Dark room doesn't show things."""
        mock_tod.return_value = TimeOfDay.NIGHT
        result = self.room1.get_display_things(self.char1)
        self.assertEqual(result, "")

    @patch("typeclasses.scripts.day_night_service.get_time_of_day")
    def test_lit_room_shows_normal_desc(self, mock_tod):
        """Lit room shows the normal description."""
        mock_tod.return_value = TimeOfDay.DAY
        self.room1.db.desc = "A sunny clearing."
        desc = self.room1.get_display_desc(self.char1)
        self.assertEqual(desc, "A sunny clearing.")


class TestLightSourceMixin(EvenniaTest):
    """Test LightSourceMixin methods."""

    def create_script(self):
        pass

    def _make_light_source(self, **kwargs):
        """Create a simple light source fixture for testing."""
        obj = create.create_object(
            "typeclasses.world_objects.lit_fixture.LitFixture",
            key="test light",
            nohome=True,
        )
        for k, v in kwargs.items():
            setattr(obj, k, v)
        return obj

    def test_light_sets_is_lit(self):
        obj = self._make_light_source(is_lit=False, fuel_remaining=100, max_fuel=100)
        success, _ = obj.light()
        self.assertTrue(success)
        self.assertTrue(obj.is_lit)

    def test_light_already_lit_fails(self):
        obj = self._make_light_source(is_lit=True)
        success, msg = obj.light()
        self.assertFalse(success)
        self.assertIn("already lit", msg)

    def test_light_no_fuel_fails(self):
        obj = self._make_light_source(is_lit=False, fuel_remaining=0, max_fuel=100)
        success, msg = obj.light()
        self.assertFalse(success)
        self.assertIn("no fuel", msg)

    def test_extinguish_sets_not_lit(self):
        obj = self._make_light_source(is_lit=True, fuel_remaining=50, max_fuel=100)
        success, _ = obj.extinguish()
        self.assertTrue(success)
        self.assertFalse(obj.is_lit)

    def test_extinguish_preserves_fuel(self):
        obj = self._make_light_source(is_lit=True, fuel_remaining=50, max_fuel=100)
        obj.extinguish()
        self.assertEqual(obj.fuel_remaining, 50)

    def test_extinguish_not_lit_fails(self):
        obj = self._make_light_source(is_lit=False)
        success, msg = obj.extinguish()
        self.assertFalse(success)
        self.assertIn("not lit", msg)

    def test_refuel_sets_to_max(self):
        obj = self._make_light_source(is_lit=False, fuel_remaining=10, max_fuel=100)
        success, _ = obj.refuel()
        self.assertTrue(success)
        self.assertEqual(obj.fuel_remaining, 100)

    def test_refuel_already_full_fails(self):
        obj = self._make_light_source(is_lit=False, fuel_remaining=100, max_fuel=100)
        success, msg = obj.refuel()
        self.assertFalse(success)
        self.assertIn("already full", msg)

    def test_refuel_infinite_fails(self):
        obj = self._make_light_source(is_lit=True, fuel_remaining=-1, max_fuel=-1)
        success, msg = obj.refuel()
        self.assertFalse(success)

    def test_fuel_display_format(self):
        obj = self._make_light_source(fuel_remaining=125)
        display = obj.get_fuel_display()
        self.assertEqual(display, "2:05")

    def test_fuel_display_zero(self):
        obj = self._make_light_source(fuel_remaining=0)
        display = obj.get_fuel_display()
        self.assertEqual(display, "0:00")


class TestLightBurnScript(EvenniaTest):
    """Test LightBurnScript fuel decrement and exhaustion."""

    def create_script(self):
        pass

    def test_tick_decrements_fuel(self):
        """Burn script tick decrements fuel on the light source."""
        from typeclasses.scripts.light_burn import LightBurnScript, BURN_TICK_SECONDS

        obj = create.create_object(
            "typeclasses.world_objects.lit_fixture.LitFixture",
            key="test lamp",
            location=self.room1,
            nohome=True,
        )
        obj.is_lit = True
        obj.fuel_remaining = 100
        obj.max_fuel = 100

        # Use MagicMock script with obj set as attribute
        script = MagicMock(spec=LightBurnScript)
        script.obj = obj
        # Call the real at_repeat
        LightBurnScript.at_repeat(script)
        self.assertEqual(obj.fuel_remaining, 100 - BURN_TICK_SECONDS)

    def test_tick_extinguishes_lantern_at_zero(self):
        """Non-consumable light extinguishes at zero fuel."""
        from typeclasses.scripts.light_burn import LightBurnScript, BURN_TICK_SECONDS

        obj = create.create_object(
            "typeclasses.world_objects.lit_fixture.LitFixture",
            key="test lamp",
            location=self.room1,
            nohome=True,
        )
        obj.is_lit = True
        obj.fuel_remaining = 5  # less than BURN_TICK_SECONDS
        obj.max_fuel = 100
        obj.is_consumable_light = False

        script = MagicMock(spec=LightBurnScript)
        script.obj = obj
        # Wire up the real helper methods so at_repeat can call them
        script._get_holder = lambda o: LightBurnScript._get_holder(script, o)
        script._check_warnings = lambda o, h: LightBurnScript._check_warnings(script, o, h)
        script._fuel_exhausted = lambda o, h: LightBurnScript._fuel_exhausted(script, o, h)
        LightBurnScript.at_repeat(script)
        self.assertFalse(obj.is_lit)
        self.assertEqual(obj.fuel_remaining, 0)


class TestTorchNFTItem(EvenniaTest):
    """Test TorchNFTItem creation and display."""

    def create_script(self):
        pass

    def test_torch_is_light_source(self):
        torch = create.create_object(
            "typeclasses.items.holdables.torch_nft_item.TorchNFTItem",
            key="a torch",
            nohome=True,
        )
        self.assertTrue(torch.is_light_source)
        self.assertTrue(torch.is_consumable_light)

    def test_torch_display_name_unlit_full(self):
        torch = create.create_object(
            "typeclasses.items.holdables.torch_nft_item.TorchNFTItem",
            key="a torch",
            nohome=True,
        )
        name = torch.get_display_name(self.char1)
        self.assertIn("unlit, full", name)

    def test_torch_display_name_lit(self):
        torch = create.create_object(
            "typeclasses.items.holdables.torch_nft_item.TorchNFTItem",
            key="a torch",
            nohome=True,
        )
        torch.is_lit = True
        torch.fuel_remaining = 300
        name = torch.get_display_name(self.char1)
        self.assertIn("lit", name)
        self.assertIn("5:00", name)

    def test_torch_display_name_spent(self):
        torch = create.create_object(
            "typeclasses.items.holdables.torch_nft_item.TorchNFTItem",
            key="a torch",
            nohome=True,
        )
        torch.fuel_remaining = 0
        name = torch.get_display_name(self.char1)
        self.assertIn("spent", name)


class TestLanternNFTItem(EvenniaTest):
    """Test LanternNFTItem creation and display."""

    def create_script(self):
        pass

    def test_lantern_is_light_source(self):
        lantern = create.create_object(
            "typeclasses.items.holdables.lantern_nft_item.LanternNFTItem",
            key="a lantern",
            nohome=True,
        )
        self.assertTrue(lantern.is_light_source)
        self.assertFalse(lantern.is_consumable_light)

    def test_lantern_display_name_empty(self):
        lantern = create.create_object(
            "typeclasses.items.holdables.lantern_nft_item.LanternNFTItem",
            key="a lantern",
            nohome=True,
        )
        lantern.fuel_remaining = 0
        name = lantern.get_display_name(self.char1)
        self.assertIn("empty", name)

    def test_lantern_display_name_full(self):
        lantern = create.create_object(
            "typeclasses.items.holdables.lantern_nft_item.LanternNFTItem",
            key="a lantern",
            nohome=True,
        )
        name = lantern.get_display_name(self.char1)
        self.assertIn("full", name)


class TestLitFixture(EvenniaTest):
    """Test LitFixture creation."""

    def create_script(self):
        pass

    def test_lit_fixture_always_lit(self):
        fixture = create.create_object(
            "typeclasses.world_objects.lit_fixture.LitFixture",
            key="a lamppost",
            location=self.room1,
            nohome=True,
        )
        self.assertTrue(fixture.is_lit)
        self.assertTrue(fixture.is_light_source)
        self.assertEqual(fixture.fuel_remaining, -1)

    def test_lit_fixture_cannot_pick_up(self):
        fixture = create.create_object(
            "typeclasses.world_objects.lit_fixture.LitFixture",
            key="a lamppost",
            location=self.room1,
            nohome=True,
        )
        result = fixture.at_pre_get(self.char1)
        self.assertFalse(result)


class TestDayNightService(EvenniaTest):
    """Test DayNightService phase transition detection."""

    def create_script(self):
        pass

    @patch("typeclasses.scripts.day_night_service.get_time_of_day")
    def test_no_broadcast_on_same_phase(self, mock_tod):
        """No broadcast when phase hasn't changed."""
        from typeclasses.scripts.day_night_service import DayNightService

        mock_tod.return_value = TimeOfDay.DAY
        service = MagicMock(spec=DayNightService)
        service.ndb = MagicMock()
        service.ndb.last_phase = TimeOfDay.DAY

        DayNightService.at_repeat(service)
        service._broadcast_transition.assert_not_called()

    @patch("typeclasses.scripts.day_night_service.get_time_of_day")
    def test_broadcast_on_phase_change(self, mock_tod):
        """Broadcast when phase changes."""
        from typeclasses.scripts.day_night_service import DayNightService

        mock_tod.return_value = TimeOfDay.NIGHT
        service = MagicMock(spec=DayNightService)
        service.ndb = MagicMock()
        service.ndb.last_phase = TimeOfDay.DUSK

        DayNightService.at_repeat(service)
        service._broadcast_transition.assert_called_once_with(TimeOfDay.NIGHT)
