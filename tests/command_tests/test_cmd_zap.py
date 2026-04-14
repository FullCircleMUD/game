"""
Tests for CmdZap — using an enchanted wand to cast its bound spell.

The wand must be in the HOLD slot. Charges decrement on each successful
zap; the wand is destroyed when the last charge is spent. Mages can use
any wand; thieves and ninjas with Magical Secrets can use a wand if
their Magical Secrets mastery >= the bound spell's tier.

The wand override flags on caster.ndb (set by CmdZap before calling
spell.cast) force the spell to cast at its base min_mastery and skip
mana cost regardless of the zapper.

evennia test --settings settings tests.command_tests.test_cmd_zap
"""

from unittest.mock import patch, MagicMock

from evennia.utils.test_resources import EvenniaCommandTest
from evennia.utils import create

from commands.all_char_cmds.cmd_zap import CmdZap
from enums.wearslot import HumanoidWearSlot


WALLET_A = "0xAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"


def _setup_mage(char):
    """Configure a mage with enough mastery to cast various tiers."""
    char.db.classes = {"mage": {"level": 10}}
    char.db.class_skill_mastery_levels = {
        "evocation": {"mastery": 5, "classes": ["mage"]},
    }
    char.mana = 100
    char.mana_max = 100
    char.intelligence = 14
    char.wisdom = 10
    char.hp = 50
    char.hp_max = 50
    char.db.spellbook = {}
    char.db.memorised_spells = {}


def _setup_warrior(char):
    """Configure a warrior — no class-skill mastery for any spell school."""
    char.db.classes = {"warrior": {"level": 5}}
    char.db.class_skill_mastery_levels = {}
    char.mana = 0
    char.mana_max = 10
    char.hp = 50
    char.hp_max = 50


def _setup_thief(char, magical_secrets_mastery=0):
    """Configure a thief with optional Magical Secrets mastery."""
    char.db.classes = {"thief": {"level": 5}}
    levels = {}
    if magical_secrets_mastery > 0:
        levels["magical secrets"] = {
            "mastery": magical_secrets_mastery,
            "classes": ["thief", "ninja"],
        }
    char.db.class_skill_mastery_levels = levels
    char.mana = 0
    char.mana_max = 10
    char.hp = 50
    char.hp_max = 50


def _create_wand(char, spell_key="magic_missile", charges=5):
    """Create a WandNFTItem and equip it in the character's HOLD slot."""
    obj = create.create_object(
        "typeclasses.items.holdables.wand_nft_item.WandNFTItem",
        key=f"Wand of {spell_key.replace('_', ' ').title()}",
        nohome=True,
    )
    obj.spell_key = spell_key
    obj.charges_max = charges
    obj.charges_remaining = charges
    obj.db_location = char
    obj.save(update_fields=["db_location"])
    # Equip into HOLD slot — wearslots store object refs, not ids
    if not char.db.wearslots:
        char.db.wearslots = {}
    char.db.wearslots[HumanoidWearSlot.HOLD.value] = obj
    return obj


# ================================================================== #
#  Held wand resolution
# ================================================================== #


class TestCmdZapHeldWand(EvenniaCommandTest):
    """Verify that zap requires a wand in the HOLD slot."""

    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)
        _setup_mage(self.char1)

    def test_zap_with_nothing_held(self):
        """Zap with no held item should error."""
        self.call(CmdZap(), "char2", "You aren't holding anything to zap.")

    def test_zap_with_non_wand_held(self):
        """Holding a non-wand item should error."""
        torch = create.create_object(
            "typeclasses.items.holdables.torch_nft_item.TorchNFTItem",
            key="a torch",
            nohome=True,
        )
        torch.db_location = self.char1
        torch.save(update_fields=["db_location"])
        if not self.char1.db.wearslots:
            self.char1.db.wearslots = {}
        self.char1.db.wearslots[HumanoidWearSlot.HOLD.value] = torch

        result = self.call(CmdZap(), "char2")
        self.assertIn("isn't a wand", result)


# ================================================================== #
#  Successful zap mechanics
# ================================================================== #


