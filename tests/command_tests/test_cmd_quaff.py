"""
Tests for the quaff command.

evennia test --settings settings tests.command_tests.test_cmd_quaff
"""

from unittest.mock import patch

from evennia.utils.test_resources import EvenniaCommandTest
from evennia.utils import create

from commands.all_char_cmds.cmd_quaff import CmdQuaff


class TestCmdQuaff(EvenniaCommandTest):
    """Test the quaff command."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.room1.always_lit = True
        self.potion = create.create_object(
            "typeclasses.items.consumables.potion_nft_item.PotionNFTItem",
            key="Healing Potion",
            location=self.char1,
            nohome=True,
        )
        self.potion.potion_effects = [
            {"type": "heal", "dice": "2d4+2"},
        ]
        # Give char1 some damage to heal
        self.char1.hp = 10
        self.char1.hp_max = 50

    def test_no_args(self):
        """Quaff with no args shows usage."""
        self.call(CmdQuaff(), "", "Quaff what?")

    def test_quaff_potion(self):
        """Quaffing a potion should consume it."""
        self.call(CmdQuaff(), "healing potion")
        # Potion should be consumed (removed from inventory)
        from typeclasses.items.consumables.potion_nft_item import PotionNFTItem
        potions = [o for o in self.char1.contents if isinstance(o, PotionNFTItem)]
        self.assertEqual(len(potions), 0)

    def test_quaff_not_found(self):
        """Quaffing something not in inventory shows error."""
        self.call(CmdQuaff(), "banana", "You aren't carrying 'banana'.")

    def test_quaff_non_potion(self):
        """Quaffing a non-potion item shows type error."""
        sword = create.create_object(
            "evennia.objects.objects.DefaultObject",
            key="sword",
            location=self.char1,
        )
        self.call(CmdQuaff(), "sword", "sword is not a potion.")

    # --- Quaffing by touch ---
    #
    # Your own pack is found by feel, so darkness costs the time spent
    # searching rather than the action.

    def _quaff_blind(self, args="healing potion"):
        """Call quaff while sightless, returning (output, completion)."""
        self.room1.always_lit = False
        self.room1.natural_light = False
        with patch("utils.busy.delay") as mock_delay:
            out = self.call(CmdQuaff(), args)
        complete = mock_delay.call_args[0][1] if mock_delay.call_args else None
        return out, complete

    def _finish(self, complete):
        """Run the deferred completion, collecting what the caller hears."""
        said = []
        self.char1.msg = lambda text="", **kwargs: said.append(str(text))
        complete()
        return " ".join(said)

    def _potions_left(self):
        from typeclasses.items.consumables.potion_nft_item import PotionNFTItem

        return [o for o in self.char1.contents if isinstance(o, PotionNFTItem)]

    def test_quaffing_in_the_dark_announces_the_fumble(self):
        out, _ = self._quaff_blind()
        self.assertIn("fumble blindly through your pack", out)

    def test_quaffing_in_the_dark_succeeds_after_the_fumble(self):
        _, complete = self._quaff_blind()
        complete()
        self.assertEqual(self._potions_left(), [])

    def test_nothing_is_drunk_until_the_fumble_ends(self):
        self._quaff_blind()
        self.assertEqual(len(self._potions_left()), 1)

    def test_a_missing_potion_is_searched_for_first(self):
        """The search gives nothing away — you fumble, then find out."""
        out, complete = self._quaff_blind("banana")
        self.assertIn("fumble blindly through your pack", out)
        self.assertNotIn("aren't carrying", out)
        self.assertIn("aren't carrying 'banana'", self._finish(complete))

    def test_quaffing_when_sighted_does_not_fumble(self):
        result = self.call(CmdQuaff(), "healing potion")
        self.assertNotIn("fumble", result)

    def test_quaffing_is_refused_while_busy(self):
        self.char1.ndb.is_processing = True
        self.call(CmdQuaff(), "healing potion", "You are busy.")
