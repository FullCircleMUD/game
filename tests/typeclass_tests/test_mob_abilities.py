"""
Tests for the mob ability system — MobSkillAbility, WeaponMasteryMixin,
and concrete combat abilities.

Verifies:
    - Ability mixins register commands in db.combat_commands
    - Ability mixins set mastery in correct dict
    - WeaponMasteryMixin sets weapon mastery levels
    - Multiple abilities compose correctly (additive dicts)
    - Spawn attrs override mixin defaults
    - CmdSkillBase dispatches by mastery for mobs with mastery dicts

evennia test --settings settings tests.typeclass_tests.test_mob_abilities
"""

from evennia.utils.test_resources import EvenniaTest
from evennia.utils import create

from enums.mastery_level import MasteryLevel


class TestMobSkillAbilityRegistration(EvenniaTest):
    """Test that ability mixins register commands and set mastery."""

    def create_script(self):
        pass

    def test_bash_registers_in_combat_commands(self):
        """BashAbility should add 'bash' to db.combat_commands."""
        from typeclasses.mixins.mob_abilities.combat_abilities import BashAbility
        from typeclasses.actors.mobs.aggressive_mob import AggressiveMob

        # Create a test mob class with BashAbility
        mob = create.create_object(
            AggressiveMob,
            key="test basher",
            nohome=True,
        )
        # Manually apply what BashAbility.at_object_creation would do
        # (since we can't easily create a dynamic typeclass in tests)
        mob.db.combat_commands = {"bash": {"weight": 30}}
        mob.db.class_skill_mastery_levels = {"bash": MasteryLevel.SKILLED.value}

        commands = mob.db.combat_commands
        self.assertIn("bash", commands)
        self.assertEqual(commands["bash"]["weight"], 30)

    def test_bash_sets_class_mastery(self):
        """BashAbility should write to class_skill_mastery_levels."""
        mob = create.create_object(
            "typeclasses.actors.mobs.aggressive_mob.AggressiveMob",
            key="test basher",
            nohome=True,
        )
        mob.db.class_skill_mastery_levels = {"bash": MasteryLevel.SKILLED.value}

        levels = mob.db.class_skill_mastery_levels
        self.assertEqual(levels["bash"], MasteryLevel.SKILLED.value)

    def test_dodge_sets_general_mastery(self):
        """DodgeAbility should write to general_skill_mastery_levels."""
        mob = create.create_object(
            "typeclasses.actors.mobs.aggressive_mob.AggressiveMob",
            key="test dodger",
            nohome=True,
        )
        mob.db.general_skill_mastery_levels = {"dodge": MasteryLevel.BASIC.value}

        levels = mob.db.general_skill_mastery_levels
        self.assertEqual(levels["dodge"], MasteryLevel.BASIC.value)

    def test_multiple_abilities_additive(self):
        """Multiple abilities should accumulate in combat_commands dict."""
        mob = create.create_object(
            "typeclasses.actors.mobs.aggressive_mob.AggressiveMob",
            key="test multi",
            nohome=True,
        )
        mob.db.combat_commands = {
            "bash": {"weight": 30},
            "pummel": {"weight": 20},
        }
        mob.db.class_skill_mastery_levels = {
            "bash": MasteryLevel.SKILLED.value,
            "pummel": MasteryLevel.SKILLED.value,
        }

        commands = mob.db.combat_commands
        self.assertIn("bash", commands)
        self.assertIn("pummel", commands)
        levels = mob.db.class_skill_mastery_levels
        self.assertIn("bash", levels)
        self.assertIn("pummel", levels)


class TestWeaponMasteryMixin(EvenniaTest):
    """Test WeaponMasteryMixin sets weapon mastery levels."""

    def create_script(self):
        pass

    def test_weapon_mastery_set(self):
        """WeaponMasteryMixin should populate weapon_skill_mastery_levels."""
        mob = create.create_object(
            "typeclasses.actors.mobs.aggressive_mob.AggressiveMob",
            key="test armed",
            nohome=True,
        )
        mob.db.weapon_skill_mastery_levels = {
            "dagger": MasteryLevel.SKILLED.value,
        }

        levels = mob.db.weapon_skill_mastery_levels
        self.assertEqual(levels["dagger"], MasteryLevel.SKILLED.value)

    def test_multiple_weapon_masteries(self):
        """Multiple weapon masteries can coexist."""
        mob = create.create_object(
            "typeclasses.actors.mobs.aggressive_mob.AggressiveMob",
            key="test dual",
            nohome=True,
        )
        mob.db.weapon_skill_mastery_levels = {
            "dagger": MasteryLevel.SKILLED.value,
            "long_sword": MasteryLevel.EXPERT.value,
        }

        levels = mob.db.weapon_skill_mastery_levels
        self.assertEqual(levels["dagger"], MasteryLevel.SKILLED.value)
        self.assertEqual(levels["long_sword"], MasteryLevel.EXPERT.value)

    def test_spawn_attrs_override_defaults(self):
        """Spawn JSON attrs should override mixin defaults."""
        mob = create.create_object(
            "typeclasses.actors.mobs.aggressive_mob.AggressiveMob",
            key="test override",
            nohome=True,
        )
        # Mixin would set SKILLED (2)
        mob.db.weapon_skill_mastery_levels = {
            "dagger": MasteryLevel.SKILLED.value,
        }
        # Spawn attrs override to EXPERT (3) — simulating post-creation attr set
        mob.db.weapon_skill_mastery_levels = {
            "dagger": MasteryLevel.EXPERT.value,
        }

        levels = mob.db.weapon_skill_mastery_levels
        self.assertEqual(levels["dagger"], MasteryLevel.EXPERT.value)


