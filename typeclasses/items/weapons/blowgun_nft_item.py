"""
BlowgunNFTItem — blowgun-type missile weapons.

Blowguns are ranged weapons that deal minimal direct damage (always 1)
but apply poison DoT and paralysis on hit. Mastery progression is
entirely in the on-hit effects, not damage scaling.

Mastery progression:
    UNSKILLED: -2 hit, 1 damage, no poison (untrained)
    BASIC:      0 hit, 1 damage, 1d3 rounds of 1d2 poison, DC 10 CON → paralysed 1 round
    SKILLED:   +2 hit, 1 damage, 1d4 rounds of 1d3 poison, DC 12 CON → paralysed 1 round
    EXPERT:    +4 hit, 1 damage, 1d4+1 rounds of 1d4 poison, DC 14 CON → paralysed 2 rounds
    MASTER:    +6 hit, 1 damage, 1d4+2 rounds of 1d5 poison, DC 17 CON → paralysed 2 rounds
    GM:        +8 hit, 1 damage, 1d4+3 rounds of 1d6 poison, DC 20 CON → paralysed 3 rounds

Melee penalty: UNSKILLED/BASIC take -2 hit in melee. SKILLED+ no penalty.

Paralysis: CON save (d20 + CON mod vs DC). Size-gated: HUGE+ immune.
    Grants advantage to all enemies (like prone).

Poison timing fork: combat_rounds if target is in combat, seconds if not.
    See CLAUDE.md "When NOT to Add a Condition Flag" for rationale.
"""

from evennia.typeclasses.attributes import AttributeProperty

from combat.combat_utils import get_actor_size
from enums.size import Size
from enums.character_class import CharacterClass
from enums.mastery_level import MasteryLevel
from enums.unused_for_reference.damage_type import DamageType
from typeclasses.items.weapons.weapon_nft_item import WeaponNFTItem
from utils.dice_roller import dice

# Sizes immune to blowgun paralysis
_PARALYSIS_IMMUNE_SIZES = {Size.HUGE, Size.GARGANTUAN}

# Poison duration dice by mastery
_BLOWGUN_POISON_DURATION = {
    MasteryLevel.BASIC: "1d3",
    MasteryLevel.SKILLED: "1d4",
    MasteryLevel.EXPERT: "1d4+1",
    MasteryLevel.MASTER: "1d4+2",
    MasteryLevel.GRANDMASTER: "1d4+3",
}

# Poison damage dice per tick by mastery
_BLOWGUN_POISON_DAMAGE = {
    MasteryLevel.BASIC: "1d2",
    MasteryLevel.SKILLED: "1d3",
    MasteryLevel.EXPERT: "1d4",
    MasteryLevel.MASTER: "1d5",
    MasteryLevel.GRANDMASTER: "1d6",
}

# CON save DC for paralysis by mastery
_BLOWGUN_PARALYSIS_DC = {
    MasteryLevel.BASIC: 10,
    MasteryLevel.SKILLED: 12,
    MasteryLevel.EXPERT: 14,
    MasteryLevel.MASTER: 17,
    MasteryLevel.GRANDMASTER: 20,
}

# Paralysis duration in combat rounds by mastery
_BLOWGUN_PARALYSIS_ROUNDS = {
    MasteryLevel.BASIC: 1,
    MasteryLevel.SKILLED: 1,
    MasteryLevel.EXPERT: 2,
    MasteryLevel.MASTER: 2,
    MasteryLevel.GRANDMASTER: 3,
}