class TestCmdZapSuccess(EvenniaCommandTest):
    """Mage zaps a charged wand — verify charges, persist, override flags."""

    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)
        _setup_mage(self.char1)
        self.wand = _create_wand(
            self.char1, spell_key="magic_missile", charges=5,
        )

    def test_zap_mage_decrements_charges(self):
        """Successful zap decrements charges_remaining by 1."""
        with patch.object(
            type(self.wand), "can_use", return_value=(True, "")
        ):
            with patch(
                "commands.all_char_cmds.cmd_zap.SPELL_REGISTRY"
            ) as mock_registry:
                mock_spell = MagicMock()
                mock_spell.target_type = "hostile"
                mock_spell.min_mastery.value = 1
                mock_spell.cast.return_value = (
                    True,
                    {"first": "ZAP", "second": None, "third": None},
                )
                mock_registry.get.return_value = mock_spell

                self.call(CmdZap(), "char2")

        self.assertEqual(self.wand.charges_remaining, 4)
        self.assertEqual(self.wand.charges_max, 5)

    def test_zap_persists_state_after_charge_decrement(self):
        """persist_wand_state must be called after a successful zap."""
        with patch.object(
            type(self.wand), "can_use", return_value=(True, "")
        ):
            with patch.object(
                self.wand, "persist_wand_state"
            ) as mock_persist:
                with patch(
                    "commands.all_char_cmds.cmd_zap.SPELL_REGISTRY"
                ) as mock_registry:
                    mock_spell = MagicMock()
                    mock_spell.target_type = "hostile"
                    mock_spell.min_mastery.value = 1
                    mock_spell.cast.return_value = (
                        True,
                        {"first": "ZAP", "second": None, "third": None},
                    )
                    mock_registry.get.return_value = mock_spell

                    self.call(CmdZap(), "char2")
                    mock_persist.assert_called_once()

    def test_zap_sets_caster_tier_override_during_cast(self):
        """Wand zap must set _wand_caster_tier_override before spell.cast.

        Verified by capturing the NDB value at the moment cast() is called.
        """
        observed_tier = []
        observed_free = []

        def fake_cast(caster, target):
            observed_tier.append(
                getattr(caster.ndb, "_wand_caster_tier_override", None)
            )
            observed_free.append(
                getattr(caster.ndb, "_wand_free_cast", None)
            )
            return (True, {"first": "ZAP", "second": None, "third": None})

        with patch.object(
            type(self.wand), "can_use", return_value=(True, "")
        ):
            with patch(
                "commands.all_char_cmds.cmd_zap.SPELL_REGISTRY"
            ) as mock_registry:
                mock_spell = MagicMock()
                mock_spell.target_type = "hostile"
                mock_spell.min_mastery.value = 3   # EXPERT
                mock_spell.cast.side_effect = fake_cast
                mock_registry.get.return_value = mock_spell

                self.call(CmdZap(), "char2")

        # During the cast, override should have been EXPERT (3)
        self.assertEqual(observed_tier, [3])
        self.assertEqual(observed_free, [True])
        # After the cast, both flags should be cleared
        self.assertIsNone(self.char1.ndb._wand_caster_tier_override)
        self.assertFalse(self.char1.ndb._wand_free_cast)

    def test_zap_with_zero_mana_still_works(self):
        """Zap is free at use time — zero mana is fine."""
        self.char1.mana = 0
        with patch.object(
            type(self.wand), "can_use", return_value=(True, "")
        ):
            with patch(
                "commands.all_char_cmds.cmd_zap.SPELL_REGISTRY"
            ) as mock_registry:
                mock_spell = MagicMock()
                mock_spell.target_type = "hostile"
                mock_spell.min_mastery.value = 1
                mock_spell.cast.return_value = (
                    True,
                    {"first": "ZAP", "second": None, "third": None},
                )
                mock_registry.get.return_value = mock_spell

                self.call(CmdZap(), "char2")

        self.assertEqual(self.wand.charges_remaining, 4)


# ================================================================== #
#  Expended wand destruction
# ================================================================== #


class TestCmdZapExpended(EvenniaCommandTest):
    """The wand is destroyed when its final charge is spent."""

    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)
        _setup_mage(self.char1)
        self.wand = _create_wand(
            self.char1, spell_key="magic_missile", charges=1,
        )

    def test_zero_charges_rejects_zap(self):
        """A wand with 0 charges should reject zap before invoking the spell."""
        self.wand.charges_remaining = 0
        result = self.call(CmdZap(), "char2")
        self.assertIn("expended", result.lower())

    def test_last_charge_destroys_wand(self):
        """Successful zap of a 1-charge wand should delete the wand."""
        wand_id = self.wand.id

        with patch.object(
            type(self.wand), "can_use", return_value=(True, "")
        ):
            with patch.object(self.char1, "remove"):
                with patch(
                    "commands.all_char_cmds.cmd_zap.SPELL_REGISTRY"
                ) as mock_registry:
                    mock_spell = MagicMock()
                    mock_spell.target_type = "hostile"
                    mock_spell.min_mastery.value = 1
                    mock_spell.cast.return_value = (
                        True,
                        {"first": "ZAP", "second": None, "third": None},
                    )
                    mock_registry.get.return_value = mock_spell

                    with patch.object(self.wand, "delete") as mock_delete:
                        self.call(CmdZap(), "char2")
                        mock_delete.assert_called_once()


