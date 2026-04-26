"""
Tests for gem enchanting — atom catalog, layered cascade, restriction
generator, and cmd_craft integration under the new rolling model.

Covers:
    1. Wear-effect template catalog (WEAR_EFFECT_TEMPLATES, GEM_POOL_WEIGHTS, GEM_MAGNITUDES)
    2. Cascade rolling (primary always; secondary/tertiary by probability)
    3. Duplicate-no-op rule
    4. Restriction generator (category cascade, polarity, alignment modes)
    5. CmdCraft integration — enchanting in a wizard's workshop wires the
       pre-disclosed outcome onto the spawned item

evennia test --settings settings tests.command_tests.test_gem_enchanting
"""

from unittest import TestCase
from unittest.mock import patch, MagicMock

from evennia.utils.test_resources import EvenniaCommandTest

from commands.room_specific_cmds.crafting.cmd_craft import CmdCraft
from enums.mastery_level import MasteryLevel
from enums.skills_enum import skills
from world.recipes.enchanting import gem_tables
from world.recipes.enchanting.gem_tables import (
    WEAR_EFFECT_TEMPLATES,
    GEM_POOL_WEIGHTS,
    GEM_MAGNITUDES,
    CASCADE_PROBABILITIES,
    RESTRICTION_PROBABILITIES,
    OUTPUT_TABLE_TO_GEM_TYPE,
    roll_wear_effects,
    roll_restrictions,
    roll_gem_enchantment,
)


WALLET_A = "0xAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
TOKEN_ID = 201


def _give_resources(char, resources):
    for res_id, amount in resources.items():
        char.receive_resource_from_reserve(res_id, amount)


def _give_gold(char, amount):
    char.receive_gold_from_reserve(amount)


def _give_enchanting_skill(char, mastery=MasteryLevel.BASIC):
    if not char.db.class_skill_mastery_levels:
        char.db.class_skill_mastery_levels = {}
    char.db.class_skill_mastery_levels[skills.ENCHANTING.value] = {
        "mastery": mastery.value,
    }


def _learn_enchant_ruby(char):
    if not char.db.recipe_book:
        char.db.recipe_book = {}
    char.db.recipe_book["enchant_ruby"] = True


def _instant_delay(seconds, callback, *args, **kwargs):
    callback(*args, **kwargs)


# ── Atom catalog structure ────────────────────────────────────────────

class TestWearEffectTemplateCatalog(TestCase):
    """Verify the atom registry and per-gem pool structure."""

    def test_ruby_pool_excludes_high_tier_atoms(self):
        """Ruby pool excludes fly, water_breathing, hasted, regen, etc."""
        ruby = GEM_POOL_WEIGHTS["ruby"]
        for excluded in ("C05", "C06", "C07", "C11", "C12", "C13", "G01"):
            self.assertNotIn(excluded, ruby)

    def test_emerald_adds_movement_and_regen(self):
        """Emerald adds fly, water_breathing, speak, detect_traps/hidden, regen."""
        emerald = GEM_POOL_WEIGHTS["emerald"]
        for added in ("C05", "C06", "C11", "C12", "C13", "G01"):
            self.assertIn(added, emerald)
        # But not hasted — that's diamond-only
        self.assertNotIn("C07", emerald)

    def test_diamond_includes_hasted(self):
        """Diamond is the only gem with hasted (C07)."""
        self.assertIn("C07", GEM_POOL_WEIGHTS["diamond"])

    def test_pool_growth_ruby_lt_emerald_lt_diamond(self):
        ruby = len(GEM_POOL_WEIGHTS["ruby"])
        emerald = len(GEM_POOL_WEIGHTS["emerald"])
        diamond = len(GEM_POOL_WEIGHTS["diamond"])
        self.assertLess(ruby, emerald)
        self.assertLess(emerald, diamond)

    def test_attacks_per_round_excluded(self):
        """S13 attacks_per_round is intentionally excluded — covered by C07 hasted."""
        self.assertNotIn("S13", WEAR_EFFECT_TEMPLATES)

    def test_hidden_and_sanctuary_excluded(self):
        """C03 hidden and C09 sanctuary excluded — break under permanent application."""
        self.assertNotIn("C03", WEAR_EFFECT_TEMPLATES)
        self.assertNotIn("C09", WEAR_EFFECT_TEMPLATES)

    def test_uniform_initial_weights(self):
        """All atoms in each pool initialized to weight 1 for now."""
        for gem_type, pool in GEM_POOL_WEIGHTS.items():
            for template_id, weight in pool.items():
                self.assertEqual(weight, 1, f"{gem_type}/{template_id} weight != 1")


