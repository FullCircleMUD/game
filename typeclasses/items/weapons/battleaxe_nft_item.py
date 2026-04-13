"""
BattleaxeNFTItem — battleaxe-type weapons with cleave and sunder.

Battleaxes are large two-handed slashing weapons. Their mastery path
combines CLEAVE (cascading AoE hits, slightly nerfed from greatsword)
with SUNDER (chance on hit to crack target's armour). Sunder stacks —
a few lucky hits can strip significant AC from a tough target.

Mastery progression:
    UNSKILLED: -2 hit, no cleave, no sunder
    BASIC:      0 hit, no cleave, no sunder
    SKILLED:   +2 hit, 20% 2nd enemy, 20% sunder (-1 AC, +1 armour durability)
    EXPERT:    +4 hit, 40% 2nd / 20% 3rd, 25% sunder (-1 AC, +1 armour durability)
    MASTER:    +6 hit, 60% 2nd / 40% 3rd / 20% 4th, 25% sunder (-2 AC, +2 armour durability)
    GM:        +8 hit, 60% 2nd / 40% 3rd / 20% 4th, 30% sunder (-2 AC, +2 armour durability)

Cleave mechanic:
    After a successful primary attack, roll d100 for each additional enemy.
    Chances are cascading — must pass 2nd check to attempt 3rd, etc.
    Each cleave hit deals full weapon damage (separate roll).
    Chain breaks on first failed check.
    Cleave hits can also proc sunder.

Sunder mechanic:
    On any hit (primary or cleave) → roll d100 vs sunder chance.
    Success → STACKING AC penalty on that target (rest of combat).
    Also deals extra durability damage to the target's body armour.
    AC floor of 10 — sunder can't reduce armor_class below base.
    Multiple sunders accumulate: e.g. 3x at SKILLED = -3 AC total.
    Cleaned up by clear_combat_effects() at end of combat.
"""

from evennia.typeclasses.attributes import AttributeProperty
from enums.unused_for_reference.damage_type import DamageType

from combat.combat_utils import get_sides
from enums.character_class import CharacterClass
from enums.mastery_level import MasteryLevel
from typeclasses.items.weapons.weapon_nft_item import WeaponNFTItem
from utils.dice_roller import dice

# Cascading cleave chances by mastery (nerfed from greatsword)
_BATTLEAXE_CLEAVE_CHANCES = {
    MasteryLevel.UNSKILLED: [],
    MasteryLevel.BASIC: [],
    MasteryLevel.SKILLED: [20],
    MasteryLevel.EXPERT: [40, 20],
    MasteryLevel.MASTER: [60, 40, 20],
    MasteryLevel.GRANDMASTER: [60, 40, 20],
}

# Sunder table: (chance %, AC penalty per hit, extra armour durability per hit)
_BATTLEAXE_SUNDER = {
    MasteryLevel.UNSKILLED: (0, 0, 0),
    MasteryLevel.BASIC: (0, 0, 0),
    MasteryLevel.SKILLED: (20, 1, 1),
    MasteryLevel.EXPERT: (25, 1, 1),
    MasteryLevel.MASTER: (25, 2, 2),
    MasteryLevel.GRANDMASTER: (30, 2, 2),
}

# Sunder cannot reduce armor_class below this value
_SUNDER_AC_FLOOR = 10


class BattleaxeMixin:
    """Battleaxe weapon identity — mastery tables and overrides.

    Shared by BattleaxeNFTItem and MobBattleaxe. Single source of truth
    for battleaxe combat mechanics (cleave + sunder).
    """

    weapon_type_key = "battleaxe"
    base_damage = AttributeProperty("d10")
    damage_type = AttributeProperty(DamageType.SLASHING)
    speed = AttributeProperty(0)
    weight = AttributeProperty(4.0)
    two_handed = AttributeProperty(True)

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
        """On-hit sunder check — chance to crack target's armour."""
        self._try_sunder(wielder, target)
        return damage

    def at_post_attack(self, wielder, target, hit, damage_dealt):
        """
        After a successful primary attack, attempt cascading cleave hits
        on additional enemies in the room. Cleave hits can also sunder.
        """
        if not hit:
            return

        mastery = self.get_wielder_mastery(wielder)
        chances = _BATTLEAXE_CLEAVE_CHANCES.get(mastery, [])
        if not chances:
            return

        # Find cleave targets — living enemies excluding primary target
        _, enemies = get_sides(wielder)
        cleave_targets = [
            e for e in enemies
            if e != target and getattr(e, "hp", 0) > 0
        ]
        if not cleave_targets:
            return

        # Resolve damage parameters
        damage_dice_str = self.get_damage_roll(mastery)
        dmg_type = self.damage_type

        for i, chance in enumerate(chances):
            if i >= len(cleave_targets):
                break

            roll = dice.roll("1d100")
            if roll > chance:
                # Chain breaks
                break

            cleave_target = cleave_targets[i]
            if getattr(cleave_target, "hp", 0) <= 0:
                continue

            # Full damage roll
            cleave_damage = dice.roll(damage_dice_str) + wielder.effective_damage_bonus
            cleave_damage = max(1, cleave_damage)
            actual = cleave_target.take_damage(
                cleave_damage, damage_type=dmg_type.value, cause="combat",
                killer=wielder,
            )

            # Weapon durability
            if hasattr(self, "reduce_durability"):
                self.reduce_durability(1)

            # Sunder check on cleave hit
            self._try_sunder(wielder, cleave_target)

            # Cleave messages
            wielder.msg(
                f"|r*CLEAVE* Your battleaxe's momentum carries through "
                f"to {cleave_target.key} for {actual} damage!|n"
            )
            cleave_target.msg(
                f"|r{wielder.key} cleaves into you with their battleaxe "
                f"for {actual} damage!|n"
            )
            if wielder.location:
                wielder.location.msg_contents(
                    f"|r{wielder.key}'s battleaxe cleaves into "
                    f"{cleave_target.key} for {actual} damage!|n",
                    exclude=[wielder, cleave_target],
                )

    def _try_sunder(self, wielder, target):
        """
        Attempt to sunder the target's armour. Stacking.

        Rolls d100 vs mastery-scaled chance. On success:
        1. Applies/stacks SUNDERED named effect (cumulative AC penalty)
        2. Deals extra durability damage to the target's body armour
        AC cannot be reduced below _SUNDER_AC_FLOOR (10).
        """
        mastery = self.get_wielder_mastery(wielder)
        chance, ac_per_hit, dur_per_hit = _BATTLEAXE_SUNDER.get(mastery, (0, 0, 0))
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
                # Already at floor — no further AC reduction possible
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
            f"|r*SUNDER* Your battleaxe cracks {target.key}'s armour! "
            f"(-{new_stacks} AC total)|n"
        )
        target.msg(
            f"|r*SUNDER* {wielder.key}'s battleaxe cracks your armour! "
            f"(-{new_stacks} AC total)|n"
        )
        if wielder.location:
            wielder.location.msg_contents(
                f"|r*SUNDER* {wielder.key}'s battleaxe cracks "
                f"{target.key}'s armour!|n",
                exclude=[wielder, target],
            )


class BattleaxeNFTItem(BattleaxeMixin, WeaponNFTItem):
    """
    Battleaxe weapons — melee, two-handed, cleave + sunder mastery path.
    """

    excluded_classes = AttributeProperty([
        CharacterClass.MAGE, CharacterClass.CLERIC, CharacterClass.THIEF,
    ])

    def at_object_creation(self):
        super().at_object_creation()
        self.tags.add("battleaxe", category="weapon_type")
