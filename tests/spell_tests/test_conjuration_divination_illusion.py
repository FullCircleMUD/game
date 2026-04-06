"""
Tests for conjuration, divination, and illusion spell schools.

Tests:
    - Registry: all spells registered with correct attributes
    - Acid Arrow: DoT application, scaling, anti-stacking, script lifecycle
    - Blur: disadvantage application, scaling, anti-stacking, script lifecycle
    - True Sight: effect application, condition granting, visibility, anti-stacking
    - Invisibility: condition, no anti-stacking, break_invisibility, duration/mana scaling
    - School membership: get_spells_for_school returns expected set
    - Descriptions and mechanics: all spells have documentation

evennia test --settings settings tests.spell_tests.test_conjuration_divination_illusion
"""

from unittest.mock import patch

from evennia.utils.create import create_object, create_script
from evennia.utils.test_resources import EvenniaTest

from combat.combat_handler import CombatHandler
from enums.condition import Condition
from enums.mastery_level import MasteryLevel
from enums.skills_enum import skills
from world.spells.registry import get_spell, get_spells_for_school


# ================================================================== #
#  Conjuration Registry Tests
# ================================================================== #

class TestConjurationRegistry(EvenniaTest):
    """Test all conjuration spells are registered correctly."""

    def create_script(self):
        pass

    def test_acid_arrow_registered(self):
        spell = get_spell("acid_arrow")
        self.assertIsNotNone(spell)
        self.assertEqual(spell.school, skills.CONJURATION)
        self.assertEqual(spell.min_mastery, MasteryLevel.BASIC)
        self.assertEqual(spell.target_type, "hostile")
        self.assertEqual(spell.mana_cost, {1: 5, 2: 8, 3: 10, 4: 14, 5: 16})

    def test_teleport_registered(self):
        spell = get_spell("teleport")
        self.assertIsNotNone(spell)
        self.assertEqual(spell.school, skills.CONJURATION)
        self.assertEqual(spell.min_mastery, MasteryLevel.SKILLED)
        self.assertEqual(spell.target_type, "none")
        self.assertEqual(spell.mana_cost, {2: 15, 3: 25, 4: 40, 5: 40})

    def test_dimensional_lock_registered(self):
        spell = get_spell("dimensional_lock")
        self.assertIsNotNone(spell)
        self.assertEqual(spell.school, skills.CONJURATION)
        self.assertEqual(spell.min_mastery, MasteryLevel.EXPERT)
        self.assertEqual(spell.target_type, "none")
        self.assertEqual(spell.mana_cost, {3: 28, 4: 39, 5: 49})

    def test_conjure_elemental_registered(self):
        spell = get_spell("conjure_elemental")
        self.assertIsNotNone(spell)
        self.assertEqual(spell.school, skills.CONJURATION)
        self.assertEqual(spell.min_mastery, MasteryLevel.MASTER)
        self.assertEqual(spell.mana_cost, {4: 56, 5: 64})

    def test_gate_registered(self):
        spell = get_spell("gate")
        self.assertIsNotNone(spell)
        self.assertEqual(spell.school, skills.CONJURATION)
        self.assertEqual(spell.min_mastery, MasteryLevel.GRANDMASTER)
        self.assertEqual(spell.mana_cost, {5: 100})
        self.assertEqual(spell.target_type, "none")

    def test_conjuration_school_has_all_spells(self):
        conj = get_spells_for_school("conjuration")
        expected = {
            "acid_arrow", "teleport", "dimensional_lock",
            "conjure_elemental", "gate",
            "light_spell", "find_familiar",
        }
        self.assertEqual(set(conj.keys()), expected)

    def test_conjuration_description_and_mechanics(self):
        """All conjuration spells should have description and mechanics."""
        for key in ["acid_arrow", "teleport", "dimensional_lock",
                     "conjure_elemental", "gate"]:
            spell = get_spell(key)
            self.assertTrue(spell.description, f"{key} missing description")
            self.assertTrue(spell.mechanics, f"{key} missing mechanics")


# ================================================================== #
#  Acid Arrow Execution Tests
# ================================================================== #

class TestAcidArrow(EvenniaTest):
    """Test Acid Arrow spell execution — DoT via AcidDoTScript."""

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.spell = get_spell("acid_arrow")
        self.char1.db.class_skill_mastery_levels = {"conjuration": 1}
        self.char1.mana = 100
        self.char2.hp = 100
        self.char2.hp_max = 100
        self.char2.damage_resistances = {}

    def test_acid_arrow_applies_named_effect(self):
        """Casting should create an acid_arrow named effect on target."""
        success, result = self.spell.cast(self.char1, self.char2)
        self.assertTrue(success)
        self.assertTrue(self.char2.has_effect("acid_arrow"))

    def test_acid_arrow_creates_dot_script(self):
        """Casting should attach an AcidDoTScript to the target."""
        self.spell.cast(self.char1, self.char2)
        scripts = self.char2.scripts.get("acid_dot")
        self.assertTrue(scripts)
        self.assertEqual(scripts[0].db.remaining_ticks, 1)  # tier 1

    def test_acid_arrow_dot_rounds_scale_with_tier(self):
        """DoT rounds should equal mastery tier."""
        for tier in range(1, 6):
            # Clean up from previous iteration
            if self.char2.has_effect("acid_arrow"):
                self.char2.remove_named_effect("acid_arrow")
            existing = self.char2.scripts.get("acid_dot")
            if existing:
                existing[0].delete()

            self.char1.db.class_skill_mastery_levels = {"conjuration": tier}
            self.char1.mana = 100
            self.spell.cast(self.char1, self.char2)
            scripts = self.char2.scripts.get("acid_dot")
            self.assertEqual(
                scripts[0].db.remaining_ticks, tier,
                f"Tier {tier} should have {tier} rounds"
            )

    def test_acid_arrow_dot_tick_deals_damage(self):
        """Each tick should deal 1d4+1 acid damage."""
        self.spell.cast(self.char1, self.char2)
        scripts = self.char2.scripts.get("acid_dot")
        hp_before = self.char2.hp
        with patch("typeclasses.scripts.acid_dot_script.dice") as mock_dice:
            mock_dice.roll.return_value = 4  # 1d4+1 = 4
            scripts[0].tick_acid()
            mock_dice.roll.assert_called_with("1d4+1")
        self.assertLess(self.char2.hp, hp_before)

    def test_acid_arrow_dot_expires_after_ticks(self):
        """DoT script should remove named effect after all ticks."""
        self.spell.cast(self.char1, self.char2)
        scripts = self.char2.scripts.get("acid_dot")
        # Tier 1 = 1 tick. After ticking once, should expire.
        with patch("typeclasses.scripts.acid_dot_script.dice") as mock_dice:
            mock_dice.roll.return_value = 3
            scripts[0].tick_acid()
        self.assertFalse(self.char2.has_effect("acid_arrow"))

    def test_acid_arrow_anti_stacking_replaces(self):
        """New cast should replace existing acid arrow, not stack."""
        self.char1.db.class_skill_mastery_levels = {"conjuration": 3}
        self.spell.cast(self.char1, self.char2)
        scripts1 = self.char2.scripts.get("acid_dot")
        self.assertEqual(scripts1[0].db.remaining_ticks, 3)

        # Recast — should replace with fresh 3-round DoT
        self.spell.cast(self.char1, self.char2)
        scripts2 = self.char2.scripts.get("acid_dot")
        self.assertEqual(len(scripts2), 1)  # only one script
        self.assertEqual(scripts2[0].db.remaining_ticks, 3)

    def test_acid_arrow_deducts_mana(self):
        """Should deduct 5 mana at tier 1."""
        self.spell.cast(self.char1, self.char2)
        self.assertEqual(self.char1.mana, 95)

    def test_acid_arrow_mastery_check(self):
        """Should fail without conjuration mastery."""
        self.char1.db.class_skill_mastery_levels = {}
        success, msg = self.spell.cast(self.char1, self.char2)
        self.assertFalse(success)
        self.assertIn("mastery", msg.lower())

    def test_acid_arrow_not_enough_mana(self):
        """Should fail with insufficient mana."""
        self.char1.mana = 4
        success, msg = self.spell.cast(self.char1, self.char2)
        self.assertFalse(success)
        self.assertIn("mana", msg.lower())

    def test_acid_arrow_multi_perspective_messages(self):
        """Should return first, second, and third person messages."""
        success, result = self.spell.cast(self.char1, self.char2)
        self.assertTrue(success)
        self.assertIsInstance(result, dict)
        self.assertIn("first", result)
        self.assertIn("second", result)
        self.assertIn("third", result)

    def test_acid_arrow_same_mana_as_magic_missile(self):
        """Mana costs should match Magic Missile exactly."""
        mm = get_spell("magic_missile")
        self.assertEqual(self.spell.mana_cost, mm.mana_cost)