class TestMagnitudes(TestCase):
    """Verify per-gem magnitudes match the spreadsheet."""

    def test_ability_scores_scale_1_2_3(self):
        for template_id in ("S01", "S02", "S03", "S04", "S05", "S06"):
            self.assertEqual(GEM_MAGNITUDES["ruby"][template_id], 1)
            self.assertEqual(GEM_MAGNITUDES["emerald"][template_id], 2)
            self.assertEqual(GEM_MAGNITUDES["diamond"][template_id], 3)

    def test_pool_maxes_scale_10_15_20(self):
        for template_id in ("S07", "S08", "S09"):
            self.assertEqual(GEM_MAGNITUDES["ruby"][template_id], 10)
            self.assertEqual(GEM_MAGNITUDES["emerald"][template_id], 15)
            self.assertEqual(GEM_MAGNITUDES["diamond"][template_id], 20)

    def test_combat_stats_scale_1_3_5(self):
        for template_id in ("S10", "S11", "S12", "S14", "S15", "S16"):
            self.assertEqual(GEM_MAGNITUDES["ruby"][template_id], 1)
            self.assertEqual(GEM_MAGNITUDES["emerald"][template_id], 3)
            self.assertEqual(GEM_MAGNITUDES["diamond"][template_id], 5)

    def test_save_bonus_uses_ability_scale(self):
        """S17 save_bonus revised to ability-score scale (+1/+2/+3)."""
        self.assertEqual(GEM_MAGNITUDES["ruby"]["S17"], 1)
        self.assertEqual(GEM_MAGNITUDES["emerald"]["S17"], 2)
        self.assertEqual(GEM_MAGNITUDES["diamond"]["S17"], 3)

    def test_crit_chance_negative(self):
        """S18 crit_chance is negative (lower threshold = wider crit range)."""
        self.assertEqual(GEM_MAGNITUDES["ruby"]["S18"], -1)
        self.assertEqual(GEM_MAGNITUDES["emerald"]["S18"], -2)
        self.assertEqual(GEM_MAGNITUDES["diamond"]["S18"], -3)

    def test_resistances_scale_10_20_30_pct(self):
        # Integer percent (matches existing prototype convention — see
        # n95_mask which uses value=25 for 25% poison resistance).
        for template_id in ("R01", "R04", "R08", "R11", "R13"):
            self.assertEqual(GEM_MAGNITUDES["ruby"][template_id], 10)
            self.assertEqual(GEM_MAGNITUDES["emerald"][template_id], 20)
            self.assertEqual(GEM_MAGNITUDES["diamond"][template_id], 30)

    def test_regen_only_emerald_and_diamond(self):
        self.assertNotIn("G01", GEM_MAGNITUDES["ruby"])
        self.assertEqual(GEM_MAGNITUDES["emerald"]["G01"], 3)
        self.assertEqual(GEM_MAGNITUDES["diamond"]["G01"], 5)


class TestProbabilityTables(TestCase):
    """Verify cascade and restriction tables match the spreadsheet."""

    def test_ruby_cascade_climbs_with_mastery(self):
        for mastery in range(1, 5):
            this = CASCADE_PROBABILITIES[("ruby", mastery)]
            nxt = CASCADE_PROBABILITIES[("ruby", mastery + 1)]
            self.assertGreaterEqual(nxt[1], this[1])
            self.assertGreaterEqual(nxt[2], this[2])

    def test_ruby_restriction_drops_with_mastery(self):
        for mastery in range(1, 5):
            this = RESTRICTION_PROBABILITIES[("ruby", mastery)]
            nxt = RESTRICTION_PROBABILITIES[("ruby", mastery + 1)]
            self.assertGreaterEqual(this[0], nxt[0])

    def test_gm_ruby_no_restrictions(self):
        self.assertEqual(
            RESTRICTION_PROBABILITIES[("ruby", 5)], [0.00, 0.00, 0.00],
        )

    def test_diamond_only_at_gm(self):
        for mastery in range(1, 5):
            self.assertNotIn(("diamond", mastery), CASCADE_PROBABILITIES)
        self.assertIn(("diamond", 5), CASCADE_PROBABILITIES)

    def test_emerald_starts_at_expert(self):
        for mastery in range(1, 3):
            self.assertNotIn(("emerald", mastery), CASCADE_PROBABILITIES)
        for mastery in range(3, 6):
            self.assertIn(("emerald", mastery), CASCADE_PROBABILITIES)


