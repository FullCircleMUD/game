"""
LanceNFTItem — lance-type weapons with mounted combat mastery.

LanceMixin defines all mastery tables and overrides — shared by
both LanceNFTItem (player weapons) and MobLance (mob weapons).

Lances are two-handed piercing weapons that are devastating on horseback
but terrible on foot. The only weapon that can knock HUGE creatures prone.

UNMOUNTED (all tiers):
    Disadvantage on all attacks, capped at 1 attack/round, no crit bonus,
    no prone chance. Standard mastery hit bonus still applies.

MOUNTED mastery progression:
    UNSKILLED:  no crit bonus, 1 attack, no prone
    BASIC:      no crit bonus, 1 attack, no prone
    SKILLED:   -1 crit threshold, 1 attack, 15% prone (up to LARGE)
    EXPERT:    -2 crit threshold, 1 attack, 20% prone (up to HUGE)
    MASTER:    -2 crit threshold, 2 attacks, 20% prone (up to HUGE)
    GM:        -3 crit threshold, 2 attacks, 25% prone (up to HUGE)

Prone mechanic (mounted only):
    On first successful hit each round → roll d100 vs mastery-scaled chance.
    Success → target is knocked PRONE (action denial + advantage for attackers).
    Size-gated: SKILLED can prone up to LARGE, EXPERT+ up to HUGE.
    GARGANTUAN always immune. Can't re-prone already prone targets.
"""

from evennia.typeclasses.attributes import AttributeProperty
from enums.unused_for_reference.damage_type import DamageType

from enums.size import Size
from enums.character_class import CharacterClass
from enums.mastery_level import MasteryLevel
from typeclasses.items.weapons.weapon_nft_item import WeaponNFTItem
from utils.dice_roller import dice

# Mounted crit threshold modifier by mastery
_LANCE_CRIT_THRESHOLD = {
    MasteryLevel.UNSKILLED: 0,
    MasteryLevel.BASIC: 0,
    MasteryLevel.SKILLED: -1,
    MasteryLevel.EXPERT: -2,
    MasteryLevel.MASTER: -2,
    MasteryLevel.GRANDMASTER: -3,
}

# Mounted extra attacks by mastery
_LANCE_MOUNTED_EXTRA_ATTACKS = {
    MasteryLevel.UNSKILLED: 0,
    MasteryLevel.BASIC: 0,
    MasteryLevel.SKILLED: 0,
    MasteryLevel.EXPERT: 0,
    MasteryLevel.MASTER: 1,
    MasteryLevel.GRANDMASTER: 1,
}

# Mounted prone chance (%) and immune sizes by mastery
# SKILLED: can prone up to LARGE (HUGE+ immune)
# EXPERT+: can prone up to HUGE (GARGANTUAN immune)
_LANCE_PRONE = {
    MasteryLevel.UNSKILLED: (0, set()),
    MasteryLevel.BASIC: (0, set()),
    MasteryLevel.SKILLED: (15, {Size.HUGE, Size.GARGANTUAN}),
    MasteryLevel.EXPERT: (20, {Size.GARGANTUAN}),
    MasteryLevel.MASTER: (20, {Size.GARGANTUAN}),
    MasteryLevel.GRANDMASTER: (25, {Size.GARGANTUAN}),
}


def _is_mounted(wielder):
    """Check if wielder is mounted (has a mount via MountMixin)."""
    return getattr(wielder.db, "mounted_on", None) is not None


class LanceMixin:
    """Lance weapon identity — mastery tables and overrides.

    Shared by LanceNFTItem and MobLance. Single source of truth
    for lance combat mechanics.
    """

    weapon_type_key = "lance"
    base_damage = AttributeProperty("2d7")
    damage_type = AttributeProperty(DamageType.PIERCING)
    speed = AttributeProperty(0)
    weight = AttributeProperty(4.0)
    two_handed = AttributeProperty(True)

    # ================================================================== #
    #  Mastery Overrides
    # ================================================================== #

    def get_mastery_crit_threshold_modifier(self, wielder):
        """Crit threshold reduction — only when mounted."""
        if not _is_mounted(wielder):
            return 0
        mastery = self.get_wielder_mastery(wielder)
        return _LANCE_CRIT_THRESHOLD.get(mastery, 0)

    def get_extra_attacks(self, wielder):
        """Extra attacks — only when mounted at MASTER+."""
        if not _is_mounted(wielder):
            return 0
        mastery = self.get_wielder_mastery(wielder)
        return _LANCE_MOUNTED_EXTRA_ATTACKS.get(mastery, 0)

    # ================================================================== #
    #  Offensive Combat Hooks
    # ================================================================== #

    def at_pre_attack(self, wielder, target):
        """
        Unmounted: set disadvantage for this attack.
        Returns 0 (no hit modifier — disadvantage handled via combat handler).
        """
        if not _is_mounted(wielder):
            handler = wielder.scripts.get("combat_handler")
            if handler and not handler[0].has_disadvantage(target):
                handler[0].set_disadvantage(target, rounds=1)
        return 0

    def at_hit(self, wielder, target, damage, damage_type):
        """On first hit each round (mounted only): attempt to knock target prone."""
        if _is_mounted(wielder):
            self._try_prone(wielder, target)
        return damage

    def _try_prone(self, wielder, target):
        """
        Attempt to knock the target prone with a mounted lance strike.

        Fires on first successful hit each round (tracked via combat handler
        lance_prone_used flag). Size-gated by mastery tier.
        GARGANTUAN always immune. Can't re-prone already prone targets.
        """
        # Only first hit per round (tracked on wielder.ndb, reset by combat handler)
        if getattr(wielder.ndb, "lance_prone_used", False):
            return
        wielder.ndb.lance_prone_used = True

        mastery = self.get_wielder_mastery(wielder)
        chance, immune_sizes = _LANCE_PRONE.get(mastery, (0, set()))
        if chance <= 0:
            return

        # Size check
        from combat.combat_utils import get_actor_size
        target_size = get_actor_size(target)
        if target_size in immune_sizes:
            return

        # Already prone — skip
        if hasattr(target, "has_effect") and target.has_effect("prone"):
            return

        roll = dice.roll("1d100")
        if roll > chance:
            return

        # Apply PRONE
        applied = target.apply_prone(1, source=wielder)
        if not applied:
            return

        wielder.msg(
            f"|g*LANCE STRIKE* Your mounted charge knocks "
            f"{target.key} to the ground!|n"
        )
        target.msg(
            f"|r*LANCE STRIKE* {wielder.key}'s mounted lance charge "
            f"knocks you to the ground!|n"
        )
        if wielder.location:
            wielder.location.msg_contents(
                f"|r*LANCE STRIKE* {wielder.key}'s mounted charge "
                f"knocks {target.key} to the ground!|n",
                exclude=[wielder, target],
            )


class LanceNFTItem(LanceMixin, WeaponNFTItem):
    """
    Lance weapons — two-handed melee, mounted combat mastery.
    Devastating when mounted, deliberately terrible on foot.
    """

    excluded_classes = AttributeProperty([
        CharacterClass.MAGE, CharacterClass.CLERIC, CharacterClass.THIEF,
    ])

    def at_object_creation(self):
        super().at_object_creation()
        self.tags.add("lance", category="weapon_type")