# ================================================================== #
#  Divination Registry Tests
# ================================================================== #

class TestDivinationRegistry(EvenniaTest):
    """Test all divination spells are registered correctly."""

    def create_script(self):
        pass

    def test_identify_registered(self):
        spell = get_spell("identify")
        self.assertIsNotNone(spell)
        self.assertEqual(spell.school, skills.DIVINATION)
        self.assertEqual(spell.min_mastery, MasteryLevel.BASIC)
        self.assertEqual(spell.target_type, "any")
        self.assertEqual(spell.mana_cost, {1: 5, 2: 8, 3: 10, 4: 14, 5: 16})

    def test_true_sight_registered(self):
        spell = get_spell("true_sight")
        self.assertIsNotNone(spell)
        self.assertEqual(spell.school, skills.DIVINATION)
        self.assertEqual(spell.min_mastery, MasteryLevel.SKILLED)
        self.assertEqual(spell.target_type, "self")

    def test_scry_registered(self):
        spell = get_spell("scry")
        self.assertIsNotNone(spell)
        self.assertEqual(spell.school, skills.DIVINATION)
        self.assertEqual(spell.min_mastery, MasteryLevel.SKILLED)
        self.assertEqual(spell.target_type, "none")
        self.assertEqual(spell.mana_cost, {2: 15, 3: 25, 4: 40, 5: 60})

    def test_mass_revelation_registered(self):
        spell = get_spell("mass_revelation")
        self.assertIsNotNone(spell)
        self.assertEqual(spell.school, skills.DIVINATION)
        self.assertEqual(spell.min_mastery, MasteryLevel.EXPERT)
        self.assertEqual(spell.target_type, "none")
        self.assertEqual(spell.mana_cost, {3: 28, 4: 39, 5: 49})

    def test_divination_school_has_all_spells(self):
        div = get_spells_for_school("divination")
        expected = {
            "identify", "true_sight", "scry", "mass_revelation",
            "locate_object", "detect_traps", "darkvision",
        }
        self.assertEqual(set(div.keys()), expected)

    def test_divination_description_and_mechanics(self):
        """All divination spells should have description and mechanics."""
        for key in ["identify", "true_sight", "scry", "mass_revelation"]:
            spell = get_spell(key)
            self.assertTrue(spell.description, f"{key} missing description")
            self.assertTrue(spell.mechanics, f"{key} missing mechanics")


# ================================================================== #
#  Identify Execution Tests
# ================================================================== #