# ── roll_effects cascade behavior ─────────────────────────────────────

class TestRollEffectsCascade(TestCase):

    @patch("world.recipes.enchanting.gem_tables.random.random")
    @patch("world.recipes.enchanting.gem_tables.random.choices")
    def test_primary_only_when_secondary_fails(self, mock_choices, mock_random):
        """Cascade aborts on first failure — primary only."""
        # primary cascade roll (always fires anyway), secondary roll fails
        mock_random.side_effect = [0.0, 0.99]  # 0.0 < 1.0, 0.99 >= 0.10
        mock_choices.side_effect = [["S01"]]  # primary picks strength
        effects = roll_wear_effects("ruby", 1)  # BASIC ruby, secondary p=0.10
        self.assertEqual(len(effects), 1)
        self.assertEqual(effects[0]["stat"], "strength")

    @patch("world.recipes.enchanting.gem_tables.random.random")
    @patch("world.recipes.enchanting.gem_tables.random.choices")
    def test_secondary_fires_when_probability_met(self, mock_choices, mock_random):
        """Secondary fires when random < cascade[1]."""
        mock_random.side_effect = [0.0, 0.0, 0.99]  # primary, secondary, tertiary fail
        mock_choices.side_effect = [["S01"], ["S02"]]
        effects = roll_wear_effects("ruby", 5)  # GM ruby cascade [1, 0.80, 0.20]
        self.assertEqual(len(effects), 2)
        self.assertEqual(effects[0]["stat"], "strength")
        self.assertEqual(effects[1]["stat"], "dexterity")

    @patch("world.recipes.enchanting.gem_tables.random.random")
    @patch("world.recipes.enchanting.gem_tables.random.choices")
    def test_duplicate_atom_is_noop(self, mock_choices, mock_random):
        """Rolling the same atom twice keeps only one (no-op on duplicate)."""
        mock_random.side_effect = [0.0, 0.0, 0.0]  # all cascade rolls fire
        mock_choices.side_effect = [["S01"], ["S01"], ["S02"]]  # collision then unique
        effects = roll_wear_effects("ruby", 5)
        self.assertEqual(len(effects), 2)  # not 3 — one was duplicate
        stats = sorted(e["stat"] for e in effects)
        self.assertEqual(stats, ["dexterity", "strength"])

    @patch("world.recipes.enchanting.gem_tables.random.random")
    @patch("world.recipes.enchanting.gem_tables.random.choices")
    def test_magnitude_filled_from_gem_table(self, mock_choices, mock_random):
        """Effect dict gets the gem-type magnitude inserted."""
        mock_random.side_effect = [0.0, 0.99]
        mock_choices.side_effect = [["S01"]]
        effects = roll_wear_effects("diamond", 5)
        self.assertEqual(effects[0]["value"], 3)  # diamond strength = +3

    @patch("world.recipes.enchanting.gem_tables.random.random")
    @patch("world.recipes.enchanting.gem_tables.random.choices")
    def test_condition_atom_has_no_value(self, mock_choices, mock_random):
        """Conditions are binary — no value field."""
        mock_random.side_effect = [0.0, 0.99]
        mock_choices.side_effect = [["C01"]]  # detect_invis
        effects = roll_wear_effects("ruby", 1)
        self.assertEqual(effects[0]["type"], "condition")
        self.assertNotIn("value", effects[0])

    def test_invalid_pair_raises(self):
        with self.assertRaises(ValueError):
            roll_wear_effects("diamond", 1)  # diamond only valid at GM


