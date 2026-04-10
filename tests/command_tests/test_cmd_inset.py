"""
Tests for the gem insetting command — inset enchanted gems into weapons.

Covers:
    1. Successful insetting — gem consumed, effects transferred, name set,
       gold consumed, metadata saved, XP awarded
    2. Validation failures — wrong room, no skill, gem not found, weapon
       not found, weapon wielded, already inset, insufficient gold, busy
    3. Cancellation — 'n' preserves gem and gold
    4. LLM name generator stub

evennia test --settings settings tests.command_tests.test_cmd_inset
"""

from unittest import TestCase
from unittest.mock import patch, MagicMock, PropertyMock

from evennia.utils.test_resources import EvenniaCommandTest

from commands.room_specific_cmds.crafting.cmd_inset import (
    CmdInset,
    _describe_effect,
)
from enums.mastery_level import MasteryLevel
from enums.skills_enum import skills
from llm.name_generator import ItemNameGenerator


WALLET_A = "0xAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"


def _give_gold(char, amount):
    char.receive_gold_from_reserve(amount)


def _give_jeweller_skill(char, mastery=MasteryLevel.BASIC):
    if not char.db.general_skill_mastery_levels:
        char.db.general_skill_mastery_levels = {}
    char.db.general_skill_mastery_levels[skills.JEWELLER.value] = mastery.value


def _instant_delay(seconds, callback, *args, **kwargs):
    callback(*args, **kwargs)


def _make_gem(char, name="Enchanted Ruby", effects=None, restrictions=None):
    """Create a mock enchanted gem in the character's inventory."""
    from evennia.utils.create import create_object
    gem = create_object(
        "typeclasses.items.base_nft_item.BaseNFTItem",
        key=name,
        location=char,
    )
    gem.db.gem_effects = effects or [
        {"type": "stat_bonus", "stat": "initiative_bonus", "value": 1}
    ]
    gem.db.gem_restrictions = restrictions or {}
    return gem


def _make_weapon(char, name="Iron Longsword"):
    """Create a weapon NFT item in the character's inventory."""
    from evennia.utils.create import create_object
    weapon = create_object(
        "typeclasses.items.weapons.weapon_nft_item.WeaponNFTItem",
        key=name,
        location=char,
    )
    weapon.token_id = 100
    weapon.wear_effects = [
        {"type": "stat_bonus", "stat": "total_hit_bonus", "value": 1}
    ]
    return weapon


# ── Unit tests — LLM name generator stub ─────────────────────────────

class TestNameGeneratorStub(TestCase):
    """Test the LLM name generator stub."""

    def test_stub_returns_hardcoded_name(self):
        gen = ItemNameGenerator()
        result = gen.generate_inset_name("Iron Longsword", [], None)
        self.assertEqual(result, "LLMName")

    def test_stub_ignores_arguments(self):
        gen = ItemNameGenerator()
        effects = [{"type": "condition", "condition": "fly"}]
        result = gen.generate_inset_name("Test Weapon", effects, "char")
        self.assertEqual(result, "LLMName")


# ── Unit tests — _describe_effect ─────────────────────────────────────

class TestDescribeEffect(TestCase):
    """Test the effect description helper."""

    def test_stat_bonus(self):
        result = _describe_effect(
            {"type": "stat_bonus", "stat": "initiative_bonus", "value": 1}
        )
        self.assertEqual(result, "+1 initiative bonus")

    def test_condition(self):
        result = _describe_effect(
            {"type": "condition", "condition": "detect_invis"}
        )
        self.assertEqual(result, "detect invis")

    def test_hit_bonus(self):
        result = _describe_effect(
            {"type": "hit_bonus", "weapon_type": "long_sword", "value": 1}
        )
        self.assertEqual(result, "+1 hit (long sword)")

    def test_damage_bonus(self):
        result = _describe_effect(
            {"type": "damage_bonus", "weapon_type": "unarmed", "value": 2}
        )
        self.assertEqual(result, "+2 damage (unarmed)")


# ── Command tests — successful insetting ─────────────────────────────

