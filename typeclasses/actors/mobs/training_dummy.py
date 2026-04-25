"""
TrainingDummy — a weak training target for the tutorial.

Fights back gently (1d2 damage) so new players learn about HP loss.
Respawns quickly. Does not wander or react to arrivals.
"""

from evennia.typeclasses.attributes import AttributeProperty

from typeclasses.actors.mob import CombatMob


class TrainingDummy(CombatMob):
    """A straw-stuffed training dummy that fights back weakly."""

    room_description = AttributeProperty(
        "stands upright on a battered post, straw bristling from canvas patched with countless practice cuts."
    )

    # ── Stats ──
    hp = AttributeProperty(20)
    base_hp_max = AttributeProperty(20)
    hp_max = AttributeProperty(20)
    base_strength = AttributeProperty(6)
    strength = AttributeProperty(6)
    base_dexterity = AttributeProperty(6)
    dexterity = AttributeProperty(6)
    base_constitution = AttributeProperty(10)
    constitution = AttributeProperty(10)
    base_armor_class = AttributeProperty(8)
    armor_class = AttributeProperty(8)
    level = AttributeProperty(1)

    # ── Combat ──
    damage_dice = AttributeProperty("1d2")
    attack_message = AttributeProperty("swings at")
    attack_delay_min = AttributeProperty(4)
    attack_delay_max = AttributeProperty(6)

    # ── Behavior ──
    is_aggressive_to_players = AttributeProperty(False)

    # ── AI ──
    ai_tick_interval = AttributeProperty(30)

    def ai_wander(self):
        """Training dummies don't move."""
        pass

    def at_new_arrival(self, arriving_obj):
        """Training dummies don't react to arrivals."""
        pass
