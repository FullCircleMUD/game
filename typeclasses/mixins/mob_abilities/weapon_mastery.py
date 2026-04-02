"""
WeaponMasteryMixin — sets weapon mastery levels on mobs.

Data-only mixin — no commands, no AI registry. Sets weapon mastery
levels in ``db.weapon_skill_mastery_levels`` so that equipped mob
weapons scale correctly through the mastery system.

Defaults are set via ``default_weapon_masteries`` on the class.
Spawn JSON ``attrs`` can override per-instance.

Usage::

    class KoboldWarrior(WeaponMasteryMixin, HumanoidWearslotsMixin, AggressiveMob):
        default_weapon_masteries = {"dagger": 2}  # SKILLED
"""

from enums.mastery_level import MasteryLevel  # noqa: F401 — convenience for importers


class WeaponMasteryMixin:
    """
    Sets weapon mastery from class defaults. Overridable via spawn attrs.

    Attributes:
        default_weapon_masteries: dict mapping weapon_type_key to mastery
            int value. E.g. ``{"dagger": 2, "long_sword": 3}``.
    """

    default_weapon_masteries = {}

    def at_object_creation(self):
        super().at_object_creation()
        if self.default_weapon_masteries:
            levels = self.db.weapon_skill_mastery_levels or {}
            levels.update(self.default_weapon_masteries)
            self.db.weapon_skill_mastery_levels = levels
