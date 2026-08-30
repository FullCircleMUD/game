"""
Tests for wear, wield, hold, remove, and equipment commands.

Uses EvenniaCommandTest with test items created as real item typeclasses
with mocked at_wear/at_remove/at_wield/at_hold hooks (avoids
NotImplementedError from abstract base classes).

Note: EvenniaCommandTest.call() checks that msg STARTS WITH the expected
string, not substring match.

evennia test --settings settings tests.command_tests.test_cmd_equipment
"""

from unittest.mock import MagicMock, patch

from evennia.utils.test_resources import EvenniaCommandTest
from evennia.utils import create

from enums.wearslot import HumanoidWearSlot
from commands.all_char_cmds.cmd_wear import CmdWear
from commands.all_char_cmds.cmd_wield import CmdWield
from commands.all_char_cmds.cmd_hold import CmdHold
from commands.all_char_cmds.cmd_remove import CmdRemove
from commands.all_char_cmds.cmd_equipment import CmdEquipment


WALLET_A = "0xAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"


def _make_wearable(key, wearslot_value, location=None, token_id=None):
    """Create a test WearableNFTItem with mocked hooks."""
    obj = create.create_object(
        "typeclasses.items.wearables.wearable_nft_item.WearableNFTItem",
        key=key,
        nohome=True,
    )
    obj.db.wearslot = wearslot_value
    obj.at_wear = MagicMock()
    obj.at_remove = MagicMock()
    if token_id is not None:
        obj.token_id = token_id
    if location:
        obj.move_to(location, quiet=True)
    return obj


def _make_weapon(key, location=None, token_id=None):
    """Create a test WeaponNFTItem with mocked hooks."""
    obj = create.create_object(
        "typeclasses.items.weapons.weapon_nft_item.WeaponNFTItem",
        key=key,
        nohome=True,
    )
    obj.at_wear = MagicMock()
    obj.at_wield = MagicMock()
    obj.at_remove = MagicMock()
    if token_id is not None:
        obj.token_id = token_id
    if location:
        obj.move_to(location, quiet=True)
    return obj


def _make_holdable(key, location=None, token_id=None):
    """Create a test HoldableNFTItem with mocked hooks."""
    obj = create.create_object(
        "typeclasses.items.holdables.holdable_nft_item.HoldableNFTItem",
        key=key,
        nohome=True,
    )
    obj.at_wear = MagicMock()
    obj.at_hold = MagicMock()
    obj.at_remove = MagicMock()
    if token_id is not None:
        obj.token_id = token_id
    if location:
        obj.move_to(location, quiet=True)
    return obj


def _make_plain_item(key, location=None):
    """Create a plain BaseNFTItem with no wearslot."""
    obj = create.create_object(
        "typeclasses.items.base_nft_item.BaseNFTItem",
        key=key,
        nohome=True,
    )
    if location:
        obj.move_to(location, quiet=True)
    return obj


# ================================================================== #
#  Wear Command Tests
# ================================================================== #