# ================================================================== #
#  Class / Magical Secrets gate
# ================================================================== #


class TestCmdZapAccessGates(EvenniaCommandTest):
    """Verify the can_use() rejection flows through to the user."""

    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)

    def test_warrior_cannot_zap_wand(self):
        """A warrior with no Magical Secrets is rejected."""
        _setup_warrior(self.char1)
        wand = _create_wand(self.char1, spell_key="magic_missile", charges=5)
        result = self.call(CmdZap(), "char2")
        # Real can_use returns "Mage class or Magical Secrets at BASIC..."
        self.assertIn("magical secrets", result.lower())
        # Charges unchanged
        self.assertEqual(wand.charges_remaining, 5)

    def test_thief_no_magical_secrets_cannot_zap(self):
        """A thief with magical_secrets mastery 0 is rejected."""
        _setup_thief(self.char1, magical_secrets_mastery=0)
        wand = _create_wand(self.char1, spell_key="magic_missile", charges=5)
        result = self.call(CmdZap(), "char2")
        self.assertIn("magical secrets", result.lower())
        self.assertEqual(wand.charges_remaining, 5)

    def test_thief_basic_secrets_can_zap_basic_wand(self):
        """Magical Secrets BASIC == 1 should allow a BASIC-tier wand zap."""
        _setup_thief(self.char1, magical_secrets_mastery=1)
        wand = _create_wand(self.char1, spell_key="magic_missile", charges=5)

        with patch(
            "commands.all_char_cmds.cmd_zap.SPELL_REGISTRY"
        ) as mock_registry:
            mock_spell = MagicMock()
            mock_spell.target_type = "hostile"
            mock_spell.min_mastery.value = 1
            mock_spell.min_mastery.name = "BASIC"
            mock_spell.cast.return_value = (
                True,
                {"first": "ZAP", "second": None, "third": None},
            )
            mock_registry.get.return_value = mock_spell

            self.call(CmdZap(), "char2")

        self.assertEqual(wand.charges_remaining, 4)

    def test_thief_basic_secrets_cannot_zap_expert_wand(self):
        """Magical Secrets BASIC (1) cannot wield an EXPERT (3) wand."""
        _setup_thief(self.char1, magical_secrets_mastery=1)
        # Real Spell registry — fireball is EXPERT
        wand = _create_wand(self.char1, spell_key="fireball", charges=5)

        result = self.call(CmdZap(), "char2")
        self.assertIn("magical secrets", result.lower())
        self.assertEqual(wand.charges_remaining, 5)

    def test_thief_master_secrets_can_zap_expert_wand(self):
        """Magical Secrets MASTER (4) can use an EXPERT (3) wand."""
        _setup_thief(self.char1, magical_secrets_mastery=4)
        wand = _create_wand(self.char1, spell_key="fireball", charges=5)

        with patch(
            "commands.all_char_cmds.cmd_zap.SPELL_REGISTRY"
        ) as mock_registry:
            mock_spell = MagicMock()
            mock_spell.target_type = "hostile"
            mock_spell.min_mastery.value = 3
            mock_spell.min_mastery.name = "EXPERT"
            mock_spell.cast.return_value = (
                True,
                {"first": "ZAP", "second": None, "third": None},
            )
            mock_registry.get.return_value = mock_spell

            self.call(CmdZap(), "char2")

        self.assertEqual(wand.charges_remaining, 4)


# ================================================================== #
#  Edge cases
# ================================================================== #


class TestCmdZapEdgeCases(EvenniaCommandTest):
    """Wand with broken state, missing target, etc."""

    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)
        _setup_mage(self.char1)

    def test_unknown_spell_key_fails_gracefully(self):
        """A wand with a spell_key that no longer exists in SPELL_REGISTRY."""
        wand = _create_wand(
            self.char1, spell_key="nonexistent_spell", charges=5,
        )
        result = self.call(CmdZap(), "char2")
        # The can_use check fires first and reports a broken binding
        self.assertIn("broken", result.lower())
        self.assertEqual(wand.charges_remaining, 5)