# ── roll_restrictions behavior (mixin-format dict output) ─────────────

class TestRollRestrictions(TestCase):

    @patch("world.recipes.enchanting.gem_tables.random.random")
    def test_no_restrictions_when_first_roll_fails(self, mock_random):
        mock_random.side_effect = [0.99]
        result = roll_restrictions("ruby", 1)
        self.assertEqual(result, {})

    @patch("world.recipes.enchanting.gem_tables.random.choice")
    @patch("world.recipes.enchanting.gem_tables.random.random")
    def test_must_be_class_populates_required_classes(self, mock_random, mock_choice):
        # cascade(fire), polarity(must_be), cascade(fail)
        mock_random.side_effect = [0.0, 0.99, 0.99]
        mock_choice.side_effect = ["class", "warrior"]
        result = roll_restrictions("ruby", 1)
        self.assertEqual(result, {"required_classes": ["warrior"]})

    @patch("world.recipes.enchanting.gem_tables.random.choice")
    @patch("world.recipes.enchanting.gem_tables.random.random")
    def test_must_not_be_class_populates_excluded_classes(self, mock_random, mock_choice):
        # cascade(fire), polarity(must_not_be), cascade(fail)
        mock_random.side_effect = [0.0, 0.0, 0.99]
        mock_choice.side_effect = ["class", "mage"]
        result = roll_restrictions("ruby", 1)
        self.assertEqual(result, {"excluded_classes": ["mage"]})

    @patch("world.recipes.enchanting.gem_tables.random.choice")
    @patch("world.recipes.enchanting.gem_tables.random.random")
    def test_must_not_be_race_populates_excluded_races(self, mock_random, mock_choice):
        mock_random.side_effect = [0.0, 0.0, 0.99]
        mock_choice.side_effect = ["race", "dwarf"]
        result = roll_restrictions("ruby", 1)
        self.assertEqual(result, {"excluded_races": ["dwarf"]})

    @patch("world.recipes.enchanting.gem_tables.random.choices")
    @patch("world.recipes.enchanting.gem_tables.random.choice")
    @patch("world.recipes.enchanting.gem_tables.random.random")
    def test_alignment_good_only_sets_min_alignment_score(self, mock_random,
                                                           mock_choice, mock_choices):
        mock_random.side_effect = [0.0, 0.99]
        mock_choice.side_effect = ["alignment"]
        mock_choices.side_effect = [["good_only"]]
        result = roll_restrictions("ruby", 1)
        self.assertEqual(result, {"min_alignment_score": 300})

    @patch("world.recipes.enchanting.gem_tables.random.choices")
    @patch("world.recipes.enchanting.gem_tables.random.choice")
    @patch("world.recipes.enchanting.gem_tables.random.random")
    def test_alignment_evil_only_sets_max_alignment_score(self, mock_random,
                                                           mock_choice, mock_choices):
        mock_random.side_effect = [0.0, 0.99]
        mock_choice.side_effect = ["alignment"]
        mock_choices.side_effect = [["evil_only"]]
        result = roll_restrictions("ruby", 1)
        self.assertEqual(result, {"max_alignment_score": -300})

    @patch("world.recipes.enchanting.gem_tables.random.choices")
    @patch("world.recipes.enchanting.gem_tables.random.choice")
    @patch("world.recipes.enchanting.gem_tables.random.random")
    def test_alignment_no_evil_uses_inclusive_boundary(self, mock_random,
                                                       mock_choice, mock_choices):
        mock_random.side_effect = [0.0, 0.99]
        mock_choice.side_effect = ["alignment"]
        mock_choices.side_effect = [["no_evil"]]
        result = roll_restrictions("ruby", 1)
        # boundary semantics: no_evil admits > -300, so min is -299 (>=)
        self.assertEqual(result, {"min_alignment_score": -299})

    @patch("world.recipes.enchanting.gem_tables.random.choices")
    @patch("world.recipes.enchanting.gem_tables.random.choice")
    @patch("world.recipes.enchanting.gem_tables.random.random")
    def test_alignment_neutral_only_sets_both_bounds(self, mock_random,
                                                      mock_choice, mock_choices):
        mock_random.side_effect = [0.0, 0.99]
        mock_choice.side_effect = ["alignment"]
        mock_choices.side_effect = [["neutral_only"]]
        result = roll_restrictions("ruby", 1)
        self.assertEqual(result, {"min_alignment_score": -299, "max_alignment_score": 299})

    @patch("world.recipes.enchanting.gem_tables.random.choice")
    @patch("world.recipes.enchanting.gem_tables.random.random")
    def test_categories_never_repeat(self, mock_random, mock_choice):
        # All 3 cascade rolls fire; categories class → race → alignment
        mock_random.side_effect = [0.0, 0.99, 0.0, 0.99, 0.0]
        mock_choice.side_effect = [
            "class", "warrior",   # iter1
            "race",  "elf",       # iter2
            "alignment",          # iter3 (mode via random.choices)
        ]
        with patch(
            "world.recipes.enchanting.gem_tables.random.choices",
            return_value=["good_only"],
        ):
            result = roll_restrictions("ruby", 1)
        # All three categories present in the resulting dict
        self.assertEqual(result.get("required_classes"), ["warrior"])
        self.assertEqual(result.get("required_races"), ["elf"])
        self.assertEqual(result.get("min_alignment_score"), 300)

    def test_no_cascade_returns_empty(self):
        """GM ruby has [0,0,0] cascade — always empty."""
        result = roll_restrictions("ruby", 5)
        self.assertEqual(result, {})


