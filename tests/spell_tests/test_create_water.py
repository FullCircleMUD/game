"""
Tests for the respec'd Create Water conjuration spell.

Create Water targets an inventory water container and adds N drinks
where N scales with mastery tier (BASIC +1 → GM +5). Caps at the
container's max_capacity. Refunds mana if the container is already
full. Mirrors forage's mastery-scaled water yield.

evennia test --settings settings tests.spell_tests.test_create_water
"""

from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from enums.mastery_level import MasteryLevel
from enums.skills_enum import skills
from world.spells.registry import get_spell, get_spells_for_school


_CHAR = "typeclasses.actors.character.FCMCharacter"
_ROOM = "typeclasses.terrain.rooms.room_base.RoomBase"


class TestCreateWaterRegistry(EvenniaTest):
    """Registry + metadata shape."""

    def create_script(self):
        pass

    def test_registered(self):
        spell = get_spell("create_water")
        self.assertIsNotNone(spell)
        self.assertEqual(spell.school, skills.CONJURATION)
        self.assertEqual(spell.min_mastery, MasteryLevel.BASIC)
        self.assertEqual(spell.target_type, "items_inventory")

    def test_in_conjuration_school(self):
        conj = get_spells_for_school("conjuration")
        self.assertIn("create_water", conj)

    def test_mana_scales_with_tier(self):
        spell = get_spell("create_water")
        self.assertEqual(spell.mana_cost, {1: 3, 2: 4, 3: 6, 4: 8, 5: 10})

    def test_aliases_include_cw(self):
        spell = get_spell("create_water")
        self.assertIn("cw", spell.aliases)


class CreateWaterTestBase(EvenniaTest):
    """Common setup: caster with Conjuration mastery and a canteen."""

    character_typeclass = _CHAR
    room_typeclass = _ROOM
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.spell = get_spell("create_water")
        self.char1.base_mana_max = 200
        self.char1.mana_max = 200
        self.char1.mana = 200

    def _set_tier(self, tier):
        self.char1.db.class_skill_mastery_levels = {"conjuration": tier}

    def _make_canteen(self, current=0, token_id=9701):
        with patch("blockchain.xrpl.services.nft.NFTService.update_metadata"), \
             patch("blockchain.xrpl.services.nft.NFTService.craft_output"):
            obj = create_object(
                "typeclasses.items.water_containers.canteen_nft_item.CanteenNFTItem",
                key="a leather canteen",
                location=self.char1,
                nohome=True,
            )
            obj.token_id = token_id
            obj.current = current
        return obj

    def _make_cask(self, current=0, token_id=9702):
        with patch("blockchain.xrpl.services.nft.NFTService.update_metadata"), \
             patch("blockchain.xrpl.services.nft.NFTService.craft_output"):
            obj = create_object(
                "typeclasses.items.water_containers.cask_nft_item.CaskNFTItem",
                key="a wooden cask",
                location=self.char1,
                nohome=True,
            )
            obj.token_id = token_id
            obj.current = current
        return obj


class TestCreateWaterScaling(CreateWaterTestBase):
    """Mastery tier → drinks added."""

    def test_basic_adds_one_drink(self):
        self._set_tier(1)
        canteen = self._make_canteen(current=0)
        self.spell.cast(self.char1, target=canteen)
        self.assertEqual(canteen.current, 1)

    def test_skilled_adds_two_drinks(self):
        self._set_tier(2)
        canteen = self._make_canteen(current=0)
        self.spell.cast(self.char1, target=canteen)
        self.assertEqual(canteen.current, 2)

    def test_expert_adds_three_drinks(self):
        self._set_tier(3)
        canteen = self._make_canteen(current=0)
        self.spell.cast(self.char1, target=canteen)
        self.assertEqual(canteen.current, 3)

    def test_master_adds_four_drinks(self):
        self._set_tier(4)
        canteen = self._make_canteen(current=0)
        self.spell.cast(self.char1, target=canteen)
        self.assertEqual(canteen.current, 4)

    def test_grandmaster_adds_five_drinks(self):
        self._set_tier(5)
        canteen = self._make_canteen(current=0)
        self.spell.cast(self.char1, target=canteen)
        # Canteen capacity is 5, so all 5 drinks land.
        self.assertEqual(canteen.current, 5)

    def test_grandmaster_on_cask_adds_five_drinks(self):
        """Cask has capacity 10 so GM (+5) leaves it half full."""
        self._set_tier(5)
        cask = self._make_cask(current=0)
        self.spell.cast(self.char1, target=cask)
        self.assertEqual(cask.current, 5)


class TestCreateWaterCapping(CreateWaterTestBase):
    """Overflow is discarded, full refuses + refunds."""

    def test_drinks_cap_at_max_capacity(self):
        """GM (+5) into a 3/5 canteen only adds 2 drinks — 3 are wasted."""
        self._set_tier(5)
        canteen = self._make_canteen(current=3)
        self.spell.cast(self.char1, target=canteen)
        self.assertEqual(canteen.current, 5)

    def test_full_container_refuses(self):
        self._set_tier(3)
        canteen = self._make_canteen(current=5)
        success, result = self.spell.cast(self.char1, target=canteen)
        self.assertFalse(success)
        self.assertIn("already full", result["first"].lower())

    def test_full_container_refunds_mana(self):
        self._set_tier(3)
        canteen = self._make_canteen(current=5)
        mana_before = self.char1.mana
        self.spell.cast(self.char1, target=canteen)
        self.assertEqual(self.char1.mana, mana_before)


class TestCreateWaterNonContainer(CreateWaterTestBase):
    """Targets that aren't water containers should refuse cleanly."""

    def test_non_water_container_refuses(self):
        self._set_tier(1)
        # Rock is not a water container — use a plain object.
        rock = create_object(key="a rock", location=self.char1, nohome=True)
        success, result = self.spell.cast(self.char1, target=rock)
        self.assertFalse(success)
        self.assertIn("cannot conjure water", result["first"].lower())


class TestCreateWaterManaCost(CreateWaterTestBase):
    """Mana cost scales per the tier table."""

    def test_mana_deducted_per_tier(self):
        expected = {1: 3, 2: 4, 3: 6, 4: 8, 5: 10}
        for tier, cost in expected.items():
            self._set_tier(tier)
            self.char1.mana = 200
            canteen = self._make_canteen(current=0, token_id=9800 + tier)
            self.spell.cast(self.char1, target=canteen)
            self.assertEqual(
                self.char1.mana, 200 - cost,
                f"Tier {tier}: expected 200-{cost}={200-cost}, got {self.char1.mana}"
            )


class TestCreateWaterPersistence(CreateWaterTestBase):
    """Successful cast fires _persist_water_state."""

    @patch("blockchain.xrpl.services.nft.NFTService.update_metadata")
    def test_persist_fires_on_success(self, mock_update):
        self._set_tier(2)
        canteen = self._make_canteen(current=0)
        mock_update.reset_mock()
        self.spell.cast(self.char1, target=canteen)
        self.assertTrue(mock_update.called)
        args = mock_update.call_args[0]
        self.assertEqual(args[1]["current"], 2)