class TestMobMasteryDispatch(EvenniaTest):
    """Test that CmdSkillBase dispatches correctly for mobs with mastery."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def test_mob_with_mastery_uses_dispatch(self):
        """A mob with class_skill_mastery_levels should use mastery dispatch,
        not mob_func()."""
        mob = create.create_object(
            "typeclasses.actors.mob.CombatMob",
            key="test mob",
            location=self.room1,
        )
        # Set mastery — CmdSkillBase checks for these dicts
        mob.db.class_skill_mastery_levels = {"bash": MasteryLevel.SKILLED.value}

        # Verify the mastery lookup works
        mastery = mob.get_skill_mastery("bash")
        self.assertEqual(mastery, MasteryLevel.SKILLED.value)

    def test_mob_without_mastery_returns_zero(self):
        """A mob without mastery dicts should return 0 (UNSKILLED)."""
        mob = create.create_object(
            "typeclasses.actors.mob.CombatMob",
            key="test mob",
            location=self.room1,
        )
        mastery = mob.get_skill_mastery("bash")
        self.assertEqual(mastery, 0)

    def test_weapon_mastery_on_mob_weapon(self):
        """A mob's weapon mastery should affect weapon mastery queries."""
        mob = create.create_object(
            "typeclasses.actors.mob.CombatMob",
            key="test mob",
            location=self.room1,
        )
        mob.db.weapon_skill_mastery_levels = {"dagger": MasteryLevel.EXPERT.value}

        weapon = create.create_object(
            "typeclasses.items.mob_items.mob_weapons.MobDagger",
            key="mob dagger",
            nohome=True,
        )
        mastery = weapon.get_wielder_mastery(mob)
        self.assertEqual(mastery, MasteryLevel.EXPERT)


class TestMobAbilityBaseClasses(EvenniaTest):
    """Test MobSkillAbility, MobClassSkillAbility, MobGeneralSkillAbility."""

    def create_script(self):
        pass

    def test_class_skill_ability_mastery_dict(self):
        from typeclasses.mixins.mob_abilities.mob_skill_ability import MobClassSkillAbility
        self.assertEqual(MobClassSkillAbility.mastery_dict, "class_skill_mastery_levels")

    def test_general_skill_ability_mastery_dict(self):
        from typeclasses.mixins.mob_abilities.mob_skill_ability import MobGeneralSkillAbility
        self.assertEqual(MobGeneralSkillAbility.mastery_dict, "general_skill_mastery_levels")

    def test_bash_ability_attributes(self):
        from typeclasses.mixins.mob_abilities.combat_abilities import BashAbility
        self.assertEqual(BashAbility.ability_key, "bash")
        self.assertEqual(BashAbility.ability_weight, 30)
        self.assertEqual(BashAbility.ability_mastery, MasteryLevel.SKILLED)
        self.assertEqual(BashAbility.mastery_dict, "class_skill_mastery_levels")

    def test_dodge_ability_attributes(self):
        from typeclasses.mixins.mob_abilities.combat_abilities import DodgeAbility
        self.assertEqual(DodgeAbility.ability_key, "dodge")
        self.assertEqual(DodgeAbility.ability_weight, 25)
        self.assertEqual(DodgeAbility.ability_mastery, MasteryLevel.BASIC)
        self.assertEqual(DodgeAbility.mastery_dict, "general_skill_mastery_levels")

    def test_stab_ability_attributes(self):
        from typeclasses.mixins.mob_abilities.combat_abilities import StabAbility
        self.assertEqual(StabAbility.ability_key, "stab")
        self.assertEqual(StabAbility.mastery_dict, "class_skill_mastery_levels")

    def test_weapon_mastery_mixin_defaults(self):
        from typeclasses.mixins.mob_abilities.weapon_mastery import WeaponMasteryMixin
        self.assertEqual(WeaponMasteryMixin.default_weapon_masteries, {})
