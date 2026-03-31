"""
WeaponNFTItem — base typeclass for all NFT-backed weapons.

Extends WearableNFTItem to inherit the data-driven wear_effects system
and durability tracking. Adds weapon-specific attributes (damage,
weapon_type, speed) and combat hooks.

Static weapon stats are drawn from the weapon prototype.
Individual item specific / mutable stats come from the NFTMirror metadata dict.

Subclass hierarchy:
    WearableNFTItem
    └── WeaponNFTItem (this class)
        └── LongswordNFTItem
        └── BowNFTItem (future)
        └── ...
"""

from evennia.typeclasses.attributes import AttributeProperty
from enums.unused_for_reference.damage_type import DamageType
from enums.mastery_level import MasteryLevel
from enums.wearslot import HumanoidWearSlot

from typeclasses.items.wearables.wearable_nft_item import WearableNFTItem


class WeaponNFTItem(WearableNFTItem):
    """
    Base class for all weapon NFTs.

    Inherits from WearableNFTItem:
        wearslot, wear_effects, max_durability, durability, repairable,
        at_wear/at_remove (data-driven effect loop), at_break (equipment break)

    Weapon-specific attributes (from prototype):
        base_damage    — lookup key into damage tables ("d4", "d6", "d8", etc.)
        material       — material tier ("wood", "bronze", "iron", "steel", "adamantine")
        damage         — legacy dict override (used by special weapons that bypass the table)
        damage_type    — from DamageType enum (slashing, piercing, etc.)
        weapon_type    — "melee" or "missile"
        speed          — initiative modifier (higher = acts first)
        two_handed     — if True, blocks use of the HOLD slot while wielded
    """

    # Damage lookup: base_damage + material resolve via world.damage_tables.
    # Set these on prototypes instead of the damage dict.
    base_damage = AttributeProperty(None)   # e.g. "d8", "d4", "2d6"
    material = AttributeProperty(None)      # e.g. "iron", "bronze", "adamantine"

    # Legacy damage dict — only used when base_damage/material are not set
    # (special weapons like blowgun/bola with fixed damage).
    damage = AttributeProperty(None)

    damage_type = AttributeProperty(DamageType.BLUDGEONING)
    weapon_type = AttributeProperty("melee")  # "melee" or "missile"
    speed = AttributeProperty(1)
    two_handed = AttributeProperty(False)
    is_finesse = AttributeProperty(False)    # True = use max(STR, DEX) for hit/damage
    can_dual_wield = AttributeProperty(False)  # True = can be equipped in HOLD slot via cmd_hold
    is_inset = AttributeProperty(False)        # True = gem has been inset, excludes from shopkeeper trade

    # Override in subclasses with WeaponType.value string (e.g. "long_sword")
    # Used for mastery lookups against wielder.db.weapon_skill_mastery_levels
    weapon_type_key = None

    # Override default wearslot from WearableNFTItem
    wearslot = AttributeProperty(HumanoidWearSlot.WIELD)

    def at_object_creation(self):
        super().at_object_creation()
        self.tags.add("weapon", category="item_type")

    def get_damage_roll(self, mastery_level=MasteryLevel.UNSKILLED):
        """
        Get the damage dice string for a given mastery level.

        Prefers the lookup table (base_damage + material). Falls back to
        the legacy damage dict for special weapons (blowgun, bola, etc.).
        """
        if self.base_damage and self.material:
            from world.damage_tables import get_damage_dice
            return get_damage_dice(self.base_damage, self.material, mastery_level)
        # Legacy fallback for special weapons with fixed damage
        if self.damage:
            return self.damage.get(mastery_level, self.damage.get(MasteryLevel.UNSKILLED, "1d2"))
        return "1d2"

    # ================================================================== #
    #  Equip / Unequip Hooks
    # ================================================================== #

    def at_wear(self, wearer):
        """Bridge for BaseWearslotsMixin.wear() — applies effects then delegates to at_wield()."""
        super().at_wear(wearer)  # applies wear_effects
        self.at_wield(wearer)

    def at_wield(self, wielder):
        """
        Extension point for weapon-specific equip behaviour.

        Called after wear_effects are applied. Override in weapon
        subclasses for additional behaviour (e.g. parry setup).

        Args:
            wielder: the Evennia object wielding this weapon
        """
        pass

    def at_remove(self, wielder):
        """Reverse wear_effects and any weapon-specific cleanup."""
        super().at_remove(wielder)

    # ================================================================== #
    #  Mastery Helpers
    # ================================================================== #

    def get_wielder_mastery(self, wielder):
        """
        Get the wielder's mastery level for this weapon type.

        Returns MasteryLevel enum. Falls back to UNSKILLED if no
        weapon_type_key is set or wielder has no mastery data.
        """
        if not self.weapon_type_key or not hasattr(wielder, "db"):
            return MasteryLevel.UNSKILLED
        mastery_int = (wielder.db.weapon_skill_mastery_levels or {}).get(
            self.weapon_type_key, 0
        )
        try:
            return MasteryLevel(mastery_int)
        except ValueError:
            return MasteryLevel.UNSKILLED

    def get_mastery_hit_bonus(self, wielder):
        """
        Get the mastery-based hit bonus for this weapon.

        Default: returns MasteryLevel.bonus (-2/0/+2/+4/+6/+8).
        Override in subclasses to adjust balance — e.g. a longsword
        at EXPERT might get extra attacks instead of full hit bonus,
        so you'd reduce the hit bonus here to compensate.
        """
        return self.get_wielder_mastery(wielder).bonus

    def get_mastery_damage_bonus(self, wielder):
        """
        Get the mastery-based damage bonus for this weapon.

        Default: returns MasteryLevel.bonus (-2/0/+2/+4/+6/+8).
        Override in subclasses to adjust balance.
        """
        return self.get_wielder_mastery(wielder).bonus

    # ================================================================== #
    #  Offensive Combat Hooks (called on the ATTACKER's weapon)
    # ================================================================== #

    def at_pre_attack(self, wielder, target):
        """
        Called before the attack roll.

        Return int hit modifier (e.g. +1 accuracy), or 0 for no change.
        """
        return 0

    def at_hit(self, wielder, target, damage, damage_type):
        """
        Called after a successful hit, before damage is applied.

        Args:
            wielder: the attacker
            target: the defender
            damage: int — raw damage rolled
            damage_type: DamageType enum — slashing, piercing, etc.

        Return int modified damage.
        """
        return damage

    def at_crit(self, wielder, target, damage, damage_type):
        """
        Called on a critical hit, after at_hit().

        Return int modified damage.
        """
        return damage

    def at_miss(self, wielder, target):
        """Called after a missed attack. Effect-only."""
        pass

    def at_kill(self, wielder, target):
        """Called when the target dies from this weapon's attack. Effect-only."""
        pass

    def at_post_attack(self, wielder, target, hit, damage_dealt):
        """
        Called at the end of an attack resolution, hit or miss.

        Args:
            wielder: the attacker
            target: the defender
            hit: bool — whether the attack hit
            damage_dealt: int — final damage dealt (0 if miss)

        Effect-only.
        """
        pass

    # ================================================================== #
    #  Defensive Combat Hooks (called on the DEFENDER's weapon)
    # ================================================================== #

    def at_pre_defend(self, wielder, attacker):
        """
        Called before defense calculation.

        Return int AC modifier (e.g. +1 parry bonus), or 0 for no change.
        """
        return 0

    def at_wielder_about_to_be_hit(self, wielder, attacker, total_hit, total_ac):
        """
        Called when an attack will hit but before damage is rolled.

        Gives the defender a chance to reactively boost AC (e.g. Shield spell).
        Return int AC modifier. If total_hit < (total_ac + modifier), the hit
        becomes a miss and follows the miss path instead.

        Crits bypass this hook entirely — they always hit.

        Args:
            wielder: the defender about to be hit
            attacker: the attacker
            total_hit: int — attacker's total hit roll (d20 + mods)
            total_ac: int — defender's current total AC

        Return int AC modifier (0 = no change).
        """
        from combat.reactive_spells import check_reactive_shield
        return check_reactive_shield(wielder)

    def at_wielder_hit(self, wielder, attacker, damage, damage_type):
        """
        Called when the wielder takes a hit, before damage is applied.

        Return int modified damage.
        """
        return damage

    def at_wielder_receive_crit(self, wielder, attacker, damage, damage_type):
        """
        Called when the wielder receives a critical hit.

        Return int modified damage.
        """
        return damage

    def at_wielder_missed(self, wielder, attacker):
        """Called when an attack misses the wielder. Effect-only."""
        pass

    # ================================================================== #
    #  Lifecycle Combat Hooks (called on ALL wielded weapons)
    # ================================================================== #

    def at_combat_start(self, wielder):
        """Called when the wielder enters combat. Effect-only."""
        pass

    def at_combat_end(self, wielder):
        """Called when the wielder exits combat. Effect-only."""
        pass

    def at_round_start(self, wielder):
        """Called at the start of each combat round. Effect-only."""
        pass

    def at_round_end(self, wielder):
        """Called at the end of each combat round. Effect-only."""
        pass

    # ================================================================== #
    #  Mastery-Scaled Combat Methods (override in subclasses)
    # ================================================================== #

    def get_parries_per_round(self, wielder):
        """Parries per round at wielder's mastery. Default: 0 (no parries)."""
        return 0

    def get_extra_attacks(self, wielder):
        """Extra attacks per round at wielder's mastery. Default: 0."""
        return 0

    def get_parry_advantage(self, wielder):
        """Whether wielder gets advantage on parry rolls. Default: False."""
        return False

    def has_riposte(self, wielder):
        """Whether wielder can riposte after a successful parry. Default: False."""
        return False

    def get_mastery_crit_threshold_modifier(self, wielder):
        """Mastery-based crit threshold modifier. Default: 0 (no change)."""
        return 0

    def get_reach_counters_per_round(self, wielder):
        """Reach counter-attacks per round at wielder's mastery. Default: 0."""
        return 0

    def get_offhand_attacks(self, wielder):
        """Off-hand attacks per round at wielder's mastery. Default: 0."""
        return 0

    def get_offhand_hit_modifier(self, wielder):
        """Hit modifier for off-hand attacks. Default: 0 (no penalty)."""
        return 0

    def get_stun_checks_per_round(self, wielder):
        """Stun check attempts per round at wielder's mastery. Default: 0."""
        return 0

    def get_disarm_checks_per_round(self, wielder):
        """Disarm check attempts per round at wielder's mastery. Default: 0."""
        return 0
