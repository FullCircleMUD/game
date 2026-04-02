"""
BaseNPC — base class for all non-player actors.

Combat vs service is behavioral, not structural. All NPCs share the full
BaseActor infrastructure (ability scores, HP/mana/move, conditions, damage
resistance, combat stats, effect system). Behavioral flags determine role.

Includes FungibleInventoryMixin so all NPCs and mobs can carry gold and
resources (for looting, pickpocketing, shopkeeper trade, etc.).

Subclasses:
    TrainerNPC — trains skills, sells recipes
    GuildmasterNPC — multiclass management, level advancement
    ShopkeeperNPC — buys and sells items (AMM integration)
    CombatMob — killable enemies with AI, loot, respawn
"""

from evennia import CmdSet
from evennia.typeclasses.attributes import AttributeProperty

from typeclasses.actors.base_actor import BaseActor


class _EmptyNPCCmdSet(CmdSet):
    """Empty default CmdSet for NPCs.

    Replaces the inherited character CmdSet (stats, skills, look, etc.)
    so player commands don't leak to nearby characters via call:true().
    Subclass role CmdSets (TrainerCmdSet, etc.) are added separately.
    """

    key = "EmptyNPCCmdSet"

    def at_cmdset_creation(self):
        pass


class BaseNPC(BaseActor):
    """
    Base class for all non-player actors.

    Inherits the full combat/condition/effect infrastructure from BaseActor.
    FungibleInventoryMixin is NOT included here — only CombatMob needs it
    (for loot). Service NPCs transact via AMMs/training mechanisms, not
    direct gold/resource inventory. Compose FungibleInventoryMixin into
    individual NPCs that need it (e.g. pickpocketable NPCs).
    """

    is_pc = False  # Evennia convention — marks as non-player

    # ── Identity ──
    level = AttributeProperty(1)            # NPC level (preset, not earned)
    is_immortal = AttributeProperty(True)   # Service NPCs can't be killed

    # ── Spawn/persistence ──
    spawn_room_id = AttributeProperty(None)  # dbref of home room for respawn
    is_unique = AttributeProperty(True)      # unique NPCs don't respawn

    def at_object_creation(self):
        super().at_object_creation()
        # Mixin inits (at_fungible_init, at_wearslots_init, etc.) are
        # handled automatically by BaseActor.at_object_creation() via
        # hasattr detection — no explicit calls needed here.
        # DefaultCharacter doesn't set call:true() — without it, Evennia
        # won't merge this NPC's CmdSet into nearby characters' commands.
        self.locks.add("call:true()")
        # Replace the inherited character CmdSet with an empty one so player
        # commands (stats, skills, look, etc.) don't leak to nearby chars.
        self.cmdset.add_default(_EmptyNPCCmdSet)

    def get_level(self):
        """Return this NPC's combat level."""
        return self.level

    def die(self, cause="unknown", killer=None):
        """Immortal NPCs cannot die. Combat mobs override this."""
        if self.is_immortal:
            self.hp = max(1, self.hp_max)  # shrug it off
            return
        super().die(cause, killer=killer)