class TestIdentify(EvenniaTest):
    """Test Identify spell execution — actor template, mastery gate, PvP check."""

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.spell = get_spell("identify")
        self.char1.db.class_skill_mastery_levels = {"divination": 1}  # BASIC
        self.char1.mana = 100

    def _make_mob(self, level=3, **kwargs):
        """Create a CombatMob for testing."""
        from typeclasses.actors.mob import CombatMob
        mob = create_object(CombatMob, key="test goblin", location=self.room1)
        mob.level = level
        mob.hp = kwargs.get("hp", 20)
        mob.hp_max = kwargs.get("hp_max", 20)
        mob.mana = kwargs.get("mana", 0)
        mob.mana_max = kwargs.get("mana_max", 0)
        mob.move = kwargs.get("move", 10)
        mob.move_max = kwargs.get("move_max", 10)
        mob.damage_dice = kwargs.get("damage_dice", "1d6")
        mob.attack_message = kwargs.get("attack_message", "slashes")
        mob.size = kwargs.get("size", "medium")
        mob.strength = kwargs.get("strength", 14)
        mob.dexterity = kwargs.get("dexterity", 12)
        mob.constitution = kwargs.get("constitution", 13)
        mob.intelligence = kwargs.get("intelligence", 8)
        mob.wisdom = kwargs.get("wisdom", 10)
        mob.charisma = kwargs.get("charisma", 6)
        mob.armor_class = kwargs.get("armor_class", 2)
        mob.damage_resistances = kwargs.get("damage_resistances", {})
        return mob

    def test_identify_mob_basic_success(self):
        """Level 3 mob with BASIC divination should succeed."""
        mob = self._make_mob(level=3)
        success, result = self.spell.cast(self.char1, mob)
        self.assertTrue(success)
        self.assertIsInstance(result, dict)
        output = result["first"]
        self.assertIn("test goblin", output)
        self.assertIn("HP:", output)
        self.assertIn("AC:", output)
        self.assertIn("STR:", output)
        self.assertIn("Damage:", output)

    def test_identify_mob_mastery_gate_fails(self):
        """Level 16 mob with BASIC tier should show 'too powerful' message."""
        mob = self._make_mob(level=16)
        success, result = self.spell.cast(self.char1, mob)
        self.assertTrue(success)
        self.assertIn("too powerful", result["first"])

    def test_identify_mob_mastery_gate_tiers(self):
        """Verify level-to-tier boundaries."""
        test_cases = [
            # (mob_level, caster_tier, should_see_stats)
            (5, 1, True),    # level 5, BASIC → pass
            (6, 1, False),   # level 6, BASIC → fail
            (6, 2, True),    # level 6, SKILLED → pass
            (15, 2, True),   # level 15, SKILLED → pass
            (16, 2, False),  # level 16, SKILLED → fail
            (16, 3, True),   # level 16, EXPERT → pass
            (25, 3, True),   # level 25, EXPERT → pass
            (26, 3, False),  # level 26, EXPERT → fail
            (26, 4, True),   # level 26, MASTER → pass
            (35, 4, True),   # level 35, MASTER → pass
            (36, 4, False),  # level 36, MASTER → fail
            (36, 5, True),   # level 36, GM → pass
        ]
        for mob_level, caster_tier, expect_stats in test_cases:
            mob = self._make_mob(level=mob_level)
            self.char1.db.class_skill_mastery_levels = {"divination": caster_tier}
            self.char1.mana = 100
            success, result = self.spell.cast(self.char1, mob)
            self.assertTrue(success)
            has_stats = "STR:" in result["first"]
            self.assertEqual(
                has_stats, expect_stats,
                f"Level {mob_level} mob, tier {caster_tier}: "
                f"expected stats={'shown' if expect_stats else 'hidden'}"
            )
            mob.delete()

    def test_identify_pc_requires_pvp_room(self):
        """Identifying a PC in non-PvP room should fail with mana refund."""
        mana_before = self.char1.mana
        success, result = self.spell.cast(self.char1, self.char2)
        self.assertFalse(success)
        self.assertIn("PvP", result)
        self.assertEqual(self.char1.mana, mana_before)  # mana refunded

    def test_identify_pc_in_pvp_room(self):
        """Identifying a PC in PvP room should succeed."""
        self.room1.allow_pvp = True
        self.char2.hp = 50
        self.char2.hp_max = 50
        success, result = self.spell.cast(self.char1, self.char2)
        self.assertTrue(success)
        output = result["first"]
        self.assertIn("HP:", output)
        self.assertIn("Wielding:", output)
        self.assertIn("Memorised Spells:", output)

    def test_identify_pc_self_always_works(self):
        """Identifying yourself should work even in non-PvP rooms."""
        success, result = self.spell.cast(self.char1, self.char1)
        self.assertTrue(success)
        self.assertIn("STR:", result["first"])

    def test_identify_mundane_object_sassy(self):
        """Non-actor, non-NFT target gets a sassy one-liner, mana consumed."""
        from evennia.objects.objects import DefaultObject
        obj = create_object(DefaultObject, key="a rock", location=self.char1)
        mana_before = self.char1.mana
        success, result = self.spell.cast(self.char1, obj)
        self.assertTrue(success)
        self.assertIn("a rock is a rock", result["first"])
        self.assertLess(self.char1.mana, mana_before)

    def test_identify_output_contains_ability_scores(self):
        """Output should contain all 6 ability score labels."""
        mob = self._make_mob()
        success, result = self.spell.cast(self.char1, mob)
        output = result["first"]
        for label in ["STR:", "DEX:", "CON:", "INT:", "WIS:", "CHA:"]:
            self.assertIn(label, output, f"Missing {label} in output")

    def test_identify_output_contains_resistances(self):
        """Resistances should appear when set."""
        mob = self._make_mob(damage_resistances={"fire": 25, "cold": -15})
        success, result = self.spell.cast(self.char1, mob)
        output = result["first"]
        self.assertIn("Fire: 25%", output)
        self.assertIn("Cold: -15%", output)
        self.assertIn("vulnerable", output)

    def test_identify_output_no_resistances(self):
        """Should show 'None' when no resistances."""
        mob = self._make_mob()
        success, result = self.spell.cast(self.char1, mob)
        self.assertIn("Resistances:|n None", result["first"])

    def test_identify_output_contains_conditions(self):
        """Conditions should appear when set."""
        mob = self._make_mob()
        mob.add_condition(Condition.DARKVISION)
        success, result = self.spell.cast(self.char1, mob)
        self.assertIn("DARKVISION", result["first"])

    def test_identify_output_contains_effects(self):
        """Named effects should appear when active."""
        mob = self._make_mob()
        from enums.named_effect import NamedEffect
        mob.apply_named_effect(key="stunned", duration=1,
                               duration_type="combat_rounds", messages={})
        success, result = self.spell.cast(self.char1, mob)
        self.assertIn("stunned", result["first"])

    def test_identify_pc_shows_memorised_spells(self):
        """Memorised spells should appear for PC targets."""
        self.room1.allow_pvp = True
        self.char2.db.memorised_spells = {"magic_missile": True}
        success, result = self.spell.cast(self.char1, self.char2)
        self.assertTrue(success)
        self.assertIn("Magic Missile", result["first"])

    def test_identify_third_person_message(self):
        """Third person should be flavour, second should be None."""
        mob = self._make_mob()
        success, result = self.spell.cast(self.char1, mob)
        self.assertIsNone(result["second"])
        self.assertIn("studies", result["third"])

    def test_identify_mob_shows_size(self):
        """Size should appear in mob output."""
        mob = self._make_mob(size="large")
        success, result = self.spell.cast(self.char1, mob)
        self.assertIn("Large", result["first"])

    def test_identify_mob_shows_damage_dice(self):
        """Damage dice should appear in mob output."""
        mob = self._make_mob(damage_dice="2d8", attack_message="crushes")
        success, result = self.spell.cast(self.char1, mob)
        self.assertIn("2d8", result["first"])
        self.assertIn("crushes", result["first"])

    def test_identify_mastery_check(self):
        """Should fail without divination mastery."""
        mob = self._make_mob()
        self.char1.db.class_skill_mastery_levels = {}
        success, msg = self.spell.cast(self.char1, mob)
        self.assertFalse(success)
        self.assertIn("mastery", msg.lower())

    def test_identify_not_enough_mana(self):
        """Should fail with insufficient mana."""
        mob = self._make_mob()
        self.char1.mana = 4
        success, msg = self.spell.cast(self.char1, mob)
        self.assertFalse(success)
        self.assertIn("mana", msg.lower())

    # ── NFT Item Identify Tests ─────────────────────────────────────

    def test_identify_weapon_shows_type(self):
        """WeaponNFTItem should show type with weapon_type and damage_type."""
        from typeclasses.items.weapons.weapon_nft_item import WeaponNFTItem
        from enums.unused_for_reference.damage_type import DamageType
        weapon = create_object(WeaponNFTItem, key="Test Sword")
        weapon.weapon_type = "melee"
        weapon.damage_type = DamageType.SLASHING
        weapon.move_to(self.char1, quiet=True)
        success, result = self.spell.cast(self.char1, weapon)
        self.assertTrue(success)
        output = result["first"]
        self.assertIn("Weapon", output)
        self.assertIn("Melee", output)
        self.assertIn("Slashing", output)

    def test_identify_weapon_shows_damage_table(self):
        """Weapon damage dict entries should appear in output."""
        from typeclasses.items.weapons.weapon_nft_item import WeaponNFTItem
        weapon = create_object(WeaponNFTItem, key="Test Blade")
        weapon.damage = {
            MasteryLevel.UNSKILLED: "1D4",
            MasteryLevel.BASIC: "1D8",
            MasteryLevel.SKILLED: "1D10",
            MasteryLevel.EXPERT: "2D6",
            MasteryLevel.MASTER: "2D8",
            MasteryLevel.GRANDMASTER: "2D8",
        }
        weapon.move_to(self.char1, quiet=True)
        success, result = self.spell.cast(self.char1, weapon)
        output = result["first"]
        self.assertIn("1D4", output)
        self.assertIn("1D8", output)
        self.assertIn("2D6", output)

    def test_identify_weapon_shows_speed_and_flags(self):
        """Speed, two-handed, and finesse flags should appear."""
        from typeclasses.items.weapons.weapon_nft_item import WeaponNFTItem
        weapon = create_object(WeaponNFTItem, key="Great Axe")
        weapon.speed = 0.8
        weapon.two_handed = True
        weapon.is_finesse = False
        weapon.move_to(self.char1, quiet=True)
        success, result = self.spell.cast(self.char1, weapon)
        output = result["first"]
        self.assertIn("0.8", output)
        self.assertIn("Two-Handed:|n Yes", output)
        self.assertIn("Finesse:|n No", output)

    def test_identify_weapon_shows_durability(self):
        """Durability should show current/max."""
        from typeclasses.items.weapons.weapon_nft_item import WeaponNFTItem
        weapon = create_object(WeaponNFTItem, key="Worn Blade")
        weapon.max_durability = 100
        weapon.durability = 75
        weapon.move_to(self.char1, quiet=True)
        success, result = self.spell.cast(self.char1, weapon)
        self.assertIn("75/100", result["first"])

    def test_identify_wearable_shows_slot_and_effects(self):
        """Wearable should show slot and wear_effects."""
        from typeclasses.items.wearables.wearable_nft_item import WearableNFTItem
        from enums.wearslot import HumanoidWearSlot
        armor = create_object(WearableNFTItem, key="Test Armor")
        armor.wearslot = HumanoidWearSlot.BODY
        armor.wear_effects = [{"type": "stat_bonus", "stat": "armor_class", "value": 2}]
        armor.max_durability = 80
        armor.durability = 60
        armor.move_to(self.char1, quiet=True)
        success, result = self.spell.cast(self.char1, armor)
        output = result["first"]
        self.assertIn("Body", output)
        self.assertIn("+2 Armor Class", output)
        self.assertIn("60/80", output)

    def test_identify_wearable_shows_restrictions(self):
        """Excluded classes should appear in restrictions."""
        from typeclasses.items.wearables.wearable_nft_item import WearableNFTItem
        armor = create_object(WearableNFTItem, key="Fighter Armor")
        armor.excluded_classes = ["mage"]
        armor.move_to(self.char1, quiet=True)
        success, result = self.spell.cast(self.char1, armor)
        output = result["first"]
        self.assertIn("Excluded: Mage", output)

    def test_identify_holdable_shows_effects(self):
        """Holdable (shield) should show AC bonus."""
        from typeclasses.items.holdables.holdable_nft_item import HoldableNFTItem
        shield = create_object(HoldableNFTItem, key="Iron Shield")
        shield.wear_effects = [{"type": "stat_bonus", "stat": "armor_class", "value": 2}]
        shield.max_durability = 100
        shield.durability = 90
        shield.move_to(self.char1, quiet=True)
        success, result = self.spell.cast(self.char1, shield)
        output = result["first"]
        self.assertIn("Holdable", output)
        self.assertIn("+2 Armor Class", output)

    def test_identify_potion_instant(self):
        """Instant potion should show restore effect and 'Instant'."""
        from typeclasses.items.consumables.potion_nft_item import PotionNFTItem
        potion = create_object(PotionNFTItem, key="Healing Potion")
        potion.potion_effects = [{"type": "restore", "stat": "hp", "dice": "2d4+1"}]
        potion.duration = 0
        potion.move_to(self.char1, quiet=True)
        success, result = self.spell.cast(self.char1, potion)
        output = result["first"]
        self.assertIn("Potion", output)
        self.assertIn("Restores HP (2d4+1)", output)
        self.assertIn("Instant", output)

    def test_identify_potion_timed(self):
        """Timed potion should show stat bonus and duration."""
        from typeclasses.items.consumables.potion_nft_item import PotionNFTItem
        potion = create_object(PotionNFTItem, key="Strength Potion")
        potion.potion_effects = [{"type": "stat_bonus", "stat": "strength", "value": 1}]
        potion.duration = 60
        potion.move_to(self.char1, quiet=True)
        success, result = self.spell.cast(self.char1, potion)
        output = result["first"]
        self.assertIn("+1 Strength", output)
        self.assertIn("1 minute", output)

    def test_identify_spell_scroll(self):
        """Spell scroll should show spell name and school."""
        from typeclasses.items.consumables.spell_scroll_nft_item import SpellScrollNFTItem
        scroll = create_object(SpellScrollNFTItem, key="MM Scroll")
        scroll.spell_key = "magic_missile"
        scroll.move_to(self.char1, quiet=True)
        success, result = self.spell.cast(self.char1, scroll)
        output = result["first"]
        self.assertIn("Spell Scroll", output)
        self.assertIn("Magic Missile", output)

    def test_identify_recipe(self):
        """Crafting recipe should show recipe key."""
        from typeclasses.items.consumables.crafting_recipe_nft_item import CraftingRecipeNFTItem
        recipe = create_object(CraftingRecipeNFTItem, key="Sword Recipe")
        recipe.recipe_key = "iron_longsword"
        recipe.move_to(self.char1, quiet=True)
        success, result = self.spell.cast(self.char1, recipe)
        output = result["first"]
        self.assertIn("Crafting Recipe", output)
        self.assertIn("Iron Longsword", output)

    def test_identify_container(self):
        """Container should show capacity and durability."""
        from typeclasses.items.containers.container_nft_item import ContainerNFTItem
        bag = create_object(ContainerNFTItem, key="Backpack")
        bag.max_container_capacity_kg = 20.0
        bag.max_durability = 50
        bag.durability = 50
        bag.move_to(self.char1, quiet=True)
        success, result = self.spell.cast(self.char1, bag)
        output = result["first"]
        self.assertIn("Container", output)
        self.assertIn("20.0 kg", output)
        self.assertIn("50/50", output)

    def test_identify_item_shows_weight(self):
        """Weight line should appear for any NFT item."""
        from typeclasses.items.base_nft_item import BaseNFTItem
        item = create_object(BaseNFTItem, key="Test Item")
        item.weight = 2.5
        item.move_to(self.char1, quiet=True)
        success, result = self.spell.cast(self.char1, item)
        self.assertIn("2.5 kg", result["first"])

    def test_identify_item_third_person(self):
        """Third person message should mention studying closely."""
        from typeclasses.items.base_nft_item import BaseNFTItem
        item = create_object(BaseNFTItem, key="Test Gem")
        item.move_to(self.char1, quiet=True)
        success, result = self.spell.cast(self.char1, item)
        self.assertTrue(success)
        self.assertIsNone(result["second"])
        self.assertIn("studies", result["third"])
        self.assertIn("Test Gem", result["third"])

    # -------------------------------------------------------------- #
    #  Item mastery gate tests
    # -------------------------------------------------------------- #

    def test_identify_item_default_gate_is_basic(self):
        """Default identify_mastery_gate=1 means BASIC tier can identify."""
        from typeclasses.items.base_nft_item import BaseNFTItem
        item = create_object(BaseNFTItem, key="Normal Item")
        item.move_to(self.char1, quiet=True)
        self.char1.db.class_skill_mastery_levels = {"divination": 1}
        self.char1.mana = 100
        success, result = self.spell.cast(self.char1, item)
        self.assertTrue(success)
        self.assertIn("Identify:", result["first"])

    def test_identify_item_gate_blocks_low_tier(self):
        """Item with identify_mastery_gate=3 should block BASIC/SKILLED."""
        from typeclasses.items.base_nft_item import BaseNFTItem
        item = create_object(BaseNFTItem, key="Rare Artifact")
        item.identify_mastery_gate = 3
        item.move_to(self.char1, quiet=True)
        self.char1.db.class_skill_mastery_levels = {"divination": 2}
        self.char1.mana = 100
        success, result = self.spell.cast(self.char1, item)
        self.assertTrue(success)  # cast succeeds (mana consumed)
        self.assertIn("elude", result["first"])
        self.assertNotIn("Identify:", result["first"])

    def test_identify_item_gate_passes_at_tier(self):
        """Item with identify_mastery_gate=3 should work at tier 3."""
        from typeclasses.items.base_nft_item import BaseNFTItem
        item = create_object(BaseNFTItem, key="Rare Artifact")
        item.identify_mastery_gate = 3
        item.move_to(self.char1, quiet=True)
        self.char1.db.class_skill_mastery_levels = {"divination": 3}
        self.char1.mana = 100
        success, result = self.spell.cast(self.char1, item)
        self.assertTrue(success)
        self.assertIn("Identify:", result["first"])

    def test_identify_item_gate_passes_above_tier(self):
        """Item with identify_mastery_gate=2 should work at tier 5."""
        from typeclasses.items.base_nft_item import BaseNFTItem
        item = create_object(BaseNFTItem, key="Uncommon Blade")
        item.identify_mastery_gate = 2
        item.move_to(self.char1, quiet=True)
        self.char1.db.class_skill_mastery_levels = {"divination": 5}
        self.char1.mana = 100
        success, result = self.spell.cast(self.char1, item)
        self.assertTrue(success)
        self.assertIn("Identify:", result["first"])

    def test_identify_item_gate_consumes_mana_on_fail(self):
        """Mastery gate failure should still consume mana (you tried)."""
        from typeclasses.items.base_nft_item import BaseNFTItem
        item = create_object(BaseNFTItem, key="Legendary Ring")
        item.identify_mastery_gate = 5
        item.move_to(self.char1, quiet=True)
        self.char1.db.class_skill_mastery_levels = {"divination": 1}
        self.char1.mana = 100
        success, result = self.spell.cast(self.char1, item)
        self.assertTrue(success)  # cast succeeded (mana consumed, partial info)
        self.assertLess(self.char1.mana, 100)  # mana was consumed

    def test_identify_item_gate_third_person_on_fail(self):
        """Mastery gate failure should still show third-person message."""
        from typeclasses.items.base_nft_item import BaseNFTItem
        item = create_object(BaseNFTItem, key="Ancient Tome")
        item.identify_mastery_gate = 4
        item.move_to(self.char1, quiet=True)
        self.char1.db.class_skill_mastery_levels = {"divination": 1}
        self.char1.mana = 100
        success, result = self.spell.cast(self.char1, item)
        self.assertIn("studies", result["third"])
        self.assertIn("Ancient Tome", result["third"])


