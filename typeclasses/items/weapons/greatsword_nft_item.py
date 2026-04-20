"""
GreatswordNFTItem — greatsword-type weapons with cleave and executioner.

Greatswords are two-handed slashing weapons. Pure offense archetype — no
parries, no flat extra attacks. Instead, mastery unlocks CLEAVE (cascading
AoE hits on successful primary attack) and EXECUTIONER (GM: bonus attack
on any kill).

Mastery progression:
    UNSKILLED: -2 hit, no cleave
    BASIC:      0 hit, no cleave
    SKILLED:   +2 hit, 25% 2nd enemy
    EXPERT:    +4 hit, 50% 2nd / 25% 3rd
    MASTER:    +6 hit, 75% 2nd / 50% 3rd / 25% 4th
    GM:        +8 hit, 75% 2nd / 50% 3rd / 25% 4th + executioner

Cleave mechanic:
    After a successful primary attack, roll d100 for each additional enemy.
    Chances are cascading — must pass 2nd check to attempt 3rd, etc.
    Each cleave hit deals full weapon damage (separate roll).
    Chain breaks on first failed check.

Executioner mechanic (GM only):
    On any kill (primary or cleave), fire a full execute_attack() on another
    living enemy. Limited to 1 per round via combat_handler.executioner_used.
    The executioner attack can itself cleave but cannot chain executioner.
"""

from evennia.typeclasses.attributes import AttributeProperty
from enums.unused_for_reference.damage_type import DamageType

from combat.combat_utils import get_sides, get_weapon, execute_attack
from enums.character_class import CharacterClass
from enums.mastery_level import MasteryLevel
from enums.size import Size
from typeclasses.items.weapons.weapon_nft_item import WeaponNFTItem
from utils.dice_roller import dice

# Cascading cleave chances by mastery — each entry is % for Nth additional enemy
_GREATSWORD_CLEAVE_CHANCES = {
    MasteryLevel.UNSKILLED: [],
    MasteryLevel.BASIC: [],
    MasteryLevel.SKILLED: [25],
    MasteryLevel.EXPERT: [50, 25],
    MasteryLevel.MASTER: [75, 50, 25],
    MasteryLevel.GRANDMASTER: [75, 50, 25],
}


class GreatswordMixin:
    """Greatsword weapon identity — mastery tables and overrides.

    Shared by GreatswordNFTItem and MobGreatsword. Single source of truth
    for greatsword combat mechanics (cleave + executioner).
    """

    weapon_type_key = "greatsword"
    base_damage = AttributeProperty("2d6")
    damage_type = AttributeProperty(DamageType.SLASHING)
    speed = AttributeProperty(0)
    weight = AttributeProperty(4.5)
    two_handed = AttributeProperty(True)

    def get_parries_per_round(self, wielder):
        return 0

    def get_extra_attacks(self, wielder):
        return 0

    # ================================================================== #
    #  Offensive Combat Hooks
    # ================================================================== #

    def at_post_attack(self, wielder, target, hit, damage_dealt):
        """
        After a successful primary attack, attempt cascading cleave hits
        on additional enemies in the room.
        """
        if not hit:
            return

        mastery = self.get_wielder_mastery(wielder)
        chances = _GREATSWORD_CLEAVE_CHANCES.get(mastery, [])
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

        killed_any = False
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
            damage = dice.roll(damage_dice_str) + wielder.effective_damage_bonus
            damage = max(1, damage)
            actual = cleave_target.take_damage(
                damage, damage_type=dmg_type.value, cause="combat",
                killer=wielder,
            )

            # Weapon durability
            if hasattr(self, "reduce_durability"):
                self.reduce_durability(1)

            # Cleave messages
            wielder.msg(
                f"|r*CLEAVE* Your greatsword's momentum carries through "
                f"to {cleave_target.key} for {actual} damage!|n"
            )
            cleave_target.msg(
                f"|r{wielder.key} cleaves into you with their greatsword "
                f"for {actual} damage!|n"
            )
            if wielder.location:
                wielder.location.msg_contents(
                    f"|r{wielder.key}'s greatsword cleaves into "
                    f"{cleave_target.key} for {actual} damage!|n",
                    exclude=[wielder, cleave_target],
                )

            # Check for kill — potential executioner trigger
            if getattr(cleave_target, "hp", 0) <= 0:
                killed_any = True

        # Executioner from cleave kills (primary kill handled by at_kill)
        if killed_any:
            self._try_executioner(wielder)

    def at_kill(self, wielder, target):
        """On kill from primary attack, attempt executioner (GM only)."""
        self._try_executioner(wielder)

    def _try_executioner(self, wielder):
        """
        GM-only: fire a bonus execute_attack on another living enemy.
        Limited to 1 per round via combat_handler.executioner_used.
        """
        mastery = self.get_wielder_mastery(wielder)
        if mastery != MasteryLevel.GRANDMASTER:
            return

        handler = wielder.scripts.get("combat_handler")
        if not handler or handler[0].executioner_used:
            return

        # Find a living enemy to strike
        _, enemies = get_sides(wielder)
        alive_enemies = [e for e in enemies if getattr(e, "hp", 0) > 0]
        if not alive_enemies:
            return

        handler[0].executioner_used = True
        new_target = alive_enemies[0]

        wielder.msg(
            f"|r*EXECUTIONER* You strike at {new_target.key} "
            f"with renewed fury!|n"
        )
        if wielder.location:
            wielder.location.msg_contents(
                f"|r*EXECUTIONER* {wielder.key} strikes at "
                f"{new_target.key} with renewed fury!|n",
                exclude=[wielder],
            )

        execute_attack(wielder, new_target)


class GreatswordNFTItem(GreatswordMixin, WeaponNFTItem):
    """
    Greatsword weapons — melee, two-handed, cleave-focused mastery path.
    """

    size = AttributeProperty(Size.MEDIUM.value)
    min_size = AttributeProperty(Size.MEDIUM.value)

    excluded_classes = AttributeProperty([
        CharacterClass.MAGE, CharacterClass.CLERIC, CharacterClass.THIEF,
    ])

    def at_object_creation(self):
        super().at_object_creation()
        self.tags.add("greatsword", category="weapon_type")
