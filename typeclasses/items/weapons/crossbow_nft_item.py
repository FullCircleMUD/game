"""
CrossbowNFTItem — crossbow-type missile weapons with knockback mastery.

Crossbows are heavy, mechanical ranged weapons. Slow to reload but
devastating on impact. No extra attacks — compensated by the chance
to knock targets PRONE, granting advantage to all attackers. The
anti-tank ranged option: one good bolt can turn a fight.

Mastery progression:
    UNSKILLED: -2 hit, no knockback, 0 extra attacks
    BASIC:      0 hit, no knockback, 0 extra attacks
    SKILLED:   +2 hit, 15% knockback (1 round prone), 0 extra attacks
    EXPERT:    +4 hit, 20% knockback (1 round prone), 0 extra attacks
    MASTER:    +6 hit, 25% knockback (1 round prone), 0 extra attacks
    GM:        +8 hit, 30% knockback (1 round prone), 0 extra attacks

Knockback mechanic:
    On hit → roll d100 vs mastery-scaled chance.
    Success → target is knocked PRONE (action denial + advantage for attackers).
    HUGE+ targets are immune (too massive to knock down).
    Anti-stacking: can't re-prone already prone target.
"""

from evennia.typeclasses.attributes import AttributeProperty

from combat.combat_utils import get_actor_size
from enums.actor_size import ActorSize
from enums.character_class import CharacterClass
from enums.mastery_level import MasteryLevel
from typeclasses.items.weapons.weapon_nft_item import WeaponNFTItem
from utils.dice_roller import dice

# Knockback chance % by mastery
_CROSSBOW_KNOCKBACK = {
    MasteryLevel.UNSKILLED: 0,
    MasteryLevel.BASIC: 0,
    MasteryLevel.SKILLED: 15,
    MasteryLevel.EXPERT: 20,
    MasteryLevel.MASTER: 25,
    MasteryLevel.GRANDMASTER: 30,
}

# Sizes immune to knockback
_KNOCKBACK_IMMUNE_SIZES = {ActorSize.HUGE, ActorSize.GARGANTUAN}


class CrossbowNFTItem(WeaponNFTItem):
    """
    Crossbow weapons — missile, knockback mastery path. No extra attacks.
    """

    weapon_type_key = "crossbow"
    weapon_type = AttributeProperty("missile")
    range = AttributeProperty(1)
    excluded_classes = AttributeProperty([
        CharacterClass.MAGE, CharacterClass.CLERIC,
    ])

    def at_object_creation(self):
        super().at_object_creation()
        self.tags.add("crossbow", category="weapon_type")

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
        chance = _CROSSBOW_KNOCKBACK.get(mastery, 0)
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
        applied = target.apply_prone(1, source=wielder)

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