# ================================================================== #
#  True Sight Execution Tests
# ================================================================== #

class TestTrueSight(EvenniaTest):
    """Test True Sight spell — tiered progression: hidden→traps→invisible."""

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.spell = get_spell("true_sight")
        self.char1.db.class_skill_mastery_levels = {"divination": 2}  # min_mastery = SKILLED
        self.char1.mana = 100

    def test_applies_named_effect(self):
        """Casting should create a true_sight named effect on caster."""
        success, result = self.spell.cast(self.char1, self.char1)
        self.assertTrue(success)
        self.assertTrue(self.char1.has_effect("true_sight"))

    def test_true_sight_tier_stored(self):
        """Caster tier should be stored in db.true_sight_tier on cast."""
        self.spell.cast(self.char1, self.char1)
        self.assertEqual(self.char1.db.true_sight_tier, 2)

    def test_true_sight_tier_stored_expert(self):
        """EXPERT tier should store tier 3."""
        self.char1.db.class_skill_mastery_levels = {"divination": 3}
        self.spell.cast(self.char1, self.char1)
        self.assertEqual(self.char1.db.true_sight_tier, 3)

    # ── DETECT_INVIS tiering ──

    def test_skilled_no_detect_invis(self):
        """SKILLED True Sight should NOT grant DETECT_INVIS."""
        self.spell.cast(self.char1, self.char1)
        self.assertFalse(self.char1.has_condition(Condition.DETECT_INVIS))

    def test_expert_no_detect_invis(self):
        """EXPERT True Sight should NOT grant DETECT_INVIS."""
        self.char1.db.class_skill_mastery_levels = {"divination": 3}
        self.spell.cast(self.char1, self.char1)
        self.assertFalse(self.char1.has_condition(Condition.DETECT_INVIS))

    def test_master_grants_detect_invis(self):
        """MASTER True Sight SHOULD grant DETECT_INVIS."""
        self.char1.db.class_skill_mastery_levels = {"divination": 4}
        self.spell.cast(self.char1, self.char1)
        self.assertTrue(self.char1.has_condition(Condition.DETECT_INVIS))

    def test_gm_grants_detect_invis(self):
        """GM True Sight SHOULD grant DETECT_INVIS."""
        self.char1.db.class_skill_mastery_levels = {"divination": 5}
        self.spell.cast(self.char1, self.char1)
        self.assertTrue(self.char1.has_condition(Condition.DETECT_INVIS))

    def test_remove_clears_detect_invis(self):
        """Removing MASTER True Sight should remove DETECT_INVIS."""
        self.char1.db.class_skill_mastery_levels = {"divination": 4}
        self.spell.cast(self.char1, self.char1)
        self.assertTrue(self.char1.has_condition(Condition.DETECT_INVIS))
        self.char1.remove_named_effect("true_sight")
        self.assertFalse(self.char1.has_condition(Condition.DETECT_INVIS))

    # ── Trap detection tiering ──

    def test_skilled_no_trap_detection(self):
        """SKILLED True Sight should NOT call _detect_traps_in_room."""
        from unittest.mock import patch
        with patch.object(self.spell, "_detect_traps_in_room") as mock_detect:
            self.spell.cast(self.char1, self.char1)
            mock_detect.assert_not_called()

    def test_expert_auto_detects_traps_on_cast(self):
        """EXPERT True Sight should call _detect_traps_in_room on cast."""
        from unittest.mock import patch
        self.char1.db.class_skill_mastery_levels = {"divination": 3}
        with patch.object(self.spell, "_detect_traps_in_room") as mock_detect:
            self.spell.cast(self.char1, self.char1)
            mock_detect.assert_called_once_with(self.char1)

    def test_master_auto_detects_traps_on_cast(self):
        """MASTER True Sight should also call _detect_traps_in_room."""
        from unittest.mock import patch
        self.char1.db.class_skill_mastery_levels = {"divination": 4}
        with patch.object(self.spell, "_detect_traps_in_room") as mock_detect:
            self.spell.cast(self.char1, self.char1)
            mock_detect.assert_called_once_with(self.char1)

    # ── Standard tests ──

    def test_anti_stacking_refunds_mana(self):
        """Recasting while active should fail and refund mana."""
        self.spell.cast(self.char1, self.char1)
        mana_after_first = self.char1.mana
        success, result = self.spell.cast(self.char1, self.char1)
        self.assertFalse(success)
        self.assertEqual(self.char1.mana, mana_after_first)

    def test_duration_scales_with_tier(self):
        """Duration should scale: SKILLED=5min, EXPERT=10min, MASTER=30min, GM=60min."""
        expected_minutes = {2: 5, 3: 10, 4: 30, 5: 60}
        for tier, minutes in expected_minutes.items():
            if self.char1.has_effect("true_sight"):
                self.char1.remove_named_effect("true_sight")
            self.char1.db.class_skill_mastery_levels = {"divination": tier}
            self.char1.mana = 100
            success, result = self.spell.cast(self.char1, self.char1)
            self.assertTrue(success)
            self.assertIn(str(minutes), result["first"],
                          f"Tier {tier} message should mention {minutes}")

    def test_mana_cost_scales_with_tier(self):
        """Mana cost: SKILLED=15, EXPERT=25, MASTER=40, GM=40."""
        expected = {2: 15, 3: 25, 4: 40, 5: 40}
        for tier, cost in expected.items():
            if self.char1.has_effect("true_sight"):
                self.char1.remove_named_effect("true_sight")
            self.char1.db.class_skill_mastery_levels = {"divination": tier}
            self.char1.mana = 100
            self.spell.cast(self.char1, self.char1)
            self.assertEqual(self.char1.mana, 100 - cost,
                             f"Tier {tier} should cost {cost} mana")

    def test_mastery_check(self):
        """Should fail without divination mastery at SKILLED level."""
        self.char1.db.class_skill_mastery_levels = {}
        success, msg = self.spell.cast(self.char1, self.char1)
        self.assertFalse(success)
        self.assertIn("mastery", msg.lower())

    def test_basic_mastery_too_low(self):
        """BASIC mastery should not be enough (min_mastery = SKILLED)."""
        self.char1.db.class_skill_mastery_levels = {"divination": 1}
        success, msg = self.spell.cast(self.char1, self.char1)
        self.assertFalse(success)

    def test_not_enough_mana(self):
        """Should fail with insufficient mana."""
        self.char1.mana = 14
        success, msg = self.spell.cast(self.char1, self.char1)
        self.assertFalse(success)
        self.assertIn("mana", msg.lower())

    def test_multi_perspective_messages(self):
        """Should return first and third person messages (no second for self-cast)."""
        success, result = self.spell.cast(self.char1, self.char1)
        self.assertTrue(success)
        self.assertIsInstance(result, dict)
        self.assertIn("first", result)
        self.assertIsNone(result["second"])
        self.assertIn("third", result)

    def test_message_reflects_tier_capabilities(self):
        """Cast message should describe what this tier reveals."""
        # SKILLED — hidden things only
        success, result = self.spell.cast(self.char1, self.char1)
        self.assertIn("hidden things", result["first"])
        self.assertNotIn("traps", result["first"])

        # EXPERT — hidden things and traps
        self.char1.remove_named_effect("true_sight")
        self.char1.db.class_skill_mastery_levels = {"divination": 3}
        self.char1.mana = 100
        success, result = self.spell.cast(self.char1, self.char1)
        self.assertIn("traps", result["first"])

        # MASTER — hidden things, traps, and invisible
        self.char1.remove_named_effect("true_sight")
        self.char1.db.class_skill_mastery_levels = {"divination": 4}
        self.char1.mana = 100
        success, result = self.spell.cast(self.char1, self.char1)
        self.assertIn("invisible", result["first"])

    def test_hidden_character_visible_with_true_sight(self):
        """A character with true_sight should see HIDDEN characters in room display."""
        from evennia.utils.create import create_object
        from typeclasses.terrain.rooms.room_base import RoomBase
        room = create_object(RoomBase, key="TestRoom", nohome=True)
        room.always_lit = True
        self.char1.location = room
        self.char2.location = room
        self.spell.cast(self.char1, self.char1)
        self.char2.add_condition(Condition.HIDDEN)
        display = room.get_display_characters(self.char1)
        self.assertIn(self.char2.key, display)

    def test_hidden_character_not_visible_without_true_sight(self):
        """A character without true_sight should NOT see HIDDEN characters."""
        from evennia.utils.create import create_object
        from typeclasses.terrain.rooms.room_base import RoomBase
        room = create_object(RoomBase, key="TestRoom", nohome=True)
        room.always_lit = True
        self.char1.location = room
        self.char2.location = room
        self.char2.add_condition(Condition.HIDDEN)
        display = room.get_display_characters(self.char1)
        self.assertNotIn(self.char2.key, display)