class BlowgunMixin:
    """Blowgun weapon identity — mastery tables and overrides.

    Shared by BlowgunNFTItem and MobBlowgun. Single source of truth
    for blowgun combat mechanics (poison + paralysis).
    """

    weapon_type_key = "blowgun"
    base_damage = AttributeProperty("d1")
    material = AttributeProperty("iron")
    weapon_type = AttributeProperty("ranged")
    damage_type = AttributeProperty(DamageType.PIERCING)
    weight = AttributeProperty(0.5)
    is_finesse = AttributeProperty(True)
    two_handed = AttributeProperty(False)
    range = AttributeProperty(1)

    # ================================================================== #
    #  Mastery Overrides
    # ================================================================== #

    def get_mastery_damage_bonus(self, wielder):
        """Blowgun dart damage is always flat — no mastery damage bonus."""
        return 0

    def get_parries_per_round(self, wielder):
        return 0

    def get_extra_attacks(self, wielder):
        return 0

    # ================================================================== #
    #  Offensive Combat Hooks
    # ================================================================== #

    def at_pre_attack(self, wielder, target):
        """
        Melee penalty for low mastery.

        UNSKILLED/BASIC take -2 hit in melee. SKILLED+ no penalty.
        Currently all combat is melee (no area rooms yet).
        """
        mastery = self.get_wielder_mastery(wielder)
        if mastery.value < MasteryLevel.SKILLED.value:
            return -2
        return 0

    def at_hit(self, wielder, target, damage, damage_type):
        """
        On-hit poison + paralysis check (BASIC+).

        1. If UNSKILLED → return damage (no poison)
        2. Apply poison DoT (named effect + script)
        3. CON save for paralysis (size-gated: HUGE+ immune)
        """
        mastery = self.get_wielder_mastery(wielder)
        if mastery.value < MasteryLevel.BASIC.value:
            return damage

        self._apply_poison(wielder, target, mastery)
        self._check_paralysis(wielder, target, mastery)

        return damage

    def _apply_poison(self, wielder, target, mastery):
        """Apply poison DoT to target — named effect + damage script."""
        poison_duration_dice = _BLOWGUN_POISON_DURATION.get(mastery, "1d3")
        poison_damage_dice = _BLOWGUN_POISON_DAMAGE.get(mastery, "1d2")
        poison_ticks = dice.roll(poison_duration_dice)

        # Remove existing poison if any (fresh dose replaces old)
        if target.has_effect("poisoned"):
            target.remove_named_effect("poisoned")
        # Also clean up any lingering script
        existing_scripts = target.scripts.get("poison_dot")
        if existing_scripts:
            existing_scripts[0].delete()

        # Apply named effect as marker (no stat effects, no condition flag)
        # Duration is informational — the script manages actual tick count
        target.apply_poisoned(poison_ticks)

        # Create the damage-ticking script
        from evennia.utils.create import create_script
        from typeclasses.scripts.poison_dot_script import PoisonDoTScript

        script = create_script(
            PoisonDoTScript,
            obj=target,
            key="poison_dot",
            autostart=False,
        )
        script.db.remaining_ticks = poison_ticks
        script.db.damage_dice = poison_damage_dice
        script.db.source_name = wielder.key
        script.start()

        # Combat messages
        wielder.msg(
            f"|gYour poisoned dart strikes {target.key}! "
            f"({poison_ticks} ticks of {poison_damage_dice} poison)|n"
        )
        target.msg(
            f"|r{wielder.key}'s poisoned dart strikes you! "
            f"You feel poison seeping into your blood.|n"
        )

    def _check_paralysis(self, wielder, target, mastery):
        """CON save for paralysis. HUGE+ enemies are immune."""
        # Size gate
        target_size = get_actor_size(target)
        if target_size in _PARALYSIS_IMMUNE_SIZES:
            return

        dc = _BLOWGUN_PARALYSIS_DC.get(mastery, 10)
        rounds = _BLOWGUN_PARALYSIS_ROUNDS.get(mastery, 1)

        # CON save: d20 + CON mod vs DC
        con_mod = target.get_attribute_bonus(target.constitution)
        save_roll = dice.roll("1d20") + con_mod

        if save_roll >= dc:
            # Saved — no paralysis
            wielder.msg(
                f"|y{target.key} resists the paralysis!|n"
            )
            target.msg(
                f"|gYou resist the paralytic poison!|n"
            )
            return

        # Failed save — apply paralysis
        applied = target.apply_paralysed(rounds, source=wielder)
        if not applied:
            return

        # Advantage granting now handled automatically by on-apply callback

        # Combat messages
        s = "s" if rounds > 1 else ""
        wielder.msg(
            f"|g*PARALYSIS* {target.key} is paralysed for {rounds} round{s}!|n"
        )
        target.msg(
            f"|r*PARALYSIS* You are paralysed for {rounds} round{s}!|n"
        )


class BlowgunNFTItem(BlowgunMixin, WeaponNFTItem):
    """
    Blowgun weapons — missile, poison-focused mastery path.
    """

    excluded_classes = AttributeProperty([CharacterClass.MAGE])

    def at_object_creation(self):
        super().at_object_creation()
        self.tags.add("blowgun", category="weapon_type")