class TestCmdWear(EvenniaCommandTest):
    """Test the wear command."""

    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)

    def test_wear_wearable_success(self):
        """Wearing a wearable item should succeed."""
        _make_wearable("Iron Helmet", HumanoidWearSlot.HEAD.value, self.char1)
        self.call(CmdWear(), "Iron Helmet", "You wear Iron Helmet")

    def test_wear_weapon_rejected(self):
        """Trying to wear a weapon should suggest 'wield'."""
        _make_weapon("Iron Longsword", self.char1)
        self.call(CmdWear(), "Iron Longsword", "Use 'wield' for weapons.")

    # --- Dressing by touch ---

    def _blind(self):
        from enums.condition import Condition

        self.char1.add_condition(Condition.BLINDED)

    def _wear_blind(self, args):
        """Call wear while sightless, returning (output, completion)."""
        with patch("utils.busy.delay") as mock_delay:
            out = self.call(CmdWear(), args)
        # delay(interval, _tick, step) — the callback is bound to its step
        delayed = mock_delay.call_args[0] if mock_delay.call_args else None
        complete = (lambda: delayed[1](*delayed[2:])) if delayed else None
        return out, complete

    def _finish(self, complete):
        """Run the deferred completion, collecting what the caller hears."""
        said = []
        self.char1.msg = lambda text="", **kwargs: said.append(str(text))
        complete()
        return " ".join(said)

    def test_wearing_blind_announces_the_fumble(self):
        _make_wearable("Iron Helmet", HumanoidWearSlot.HEAD.value, self.char1)
        self._blind()
        out, _ = self._wear_blind("Iron Helmet")
        self.assertIn("dressing by feel", out)

    def test_wearing_blind_succeeds_after_the_fumble(self):
        helmet = _make_wearable(
            "Iron Helmet", HumanoidWearSlot.HEAD.value, self.char1
        )
        self._blind()
        _, complete = self._wear_blind("Iron Helmet")
        complete()
        self.assertTrue(self.char1.is_worn(helmet))

    def test_nothing_goes_on_until_the_fumble_ends(self):
        helmet = _make_wearable(
            "Iron Helmet", HumanoidWearSlot.HEAD.value, self.char1
        )
        self._blind()
        self._wear_blind("Iron Helmet")
        self.assertFalse(self.char1.is_worn(helmet))

    def test_a_missing_item_is_searched_for_first(self):
        """The search gives nothing away — you fumble, then find out."""
        self._blind()
        out, complete = self._wear_blind("Iron Helmet")
        self.assertIn("dressing by feel", out)
        self.assertNotIn("aren't carrying", out)
        self.assertIn("aren't carrying 'Iron Helmet'", self._finish(complete))

    def test_wearing_when_sighted_does_not_fumble(self):
        _make_wearable("Iron Helmet", HumanoidWearSlot.HEAD.value, self.char1)
        result = self.call(CmdWear(), "Iron Helmet")
        self.assertNotIn("fumble", result)

    def test_wearing_is_refused_while_busy(self):
        _make_wearable("Iron Helmet", HumanoidWearSlot.HEAD.value, self.char1)
        self.char1.ndb.is_processing = True
        self.call(CmdWear(), "Iron Helmet", "You are busy.")

    def test_wear_holdable_rejected(self):
        """Trying to wear a holdable should suggest 'hold'."""
        _make_holdable("Iron Shield", self.char1)
        self.call(CmdWear(), "Iron Shield", "Use 'hold' for that.")

    def test_wear_plain_item_rejected(self):
        """Wearing a plain item with no wearslot should fail."""
        _make_plain_item("Glass Bauble", self.char1)
        self.call(CmdWear(), "Glass Bauble", "Glass Bauble is not something that can be worn.")

    def test_wear_already_worn(self):
        """Wearing an already-worn item should fail."""
        helmet = _make_wearable("Iron Helmet", HumanoidWearSlot.HEAD.value, self.char1)
        self.char1.wear(helmet)
        self.call(CmdWear(), "Iron Helmet", "You must remove Iron Helmet first.")

    def test_wear_slot_occupied(self):
        """Wearing when the slot is already occupied should fail."""
        helmet1 = _make_wearable("Iron Helmet", HumanoidWearSlot.HEAD.value, self.char1)
        _make_wearable("Steel Helmet", HumanoidWearSlot.HEAD.value, self.char1)
        self.char1.wear(helmet1)
        self.call(CmdWear(), "Steel Helmet", "Your Head slot is already occupied.")

    def test_wear_no_args(self):
        """Wear with no arguments should show error."""
        self.call(CmdWear(), "", "Wear what?")

    # ── which one, and how many ───────────────────────────────────

    def test_two_identical_items_wear_one(self):
        """Two of the same helmet is an answer, not a question."""
        _make_wearable("Iron Helmet", HumanoidWearSlot.HEAD.value, self.char1)
        _make_wearable("Iron Helmet", HumanoidWearSlot.HEAD.value, self.char1)
        self.call(CmdWear(), "Iron Helmet", "You wear Iron Helmet")

    def test_two_distinct_matches_ask_which(self):
        iron = _make_wearable(
            "Iron Helmet", HumanoidWearSlot.HEAD.value, self.char1)
        steel = _make_wearable(
            "Steel Helmet", HumanoidWearSlot.HEAD.value, self.char1)
        self.call(CmdWear(), "helmet", "More than one match")
        self.assertIsNone(self.char1.get_slot(HumanoidWearSlot.HEAD))
        self.assertEqual(iron.location, self.char1)
        self.assertEqual(steel.location, self.char1)

    def test_a_name_starting_with_a_resource_is_still_an_item(self):
        """`wear gold ring` is the ring, never the currency."""
        self.char1.db.gold = 100
        ring = _make_wearable(
            "Gold Ring", HumanoidWearSlot.LEFT_RING_FINGER.value, self.char1)
        self.call(CmdWear(), "Gold Ring", "You wear Gold Ring")
        self.assertIs(
            self.char1.get_slot(HumanoidWearSlot.LEFT_RING_FINGER), ring)

    def test_a_count_is_refused(self):
        """You put on one piece at a time."""
        _make_wearable("Iron Helmet", HumanoidWearSlot.HEAD.value, self.char1)
        _make_wearable("Iron Helmet", HumanoidWearSlot.HEAD.value, self.char1)
        self.call(CmdWear(), "2 Iron Helmet", "You wear one piece at a time")
        self.assertIsNone(self.char1.get_slot(HumanoidWearSlot.HEAD))

    def test_all_of_one_item_is_refused_but_bare_all_still_works(self):
        """`wear all helmet` is a count; `wear all` is the bulk action."""
        _make_wearable("Iron Helmet", HumanoidWearSlot.HEAD.value, self.char1)
        self.call(CmdWear(), "all Iron Helmet", "You wear one piece at a time")
        self.assertIsNone(self.char1.get_slot(HumanoidWearSlot.HEAD))

    def test_wear_by_token_id(self):
        """Wearing by dbref should work."""
        helmet = _make_wearable("Iron Helmet", HumanoidWearSlot.HEAD.value, self.char1, token_id=7)
        self.call(CmdWear(), f"#{helmet.id}", "You wear Iron Helmet")

    def test_wear_by_partial_name(self):
        """Wearing by partial name (substring) should work."""
        _make_wearable("Iron Helmet", HumanoidWearSlot.HEAD.value, self.char1)
        self.call(CmdWear(), "helmet", "You wear Iron Helmet")

    def test_wear_excludes_already_worn_from_search(self):
        """With two identical items, one worn, 'wear earring' should find the unworn one."""
        ear1 = _make_wearable("Copper Earring", HumanoidWearSlot.LEFT_EAR.value, self.char1)
        _make_wearable("Copper Earring", HumanoidWearSlot.RIGHT_EAR.value, self.char1)
        self.char1.wear(ear1)
        # Should not get ambiguity error — worn earring excluded from search
        self.call(CmdWear(), "earring", "You wear Copper Earring")

    def test_wear_all_matches_worn_shows_message(self):
        """If every match is already worn, show 'must remove first'."""
        ear1 = _make_wearable("Copper Earring", HumanoidWearSlot.LEFT_EAR.value, self.char1)
        self.char1.wear(ear1)
        self.call(CmdWear(), "earring", "You must remove Copper Earring first.")

    # ---------------- wear all ---------------- #

    def test_wear_all_empty_inventory(self):
        """`wear all` with no equippables should report friendly empty."""
        self.call(CmdWear(), "all", "You have nothing wearable to put on.")

    def test_wear_all_skips_plain_items(self):
        """`wear all` should ignore non-wearable items entirely."""
        _make_plain_item("Glass Bauble", self.char1)
        # Plain item only — no equippables — should still report empty
        self.call(CmdWear(), "all", "You have nothing wearable to put on.")

    def test_wear_all_mixed_inventory(self):
        """`wear all` should equip armour, weapons, and holdables in one pass."""
        _make_wearable("Iron Helmet", HumanoidWearSlot.HEAD.value, self.char1)
        _make_weapon("Iron Longsword", self.char1)
        _make_holdable("Iron Shield", self.char1)
        _make_plain_item("Glass Bauble", self.char1)
        result = self.call(CmdWear(), "all")
        # All three equippables should appear in the summary
        self.assertIn("Iron Helmet", result)
        self.assertIn("Iron Longsword", result)
        self.assertIn("Iron Shield", result)
        # Plain item should be silently skipped
        self.assertNotIn("Glass Bauble", result)

    def test_wear_all_skips_already_worn(self):
        """`wear all` should not retry items the character already has on."""
        helmet = _make_wearable(
            "Iron Helmet", HumanoidWearSlot.HEAD.value, self.char1
        )
        self.char1.wear(helmet)
        _make_wearable("Iron Boots", HumanoidWearSlot.FEET.value, self.char1)
        result = self.call(CmdWear(), "all")
        self.assertIn("Iron Boots", result)
        # Already-worn helmet should not appear in the summary line
        self.assertNotIn("You wear: Iron Helmet", result)

    def test_wear_all_two_rings_first_fit(self):
        """Two rings should fill both finger slots via first-fit."""
        _make_wearable(
            "Copper Ring",
            [HumanoidWearSlot.LEFT_RING_FINGER.value,
             HumanoidWearSlot.RIGHT_RING_FINGER.value],
            self.char1,
        )
        _make_wearable(
            "Silver Ring",
            [HumanoidWearSlot.LEFT_RING_FINGER.value,
             HumanoidWearSlot.RIGHT_RING_FINGER.value],
            self.char1,
        )
        self.call(CmdWear(), "all")
        self.assertEqual(
            self.char1.get_slot(HumanoidWearSlot.LEFT_RING_FINGER.value).key,
            "Copper Ring",
        )
        self.assertEqual(
            self.char1.get_slot(HumanoidWearSlot.RIGHT_RING_FINGER.value).key,
            "Silver Ring",
        )

    def test_wear_all_slot_conflict_reports_skip(self):
        """A second item competing for a filled slot should be reported skipped."""
        helmet1 = _make_wearable(
            "Iron Helmet", HumanoidWearSlot.HEAD.value, self.char1
        )
        self.char1.wear(helmet1)
        _make_wearable(
            "Steel Helmet", HumanoidWearSlot.HEAD.value, self.char1
        )
        result = self.call(CmdWear(), "all")
        # The unworn helmet should appear in the per-item skipped lines
        self.assertIn("Steel Helmet", result)
        self.assertIn("Head", result)  # slot name appears in rejection msg

    def test_wear_item_not_in_inventory(self):
        """Wearing a non-existent item should emit the nofound_string
        from the targeting helper.

        Regression test for the migration to resolve_item_in_source.
        Pre-migration, the bare caller.search emitted Evennia's
        generic "Could not find 'X'" default. Post-migration, the
        command passes its own nofound_string via the helper and
        the error wording is specific ("You aren't carrying 'X'.")
        and consistent with cmd_drop / cmd_give / cmd_hold.

        Uses an empty inventory to additionally exercise the path
        where walk_contents returns no candidates — locks in the
        recent helper fix that stopped short-circuiting on empty
        candidate lists.
        """
        self.call(
            CmdWear(), "nonexistent",
            "You aren't carrying 'nonexistent'.",
        )