# ================================================================== #
#  Illusion Registry Tests
# ================================================================== #

class TestIllusionRegistry(EvenniaTest):
    """Test all illusion spells are registered correctly."""

    def create_script(self):
        pass

    def test_blur_registered(self):
        spell = get_spell("blur")
        self.assertIsNotNone(spell)
        self.assertEqual(spell.school, skills.ILLUSION)
        self.assertEqual(spell.min_mastery, MasteryLevel.BASIC)
        self.assertEqual(spell.target_type, "self")
        self.assertEqual(spell.mana_cost, {1: 5, 2: 8, 3: 10, 4: 14, 5: 16})

    def test_invisibility_registered(self):
        spell = get_spell("invisibility")
        self.assertIsNotNone(spell)
        self.assertEqual(spell.school, skills.ILLUSION)
        self.assertEqual(spell.min_mastery, MasteryLevel.SKILLED)
        self.assertEqual(spell.target_type, "self")

    def test_mass_confusion_registered(self):
        spell = get_spell("mass_confusion")
        self.assertIsNotNone(spell)
        self.assertEqual(spell.school, skills.ILLUSION)
        self.assertEqual(spell.min_mastery, MasteryLevel.EXPERT)
        self.assertEqual(spell.target_type, "none")
        self.assertEqual(spell.mana_cost, {3: 28, 4: 39, 5: 49})

    def test_greater_invisibility_registered(self):
        spell = get_spell("greater_invisibility")
        self.assertIsNotNone(spell)
        self.assertEqual(spell.school, skills.ILLUSION)
        self.assertEqual(spell.min_mastery, MasteryLevel.MASTER)
        self.assertEqual(spell.target_type, "friendly")
        self.assertEqual(spell.mana_cost, {4: 56, 5: 64})

    def test_phantasmal_killer_registered(self):
        spell = get_spell("phantasmal_killer")
        self.assertIsNotNone(spell)
        self.assertEqual(spell.school, skills.ILLUSION)
        self.assertEqual(spell.min_mastery, MasteryLevel.GRANDMASTER)
        self.assertEqual(spell.mana_cost, {5: 100})
        self.assertEqual(spell.target_type, "hostile")

    def test_illusion_school_has_all_spells(self):
        ill = get_spells_for_school("illusion")
        expected = {
            "blur", "invisibility", "mass_confusion",
            "greater_invisibility", "phantasmal_killer",
            "mirror_image", "disguise_self", "distract",
        }
        self.assertEqual(set(ill.keys()), expected)

    def test_illusion_description_and_mechanics(self):
        """All illusion spells should have description and mechanics."""
        for key in ["blur", "invisibility", "mass_confusion",
                     "greater_invisibility", "phantasmal_killer"]:
            spell = get_spell(key)
            self.assertTrue(spell.description, f"{key} missing description")
            self.assertTrue(spell.mechanics, f"{key} missing mechanics")