# ── roll_gem_enchantment top-level ────────────────────────────────────

class TestRollGemEnchantment(TestCase):

    def test_unknown_table_key_raises(self):
        with self.assertRaises(ValueError):
            roll_gem_enchantment("enchanted_sapphire", 1)

    @patch("world.recipes.enchanting.gem_tables.random.random")
    @patch("world.recipes.enchanting.gem_tables.random.choices")
    def test_returns_effects_list_and_restrictions_dict(self, mock_choices,
                                                         mock_random):
        # Force minimal output: 1 effect, 0 restrictions
        # roll_effects: primary fires (0.0), secondary fails (0.99)
        # roll_restrictions: 1st cascade fails (0.99)
        mock_random.side_effect = [0.0, 0.99, 0.99]
        mock_choices.side_effect = [["S01"]]
        effects, restrictions = roll_gem_enchantment("enchanted_ruby", 1)
        self.assertIsInstance(effects, list)
        self.assertIsInstance(restrictions, dict)
        self.assertEqual(len(effects), 1)
        self.assertEqual(restrictions, {})


# ── Integration: cmd_craft enchanting flow ────────────────────────────

class TestCmdCraftEnchantRubyIntegration(EvenniaCommandTest):
    """End-to-end craft flow with the new outcome shape — mocks at the
    EnchantmentService level so we control the outcome without depending
    on random rolls inside the rolling functions."""

    databases = "__all__"
    room_typeclass = "typeclasses.terrain.rooms.room_crafting.RoomCrafting"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)
        self.room1.db.crafting_type = "wizards_workshop"
        self.room1.db.mastery_level = 1
        self.room1.db.craft_cost = 5
        _give_enchanting_skill(self.char1)
        _learn_enchant_ruby(self.char1)
        _give_resources(self.char1, {16: 5, 33: 3})
        _give_gold(self.char1, 50)

    def _run_craft_with_outcome(self, mock_assign, mock_spawn, effects,
                                restrictions=None):
        """Helper: stub the enchantment service to return a fixed outcome."""
        mock_assign.return_value = TOKEN_ID
        item = MagicMock()
        mock_spawn.return_value = item
        outcome = {"wear_effects": effects, "restrictions": restrictions or {}}
        with patch(
            "commands.room_specific_cmds.crafting.cmd_craft.EnchantmentService.preview_slot",
            return_value={"slot_number": 1, **outcome},
        ), patch(
            "commands.room_specific_cmds.crafting.cmd_craft.EnchantmentService.consume_slot",
            return_value=outcome,
        ):
            self.call(CmdCraft(), "enchanted ruby", inputs=["y"])
        return item

    @patch("commands.room_specific_cmds.crafting.cmd_craft.delay",
           side_effect=_instant_delay)
    @patch("typeclasses.items.base_nft_item.BaseNFTItem.spawn_into")
    @patch("typeclasses.items.base_nft_item.BaseNFTItem.assign_to_blank_token")
    def test_effects_land_on_wear_effects(self, mock_assign, mock_spawn,
                                            mock_delay):
        """Effects go onto the gem's wear_effects (standard field name —
        same one weapons use)."""
        effects = [
            {"type": "stat_bonus", "stat": "strength", "value": 1},
            {"type": "condition", "condition": "detect_invis"},
        ]
        item = self._run_craft_with_outcome(
            mock_assign, mock_spawn, effects, restrictions={},
        )
        self.assertEqual(item.db.wear_effects, effects)

    @patch("commands.room_specific_cmds.crafting.cmd_craft.delay",
           side_effect=_instant_delay)
    @patch("typeclasses.items.base_nft_item.BaseNFTItem.spawn_into")
    @patch("typeclasses.items.base_nft_item.BaseNFTItem.assign_to_blank_token")
    def test_restrictions_set_directly_on_mixin_fields(self, mock_assign,
                                                        mock_spawn, mock_delay):
        """Restrictions populate the gem's ItemRestrictionMixin fields
        directly — required_classes, excluded_classes, etc. — rather than
        a custom db.gem_restrictions attribute."""
        restrictions = {
            "required_classes": ["warrior"],
            "excluded_races": ["dwarf"],
            "min_alignment_score": -299,  # no_evil
        }
        item = self._run_craft_with_outcome(
            mock_assign, mock_spawn,
            effects=[{"type": "stat_bonus", "stat": "strength", "value": 1}],
            restrictions=restrictions,
        )
        self.assertEqual(item.required_classes, ["warrior"])
        self.assertEqual(item.excluded_races, ["dwarf"])
        self.assertEqual(item.min_alignment_score, -299)

    @patch("commands.room_specific_cmds.crafting.cmd_craft.delay",
           side_effect=_instant_delay)
    @patch("typeclasses.items.base_nft_item.BaseNFTItem.spawn_into")
    @patch("typeclasses.items.base_nft_item.BaseNFTItem.assign_to_blank_token")
    def test_consumes_resources_and_gold(self, mock_assign, mock_spawn,
                                          mock_delay):
        self._run_craft_with_outcome(
            mock_assign, mock_spawn,
            effects=[{"type": "stat_bonus", "stat": "strength", "value": 1}],
        )
        # 2 Arcane Dust consumed (had 5)
        self.assertEqual(self.char1.get_resource(16), 3)
        # 1 Ruby consumed (had 3)
        self.assertEqual(self.char1.get_resource(33), 2)
        # 5 gold consumed (had 50)
        self.assertEqual(self.char1.get_gold(), 45)