# ================================================================== #
#  Wield Command Tests
# ================================================================== #

class TestCmdWield(EvenniaCommandTest):
    """Test the wield command."""

    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)

    def test_wield_weapon_success(self):
        """Wielding a weapon should succeed."""
        _make_weapon("Iron Longsword", self.char1)
        self.call(CmdWield(), "Iron Longsword", "You wield Iron Longsword")

    def test_wield_non_weapon_rejected(self):
        """Wielding a non-weapon should fail."""
        _make_wearable("Iron Helmet", HumanoidWearSlot.HEAD.value, self.char1)
        self.call(CmdWield(), "Iron Helmet", "That's not a weapon.")

    def test_wield_slot_occupied(self):
        """Wielding when WIELD slot is occupied should fail."""
        sword1 = _make_weapon("Iron Longsword", self.char1)
        _make_weapon("Steel Longsword", self.char1)
        self.char1.wear(sword1)
        self.call(CmdWield(), "Steel Longsword", "Your Wield slot is already occupied.")

    def test_wield_no_args(self):
        """Wield with no arguments should show error."""
        self.call(CmdWield(), "", "Wield what?")

    # ── which weapon, and how many ────────────────────────────────

    def test_two_identical_weapons_wield_one(self):
        """Two of the same sword is an answer, not a question."""
        _make_weapon("Iron Longsword", self.char1)
        _make_weapon("Iron Longsword", self.char1)
        self.call(CmdWield(), "Iron Longsword", "You wield Iron Longsword")

    def test_two_distinct_matches_ask_which(self):
        """Two different swords sharing a word is a real question."""
        iron = _make_weapon("Iron Longsword", self.char1)
        steel = _make_weapon("Steel Longsword", self.char1)
        self.call(CmdWield(), "longsword", "More than one match")
        self.assertIsNone(self.char1.get_slot(HumanoidWearSlot.WIELD))
        self.assertEqual(iron.location, self.char1)
        self.assertEqual(steel.location, self.char1)

    def test_exact_name_beats_a_longer_partial(self):
        """Typing a weapon's full name is never ambiguous."""
        plain = _make_weapon("Iron Longsword", self.char1)
        _make_weapon("Iron Longsword of Flame", self.char1)
        self.call(CmdWield(), "Iron Longsword", "You wield Iron Longsword")
        self.assertIs(self.char1.get_slot(HumanoidWearSlot.WIELD), plain)

    def test_a_count_is_refused(self):
        """You wield one weapon. Only fungibles come in amounts."""
        _make_weapon("Iron Longsword", self.char1)
        _make_weapon("Iron Longsword", self.char1)
        self.call(CmdWield(), "2 Iron Longsword", "You wield one weapon at a time")
        self.assertIsNone(self.char1.get_slot(HumanoidWearSlot.WIELD))

    def test_all_of_a_weapon_is_refused_the_same_way(self):
        _make_weapon("Iron Longsword", self.char1)
        self.call(CmdWield(), "all Iron Longsword", "You wield one weapon at a time")
        self.assertIsNone(self.char1.get_slot(HumanoidWearSlot.WIELD))


