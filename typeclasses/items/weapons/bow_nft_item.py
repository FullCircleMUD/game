"""
BowNFTItem — bow-type missile weapons with slowing shot + extra attacks.

Bows are the premier ranged DPS weapon. At higher mastery, arrows can
slow targets (contested DEX+mastery vs STR — an arrow in the leg slows
you down unless you can power through it). At MASTER+, the archer's
speed grants an extra attack per round.

Mastery progression:
    UNSKILLED: -2 hit, no slow, 0 extra attacks
    BASIC:      0 hit, no slow, 0 extra attacks
    SKILLED:   +2 hit, contested slow (1 round), 0 extra attacks
    EXPERT:    +4 hit, contested slow (2 rounds), 0 extra attacks
    MASTER:    +6 hit, contested slow (2 rounds), 1 extra attack
    GM:        +8 hit, contested slow (3 rounds), 1 extra attack

Slowing Shot mechanic:
    On hit → contested roll: d20 + DEX mod + mastery bonus
                             vs d20 + STR mod (target powers through).
    Archer wins → SLOWED (caps attacks at 1/round, blocks off-hand).
    Duration scales with mastery (1–3 rounds).
    Anti-stacking: new slow replaces existing slow.
"""

from evennia.typeclasses.attributes import AttributeProperty

from enums.character_class import CharacterClass
from enums.mastery_level import MasteryLevel
from typeclasses.items.weapons.weapon_nft_item import WeaponNFTItem
from utils.dice_roller import dice

# Slow duration by mastery (0 = no slow at that tier)
_BOW_SLOW_ROUNDS = {
    MasteryLevel.UNSKILLED: 0,
    MasteryLevel.BASIC: 0,
    MasteryLevel.SKILLED: 1,
    MasteryLevel.EXPERT: 2,
    MasteryLevel.MASTER: 2,
    MasteryLevel.GRANDMASTER: 3,
}

# Extra attacks per round by mastery
_BOW_EXTRA_ATTACKS = {
    MasteryLevel.UNSKILLED: 0,
    MasteryLevel.BASIC: 0,
    MasteryLevel.SKILLED: 0,
    MasteryLevel.EXPERT: 0,
    MasteryLevel.MASTER: 1,
    MasteryLevel.GRANDMASTER: 1,
}


class BowNFTItem(WeaponNFTItem):
    """
    Bow weapons — missile, slowing shot + rapid fire mastery path.
    """

    weapon_type_key = "bow"
    weapon_type = AttributeProperty("missile")
    range = AttributeProperty(1)
    excluded_classes = AttributeProperty([
        CharacterClass.MAGE, CharacterClass.CLERIC,
    ])

    def at_object_creation(self):
        super().at_object_creation()
        self.tags.add("bow", category="weapon_type")

    # ================================================================== #
    #  Mastery Overrides
    # ================================================================== #

    def get_parries_per_round(self, wielder):
        return 0

    def get_extra_attacks(self, wielder):
        mastery = self.get_wielder_mastery(wielder)
        return _BOW_EXTRA_ATTACKS.get(mastery, 0)

    # ================================================================== #
    #  Offensive Combat Hooks
    # ================================================================== #

    def at_hit(self, wielder, target, damage, damage_type):
        """On-hit slowing shot — contested check to slow target."""
        self._try_slow(wielder, target)
        return damage

    def _try_slow(self, wielder, target):
        """
        Attempt to slow the target with an arrow.

        Contested roll:
            Archer: d20 + DEX mod + mastery bonus
            Target: d20 + STR mod (powering through the arrow)
        Archer wins → SLOWED for mastery-scaled duration.
        """
        mastery = self.get_wielder_mastery(wielder)
        rounds = _BOW_SLOW_ROUNDS.get(mastery, 0)
        if rounds <= 0:
            return

        # Contested roll
        archer_roll = dice.roll("1d20")
        archer_dex = wielder.get_attribute_bonus(wielder.dexterity)
        mastery_bonus = mastery.bonus
        archer_total = archer_roll + archer_dex + mastery_bonus

        target_roll = dice.roll("1d20")
        target_str = target.get_attribute_bonus(target.strength)
        target_total = target_roll + target_str

        if archer_total <= target_total:
            # Target powers through
            return

        # Apply SLOWED
        applied = target.apply_slowed(rounds, source=wielder)

        if applied:
            s = "s" if rounds != 1 else ""
            wielder.msg(
                f"|B*SLOWING SHOT* Your arrow pins {target.key}'s movement! "
                f"({rounds} round{s})|n"
            )
            target.msg(
                f"|B*SLOWING SHOT* {wielder.key}'s arrow pins your movement! "
                f"({rounds} round{s})|n"
            )
            if wielder.location:
                wielder.location.msg_contents(
                    f"|B*SLOWING SHOT* {wielder.key}'s arrow pins "
                    f"{target.key}'s movement!|n",
                    exclude=[wielder, target],
                )
