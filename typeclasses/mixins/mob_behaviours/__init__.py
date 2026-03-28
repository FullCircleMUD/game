"""
Reusable mob behavior mixins.

Plug-and-play behaviors that can be composed into any AggressiveMob
subclass via multiple inheritance.
"""

from typeclasses.mixins.mob_behaviours.pack_courage_mixin import PackCourageMixin
from typeclasses.mixins.mob_behaviours.rampage_mixin import RampageMixin
from typeclasses.mixins.mob_behaviours.tactical_dodge_mixin import TacticalDodgeMixin

__all__ = [
    "PackCourageMixin",
    "RampageMixin",
    "TacticalDodgeMixin",
]
