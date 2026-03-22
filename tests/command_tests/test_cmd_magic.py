"""
Tests for magic commands — cast, transcribe, memorise, forget, spells.

Uses EvenniaCommandTest with yield-based inputs for transcribe confirmations.
Creates SpellScrollNFTItem directly for isolation.

evennia test --settings settings tests.command_tests.test_cmd_magic
"""

from unittest.mock import patch

from django.conf import settings

from evennia.utils.test_resources import EvenniaCommandTest
from evennia.utils import create

from commands.all_char_cmds.cmd_cast import CmdCast
from commands.all_char_cmds.cmd_transcribe import CmdTranscribe
from commands.all_char_cmds.cmd_memorise import CmdMemorise, CmdForget
from commands.all_char_cmds.cmd_spells import CmdSpells


CHAIN_ID = settings.BLOCKCHAIN_CHAIN_ID
CONTRACT_NFT = settings.CONTRACT_NFT
WALLET_A = "0xAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
TOKEN_ID = 201


def _create_scroll(char, token_id=TOKEN_ID, spell_key="magic_missile"):
    """Create a SpellScrollNFTItem in character's inventory."""
    obj = create.create_object(
        "typeclasses.items.consumables.spell_scroll_nft_item.SpellScrollNFTItem",
        key="Scroll of Magic Missile",
        nohome=True,
    )
    obj.token_id = token_id
    obj.chain_id = CHAIN_ID
    obj.contract_address = CONTRACT_NFT
    obj.spell_key = spell_key
    # Place directly in inventory bypassing at_post_move
    obj.db_location = char
    obj.save(update_fields=["db_location"])
    return obj


def _setup_mage(char, mastery=1):
    """Configure character as a mage with evocation mastery."""
    char.db.classes = {"mage": {"level": 8}}
    char.db.class_skill_mastery_levels = {"evocation": mastery}
    char.mana = 100
    char.intelligence = 14
    char.wisdom = 10
    char.hp = 50
    char.hp_max = 50
    char.db.spellbook = {}
    char.db.memorised_spells = {}


def _setup_cleric(char, mastery=1):
    """Configure character as a cleric with divine_healing mastery."""
    char.db.classes = {"cleric": {"level": 8}}
    char.db.class_skill_mastery_levels = {"divine_healing": mastery}
    char.mana = 100
    char.intelligence = 10
    char.wisdom = 14
    char.hp = 50
    char.hp_max = 50
    char.db.spellbook = {}
    char.db.memorised_spells = {}


# ================================================================== #
#  Transcribe Command
# ================================================================== #

class TestCmdTranscribeSuccess(EvenniaCommandTest):
    """Test successful spell scroll transcription."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)
        _setup_mage(self.char1)
        self.scroll = _create_scroll(self.char1)

    @patch("blockchain.xrpl.services.nft.NFTService.craft_input")
    def test_transcribe_learns_spell(self, mock_craft):
        """Transcribe should learn the spell from the scroll."""
        self.call(CmdTranscribe(), "scroll", inputs=["y"])
        self.assertTrue(self.char1.knows_spell("magic_missile"))

    @patch("blockchain.xrpl.services.nft.NFTService.craft_input")
    def test_transcribe_consumes_scroll(self, mock_craft):
        """After transcribing, scroll should be consumed."""
        self.call(CmdTranscribe(), "scroll", inputs=["y"])
        from typeclasses.items.consumables.spell_scroll_nft_item import SpellScrollNFTItem
        scrolls = [o for o in self.char1.contents if isinstance(o, SpellScrollNFTItem)]
        self.assertEqual(len(scrolls), 0)


class TestCmdTranscribeFailures(EvenniaCommandTest):
    """Test transcribe command failure cases."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)
        _setup_mage(self.char1)

    def test_no_args(self):
        """Transcribe with no args should show usage."""
        self.call(CmdTranscribe(), "", "Transcribe what?")

    def test_no_scrolls(self):
        """Transcribe with no spell scrolls in inventory."""
        self.call(CmdTranscribe(), "scroll", "You aren't carrying any spell scrolls.")

    def test_wrong_name(self):
        """Transcribe with non-matching name."""
        _create_scroll(self.char1)
        self.call(CmdTranscribe(), "potion of doom", "You don't have a spell scroll by that name.")

    def test_insufficient_mastery(self):
        """Transcribe when caster has no evocation mastery."""
        self.char1.db.class_skill_mastery_levels = {}
        _create_scroll(self.char1)
        self.call(CmdTranscribe(), "scroll", inputs=["y"])
        self.assertFalse(self.char1.knows_spell("magic_missile"))

    @patch("blockchain.xrpl.services.nft.NFTService.craft_input")
    def test_already_known(self, mock_craft):
        """Transcribe when spell already known should fail and keep scroll."""
        scroll = _create_scroll(self.char1)
        self.char1.db.spellbook = {"magic_missile": True}
        self.call(CmdTranscribe(), "scroll", "You already know", inputs=["y"])
        self.assertIn(scroll, self.char1.contents)
        mock_craft.assert_not_called()