class TestInsetSuccess(EvenniaCommandTest):
    """Test successful gem insetting."""

    databases = "__all__"
    room_typeclass = "typeclasses.terrain.rooms.room_crafting.RoomCrafting"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)
        self.room1.db.crafting_type = "jeweller"
        self.room1.db.mastery_level = 1
        self.room1.db.craft_cost = 5
        self.room1.db.craft_xp_multiplier = 1.0
        _give_jeweller_skill(self.char1)
        _give_gold(self.char1, 50)

    @patch("commands.room_specific_cmds.crafting.cmd_inset.delay",
           side_effect=_instant_delay)
    @patch("commands.room_specific_cmds.crafting.cmd_inset.NFTGameState")
    def test_gem_consumed(self, mock_nft_cls, mock_delay):
        """Insetting should delete (consume) the gem."""
        gem = _make_gem(self.char1)
        weapon = _make_weapon(self.char1)
        mock_nft = MagicMock()
        mock_nft.metadata = {}
        mock_nft_cls.objects.get.return_value = mock_nft

        self.call(CmdInset(), f"{gem.key} in {weapon.key}", inputs=["y"])

        # Gem should be deleted
        self.assertNotIn(gem, self.char1.contents)

    @patch("commands.room_specific_cmds.crafting.cmd_inset.delay",
           side_effect=_instant_delay)
    @patch("commands.room_specific_cmds.crafting.cmd_inset.NFTGameState")
    def test_weapon_gets_gem_effects(self, mock_nft_cls, mock_delay):
        """Weapon should have gem_effects after insetting."""
        effects = [{"type": "condition", "condition": "fly"}]
        gem = _make_gem(self.char1, effects=effects)
        weapon = _make_weapon(self.char1)
        mock_nft = MagicMock()
        mock_nft.metadata = {}
        mock_nft_cls.objects.get.return_value = mock_nft

        self.call(CmdInset(), f"{gem.key} in {weapon.key}", inputs=["y"])

        self.assertEqual(weapon.db.gem_effects, effects)

    @patch("commands.room_specific_cmds.crafting.cmd_inset.delay",
           side_effect=_instant_delay)
    @patch("commands.room_specific_cmds.crafting.cmd_inset.NFTGameState")
    def test_weapon_gets_gem_restrictions(self, mock_nft_cls, mock_delay):
        """Weapon should have gem_restrictions after insetting."""
        restrictions = {"required_races": ["dwarf"]}
        gem = _make_gem(self.char1, restrictions=restrictions)
        weapon = _make_weapon(self.char1)
        mock_nft = MagicMock()
        mock_nft.metadata = {}
        mock_nft_cls.objects.get.return_value = mock_nft

        self.call(CmdInset(), f"{gem.key} in {weapon.key}", inputs=["y"])

        self.assertEqual(weapon.db.gem_restrictions, restrictions)

    @patch("commands.room_specific_cmds.crafting.cmd_inset.delay",
           side_effect=_instant_delay)
    @patch("commands.room_specific_cmds.crafting.cmd_inset.NFTGameState")
    def test_wear_effects_extended(self, mock_nft_cls, mock_delay):
        """Weapon's wear_effects should include original + gem effects."""
        gem_effects = [{"type": "condition", "condition": "darkvision"}]
        gem = _make_gem(self.char1, effects=gem_effects)
        weapon = _make_weapon(self.char1)
        original_effects = list(weapon.wear_effects)
        mock_nft = MagicMock()
        mock_nft.metadata = {}
        mock_nft_cls.objects.get.return_value = mock_nft

        self.call(CmdInset(), f"{gem.key} in {weapon.key}", inputs=["y"])

        self.assertEqual(
            weapon.wear_effects,
            original_effects + gem_effects
        )

    @patch("commands.room_specific_cmds.crafting.cmd_inset.delay",
           side_effect=_instant_delay)
    @patch("commands.room_specific_cmds.crafting.cmd_inset.NFTGameState")
    def test_weapon_renamed(self, mock_nft_cls, mock_delay):
        """Weapon should get LLM-generated name."""
        gem = _make_gem(self.char1)
        weapon = _make_weapon(self.char1)
        mock_nft = MagicMock()
        mock_nft.metadata = {}
        mock_nft_cls.objects.get.return_value = mock_nft

        self.call(CmdInset(), f"{gem.key} in {weapon.key}", inputs=["y"])

        self.assertEqual(weapon.key, "LLMName")

    @patch("commands.room_specific_cmds.crafting.cmd_inset.delay",
           side_effect=_instant_delay)
    @patch("commands.room_specific_cmds.crafting.cmd_inset.NFTGameState")
    def test_gold_consumed(self, mock_nft_cls, mock_delay):
        """Workshop fee should be deducted."""
        gem = _make_gem(self.char1)
        weapon = _make_weapon(self.char1)
        mock_nft = MagicMock()
        mock_nft.metadata = {}
        mock_nft_cls.objects.get.return_value = mock_nft

        self.call(CmdInset(), f"{gem.key} in {weapon.key}", inputs=["y"])

        self.assertEqual(self.char1.get_gold(), 45)

    @patch("commands.room_specific_cmds.crafting.cmd_inset.delay",
           side_effect=_instant_delay)
    @patch("commands.room_specific_cmds.crafting.cmd_inset.NFTGameState")
    def test_metadata_saved(self, mock_nft_cls, mock_delay):
        """NFTGameState metadata should be updated with new name and effects."""
        gem_effects = [{"type": "condition", "condition": "fly"}]
        gem = _make_gem(self.char1, effects=gem_effects)
        weapon = _make_weapon(self.char1)
        mock_nft = MagicMock()
        mock_nft.metadata = {}
        mock_nft_cls.objects.get.return_value = mock_nft

        self.call(CmdInset(), f"{gem.key} in {weapon.key}", inputs=["y"])

        self.assertEqual(mock_nft.metadata["name"], "LLMName")
        self.assertEqual(mock_nft.metadata["gem_effects"], gem_effects)
        mock_nft.save.assert_called_once()

    @patch("commands.room_specific_cmds.crafting.cmd_inset.delay",
           side_effect=_instant_delay)
    @patch("commands.room_specific_cmds.crafting.cmd_inset.NFTGameState")
    def test_xp_awarded(self, mock_nft_cls, mock_delay):
        """Character should receive XP after insetting."""
        gem = _make_gem(self.char1)
        weapon = _make_weapon(self.char1)
        mock_nft = MagicMock()
        mock_nft.metadata = {}
        mock_nft_cls.objects.get.return_value = mock_nft
        self.char1.experience_points = 0

        self.call(CmdInset(), f"{gem.key} in {weapon.key}", inputs=["y"])

        self.assertEqual(self.char1.experience_points, 10)

    @patch("commands.room_specific_cmds.crafting.cmd_inset.delay",
           side_effect=_instant_delay)
    @patch("commands.room_specific_cmds.crafting.cmd_inset.NFTGameState")
    def test_success_message(self, mock_nft_cls, mock_delay):
        """Should show success message with the new name."""
        gem = _make_gem(self.char1)
        weapon = _make_weapon(self.char1)
        mock_nft = MagicMock()
        mock_nft.metadata = {}
        mock_nft_cls.objects.get.return_value = mock_nft

        result = self.call(
            CmdInset(), f"{gem.key} in {weapon.key}", inputs=["y"]
        )

        self.assertIn("LLMName", result)

    @patch("commands.room_specific_cmds.crafting.cmd_inset.delay",
           side_effect=_instant_delay)
    @patch("commands.room_specific_cmds.crafting.cmd_inset.NFTGameState")
    def test_processing_cleared(self, mock_nft_cls, mock_delay):
        """ndb.is_processing should be cleared after insetting."""
        gem = _make_gem(self.char1)
        weapon = _make_weapon(self.char1)
        mock_nft = MagicMock()
        mock_nft.metadata = {}
        mock_nft_cls.objects.get.return_value = mock_nft

        self.call(CmdInset(), f"{gem.key} in {weapon.key}", inputs=["y"])

        self.assertFalse(self.char1.ndb.is_processing)