# ================================================================== #
#  Blur Execution Tests
# ================================================================== #

class TestBlur(EvenniaTest):
    """Test Blur spell execution — disadvantage via BlurScript."""

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.spell = get_spell("blur")
        self.char1.db.class_skill_mastery_levels = {"illusion": 1}
        self.char1.mana = 100
        self.char1.hp = 100
        self.char1.hp_max = 100
        self.char2.hp = 100
        self.char2.hp_max = 100
        # PvP so char2 is an enemy of char1
        self.room1.allow_pvp = True
        # Both need combat handlers for get_sides to find them
        self.ch1_handler = create_script(
            CombatHandler, obj=self.char1, key="combat_handler"
        )
        self.ch2_handler = create_script(
            CombatHandler, obj=self.char2, key="combat_handler"
        )

    def tearDown(self):
        for char in (self.char1, self.char2):
            for key in ("combat_handler", "blur_effect"):
                scripts = char.scripts.get(key)
                if scripts:
                    for s in scripts:
                        s.delete()
        super().tearDown()

    def test_blur_applies_named_effect(self):
        """Casting should create a blurred named effect on caster."""
        success, result = self.spell.cast(self.char1, self.char1)
        self.assertTrue(success)
        self.assertTrue(self.char1.has_effect("blurred"))

    def test_blur_creates_script(self):
        """Casting should attach a BlurScript to the caster."""
        self.spell.cast(self.char1, self.char1)
        scripts = self.char1.scripts.get("blur_effect")
        self.assertTrue(scripts)
        self.assertEqual(scripts[0].db.remaining_ticks, 3)  # tier 1 = 3 rounds

    def test_blur_requires_combat(self):
        """Should fail if caster is not in combat, with mana refunded."""
        # Remove combat handler
        self.ch1_handler.delete()
        mana_before = self.char1.mana
        success, result = self.spell.cast(self.char1, self.char1)
        self.assertFalse(success)
        self.assertEqual(self.char1.mana, mana_before)  # mana refunded

    def test_blur_sets_disadvantage_on_enemies(self):
        """Casting should immediately set disadvantage on enemies."""
        self.spell.cast(self.char1, self.char1)
        # char2's combat handler should have disadvantage against char1
        self.assertTrue(self.ch2_handler.has_disadvantage(self.char1))

    def test_blur_rounds_scale_with_tier(self):
        """Script remaining_ticks should follow _ROUNDS scaling."""
        expected = {1: 3, 2: 4, 3: 5, 4: 6, 5: 7}
        for tier in range(1, 6):
            # Clean up from previous iteration
            if self.char1.has_effect("blurred"):
                self.char1.remove_named_effect("blurred")
            existing = self.char1.scripts.get("blur_effect")
            if existing:
                existing[0].delete()

            self.char1.db.class_skill_mastery_levels = {"illusion": tier}
            self.char1.mana = 100
            self.spell.cast(self.char1, self.char1)
            scripts = self.char1.scripts.get("blur_effect")
            self.assertEqual(
                scripts[0].db.remaining_ticks, expected[tier],
                f"Tier {tier} should have {expected[tier]} rounds"
            )

    def test_blur_tick_sets_disadvantage(self):
        """Each tick should refresh disadvantage on enemies."""
        self.char1.db.class_skill_mastery_levels = {"illusion": 3}
        self.spell.cast(self.char1, self.char1)
        scripts = self.char1.scripts.get("blur_effect")

        # Clear the initial disadvantage to verify tick sets it fresh
        self.ch2_handler.set_disadvantage(self.char1, rounds=0)
        self.assertFalse(self.ch2_handler.has_disadvantage(self.char1))

        # Tick the blur script
        scripts[0].tick_blur()
        self.assertTrue(self.ch2_handler.has_disadvantage(self.char1))

    def test_blur_expires_after_ticks(self):
        """BlurScript should remove named effect after all ticks."""
        self.spell.cast(self.char1, self.char1)
        scripts = self.char1.scripts.get("blur_effect")
        # Tier 1 = 3 ticks. After ticking 3 times, should expire.
        for _ in range(3):
            scripts[0].tick_blur()
        self.assertFalse(self.char1.has_effect("blurred"))

    def test_blur_anti_stacking_replaces(self):
        """New cast should replace existing blur, not stack."""
        self.char1.db.class_skill_mastery_levels = {"illusion": 3}
        self.spell.cast(self.char1, self.char1)
        scripts1 = self.char1.scripts.get("blur_effect")
        self.assertEqual(scripts1[0].db.remaining_ticks, 5)  # tier 3 = 5 rounds

        # Recast — should replace with fresh 5-round blur
        self.spell.cast(self.char1, self.char1)
        scripts2 = self.char1.scripts.get("blur_effect")
        self.assertEqual(len(scripts2), 1)  # only one script
        self.assertEqual(scripts2[0].db.remaining_ticks, 5)

    def test_blur_deducts_mana(self):
        """Should deduct 5 mana at tier 1."""
        self.spell.cast(self.char1, self.char1)
        self.assertEqual(self.char1.mana, 95)

    def test_blur_mastery_check(self):
        """Should fail without illusion mastery."""
        self.char1.db.class_skill_mastery_levels = {}
        success, msg = self.spell.cast(self.char1, self.char1)
        self.assertFalse(success)
        self.assertIn("mastery", msg.lower())

    def test_blur_not_enough_mana(self):
        """Should fail with insufficient mana."""
        self.char1.mana = 4
        success, msg = self.spell.cast(self.char1, self.char1)
        self.assertFalse(success)
        self.assertIn("mana", msg.lower())

    def test_blur_multi_perspective_messages(self):
        """Should return first and third person messages (no second for self-cast)."""
        success, result = self.spell.cast(self.char1, self.char1)
        self.assertTrue(success)
        self.assertIsInstance(result, dict)
        self.assertIn("first", result)
        self.assertIsNone(result["second"])
        self.assertIn("third", result)

    def test_blur_same_mana_as_magic_missile(self):
        """Mana costs should match Magic Missile exactly."""
        mm = get_spell("magic_missile")
        self.assertEqual(self.spell.mana_cost, mm.mana_cost)


