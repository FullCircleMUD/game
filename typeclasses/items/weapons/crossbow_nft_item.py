"""
CrossbowNFTItem — crossbow-type missile weapons with knockback mastery.

Crossbows are heavy, mechanical ranged weapons (d12 base). Slow to
reload but devastating on impact. No extra attacks — compensated by
the higher per-bolt damage and chance to knock targets PRONE. The
ranged shortsword: easier to learn, better early, surpassed by the
bow at endgame when the bow gets its second attack.

Mastery progression:
    UNSKILLED: -2 hit, no knockback
    BASIC:      0 hit, no knockback
    SKILLED:   +2 hit, 15% knockback (1 round prone)
    EXPERT:    +4 hit, 25% knockback (1 round prone)
    MASTER:    +6 hit, 35% knockback (1 round prone)
    GM:        +8 hit, 40% knockback (2 rounds prone)

Knockback mechanic:
    On hit → roll d100 vs mastery-scaled chance.
    Success → target is knocked PRONE (action denial + advantage for attackers).
    HUGE+ targets are immune (too massive to knock down).
    Anti-stacking: can't re-prone already prone target.
    GM capstone: 2-round prone duration creates devastating setup windows.
"""

from evennia.typeclasses.attributes import AttributeProperty
from enums.unused_for_reference.damage_type import DamageType

from combat.combat_utils import get_actor_size
from enums.size import Size
from enums.character_class import CharacterClass
from enums.mastery_level import MasteryLevel
from typeclasses.items.weapons.weapon_nft_item import WeaponNFTItem
from utils.dice_roller import dice

# Knockback chance % by mastery
_CROSSBOW_KNOCKBACK = {
    MasteryLevel.UNSKILLED: (0, 0),
    MasteryLevel.BASIC: (0, 0),
    MasteryLevel.SKILLED: (15, 1),
    MasteryLevel.EXPERT: (25, 1),
    MasteryLevel.MASTER: (35, 1),
    MasteryLevel.GRANDMASTER: (40, 2),
}

# Sizes immune to knockback
_KNOCKBACK_IMMUNE_SIZES = {Size.HUGE, Size.GARGANTUAN}


class CrossbowMixin:
    """Crossbow weapon identity — mastery tables and overrides.

    Shared by CrossbowNFTItem and MobCrossbow. Single source of truth
    for crossbow combat mechanics (knockback).
    """

    weapon_type_key = "crossbow"
    base_damage = AttributeProperty("d12")
    damage_type = AttributeProperty(DamageType.PIERCING)
    speed = AttributeProperty(0)
    weight = AttributeProperty(3.5)
    weapon_type = AttributeProperty("missile")
    range = AttributeProperty(1)

    # ================================================================== #
    #  Mastery Overrides
    # ================================================================== #

    def get_parries_per_round(self, wielder):
        return 0

    def get_extra_attacks(self, wielder):
        return 0

    # ================================================================== #
    #  Offensive Combat Hooks
    # ================================================================== #

    def at_hit(self, wielder, target, damage, damage_type):
        """On-hit knockback check — chance to knock target prone."""
        self._try_knockback(wielder, target)
        return damage

    def _try_knockback(self, wielder, target):
        """
        Attempt to knock the target prone with a heavy bolt.

        Rolls d100 vs mastery-scaled chance. On success:
        1. Applies PRONE named effect (action denial)
        2. Grants advantage to all attackers (on-apply callback)
        HUGE+ targets are immune. Already-prone targets are skipped.
        """
        mastery = self.get_wielder_mastery(wielder)
        chance, duration = _CROSSBOW_KNOCKBACK.get(mastery, (0, 0))
        if chance <= 0:
            return

        # Size gate — HUGE+ immune
        target_size = get_actor_size(target)
        if target_size in _KNOCKBACK_IMMUNE_SIZES:
            return

        # Already prone — skip
        if hasattr(target, "has_effect") and target.has_effect("prone"):
            return

        roll = dice.roll("1d100")
        if roll > chance:
            return

        # Apply PRONE
        applied = target.apply_prone(duration, source=wielder)

        if applied:
            wielder.msg(
                f"|y*KNOCKBACK* Your crossbow bolt slams {target.key} "
                f"to the ground!|n"
            )
            target.msg(
                f"|y*KNOCKBACK* {wielder.key}'s crossbow bolt slams you "
                f"to the ground!|n"
            )
            if wielder.location:
                wielder.location.msg_contents(
                    f"|y*KNOCKBACK* {wielder.key}'s crossbow bolt slams "
                    f"{target.key} to the ground!|n",
                    exclude=[wielder, target],
                )


class CrossbowNFTItem(CrossbowMixin, WeaponNFTItem):
    """
    Crossbow weapons — missile, knockback mastery path. No extra attacks.
    """

    excluded_classes = AttributeProperty([
        CharacterClass.MAGE, CharacterClass.CLERIC,
    ])

    def at_object_creation(self):
        super().at_object_creation()
        self.tags.add("crossbow", category="weapon_type")
