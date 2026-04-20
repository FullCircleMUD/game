"""
Tests for WaterContainerMixin and the canteen / cask concrete typeclasses.

Covers:
  - drink_from steps thirst up by one and decrements current
  - drink_from on an empty container fails cleanly
  - drink_from on a character with no thirst meter fails cleanly
  - hitting REFRESHED via drink sets the free-pass tick flag
  - refill_to_full sets current = max_capacity
  - is_empty / is_full properties
  - mirror metadata persistence on both write paths
  - canteen has 5 drinks, cask has 10 drinks (cask = 2x canteen)
"""

from unittest.mock import patch

from evennia.utils.test_resources import EvenniaTest
from evennia.utils import create

from enums.thirst_level import ThirstLevel


WALLET_A = "0xAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"


class WaterContainerTestBase(EvenniaTest):
    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)
        # Default thirst is REFRESHED, which now refuses drinks. Drop a stage
        # so the standard drink_from / persistence paths exercise their normal
        # flow; tests that need REFRESHED set it explicitly.
        self.char1.thirst_level = ThirstLevel.THIRSTY

    def _make_canteen(self, token_id=8101):
        with patch("blockchain.xrpl.services.nft.NFTService.update_metadata"), \
             patch("blockchain.xrpl.services.nft.NFTService.craft_output"):
            obj = create.create_object(
                "typeclasses.items.water_containers.canteen_nft_item.CanteenNFTItem",
                key="a leather canteen",
                location=self.char1,
                nohome=True,
            )
            obj.token_id = token_id
        return obj

    def _make_cask(self, token_id=8102):
        with patch("blockchain.xrpl.services.nft.NFTService.update_metadata"), \
             patch("blockchain.xrpl.services.nft.NFTService.craft_output"):
            obj = create.create_object(
                "typeclasses.items.water_containers.cask_nft_item.CaskNFTItem",
                key="a wooden cask",
                location=self.char1,
                nohome=True,
            )
            obj.token_id = token_id
        return obj


class TestCanteenDefaults(WaterContainerTestBase):

    def test_canteen_starts_full(self):
        canteen = self._make_canteen()
        self.assertEqual(canteen.current, 5)
        self.assertEqual(canteen.max_capacity, 5)
        self.assertTrue(canteen.is_full)
        self.assertFalse(canteen.is_empty)

    def test_canteen_is_water_container_marker(self):
        canteen = self._make_canteen()
        self.assertTrue(getattr(canteen, "is_water_container", False))


class TestCaskDefaults(WaterContainerTestBase):

    def test_cask_capacity_is_double_canteen(self):
        canteen = self._make_canteen()
        cask = self._make_cask()
        self.assertEqual(cask.max_capacity, canteen.max_capacity * 2)

    def test_cask_starts_full(self):
        cask = self._make_cask()
        self.assertEqual(cask.current, 10)
        self.assertTrue(cask.is_full)


class TestDrinkFrom(WaterContainerTestBase):

    def test_drink_from_steps_thirst_up_one(self):
        canteen = self._make_canteen()
        self.char1.thirst_level = ThirstLevel.THIRSTY
        canteen.drink_from(self.char1)
        self.assertEqual(self.char1.thirst_level, ThirstLevel.VERY_THIRSTY.get_level(
            ThirstLevel.THIRSTY.value + 1))

    def test_drink_from_decrements_current(self):
        canteen = self._make_canteen()
        starting = canteen.current
        canteen.drink_from(self.char1)
        self.assertEqual(canteen.current, starting - 1)

    def test_drink_from_empty_fails(self):
        canteen = self._make_canteen()
        canteen.current = 0
        ok, msg = canteen.drink_from(self.char1)
        self.assertFalse(ok)
        self.assertIn("empty", msg.lower())

    def test_drink_from_at_refreshed_refuses(self):
        canteen = self._make_canteen()
        self.char1.thirst_level = ThirstLevel.REFRESHED
        starting = canteen.current
        ok, msg = canteen.drink_from(self.char1)
        # Mirrors `eat`'s 'already full' refusal — no drink consumed.
        self.assertFalse(ok)
        self.assertIn("not thirsty", msg.lower())
        self.assertEqual(canteen.current, starting)
        self.assertEqual(self.char1.thirst_level, ThirstLevel.REFRESHED)

    def test_drink_to_refreshed_sets_free_pass(self):
        canteen = self._make_canteen()
        self.char1.thirst_level = ThirstLevel.HYDRATED
        self.char1.thirst_free_pass_tick = False
        canteen.drink_from(self.char1)
        self.assertEqual(self.char1.thirst_level, ThirstLevel.REFRESHED)
        self.assertTrue(self.char1.thirst_free_pass_tick)


class TestRefillToFull(WaterContainerTestBase):

    def test_refill_sets_current_to_max(self):
        canteen = self._make_canteen()
        canteen.current = 1
        ok, msg = canteen.refill_to_full()
        self.assertTrue(ok)
        self.assertEqual(canteen.current, canteen.max_capacity)

    def test_refill_already_full_fails(self):
        canteen = self._make_canteen()
        ok, msg = canteen.refill_to_full()
        self.assertFalse(ok)
        self.assertIn("full", msg.lower())


class TestMirrorPersistence(WaterContainerTestBase):

    @patch("blockchain.xrpl.services.nft.NFTService.update_metadata")
    def test_drink_persists_state(self, mock_update):
        canteen = self._make_canteen()
        mock_update.reset_mock()
        canteen.drink_from(self.char1)
        mock_update.assert_called_once()
        args = mock_update.call_args[0]
        self.assertEqual(args[1]["current"], canteen.current)
        self.assertEqual(args[1]["max_capacity"], canteen.max_capacity)

    @patch("blockchain.xrpl.services.nft.NFTService.update_metadata")
    def test_refill_persists_state(self, mock_update):
        canteen = self._make_canteen()
        canteen.current = 0
        mock_update.reset_mock()
        canteen.refill_to_full()
        mock_update.assert_called_once()
        args = mock_update.call_args[0]
        self.assertEqual(args[1]["current"], canteen.max_capacity)