# ================================================================== #
#  Hold Command Tests
# ================================================================== #

class TestCmdHold(EvenniaCommandTest):
    """Test the hold command."""

    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)

    def test_hold_holdable_success(self):
        """Holding a holdable item should succeed."""
        _make_holdable("Iron Shield", self.char1)
        self.call(CmdHold(), "Iron Shield", "You hold Iron Shield")

    def test_hold_non_holdable_rejected(self):
        """Holding a non-holdable should fail."""
        _make_wearable("Iron Helmet", HumanoidWearSlot.HEAD.value, self.char1)
        self.call(CmdHold(), "Iron Helmet", "That's not something you can hold.")

    def test_hold_slot_occupied(self):
        """Holding when HOLD slot is occupied should fail."""
        shield1 = _make_holdable("Iron Shield", self.char1)
        _make_holdable("Wooden Shield", self.char1)
        self.char1.wear(shield1)
        self.call(CmdHold(), "Wooden Shield", "Your Hold slot is already occupied.")

    def test_hold_no_args(self):
        """Hold with no arguments should show error."""
        self.call(CmdHold(), "", "Hold what?")

    # ── which one, and how many ───────────────────────────────────

    def test_two_identical_items_hold_one(self):
        """Two of the same torch is an answer, not a question."""
        _make_holdable("Brass Torch", self.char1)
        _make_holdable("Brass Torch", self.char1)
        self.call(CmdHold(), "Brass Torch", "You hold Brass Torch")

    def test_two_distinct_matches_ask_which(self):
        brass = _make_holdable("Brass Torch", self.char1)
        pitch = _make_holdable("Pitch Torch", self.char1)
        self.call(CmdHold(), "torch", "More than one match")
        self.assertIsNone(self.char1.get_slot(HumanoidWearSlot.HOLD))
        self.assertEqual(brass.location, self.char1)
        self.assertEqual(pitch.location, self.char1)

    def test_a_name_starting_with_a_resource_is_still_an_item(self):
        """`hold gold lantern` is the lantern, never the currency."""
        self.char1.db.gold = 100
        lantern = _make_holdable("Gold Lantern", self.char1)
        self.call(CmdHold(), "Gold Lantern", "You hold Gold Lantern")
        self.assertIs(self.char1.get_slot(HumanoidWearSlot.HOLD), lantern)

    def test_a_count_is_refused(self):
        """You hold one thing. Only fungibles come in amounts."""
        _make_holdable("Brass Torch", self.char1)
        _make_holdable("Brass Torch", self.char1)
        self.call(CmdHold(), "2 Brass Torch", "You hold one thing at a time")
        self.assertIsNone(self.char1.get_slot(HumanoidWearSlot.HOLD))

    def test_all_of_an_item_is_refused_the_same_way(self):
        _make_holdable("Brass Torch", self.char1)
        self.call(CmdHold(), "all Brass Torch", "You hold one thing at a time")
        self.assertIsNone(self.char1.get_slot(HumanoidWearSlot.HOLD))

    # --- Holding by touch ---
    #
    # Your own pack is findable by feel, so darkness costs time rather
    # than the action. The search runs before the outcome is known.

    def _blind(self):
        from enums.condition import Condition

        self.char1.add_condition(Condition.BLINDED)

    def _hold_blind(self, args):
        """Call hold while sightless, returning (output, completion)."""
        with patch("utils.busy.delay") as mock_delay:
            out = self.call(CmdHold(), args)
        # delay(interval, _tick, step) — the callback is bound to its step
        delayed = mock_delay.call_args[0] if mock_delay.call_args else None
        complete = (lambda: delayed[1](*delayed[2:])) if delayed else None
        return out, complete

    def test_hold_in_the_dark_announces_the_fumble(self):
        self._blind()
        _make_holdable("Iron Shield", self.char1)
        out, _ = self._hold_blind("Iron Shield")
        self.assertIn("fumble blindly through your pack", out)

    def test_hold_in_the_dark_succeeds_after_the_fumble(self):
        self._blind()
        _make_holdable("Iron Shield", self.char1)
        _, complete = self._hold_blind("Iron Shield")
        complete()
        self.assertEqual(
            self.char1.get_slot(HumanoidWearSlot.HOLD).key, "Iron Shield"
        )

    def test_hold_in_the_dark_holds_nothing_until_the_fumble_ends(self):
        self._blind()
        _make_holdable("Iron Shield", self.char1)
        self._hold_blind("Iron Shield")
        self.assertIsNone(self.char1.get_slot(HumanoidWearSlot.HOLD))

    def test_a_missing_item_is_searched_for_first(self):
        """The search gives nothing away — you fumble, then find out."""
        self._blind()
        out, complete = self._hold_blind("Iron Shield")
        self.assertIn("fumble blindly through your pack", out)
        self.assertNotIn("aren't carrying", out)
        complete()

    def test_hold_when_sighted_does_not_fumble(self):
        _make_holdable("Iron Shield", self.char1)
        result = self.call(CmdHold(), "Iron Shield")
        self.assertNotIn("fumble", result)

    def test_hold_is_refused_while_busy(self):
        _make_holdable("Iron Shield", self.char1)
        self.char1.ndb.is_processing = True
        self.call(CmdHold(), "Iron Shield", "You are busy.")

    def test_hold_item_not_in_inventory(self):
        """Hold a non-existent item should show command-layer error.

        Locks in the error wording introduced when cmd_hold migrated
        to resolve_item_in_source. Pre-migration, the bare
        caller.search emitted Evennia's generic "You don't see 'X'
        here" as a side effect. Post-migration, the command owns the
        error wording and emits "You aren't carrying 'X'" whether
        the inventory is empty or the name just doesn't match.

        Critical regression test: if the command's explicit error
        message is ever removed (e.g. someone reverting to the old
        silent-return pattern), this test catches it.
        """
        self.call(
            CmdHold(), "nonexistent",
            "You aren't carrying 'nonexistent'.",
        )


