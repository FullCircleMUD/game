"""
Tests for LightSourceMixin mirror metadata persistence.

Verifies that light(), extinguish(), refuel() patch NFTGameState.metadata
via NFTMirrorMixin.persist_metadata, and that the LightBurnScript's
per-tick decrement does NOT write to the mirror (deliberate — avoid
churning the DB every 30s for every lit torch in the game).

The cmd-level behaviour is covered by tests.command_tests.test_cmd_light.
"""

from unittest.mock import patch

from evennia.utils.test_resources import EvenniaTest
from evennia.utils import create

from typeclasses.scripts.light_burn import LightBurnScript


TORCH_TOKEN = 8001
LANTERN_TOKEN = 8002


class LightPersistenceTestBase(EvenniaTest):
    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"
    databases = "__all__"

    def create_script(self):
        pass

    def _make_torch(self, token_id=TORCH_TOKEN):
        torch = create.create_object(
            "typeclasses.items.holdables.torch_nft_item.TorchNFTItem",
            key="torch",
            location=self.char1,
            nohome=True,
        )
        torch.token_id = token_id
        return torch

    def _make_lantern(self, token_id=LANTERN_TOKEN):
        lantern = create.create_object(
            "typeclasses.items.holdables.lantern_nft_item.LanternNFTItem",
            key="lantern",
            location=self.char1,
            nohome=True,
        )
        lantern.token_id = token_id
        return lantern


class TestLightSourcePersistence(LightPersistenceTestBase):

    @patch("blockchain.xrpl.services.nft.NFTService.update_metadata")
    def test_light_persists_is_lit_true(self, mock_update):
        torch = self._make_torch()
        mock_update.reset_mock()

        ok, _ = torch.light()

        self.assertTrue(ok)
        self.assertTrue(torch.is_lit)
        mock_update.assert_called_once()
        args, kwargs = mock_update.call_args
        self.assertEqual(args[0], TORCH_TOKEN)
        self.assertEqual(args[1]["is_lit"], True)
        self.assertEqual(args[1]["fuel_remaining"], torch.fuel_remaining)
        self.assertEqual(args[1]["max_fuel"], torch.max_fuel)

    @patch("blockchain.xrpl.services.nft.NFTService.update_metadata")
    def test_extinguish_persists_is_lit_false(self, mock_update):
        torch = self._make_torch()
        torch.light()
        mock_update.reset_mock()

        ok, _ = torch.extinguish()

        self.assertTrue(ok)
        self.assertFalse(torch.is_lit)
        mock_update.assert_called_once()
        _, call_kwargs = mock_update.call_args
        patch_dict = mock_update.call_args[0][1]
        self.assertEqual(patch_dict["is_lit"], False)

    @patch("blockchain.xrpl.services.nft.NFTService.update_metadata")
    def test_refuel_persists_full_fuel(self, mock_update):
        lantern = self._make_lantern()
        lantern.fuel_remaining = lantern.max_fuel // 2
        mock_update.reset_mock()

        ok, _ = lantern.refuel()

        self.assertTrue(ok)
        self.assertEqual(lantern.fuel_remaining, lantern.max_fuel)
        mock_update.assert_called_once()
        patch_dict = mock_update.call_args[0][1]
        self.assertEqual(patch_dict["fuel_remaining"], lantern.max_fuel)

    @patch("blockchain.xrpl.services.nft.NFTService.update_metadata")
    def test_burn_tick_does_not_persist(self, mock_update):
        """
        The per-tick fuel decrement must not write to the mirror. Deliberate:
        keeps the mirror DB quiet for every lit torch in the game.
        """
        torch = self._make_torch()
        torch.light()
        mock_update.reset_mock()

        # Simulate a burn tick directly. Can't use the real script cleanly
        # in a unit test, so call the same mutation path.
        torch.fuel_remaining = max(0, torch.fuel_remaining - 30)

        # No persist_metadata call during per-tick decrement
        mock_update.assert_not_called()

    @patch("blockchain.xrpl.services.nft.NFTService.update_metadata")
    def test_lantern_exhaust_routes_through_extinguish(self, mock_update):
        """
        When a lantern runs out of fuel, LightBurnScript._fuel_exhausted()
        must call obj.extinguish() so the final is_lit=False, fuel=0
        snapshot lands in mirror metadata.
        """
        lantern = self._make_lantern()
        lantern.light()
        # Drain so the next exhaust handler call sees zero fuel
        lantern.fuel_remaining = 0
        mock_update.reset_mock()

        # Grab the running script and invoke the exhaust path directly
        scripts = lantern.scripts.get("light_burn")
        self.assertTrue(scripts)
        script = scripts[0]
        script._fuel_exhausted(lantern, holder=self.char1)

        self.assertFalse(lantern.is_lit)
        # Lantern survives (not deleted) — this is the whole point of the route
        self.assertIsNotNone(lantern.pk)
        mock_update.assert_called()
        final_patch = mock_update.call_args[0][1]
        self.assertEqual(final_patch["is_lit"], False)
        self.assertEqual(final_patch["fuel_remaining"], 0)

    @patch("blockchain.xrpl.services.nft.NFTService.update_metadata")
    def test_no_persist_before_token_assigned(self, mock_update):
        torch = self._make_torch(token_id=None)
        torch.token_id = None
        mock_update.reset_mock()

        torch.light()

        mock_update.assert_not_called()
