"""
CombatCompanionMixin — gives a pet combat capability.

Compose onto any BasePet subclass that should fight. Provides CombatMixin
(initiate_attack, enter_combat, exit_combat, CmdSetMobCombat injection)
plus pet-specific combat AI.

Usage:
    class WarDog(CombatCompanionMixin, BasePet):
        damage_dice = AttributeProperty("1d6")
        attack_message = AttributeProperty("bites at")

Non-combat pets (mule, cat) simply don't compose this mixin.
"""

from evennia.typeclasses.attributes import AttributeProperty

from typeclasses.mixins.combat_mixin import CombatMixin


class CombatCompanionMixin(CombatMixin):
    """
    Mixin that makes a pet capable of combat.

    Inherits CombatMixin for combat handler access, initiate_attack(),
    enter_combat(), and CmdSetMobCombat injection.

    Adds pet-specific AI: keep attacking current target, no complex
    state machine needed.
    """

    # ── Combat stats (override in subclasses) ──
    damage_dice = AttributeProperty("1d4")
    attack_message = AttributeProperty("attacks")
    attack_delay_min = AttributeProperty(3)
    attack_delay_max = AttributeProperty(5)

    # Initiative speed for pets — same scale as mobs (0-4)
    initiative_speed = AttributeProperty(1)

    # ── Aggro ──
    is_aggressive_to_players = AttributeProperty(False)  # pets don't aggro PCs

    def at_combat_tick(self, handler):
        """Simple pet combat AI — just keep attacking."""
        # Pet doesn't make tactical decisions — it just attacks.
        # The handler's auto_attack_first_enemy handles targeting.
        pass

    def at_new_arrival(self, arriving_obj):
        """
        React to new arrivals. Combat pets could aggro hostiles here.
        Default: do nothing (wait for owner's command or group combat pull).
        """
        pass
