"""
AxeNFTItem — handaxe-type weapons with sunder mastery + extra attack.

Handaxes are fast one-handed slashing weapons. Paired with a shield,
they offer a balance of offense and defense — lighter sunder than the
battleaxe but you survive to keep swinging. At MASTER+ mastery, the
handaxe's speed grants an extra attack per round, giving more chances
to proc sunder over a fight.

Mastery progression:
    UNSKILLED: -2 hit, no sunder, 0 extra attacks
    BASIC:      0 hit, no sunder, 0 extra attacks
    SKILLED:   +2 hit, 10% sunder (-1 AC, +1 armour durability), 0 extra attacks
    EXPERT:    +4 hit, 15% sunder (-1 AC, +1 armour durability), 0 extra attacks
    MASTER:    +6 hit, 15% sunder (-1 AC, +1 armour durability), 1 extra attack
    GM:        +8 hit, 20% sunder (-1 AC, +1 armour durability), 1 extra attack

Sunder mechanic:
    On hit → roll d100 vs sunder chance (mastery-scaled).
    Success → STACKING AC penalty on that target (rest of combat).
    Also deals extra durability damage to the target's body armour.
    AC floor of 10 — sunder can't reduce armor_class below base.
    Lighter than battleaxe — always -1 AC per proc (never -2).
    Cleaned up by clear_combat_effects() at end of combat.
"""

from evennia.typeclasses.attributes import AttributeProperty
from enums.unused_for_reference.damage_type import DamageType

from enums.character_class import CharacterClass
from enums.mastery_level import MasteryLevel
from enums.size import Size
from typeclasses.items.weapons.weapon_nft_item import WeaponNFTItem
from utils.dice_roller import dice

# Sunder table: (chance %, AC penalty per hit, extra armour durability per hit)
# Lower chances and always -1 AC — lighter weapon than battleaxe
_AXE_SUNDER = {
    MasteryLevel.UNSKILLED: (0, 0, 0),
    MasteryLevel.BASIC: (0, 0, 0),
    MasteryLevel.SKILLED: (10, 1, 1),
    MasteryLevel.EXPERT: (15, 1, 1),
    MasteryLevel.MASTER: (15, 1, 1),
    MasteryLevel.GRANDMASTER: (20, 1, 1),
}

# Extra attacks per round by mastery
_AXE_EXTRA_ATTACKS = {
    MasteryLevel.UNSKILLED: 0,
    MasteryLevel.BASIC: 0,
    MasteryLevel.SKILLED: 0,
    MasteryLevel.EXPERT: 0,
    MasteryLevel.MASTER: 1,
    MasteryLevel.GRANDMASTER: 1,
}

# Sunder cannot reduce armor_class below this value
_SUNDER_AC_FLOOR = 10


class AxeMixin:
    """Handaxe weapon identity — mastery tables and overrides.

    Shared by AxeNFTItem and MobAxe. Single source of truth
    for handaxe combat mechanics (sunder + extra attacks).
    """

    weapon_type_key = "handaxe"
    base_damage = AttributeProperty("d6")
    damage_type = AttributeProperty(DamageType.SLASHING)
    speed = AttributeProperty(2)
    weight = AttributeProperty(2.0)

    # ================================================================== #
    #  Mastery Overrides
    # ================================================================== #

    def get_parries_per_round(self, wielder):
        return 0

    def get_extra_attacks(self, wielder):
        mastery = self.get_wielder_mastery(wielder)
        return _AXE_EXTRA_ATTACKS.get(mastery, 0)

    # ================================================================== #
    #  Offensive Combat Hooks
    # ================================================================== #

    def at_hit(self, wielder, target, damage, damage_type):
        """On-hit sunder check — chance to crack target's armour."""
        self._try_sunder(wielder, target)
        return damage

    def _try_sunder(self, wielder, target):
        """
        Attempt to sunder the target's armour. Stacking.

        Rolls d100 vs mastery-scaled chance. On success:
        1. Applies/stacks SUNDERED named effect (cumulative AC penalty)
        2. Deals extra durability damage to the target's body armour
        AC cannot be reduced below _SUNDER_AC_FLOOR (10).
        """
        mastery = self.get_wielder_mastery(wielder)
        chance, ac_per_hit, dur_per_hit = _AXE_SUNDER.get(mastery, (0, 0, 0))
        if chance <= 0:
            return

        roll = dice.roll("1d100")
        if roll > chance:
            return

        # Calculate current sunder state
        has_sunder = hasattr(target, "has_effect") and target.has_effect("sundered")
        current_stacks = (target.db.sunder_stacks or 0) if has_sunder else 0

        # Compute base AC (undo current sunder to get real equipment AC)
        current_ac = getattr(target, "armor_class", 10)
        base_ac = current_ac + current_stacks

        # Check AC floor — can't sunder below 10
        new_stacks = current_stacks + ac_per_hit
        if base_ac - new_stacks < _SUNDER_AC_FLOOR:
            new_stacks = max(0, base_ac - _SUNDER_AC_FLOOR)
            if new_stacks <= current_stacks:
                return

        # Remove existing sunder to replace with updated total
        if has_sunder:
            target.remove_named_effect("sundered")

        # Apply stacked sunder
        target.apply_sundered(-new_stacks, 99, source=wielder)
        target.db.sunder_stacks = new_stacks

        # Extra durability damage to body armour
        if dur_per_hit > 0:
            body_armor = target.get_slot("BODY") if hasattr(target, "get_slot") else None
            if body_armor and hasattr(body_armor, "reduce_durability"):
                body_armor.reduce_durability(dur_per_hit)

        # Messages
        wielder.msg(
            f"|r*SUNDER* Your axe cracks {target.key}'s armour! "
            f"(-{new_stacks} AC total)|n"
        )
        target.msg(
            f"|r*SUNDER* {wielder.key}'s axe cracks your armour! "
            f"(-{new_stacks} AC total)|n"
        )
        if wielder.location:
            wielder.location.msg_contents(
                f"|r*SUNDER* {wielder.key}'s axe cracks "
                f"{target.key}'s armour!|n",
                exclude=[wielder, target],
            )


class AxeNFTItem(AxeMixin, WeaponNFTItem):
    """
    Handaxe weapons — melee, one-handed, sunder + extra attack mastery.
    """

    size = AttributeProperty(Size.SMALL.value)

    excluded_classes = AttributeProperty([
        CharacterClass.MAGE, CharacterClass.CLERIC,
    ])

    def at_object_creation(self):
        super().at_object_creation()
        self.tags.add("axe", category="weapon_type")