# ── Command tests — validation failures ──────────────────────────────

class TestInsetValidation(EvenniaCommandTest):
    """Test validation error paths for insetting."""

    databases = "__all__"
    room_typeclass = "typeclasses.terrain.rooms.room_crafting.RoomCrafting"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)
        self.room1.db.crafting_type = "jeweller"
        self.room1.db.mastery_level = 1
        self.room1.db.craft_cost = 5
        self.room1.db.craft_xp_multiplier = 1.0
        _give_jeweller_skill(self.char1)
        _give_gold(self.char1, 50)

    def test_no_args(self):
        """Should show usage with no arguments."""
        result = self.call(CmdInset(), "")
        self.assertIn("Usage:", result)

    def test_missing_in_keyword(self):
        """Should show usage when 'in' keyword missing."""
        result = self.call(CmdInset(), "ruby longsword")
        self.assertIn("Usage:", result)

    def test_wrong_room_type(self):
        """Should fail if not in a jeweller room."""
        self.room1.db.crafting_type = "smithy"
        gem = _make_gem(self.char1)
        weapon = _make_weapon(self.char1)
        result = self.call(
            CmdInset(), f"{gem.key} in {weapon.key}"
        )
        self.assertIn("jeweller's workshop", result)

    def test_no_jeweller_skill(self):
        """Should fail if character lacks jeweller skill."""
        self.char1.db.general_skill_mastery_levels = {}
        gem = _make_gem(self.char1)
        weapon = _make_weapon(self.char1)
        result = self.call(
            CmdInset(), f"{gem.key} in {weapon.key}"
        )
        self.assertIn("mastery", result)

    def test_gem_not_found(self):
        """Should fail if gem not in inventory."""
        weapon = _make_weapon(self.char1)
        result = self.call(CmdInset(), f"Enchanted Ruby in {weapon.key}")
        self.assertIn("don't have", result)

    def test_not_enchanted_gem(self):
        """Should fail if item doesn't have gem_effects."""
        from evennia.utils.create import create_object
        fake_gem = create_object(
            "typeclasses.items.base_nft_item.BaseNFTItem",
            key="Regular Ruby",
            location=self.char1,
        )
        weapon = _make_weapon(self.char1)
        result = self.call(
            CmdInset(), f"{fake_gem.key} in {weapon.key}"
        )
        self.assertIn("not an enchanted gem", result)

    def test_weapon_not_found(self):
        """Should fail if weapon not in inventory."""
        gem = _make_gem(self.char1)
        result = self.call(CmdInset(), f"{gem.key} in Iron Longsword")
        self.assertIn("don't have", result)

    def test_not_a_weapon(self):
        """Should fail if target is not a WeaponNFTItem."""
        from evennia.utils.create import create_object
        gem = _make_gem(self.char1)
        not_weapon = create_object(
            "typeclasses.items.base_nft_item.BaseNFTItem",
            key="Leather Helm",
            location=self.char1,
        )
        result = self.call(
            CmdInset(), f"{gem.key} in {not_weapon.key}"
        )
        self.assertIn("not a weapon", result)

    def test_weapon_already_inset(self):
        """Should fail if weapon already has gem_effects."""
        gem = _make_gem(self.char1)
        weapon = _make_weapon(self.char1)
        weapon.db.gem_effects = [{"type": "condition", "condition": "fly"}]
        result = self.call(
            CmdInset(), f"{gem.key} in {weapon.key}"
        )
        self.assertIn("already has an inset gem", result)

    def test_insufficient_gold(self):
        """Should fail if not enough gold."""
        self.char1.return_gold_to_reserve(self.char1.get_gold())
        _give_gold(self.char1, 2)
        gem = _make_gem(self.char1)
        weapon = _make_weapon(self.char1)
        result = self.call(
            CmdInset(), f"{gem.key} in {weapon.key}"
        )
        self.assertIn("gold", result)

    def test_busy_processing(self):
        """Should fail if character is already busy."""
        self.char1.ndb.is_processing = True
        gem = _make_gem(self.char1)
        weapon = _make_weapon(self.char1)
        result = self.call(
            CmdInset(), f"{gem.key} in {weapon.key}"
        )
        self.assertIn("already busy", result)
        self.char1.ndb.is_processing = False

    def test_weapon_wielded(self):
        """Should fail if weapon is currently wielded."""
        gem = _make_gem(self.char1)
        weapon = _make_weapon(self.char1)
        # Simulate the weapon being worn/wielded
        if not self.char1.db.wearslots:
            self.char1.db.wearslots = {}
        self.char1.db.wearslots["WIELD"] = weapon
        result = self.call(
            CmdInset(), f"{gem.key} in {weapon.key}"
        )
        self.assertIn("remove", result.lower())
        # Clean up
        self.char1.db.wearslots["WIELD"] = None

    def test_unknown_gem_type(self):
        """Should fail if gem name doesn't match any known tier."""
        gem = _make_gem(self.char1, name="Enchanted Topaz")
        weapon = _make_weapon(self.char1)
        result = self.call(
            CmdInset(), f"{gem.key} in {weapon.key}"
        )
        self.assertIn("cannot be inset", result)