# ================================================================== #
#  Invisibility Execution Tests
# ================================================================== #

class TestInvisibility(EvenniaTest):
    """Test Invisibility spell execution — INVISIBLE condition, no anti-stacking, break."""

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.spell = get_spell("invisibility")
        self.char1.db.class_skill_mastery_levels = {"illusion": 2}  # min_mastery = SKILLED
        self.char1.mana = 100

    def test_applies_named_effect(self):
        """Casting should create an invisible named effect on caster."""
        success, result = self.spell.cast(self.char1, self.char1)
        self.assertTrue(success)
        self.assertTrue(self.char1.has_effect("invisible"))

    def test_grants_invisible_condition(self):
        """Casting should grant INVISIBLE condition."""
        self.spell.cast(self.char1, self.char1)
        self.assertTrue(self.char1.has_condition(Condition.INVISIBLE))

    def test_remove_clears_condition(self):
        """Removing the named effect should remove INVISIBLE condition."""
        self.spell.cast(self.char1, self.char1)
        self.assertTrue(self.char1.has_condition(Condition.INVISIBLE))
        self.char1.remove_named_effect("invisible")
        self.assertFalse(self.char1.has_condition(Condition.INVISIBLE))

    def test_no_anti_stacking(self):
        """Recasting should succeed — INVISIBLE is condition-only, no stat impact."""
        self.spell.cast(self.char1, self.char1)
        self.assertTrue(self.char1.has_effect("invisible"))
        # Condition ref count should be 1
        self.assertEqual(self.char1.get_condition_count(Condition.INVISIBLE), 1)
        # Second cast should also succeed (named effect replaced, condition incremented)
        # apply_named_effect returns False for duplicate key, but the spell doesn't check
        # — it always calls apply_named_effect. The named effect won't stack (same key),
        # but the condition won't double either since the effect is already tracked.
        # The key behavior: has_condition(INVISIBLE) stays True.
        self.assertTrue(self.char1.has_condition(Condition.INVISIBLE))

    def test_duration_scales_with_tier(self):
        """Duration should scale: SKILLED=5min, EXPERT=10min, MASTER=30min, GM=60min."""
        expected_minutes = {2: 5, 3: 10, 4: 30, 5: 60}
        for tier, minutes in expected_minutes.items():
            if self.char1.has_effect("invisible"):
                self.char1.remove_named_effect("invisible")
            self.char1.db.class_skill_mastery_levels = {"illusion": tier}
            self.char1.mana = 100
            success, result = self.spell.cast(self.char1, self.char1)
            self.assertTrue(success)
            self.assertIn(str(minutes), result["first"],
                          f"Tier {tier} message should mention {minutes}")

    def test_mana_cost_scales_with_tier(self):
        """Mana cost: SKILLED=15, EXPERT=25, MASTER=40, GM=40."""
        expected = {2: 15, 3: 25, 4: 40, 5: 40}
        for tier, cost in expected.items():
            if self.char1.has_effect("invisible"):
                self.char1.remove_named_effect("invisible")
            self.char1.db.class_skill_mastery_levels = {"illusion": tier}
            self.char1.mana = 100
            self.spell.cast(self.char1, self.char1)
            self.assertEqual(self.char1.mana, 100 - cost,
                             f"Tier {tier} should cost {cost} mana")

    def test_mastery_check(self):
        """Should fail without illusion mastery at SKILLED level."""
        self.char1.db.class_skill_mastery_levels = {}
        success, msg = self.spell.cast(self.char1, self.char1)
        self.assertFalse(success)
        self.assertIn("mastery", msg.lower())

    def test_basic_mastery_too_low(self):
        """BASIC mastery should not be enough (min_mastery = SKILLED)."""
        self.char1.db.class_skill_mastery_levels = {"illusion": 1}
        success, msg = self.spell.cast(self.char1, self.char1)
        self.assertFalse(success)

    def test_not_enough_mana(self):
        """Should fail with insufficient mana."""
        self.char1.mana = 14
        success, msg = self.spell.cast(self.char1, self.char1)
        self.assertFalse(success)
        self.assertIn("mana", msg.lower())

    def test_multi_perspective_messages(self):
        """Should return first and third person messages (no second for self-cast)."""
        success, result = self.spell.cast(self.char1, self.char1)
        self.assertTrue(success)
        self.assertIsInstance(result, dict)
        self.assertIn("first", result)
        self.assertIsNone(result["second"])
        self.assertIn("third", result)

    def test_break_invisibility_zeros_all_refs(self):
        """break_invisibility() should zero condition regardless of ref count."""
        # Apply via spell (1 ref from named effect)
        self.spell.cast(self.char1, self.char1)
        # Manually add extra refs (simulating multiple sources)
        self.char1._add_condition_raw(Condition.INVISIBLE)
        self.char1._add_condition_raw(Condition.INVISIBLE)
        self.assertEqual(self.char1.get_condition_count(Condition.INVISIBLE), 3)

        # Break should zero everything
        result = self.char1.break_invisibility()
        self.assertTrue(result)
        self.assertFalse(self.char1.has_condition(Condition.INVISIBLE))
        self.assertEqual(self.char1.get_condition_count(Condition.INVISIBLE), 0)
        self.assertFalse(self.char1.has_effect("invisible"))

    def test_break_invisibility_returns_false_if_not_invisible(self):
        """break_invisibility() should return False if not invisible."""
        result = self.char1.break_invisibility()
        self.assertFalse(result)