class TestCmdTranscribeCancel(EvenniaCommandTest):
    """Test transcribe Y/N cancellation."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)
        _setup_mage(self.char1)
        self.scroll = _create_scroll(self.char1)

    @patch("blockchain.xrpl.services.nft.NFTService.craft_input")
    def test_cancel_keeps_scroll(self, mock_craft):
        """Answering 'n' should cancel and keep scroll."""
        self.call(CmdTranscribe(), "scroll", inputs=["n"])
        self.assertIn(self.scroll, self.char1.contents)
        self.assertFalse(self.char1.knows_spell("magic_missile"))
        mock_craft.assert_not_called()


# ================================================================== #
#  Cast Command
# ================================================================== #

class TestCmdCast(EvenniaCommandTest):
    """Test the cast command."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        _setup_mage(self.char1)
        self.char1.db.spellbook = {"magic_missile": True}
        self.char1.db.memorised_spells = {"magic_missile": True}
        # Target
        self.char2.hp = 100
        self.char2.hp_max = 100

    def test_no_args(self):
        """Cast with no args shows usage."""
        self.call(CmdCast(), "", "Cast what?")

    def test_cast_hostile_with_target(self):
        """Cast magic missile at target should deal damage."""
        self.call(CmdCast(), f"magic missile {self.char2.key}")
        self.assertLess(self.char2.hp, 100)

    def test_cast_hostile_no_target(self):
        """Cast hostile spell with no target should show error."""
        self.call(CmdCast(), "magic missile", "Cast Magic Missile at whom?")

    def test_cast_not_memorised(self):
        """Cast a spell that isn't memorised should fail."""
        self.char1.db.memorised_spells = {}
        self.call(CmdCast(), f"magic missile {self.char2.key}", "You haven't memorised")

    def test_cast_unknown_spell(self):
        """Cast a spell that doesn't exist should fail."""
        self.call(CmdCast(), f"baleful polymorph {self.char2.key}", "You don't know a spell")

    def test_cast_deducts_mana(self):
        """Casting should deduct mana."""
        start_mana = self.char1.mana
        self.call(CmdCast(), f"magic missile {self.char2.key}")
        self.assertLess(self.char1.mana, start_mana)

    def test_cast_insufficient_mana(self):
        """Cast with insufficient mana should fail."""
        self.char1.mana = 0
        self.call(CmdCast(), f"magic missile {self.char2.key}", "Not enough mana")

    def test_cast_friendly_no_target_heals_self(self):
        """Cast friendly spell with no target should target self."""
        _setup_cleric(self.char1)
        self.char1.db.spellbook = {"cure_wounds": True}
        self.char1.db.memorised_spells = {"cure_wounds": True}
        self.char1.hp = 10
        self.char1.hp_max = 100
        self.call(CmdCast(), "cure wounds")
        self.assertGreater(self.char1.hp, 10)

    def test_cast_by_alias(self):
        """Cast via alias (mm) should resolve to magic missile."""
        self.call(CmdCast(), f"mm {self.char2.key}")
        self.assertLess(self.char2.hp, 100)

    def test_cast_success_message(self):
        """Successful cast should show first-person message to caster."""
        result = self.call(CmdCast(), f"magic missile {self.char2.key}")
        self.assertIn("You fire", result)
        self.assertIn("glowing missile", result)