# ── Command tests — cancellation ──────────────────────────────────────

class TestInsetCancellation(EvenniaCommandTest):
    """Test that cancelling preserves gem and gold."""

    databases = "__all__"
    room_typeclass = "typeclasses.terrain.rooms.room_crafting.RoomCrafting"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)
        self.room1.db.crafting_type = "jeweller"
        self.room1.db.mastery_level = 1
        self.room1.db.craft_cost = 5
        self.room1.db.craft_xp_multiplier = 1.0
        _give_jeweller_skill(self.char1)
        _give_gold(self.char1, 50)

    def test_cancel_preserves_gem(self):
        """Cancelling should keep the gem in inventory."""
        gem = _make_gem(self.char1)
        weapon = _make_weapon(self.char1)

        self.call(CmdInset(), f"{gem.key} in {weapon.key}", inputs=["n"])

        self.assertIn(gem, self.char1.contents)

    def test_cancel_preserves_gold(self):
        """Cancelling should not deduct gold."""
        gem = _make_gem(self.char1)
        weapon = _make_weapon(self.char1)

        self.call(CmdInset(), f"{gem.key} in {weapon.key}", inputs=["n"])

        self.assertEqual(self.char1.get_gold(), 50)

    def test_cancel_message(self):
        """Should show cancellation message."""
        gem = _make_gem(self.char1)
        weapon = _make_weapon(self.char1)

        result = self.call(
            CmdInset(), f"{gem.key} in {weapon.key}", inputs=["n"]
        )

        self.assertIn("cancelled", result)