# ── Validation failures (independent of new rolling) ──────────────────

class TestCmdCraftEnchantValidation(EvenniaCommandTest):

    databases = "__all__"
    room_typeclass = "typeclasses.terrain.rooms.room_crafting.RoomCrafting"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)
        self.room1.db.crafting_type = "wizards_workshop"
        self.room1.db.mastery_level = 1
        self.room1.db.craft_cost = 5
        _give_enchanting_skill(self.char1)
        _learn_enchant_ruby(self.char1)

    def test_insufficient_arcane_dust(self):
        _give_resources(self.char1, {16: 1, 33: 1})
        _give_gold(self.char1, 50)
        result = self.call(CmdCraft(), "enchanted ruby")
        self.assertIn("You don't have enough materials", result)

    def test_insufficient_ruby(self):
        _give_resources(self.char1, {16: 5})
        _give_gold(self.char1, 50)
        result = self.call(CmdCraft(), "enchanted ruby")
        self.assertIn("You don't have enough materials", result)

    def test_no_enchanting_skill(self):
        self.char1.db.class_skill_mastery_levels = {}
        _give_resources(self.char1, {16: 5, 33: 3})
        _give_gold(self.char1, 50)
        result = self.call(CmdCraft(), "enchanted ruby")
        self.assertIn("You need at least", result)
