"""
Tests for hostile-spell integration with the combat round system.

Covers:
    - Default entry policy (actor_hostile aggros, others don't)
    - Per-spell override of should_enter_combat
    - Shared skill_cooldown gates spell-to-spell spam
    - Shared skill_cooldown gates cross-action (spell then bash)
    - Tier-based cooldown defaults from min_mastery.value
    - Explicit cooldown=0 bypass (reactive / buff spells)
    - Out-of-combat casting is free (no handler, no cooldown)
    - AoE enters combat on every affected target

evennia test --settings settings tests.spell_tests.test_spell_combat_integration
"""

from evennia.utils.test_resources import EvenniaTest

from enums.mastery_level import MasteryLevel
from enums.skills_enum import skills
from world.spells.base_spell import Spell
from world.spells.registry import get_spell


class _SpellCombatBase(EvenniaTest):
    """Shared setup: real combat-enabled room, live char1 and char2."""

    character_typeclass = "typeclasses.actors.character.FCMCharacter"
    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.room1.allow_combat = True
        for char in (self.char1, self.char2):
            char.hp = 100
            char.hp_max = 100
            char.mana = 200
            char.move = 100

    def tearDown(self):
        for char in (self.char1, self.char2):
            handlers = char.scripts.get("combat_handler")
            if handlers:
                for h in handlers:
                    h.stop()
                    h.delete()
        super().tearDown()

    def _set_mastery(self, char, school_key, level):
        if not char.db.class_skill_mastery_levels:
            char.db.class_skill_mastery_levels = {}
        char.db.class_skill_mastery_levels[school_key] = {
            "mastery": level.value,
            "classes": ["Mage"],
        }

    def _handler(self, char):
        handlers = char.scripts.get("combat_handler")
        return handlers[0] if handlers else None


# ================================================================== #
#  Combat Entry Policy
# ================================================================== #


class TestCombatEntryPolicy(_SpellCombatBase):
    """A hostile spell cast on a live target enters combat; non-hostile doesn't."""

    def test_hostile_spell_enters_combat(self):
        """Magic Missile (actor_hostile) creates handlers on both sides."""
        self._set_mastery(self.char1, "evocation", MasteryLevel.BASIC)
        spell = get_spell("magic_missile")
        success, _ = spell.cast(self.char1, self.char2)
        self.assertTrue(success)
        self.assertIsNotNone(self._handler(self.char1))
        self.assertIsNotNone(self._handler(self.char2))

    def test_self_target_spell_does_not_enter_combat(self):
        """Shield (target_type=self) creates no handler."""
        self._set_mastery(self.char1, "abjuration", MasteryLevel.BASIC)
        spell = get_spell("shield")
        spell.cast(self.char1, self.char1)
        self.assertIsNone(self._handler(self.char1))
        self.assertIsNone(self._handler(self.char2))

    def test_friendly_spell_does_not_enter_combat(self):
        """Bless (target_type=actor_friendly) creates no handler."""
        self._set_mastery(self.char1, "divine_protection", MasteryLevel.BASIC)
        spell = get_spell("bless")
        spell.cast(self.char1, self.char2)
        self.assertIsNone(self._handler(self.char1))
        self.assertIsNone(self._handler(self.char2))

# ================================================================== #
#  Per-spell Override
# ================================================================== #


class _DummyCharm(Spell):
    """Test-only spell: hostile, but only enters combat when resisted."""
    key = "test_charm"
    name = "Test Charm"
    school = skills.DIVINE_DOMINION
    min_mastery = MasteryLevel.BASIC
    mana_cost = {1: 1}
    target_type = "actor_hostile"
    cooldown = 0

    _resist_next = True

    def _execute(self, caster, target, **kwargs):
        # Flag the outcome in the result dict so should_enter_combat can branch.
        return True, {
            "first": "ok",
            "second": "ok",
            "third": "ok",
            "resisted": self._resist_next,
        }

    def should_enter_combat(self, caster, target, result):
        return bool(result.get("resisted"))


class TestShouldEnterCombatOverride(_SpellCombatBase):
    """Per-spell overrides can condition combat entry on the cast result."""

    def setUp(self):
        super().setUp()
        self._set_mastery(self.char1, "divine_dominion", MasteryLevel.BASIC)
        self.spell = _DummyCharm()

    def test_override_aggros_on_resist(self):
        self.spell._resist_next = True
        self.spell.cast(self.char1, self.char2)
        self.assertIsNotNone(self._handler(self.char2))

    def test_override_does_not_aggro_on_success(self):
        self.spell._resist_next = False
        self.spell.cast(self.char1, self.char2)
        self.assertIsNone(self._handler(self.char2))


# ================================================================== #
#  Shared Cooldown Gate
# ================================================================== #


