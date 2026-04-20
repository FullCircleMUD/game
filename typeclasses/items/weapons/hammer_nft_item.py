"""
HammerNFTItem — hammer-type weapons with devastating blow mastery.

HammerMixin defines all mastery tables and overrides — shared by
both HammerNFTItem (player weapons) and MobHammer (mob weapons).

Hammers are heavy bludgeoning weapons. Their unique mastery path
amplifies critical hit damage with a scaling multiplier. Normal crits
double the weapon dice; hammer mastery multiplies the entire crit
damage further, making each crit increasingly devastating.

Mastery progression:
    UNSKILLED: -2 hit, standard 2x crit
    BASIC:      0 hit, standard 2x crit
    SKILLED:   +2 hit, ~2.5x crit (1.25x multiplier on doubled damage)
    EXPERT:    +4 hit, ~3x crit   (1.5x multiplier)
    MASTER:    +6 hit, ~3.5x crit (1.75x multiplier)
    GM:        +8 hit, ~4x crit   (2.0x multiplier)

Devastating Blow mechanic:
    at_crit() receives already-doubled damage from the combat system.
    Hammer multiplies this further by a mastery-scaled factor.
    Crit threshold stays at default (nat 20) — crits are rare but
    catastrophic. Build-around weapon: stack crit threshold reduction
    gear + damage gear for maximum spike.
"""

from evennia.typeclasses.attributes import AttributeProperty
from enums.unused_for_reference.damage_type import DamageType

from enums.character_class import CharacterClass
from enums.mastery_level import MasteryLevel
from enums.size import Size
from typeclasses.items.weapons.weapon_nft_item import WeaponNFTItem

# Crit damage multiplier by mastery (applied to already-doubled crit damage)
_HAMMER_CRIT_MULTIPLIER = {
    MasteryLevel.UNSKILLED: 1.0,
    MasteryLevel.BASIC: 1.0,
    MasteryLevel.SKILLED: 1.25,
    MasteryLevel.EXPERT: 1.5,
    MasteryLevel.MASTER: 1.75,
    MasteryLevel.GRANDMASTER: 2.0,
}


class HammerMixin:
    """Hammer weapon identity — mastery tables and overrides.

    Shared by HammerNFTItem and MobHammer. Single source of truth
    for hammer combat mechanics.
    """

    weapon_type_key = "hammer"
    base_damage = AttributeProperty("d8")
    weight = AttributeProperty(3.5)

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

    def at_crit(self, wielder, target, damage, damage_type):
        """
        Devastating Blow — amplify crit damage by mastery-scaled multiplier.

        Called after the combat system has already doubled the weapon dice.
        Multiplies the entire crit damage further for massive spikes.
        """
        mastery = self.get_wielder_mastery(wielder)
        multiplier = _HAMMER_CRIT_MULTIPLIER.get(mastery, 1.0)

        if multiplier > 1.0:
            damage = int(damage * multiplier)

            wielder.msg(
                f"|R*DEVASTATING BLOW* Your hammer delivers a "
                f"bone-crushing critical strike!|n"
            )
            target.msg(
                f"|R*DEVASTATING BLOW* {wielder.key}'s hammer delivers a "
                f"bone-crushing critical strike!|n"
            )
            if wielder.location:
                wielder.location.msg_contents(
                    f"|R*DEVASTATING BLOW* {wielder.key}'s hammer delivers "
                    f"a bone-crushing critical strike to {target.key}!|n",
                    exclude=[wielder, target],
                )

        return damage


class HammerNFTItem(HammerMixin, WeaponNFTItem):
    """
    Hammer weapons — melee, bludgeoning, devastating blow crit mastery.
    """

    size = AttributeProperty(Size.SMALL.value)

    excluded_classes = AttributeProperty([CharacterClass.MAGE])

    def at_object_creation(self):
        super().at_object_creation()
        self.tags.add("hammer", category="weapon_type")