# ================================================================== #
#  Remove Command Tests
# ================================================================== #

class TestCmdRemove(EvenniaCommandTest):
    """Test the remove command."""

    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)

    def test_remove_worn_item(self):
        """Removing a worn item should succeed."""
        helmet = _make_wearable("Iron Helmet", HumanoidWearSlot.HEAD.value, self.char1)
        self.char1.wear(helmet)
        self.call(CmdRemove(), "Iron Helmet", "You remove Iron Helmet")

    def test_remove_not_worn(self):
        """Removing an item that isn't worn should fail."""
        _make_wearable("Iron Helmet", HumanoidWearSlot.HEAD.value, self.char1)
        self.call(CmdRemove(), "Iron Helmet", "You aren't wearing 'Iron Helmet'.")

    def test_remove_weapon(self):
        """Removing a wielded weapon should work."""
        sword = _make_weapon("Iron Longsword", self.char1)
        self.char1.wear(sword)
        self.call(CmdRemove(), "Iron Longsword", "You remove Iron Longsword")

    def test_remove_by_partial_name(self):
        """Removing by partial name should work via substring matching."""
        helmet = _make_wearable("Iron Helmet", HumanoidWearSlot.HEAD.value, self.char1)
        self.char1.wear(helmet)
        self.call(CmdRemove(), "helmet", "You remove Iron Helmet")

    def test_remove_only_matches_worn_items(self):
        """With two identical items, one worn, 'remove earring' should find the worn one."""
        ear1 = _make_wearable("Copper Earring", HumanoidWearSlot.LEFT_EAR.value, self.char1)
        _make_wearable("Copper Earring", HumanoidWearSlot.RIGHT_EAR.value, self.char1)
        self.char1.wear(ear1)
        # Should not get ambiguity error — only worn earring matches
        self.call(CmdRemove(), "earring", "You remove Copper Earring")

    def test_remove_no_worn_match(self):
        """Removing an item when no worn match exists should fail."""
        _make_wearable("Copper Earring", HumanoidWearSlot.LEFT_EAR.value, self.char1)
        self.call(CmdRemove(), "earring", "You aren't wearing 'earring'.")

    def test_remove_no_args(self):
        """Remove with no arguments should show error."""
        self.call(CmdRemove(), "", "Remove what?")

    # ── which one, and how many ───────────────────────────────────

    def test_two_identical_worn_items_remove_one(self):
        """A matched pair is an answer, not a question."""
        left = _make_wearable(
            "Copper Earring", HumanoidWearSlot.LEFT_EAR.value, self.char1)
        right = _make_wearable(
            "Copper Earring", HumanoidWearSlot.RIGHT_EAR.value, self.char1)
        self.char1.wear(left)
        self.char1.wear(right)
        self.call(CmdRemove(), "earring", "You remove Copper Earring")

    def test_two_distinct_worn_matches_ask_which(self):
        """A gold ring and a silver ring are a real question."""
        gold = _make_wearable(
            "Gold Ring", HumanoidWearSlot.LEFT_RING_FINGER.value, self.char1)
        silver = _make_wearable(
            "Silver Ring", HumanoidWearSlot.RIGHT_RING_FINGER.value, self.char1)
        self.char1.wear(gold)
        self.char1.wear(silver)
        self.call(CmdRemove(), "ring", "More than one match")
        self.assertIs(
            self.char1.get_slot(HumanoidWearSlot.LEFT_RING_FINGER), gold)
        self.assertIs(
            self.char1.get_slot(HumanoidWearSlot.RIGHT_RING_FINGER), silver)

    def test_exact_name_beats_a_longer_partial(self):
        plain = _make_wearable(
            "Gold Ring", HumanoidWearSlot.LEFT_RING_FINGER.value, self.char1)
        warding = _make_wearable(
            "Gold Ring of Warding", HumanoidWearSlot.RIGHT_RING_FINGER.value,
            self.char1)
        self.char1.wear(plain)
        self.char1.wear(warding)
        self.call(CmdRemove(), "Gold Ring", "You remove Gold Ring")
        self.assertIsNone(
            self.char1.get_slot(HumanoidWearSlot.LEFT_RING_FINGER))
        self.assertIs(
            self.char1.get_slot(HumanoidWearSlot.RIGHT_RING_FINGER), warding)

    def test_a_count_is_refused(self):
        """You take gear off one piece at a time."""
        left = _make_wearable(
            "Copper Earring", HumanoidWearSlot.LEFT_EAR.value, self.char1)
        right = _make_wearable(
            "Copper Earring", HumanoidWearSlot.RIGHT_EAR.value, self.char1)
        self.char1.wear(left)
        self.char1.wear(right)
        self.call(CmdRemove(), "2 earring", "You remove one piece at a time")
        self.assertIs(self.char1.get_slot(HumanoidWearSlot.LEFT_EAR), left)

    def test_all_of_a_worn_item_is_refused_the_same_way(self):
        left = _make_wearable(
            "Copper Earring", HumanoidWearSlot.LEFT_EAR.value, self.char1)
        self.char1.wear(left)
        self.call(CmdRemove(), "all earring", "You remove one piece at a time")
        self.assertIs(self.char1.get_slot(HumanoidWearSlot.LEFT_EAR), left)

    # --- Undressing by touch ---
    #
    # It is your own gear on your own body, but getting it off in the
    # dark is fiddlier than it sounds, so it costs the time.

    def _blind(self):
        from enums.condition import Condition

        self.char1.add_condition(Condition.BLINDED)

    def _remove_blind(self, args):
        """Call remove while sightless, returning (output, completion)."""
        with patch("utils.busy.delay") as mock_delay:
            out = self.call(CmdRemove(), args)
        # delay(interval, _tick, step) — the callback is bound to its step
        delayed = mock_delay.call_args[0] if mock_delay.call_args else None
        complete = (lambda: delayed[1](*delayed[2:])) if delayed else None
        return out, complete

    def _finish(self, complete):
        """Run the deferred completion, collecting what the caller hears."""
        said = []
        self.char1.msg = lambda text="", **kwargs: said.append(str(text))
        complete()
        return " ".join(said)

    def _worn_helmet(self):
        helmet = _make_wearable(
            "Iron Helmet", HumanoidWearSlot.HEAD.value, self.char1
        )
        self.char1.wear(helmet)
        return helmet

    def test_removing_blind_announces_the_search(self):
        self._worn_helmet()
        self._blind()
        out, _ = self._remove_blind("Iron Helmet")
        self.assertIn("working at the straps", out)

    def test_removing_blind_succeeds_after_the_search(self):
        helmet = self._worn_helmet()
        self._blind()
        _, complete = self._remove_blind("Iron Helmet")
        complete()
        self.assertFalse(self.char1.is_worn(helmet))

    def test_nothing_comes_off_until_the_search_ends(self):
        helmet = self._worn_helmet()
        self._blind()
        self._remove_blind("Iron Helmet")
        self.assertTrue(self.char1.is_worn(helmet))

    def test_an_unworn_item_is_searched_for_first(self):
        """The search gives nothing away — you grope, then find out."""
        self._blind()
        out, complete = self._remove_blind("Iron Helmet")
        self.assertIn("working at the straps", out)
        self.assertNotIn("aren't wearing", out)
        self.assertIn("aren't wearing 'Iron Helmet'", self._finish(complete))

    def test_removing_when_sighted_does_not_search(self):
        self._worn_helmet()
        result = self.call(CmdRemove(), "Iron Helmet")
        self.assertNotIn("working at the straps", result)

    def test_removing_is_refused_while_busy(self):
        self._worn_helmet()
        self.char1.ndb.is_processing = True
        self.call(CmdRemove(), "Iron Helmet", "You are busy.")

    def test_remove_item_not_found(self):
        """Removing a non-existent item should emit the nofound_string
        from the targeting helper.

        Distinct from test_remove_not_worn (which tests an item
        that IS in inventory but not currently worn — that case
        hits FCMCharacter.search's only_worn handling and emits
        "You are not wearing that."). This test covers the other
        error path: the name doesn't match ANY item at all.

        Post-migration, the command passes its own nofound_string
        via the helper which emits "You aren't wearing 'X'." for
        the no-match case. Semantically correct — the player's
        complaint on `remove banana` with no banana is "I'm not
        wearing that", not "I'm not carrying that".
        """
        self.call(
            CmdRemove(), "nonexistent",
            "You aren't wearing 'nonexistent'.",
        )


# ================================================================== #
#  Equipment Command Tests
# ================================================================== #

class TestCmdEquipment(EvenniaCommandTest):
    """Test the equipment display command."""

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)

    def test_equipment_shows_header(self):
        """Equipment output should start with the header."""
        result = self.call(CmdEquipment(), "")
        self.assertIn("Equipped Items", result)

    def test_equipment_with_item_shows_header(self):
        """Equipment with worn item should still start with header."""
        helmet = _make_wearable("Iron Helmet", HumanoidWearSlot.HEAD.value, self.char1)
        self.char1.wear(helmet)
        result = self.call(CmdEquipment(), "")
        self.assertIn("Equipped Items", result)

    def test_equipment_with_item_in_slot(self):
        """Verify worn item appears in the character's wearslots."""
        helmet = _make_wearable("Iron Helmet", HumanoidWearSlot.HEAD.value, self.char1)
        self.char1.wear(helmet)
        self.assertTrue(self.char1.is_worn(helmet))
        self.assertEqual(self.char1.get_slot("HEAD"), helmet)