# ================================================================== #
#  Memorise Command
# ================================================================== #

class TestCmdMemorise(EvenniaCommandTest):
    """Test the memorise command."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        _setup_mage(self.char1)
        self.char1.db.spellbook = {"magic_missile": True}
        self.char1.db.memorised_spells = {}

    def test_no_args(self):
        """Memorise with no args shows usage."""
        self.call(CmdMemorise(), "", "Memorise what?")

    def test_unknown_spell(self):
        """Memorise a spell that doesn't exist shows error."""
        self.call(CmdMemorise(), "baleful polymorph", "You don't know a spell")

    def test_not_known(self):
        """Memorise a spell the character doesn't know shows error."""
        self.char1.db.spellbook = {}
        self.call(CmdMemorise(), "magic missile", "You don't know Magic Missile")

    def test_already_memorised(self):
        """Memorise a spell already memorised shows error."""
        self.char1.db.memorised_spells = {"magic_missile": True}
        self.call(CmdMemorise(), "magic missile", "Magic Missile is already memorised")


# ================================================================== #
#  Forget Command
# ================================================================== #

class TestCmdForget(EvenniaCommandTest):
    """Test the forget command."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        _setup_mage(self.char1)
        self.char1.db.spellbook = {"magic_missile": True}
        self.char1.db.memorised_spells = {"magic_missile": True}

    def test_no_args(self):
        """Forget with no args shows usage."""
        self.call(CmdForget(), "", "Forget what?")

    def test_forget_success(self):
        """Forget a memorised spell should succeed."""
        self.call(CmdForget(), "magic missile", "You forget Magic Missile.")

    def test_forget_removes_from_memorised(self):
        """After forgetting, spell should not be memorised."""
        self.call(CmdForget(), "magic missile")
        self.assertFalse(self.char1.is_memorised("magic_missile"))

    def test_forget_still_known(self):
        """After forgetting, spell should still be known."""
        self.call(CmdForget(), "magic missile")
        self.assertTrue(self.char1.knows_spell("magic_missile"))

    def test_forget_not_memorised(self):
        """Forget a spell that isn't memorised should fail."""
        self.char1.db.memorised_spells = {}
        self.call(CmdForget(), "magic missile", "That spell isn't memorised.")

    def test_forget_unknown_spell(self):
        """Forget a spell that doesn't exist should show error."""
        self.call(CmdForget(), "baleful polymorph", "You don't know a spell")


# ================================================================== #
#  Spells Command
# ================================================================== #

class TestCmdSpells(EvenniaCommandTest):
    """Test the spells display command."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        _setup_mage(self.char1)
        self.char1.db.spellbook = {"magic_missile": True}
        self.char1.db.memorised_spells = {"magic_missile": True}

    def test_spells_shows_header(self):
        """Spells command should show the Spellbook header."""
        result = self.call(CmdSpells(), "")
        self.assertIn("Spellbook", result)

    def test_spells_shows_school(self):
        """Spells command should show the school name."""
        result = self.call(CmdSpells(), "")
        self.assertIn("Evocation", result)

    def test_spells_shows_memorised_marker(self):
        """Memorised spells should show [M] marker."""
        result = self.call(CmdSpells(), "")
        self.assertIn("[M]", result)

    def test_spells_no_spells(self):
        """Spells with empty spellbook shows message."""
        self.char1.db.spellbook = {}
        self.call(CmdSpells(), "", "You don't know any spells.")

    def test_spells_shows_memory_slots(self):
        """Spells command shows memory slot usage."""
        result = self.call(CmdSpells(), "")
        self.assertIn("Memory slots:", result)
