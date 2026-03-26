"""
RemortMixin — remort-related attributes and the at_remort() reset method.

Tracks remort count, point buy budget, and per-level bonuses earned from
remort perks. The at_remort() method strips the character back to a blank
slate (preserving learned spells, recipes, and perk bonuses) so they can
go through chargen again.
"""

from evennia.typeclasses.attributes import AttributeProperty


class RemortMixin:
    """Mixin providing remort attributes and reset logic for FCMCharacter."""

    # How many times the character has remorted
    num_remorts = AttributeProperty(0)

    # Ability score point buy budget — starts at 27, can increase via perk
    point_buy = AttributeProperty(27)

    # Per-level bonuses from remort perks (applied during level-up)
    bonus_hp_per_level = AttributeProperty(0)
    bonus_mana_per_level = AttributeProperty(0)
    bonus_move_per_level = AttributeProperty(0)

    # Flat skill point bonuses from remort perks (added to chargen budget)
    bonus_weapon_skill_pts = AttributeProperty(0)
    bonus_class_skill_pts = AttributeProperty(0)
    bonus_general_skill_pts = AttributeProperty(0)

    def at_remort(self, account_bank):
        """
        Strip this character for remort. Transfers all items and currency
        to the account bank, wipes stats back to defaults, increments
        num_remorts, but preserves learned spells, recipes, and perk bonuses.

        Args:
            account_bank: The AccountBank object to transfer items/currency to.

        Must be called AFTER the remort perk has been applied.
        """
        from typeclasses.items.base_nft_item import BaseNFTItem

        # --- Transfer inventory to account bank ---

        # Unequip all worn items first
        if hasattr(self, "db") and self.db.wearslots:
            for slot, item in dict(self.db.wearslots).items():
                if item is not None:
                    self.remove(item)

        # Move all NFT items to account bank
        for obj in list(self.contents):
            if isinstance(obj, BaseNFTItem):
                obj.move_to(account_bank, quiet=True)

        # Transfer gold
        gold = self.get_gold()
        if gold > 0:
            self.transfer_gold_to(account_bank, gold)

        # Transfer all resources
        resources = dict(self.db.resources or {})
        for rid, amount in resources.items():
            if amount > 0:
                self.transfer_resource_to(account_bank, rid, amount)

        # --- Wipe quests (allows restart of starter quests on remort) ---
        self.attributes.clear(category="fcm_quests")

        # --- Wipe spells (granted only — learned persist) ---
        self.revoke_all_granted_spells()
        self.db.memorised_spells = {}

        # --- Reset ability scores to base 8 ---
        for stat in ("strength", "dexterity", "constitution",
                     "intelligence", "wisdom", "charisma"):
            setattr(self, stat, 8)
            setattr(self, f"base_{stat}", 8)

        # --- Reset HP / mana / move ---
        self.hp = 1
        self.base_hp_max = 2
        self.hp_max = 2
        self.mana = 0
        self.base_mana_max = 1
        self.mana_max = 1
        self.move = 2
        self.base_move_max = 3
        self.move_max = 3

        # --- Reset armor and combat caches ---
        self.base_armor_class = 10
        self.armor_class = 10
        self.base_crit_threshold = 20
        self.initiative_bonus = 0
        self.total_hit_bonus = 0
        self.total_damage_bonus = 0
        self.attacks_per_round = 1

        # --- Reset XP and levels ---
        self.experience_points = 0
        self.total_level = 1
        self.highest_xp_level_earned = 1
        self.levels_to_spend = 0

        # --- Reset skill points and mastery ---
        self.general_skill_pts_available = 0
        self.weapon_skill_pts_available = 0
        self.db.general_skill_mastery_levels = {}
        self.db.class_skill_mastery_levels = {}
        self.db.weapon_skill_mastery_levels = {}
        self.db.classes = {}

        # --- Reset conditions and resistances ---
        if hasattr(self, "conditions"):
            self.conditions = {}
        if hasattr(self, "damage_resistances"):
            self.damage_resistances = {}

        # --- Reset languages (chargen will re-set) ---
        self.db.languages = set()

        # --- Reset misc ---
        self.extra_memory_slots = 0
        self.hunger_level = self._get_default_hunger()
        self.room_vertical_position = 0

        # Dismiss pet and mount
        if self.active_pet:
            self.active_pet = None
        if self.active_mount:
            self.active_mount = None

        # Remove class and race cmdsets (chargen will re-add)
        self._remove_class_and_race_cmdsets()

        # --- Increment remort count ---
        self.num_remorts += 1

    def _get_default_hunger(self):
        """Return the default hunger level."""
        from enums.hunger_level import HungerLevel
        return HungerLevel.FULL

    def _remove_class_and_race_cmdsets(self):
        """Remove all class and race cmdsets so chargen can re-add them."""
        from typeclasses.actors.char_classes import CLASS_REGISTRY
        from typeclasses.actors.races import RACE_REGISTRY

        for cls in CLASS_REGISTRY.values():
            if cls.class_cmdset:
                self.cmdset.remove(cls.class_cmdset)

        for race in RACE_REGISTRY.values():
            if race.racial_cmdset:
                self.cmdset.remove(race.racial_cmdset)
