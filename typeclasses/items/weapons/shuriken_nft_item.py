"""
ShurikenNFTItem — thrown star weapons with multi-throw + crit scaling.

Shurikens are ninja-only thrown weapons. Each throw consumes the
shuriken — on hit it lodges in the target's inventory, on miss it
falls to the room floor. Both cases allow recovery. Shurikens are
unbreakable (no durability loss). At higher mastery, ninjas throw
multiple stars per round with increasing precision.

Mastery progression:
    UNSKILLED: -2 hit, 1 throw, 0 crit mod
    BASIC:      0 hit, 1 throw, 0 crit mod
    SKILLED:   +2 hit, 1 throw, -1 crit threshold
    EXPERT:    +4 hit, 2 throws, -1 crit threshold
    MASTER:    +6 hit, 2 throws, -2 crit threshold
    GM:        +8 hit, 3 throws, -2 crit threshold

Consumable mechanic:
    On hit → shuriken moves to target's inventory (can be looted)
    On miss → shuriken falls to room floor (can be picked up)
    After each throw, auto-equips next shuriken from wielder's inventory.
    If no shurikens remain, subsequent attacks use UNARMED fallback.

Crit scaling:
    Lower crit threshold synergises with multi-throw — more attacks
    means more chances to land critical hits.
"""

from evennia.typeclasses.attributes import AttributeProperty

from enums.character_class import CharacterClass
from enums.mastery_level import MasteryLevel
from typeclasses.items.weapons.weapon_nft_item import WeaponNFTItem

# Extra attacks per round by mastery (total throws = 1 + extra)
_SHURIKEN_EXTRA_ATTACKS = {
    MasteryLevel.UNSKILLED: 0,
    MasteryLevel.BASIC: 0,
    MasteryLevel.SKILLED: 0,
    MasteryLevel.EXPERT: 1,
    MasteryLevel.MASTER: 1,
    MasteryLevel.GRANDMASTER: 2,
}

# Crit threshold modifier by mastery (negative = easier to crit)
_SHURIKEN_CRIT_MOD = {
    MasteryLevel.UNSKILLED: 0,
    MasteryLevel.BASIC: 0,
    MasteryLevel.SKILLED: -1,
    MasteryLevel.EXPERT: -1,
    MasteryLevel.MASTER: -2,
    MasteryLevel.GRANDMASTER: -2,
}


class ShurikenNFTItem(WeaponNFTItem):
    """
    Shuriken weapons — missile, finesse, multi-throw + crit mastery.
    Consumable: each throw moves the shuriken to target or room.
    """

    weapon_type_key = "shuriken"
    required_classes = AttributeProperty([CharacterClass.NINJA])
    weapon_type = AttributeProperty("missile")
    is_finesse = AttributeProperty(True)
    range = AttributeProperty(1)

    def at_object_creation(self):
        super().at_object_creation()
        self.tags.add("shuriken", category="weapon_type")

    # ================================================================== #
    #  Mastery Overrides
    # ================================================================== #

    def get_parries_per_round(self, wielder):
        return 0

    def get_extra_attacks(self, wielder):
        mastery = self.get_wielder_mastery(wielder)
        return _SHURIKEN_EXTRA_ATTACKS.get(mastery, 0)

    def get_mastery_crit_threshold_modifier(self, wielder):
        mastery = self.get_wielder_mastery(wielder)
        return _SHURIKEN_CRIT_MOD.get(mastery, 0)

    # ================================================================== #
    #  Unbreakable — shurikens don't lose durability
    # ================================================================== #

    def reduce_durability(self, amount=1):
        """Shurikens are unbreakable — no durability loss."""
        pass

    # ================================================================== #
    #  Consumable — shuriken moves on throw
    # ================================================================== #

    def at_post_attack(self, wielder, target, hit, damage_dealt):
        """
        After each throw, move the shuriken:
        - Hit: shuriken lodges in target (target's inventory)
        - Miss: shuriken falls to room floor

        Then auto-equip the next shuriken from wielder's inventory.
        """
        if hit:
            self._consume_shuriken(wielder, target)
        # Miss is handled by at_miss

    def at_miss(self, wielder, target):
        """On miss, shuriken falls to room floor."""
        self._consume_shuriken(wielder, None)

    def _consume_shuriken(self, wielder, target):
        """
        Move this shuriken away from the wielder and auto-equip the next one.

        Args:
            wielder: the ninja throwing the shuriken
            target: if not None, shuriken goes to target's inventory (hit).
                    if None, shuriken falls to room floor (miss).
        """
        # Unequip from wielder's slot
        if hasattr(wielder, "db") and wielder.db.wearslots:
            slots = wielder.db.wearslots
            if slots.get("WIELD") == self:
                slots["WIELD"] = None

        # Move shuriken to destination
        if target is not None:
            self.move_to(target, quiet=True)
        elif wielder.location:
            self.move_to(wielder.location, quiet=True)

        # Auto-equip next shuriken from inventory
        self._auto_equip_next(wielder)

    def _auto_equip_next(self, wielder):
        """Find and equip the next available shuriken from wielder's inventory."""
        for item in wielder.contents:
            if (item != self
                    and hasattr(item, "weapon_type_key")
                    and item.weapon_type_key == "shuriken"
                    and not wielder.is_worn(item)):
                # Directly slot it — skip full wear() validation since
                # it's the same weapon type we already passed checks for
                if hasattr(wielder, "db") and wielder.db.wearslots:
                    wielder.db.wearslots["WIELD"] = item
                    if hasattr(item, "at_wield"):
                        item.at_wield(wielder)
                return

        # No more shurikens available
        wielder.msg(
            "|yYou have no more shurikens to throw!|n"
        )