class TestSharedCooldownGate(_SpellCombatBase):
    """Casting sets handler.skill_cooldown, which blocks further specials."""

    def setUp(self):
        super().setUp()
        self._set_mastery(self.char1, "evocation", MasteryLevel.BASIC)

    def test_basic_cast_sets_cooldown_to_one(self):
        get_spell("magic_missile").cast(self.char1, self.char2)
        self.assertEqual(self._handler(self.char1).skill_cooldown, 1)

    def test_second_hostile_cast_blocked_same_round(self):
        """Fire magic_missile, then try another hostile cast — should be blocked."""
        first = get_spell("magic_missile")
        first.cast(self.char1, self.char2)
        hp_before = self.char2.hp

        # Second cast should be rejected due to shared cooldown.
        success, result = first.cast(self.char1, self.char2)
        self.assertFalse(success)
        self.assertIn("cooldown", str(result).lower())
        # Target HP unchanged (no damage from rejected cast).
        self.assertEqual(self.char2.hp, hp_before)

    def test_cooldown_releases_after_tick(self):
        """One tick decrement on the handler lets the caster fire again."""
        spell = get_spell("magic_missile")
        spell.cast(self.char1, self.char2)
        handler = self._handler(self.char1)
        self.assertEqual(handler.skill_cooldown, 1)

        # Simulate one tick of decrement.
        handler.skill_cooldown = max(0, handler.skill_cooldown - 1)

        success, _ = spell.cast(self.char1, self.char2)
        self.assertTrue(success)


# ================================================================== #
#  Tier Gradient
# ================================================================== #


class TestTierGradient(_SpellCombatBase):
    """Default cooldown equals min_mastery.value (floor 1)."""

    def test_basic_tier_cooldown_is_one(self):
        self._set_mastery(self.char1, "evocation", MasteryLevel.BASIC)
        # magic_missile is BASIC (tier 1); no explicit cooldown override.
        spell = get_spell("magic_missile")
        self.assertEqual(spell.get_cooldown(), 1)

    def test_expert_tier_cooldown_is_three(self):
        # Fireball is EXPERT (tier 3) with no explicit cooldown.
        spell = get_spell("fireball")
        self.assertEqual(spell.get_cooldown(), 3)

    def test_expert_cast_locks_handler_for_three_rounds(self):
        self._set_mastery(self.char1, "evocation", MasteryLevel.EXPERT)
        self.char1.mana = 500
        spell = get_spell("fireball")
        spell.cast(self.char1, self.char2)
        self.assertEqual(self._handler(self.char1).skill_cooldown, 3)


# ================================================================== #
#  Cooldown Override (cooldown = 0)
# ================================================================== #


class TestCooldownOverride(_SpellCombatBase):
    """Reactive/buff spells with explicit cooldown=0 bypass pacing."""

    def test_shield_cooldown_is_zero(self):
        spell = get_spell("shield")
        self.assertEqual(spell.get_cooldown(), 0)

    def test_smite_cooldown_is_zero(self):
        spell = get_spell("smite")
        self.assertEqual(spell.get_cooldown(), 0)


# ================================================================== #
#  Out-of-combat Freedom
# ================================================================== #


class TestOutOfCombatFreedom(_SpellCombatBase):
    """With no handler, is_on_cooldown is always (False, 0)."""

    def test_is_on_cooldown_returns_false_without_handler(self):
        spell = get_spell("magic_missile")
        on_cd, remaining = spell.is_on_cooldown(self.char1)
        self.assertFalse(on_cd)
        self.assertEqual(remaining, 0)

    def test_apply_cooldown_noop_without_handler(self):
        spell = get_spell("magic_missile")
        spell.apply_cooldown(self.char1)  # Should not raise.
        self.assertIsNone(self._handler(self.char1))

    def test_utility_spell_cast_repeatedly_without_handler(self):
        """A self-target utility spell creates no handler and is never gated."""

        class _DummyBuff(Spell):
            key = "test_buff"
            name = "Test Buff"
            school = skills.ABJURATION
            min_mastery = MasteryLevel.BASIC
            mana_cost = {1: 1}
            target_type = "self"
            cooldown = 0

            def _execute(self, caster, target, **kwargs):
                return True, {"first": "ok", "second": None, "third": None}

        self._set_mastery(self.char1, "abjuration", MasteryLevel.BASIC)
        spell = _DummyBuff()
        first_ok, _ = spell.cast(self.char1, self.char1)
        second_ok, _ = spell.cast(self.char1, self.char1)
        self.assertTrue(first_ok)
        self.assertTrue(second_ok)
        self.assertIsNone(self._handler(self.char1))


# ================================================================== #
#  AoE Entry
# ================================================================== #


class TestAoECombatEntry(_SpellCombatBase):
    """Fireball pulls every affected target into combat."""

    def test_aoe_enters_combat_on_primary_and_secondaries(self):
        from evennia.utils import create
        third = create.create_object(
            self.character_typeclass,
            key="goblin",
            location=self.room1,
        )
        try:
            third.hp = 100
            third.hp_max = 100
            self._set_mastery(self.char1, "evocation", MasteryLevel.EXPERT)
            self.char1.mana = 500

            spell = get_spell("fireball")
            spell.cast(self.char1, self.char2, secondaries=[third])

            self.assertIsNotNone(self._handler(self.char1))
            self.assertIsNotNone(self._handler(self.char2))
            self.assertIsNotNone(
                third.scripts.get("combat_handler"),
                "Secondary AoE target should be pulled into combat",
            )
        finally:
            handlers = third.scripts.get("combat_handler")
            if handlers:
                for h in handlers:
                    h.stop()
                    h.delete()
            third.delete()
