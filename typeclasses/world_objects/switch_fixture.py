"""
SwitchFixture — a WorldFixture that can be toggled on/off.

Combines SwitchMixin (toggle state, verbs, hooks) with WorldFixture
(immovable, non-NFT, hidden/invisible support). Used for levers,
buttons, valves, and anything else players interact with to trigger
an effect.

Override at_activate/at_deactivate in subclasses or set them
dynamically in zone builders for custom effects.
"""

from typeclasses.mixins.switch_mixin import SwitchMixin
from typeclasses.world_objects.base_fixture import WorldFixture


class SwitchFixture(SwitchMixin, WorldFixture):
    """A WorldFixture that can be toggled on/off."""

    pass