# ── Command tests — mastery tiers ─────────────────────────────────────

class TestInsetMasteryTiers(EvenniaCommandTest):
    """Test gem tier mastery requirements."""

    databases = "__all__"
    room_typeclass = "typeclasses.terrain.rooms.room_crafting.RoomCrafting"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)
        self.room1.db.crafting_type = "jeweller"
        self.room1.db.mastery_level = 5
        self.room1.db.craft_cost = 5
        self.room1.db.craft_xp_multiplier = 1.0
        _give_gold(self.char1, 100)

    def test_ruby_needs_basic(self):
        """Ruby should require BASIC jeweller mastery."""
        _give_jeweller_skill(self.char1, MasteryLevel.BASIC)
        gem = _make_gem(self.char1, name="Enchanted Ruby")
        weapon = _make_weapon(self.char1)

        # Should pass mastery check (gets to confirmation)
        result = self.call(
            CmdInset(), f"{gem.key} in {weapon.key}", inputs=["n"]
        )
        self.assertIn("cancelled", result)

    def test_emerald_needs_expert(self):
        """Emerald should require EXPERT jeweller mastery."""
        _give_jeweller_skill(self.char1, MasteryLevel.SKILLED)
        gem = _make_gem(self.char1, name="Enchanted Emerald")
        weapon = _make_weapon(self.char1)

        result = self.call(
            CmdInset(), f"{gem.key} in {weapon.key}"
        )
        self.assertIn("EXPERT", result)

    def test_emerald_passes_with_expert(self):
        """Emerald should pass with EXPERT mastery."""
        _give_jeweller_skill(self.char1, MasteryLevel.EXPERT)
        gem = _make_gem(self.char1, name="Enchanted Emerald")
        weapon = _make_weapon(self.char1)

        result = self.call(
            CmdInset(), f"{gem.key} in {weapon.key}", inputs=["n"]
        )
        self.assertIn("cancelled", result)

    def test_diamond_needs_grandmaster(self):
        """Diamond should require GRANDMASTER jeweller mastery."""
        _give_jeweller_skill(self.char1, MasteryLevel.MASTER)
        gem = _make_gem(self.char1, name="Enchanted Diamond")
        weapon = _make_weapon(self.char1)

        result = self.call(
            CmdInset(), f"{gem.key} in {weapon.key}"
        )
        self.assertIn("GRAND MASTER", result)

    def test_diamond_passes_with_grandmaster(self):
        """Diamond should pass with GRANDMASTER mastery."""
        _give_jeweller_skill(self.char1, MasteryLevel.GRANDMASTER)
        gem = _make_gem(self.char1, name="Enchanted Diamond")
        weapon = _make_weapon(self.char1)

        result = self.call(
            CmdInset(), f"{gem.key} in {weapon.key}", inputs=["n"]
        )
        self.assertIn("cancelled", result)
