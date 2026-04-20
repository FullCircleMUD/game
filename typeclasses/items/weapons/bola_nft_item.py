"""
BolaNFTItem — bola-type missile weapons.

Bolas are ranged CC weapons that deal minimal direct damage (always 1)
but entangle targets on hit via a contested DEX roll. Mastery progression
is entirely in entangle duration, not damage scaling.

Mastery progression:
    UNSKILLED: -2 hit, 1 damage, max 1 round entangle
    BASIC:      0 hit, 1 damage, max 2 rounds entangle
    SKILLED:   +2 hit, 1 damage, max 3 rounds entangle
    EXPERT:    +4 hit, 1 damage, max 4 rounds entangle
    MASTER:    +6 hit, 1 damage, max 5 rounds entangle
    GM:        +8 hit, 1 damage, max 6 rounds entangle

Entangle mechanic:
    On hit → contested roll: d20 + attacker DEX + mastery bonus
                          vs d20 + target DEX.
    Attacker wins → target ENTANGLED. Attacker's total roll = escape DC.
    Each round: target rolls d20 + STR bonus vs escape DC to break free.
    Max duration cap prevents infinite lockdowns even on nat 20.
    HUGE+ targets are immune.
    All enemies get advantage while target is entangled.
"""

from evennia.typeclasses.attributes import AttributeProperty

from combat.combat_utils import get_actor_size
from enums.size import Size
from enums.character_class import CharacterClass
from enums.mastery_level import MasteryLevel

from enums.unused_for_reference.damage_type import DamageType
from typeclasses.items.weapons.weapon_nft_item import WeaponNFTItem
from utils.dice_roller import dice

# Sizes immune to bola entangle
_ENTANGLE_IMMUNE_SIZES = {Size.HUGE, Size.GARGANTUAN}

# Max entangle duration (combat rounds) by mastery — safety valve
_BOLA_MAX_ENTANGLE_ROUNDS = {
    MasteryLevel.UNSKILLED: 1,
    MasteryLevel.BASIC: 2,
    MasteryLevel.SKILLED: 3,
    MasteryLevel.EXPERT: 4,
    MasteryLevel.MASTER: 5,
    MasteryLevel.GRANDMASTER: 6,
}


class BolaMixin:
    """Bola weapon identity — mastery tables and overrides.

    Shared by BolaNFTItem and MobBola. Single source of truth
    for bola combat mechanics (entangle).
    """

    weapon_type_key = "bola"
    base_damage = AttributeProperty("d1")
    material = AttributeProperty("iron")
    weapon_type = AttributeProperty("ranged")
    damage_type = AttributeProperty(DamageType.BLUDGEONING)
    weight = AttributeProperty(1.0)
    is_finesse = AttributeProperty(True)
    two_handed = AttributeProperty(False)
    range = AttributeProperty(1)

    # ================================================================== #
    #  Mastery Overrides
    # ================================================================== #

    def get_mastery_damage_bonus(self, wielder):
        """Bola damage is always flat — no mastery damage bonus."""
        return 0

    def get_parries_per_round(self, wielder):
        return 0

    def get_extra_attacks(self, wielder):
        return 0

    # ================================================================== #
    #  Offensive Combat Hooks
    # ================================================================== #

    def at_hit(self, wielder, target, damage, damage_type):
        """
        On-hit entangle check via contested DEX roll.

        1. Size gate: HUGE+ immune
        2. Contested roll: d20 + DEX + mastery vs d20 + DEX
        3. Attacker wins → ENTANGLED with save-each-round (STR vs attacker roll)
        4. Grant advantage to all enemies
        """
        mastery = self.get_wielder_mastery(wielder)

        # Size gate
        target_size = get_actor_size(target)
        if target_size in _ENTANGLE_IMMUNE_SIZES:
            wielder.msg(
                f"|y{target.key} is too large to be entangled by a bola!|n"
            )
            return damage

        # Contested roll: attacker DEX + mastery vs target DEX
        attacker_dex = wielder.get_attribute_bonus(wielder.dexterity)
        attacker_roll = dice.roll("1d20") + attacker_dex + mastery.bonus
        defender_dex = target.get_attribute_bonus(target.dexterity)
        defender_roll = dice.roll("1d20") + defender_dex

        if attacker_roll <= defender_roll:
            # Target dodges the bola
            wielder.msg(
                f"|y{target.key} dodges the bola!|n"
            )
            target.msg(
                f"|gYou dodge {wielder.key}'s bola!|n"
            )
            return damage

        # Attacker wins — entangle with attacker's roll as escape DC
        max_rounds = _BOLA_MAX_ENTANGLE_ROUNDS.get(mastery, 2)

        applied = target.apply_entangled(
            max_rounds, source=wielder,
            save_dc=attacker_roll,
            save_messages={
                "success": "|gYou strain against the bola and tear free!|n",
                "fail": "|rYou struggle against the bola but cannot break free!|n",
                "success_third": "{name} strains against the bola and tears free!",
                "fail_third": "{name} struggles against the bola but cannot break free!",
            },
        )
        if not applied:
            # Already entangled (anti-stacking)
            return damage

        # Advantage granting now handled automatically by on-apply callback

        # Combat messages
        s = "s" if max_rounds != 1 else ""
        wielder.msg(
            f"|g*ENTANGLE* Your bola wraps around {target.key}! "
            f"(up to {max_rounds} round{s})|n"
        )
        target.msg(
            f"|r*ENTANGLE* {wielder.key}'s bola wraps around your legs!|n"
        )

        return damage


class BolaNFTItem(BolaMixin, WeaponNFTItem):
    """
    Bola weapons — missile, entangle-focused mastery path.
    """

    excluded_classes = AttributeProperty([CharacterClass.MAGE])

    def at_object_creation(self):
        super().at_object_creation()
        self.tags.add("bola", category="weapon_type")
