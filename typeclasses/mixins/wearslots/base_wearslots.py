"""
BaseWearslotsMixin — adds equipment slot management to any Evennia object.

Mix into Characters, Mobs, Pets, Mounts — anything that can wear or
equip items. Items remain in the object's contents; the wearslot dict
holds references to items that are currently equipped.

Child classes MUST:
    1. Override at_wearslots_init() to define their specific slots.
    2. Override can_wear(item) to implement validation rules.

Object flow:
    world <-> contents (inventory) <-> wearslots (equipment)

    Only the world <-> contents boundary changes carrying weight.
    Contents <-> wearslots is an internal shuffle with no weight change.

Wearslot dict keys are enum .value strings (from enums.wearslot).
Items declare their slot(s) using the same enum values.

After equipping/unequipping, the mixin calls the item's at_wear/at_remove
(or at_wield/at_hold) hook so the item can apply/reverse stat effects
on the wearer.

Data storage:
    self.db.wearslots — dict {slot_name (str): item (obj or None)}

Public API:
    # Equip / unequip
    self.wear(item)            -> (bool, str)
    self.remove(item)          -> (bool, str)

    # Slot queries
    self.slot_is_available(item) -> bool
    self.get_available_slot(item) -> str | None
    self.is_worn(item)           -> bool
    self.get_slot(slot_name)     -> obj | None
    self.get_all_worn()          -> dict

    # Validation (must override)
    self.can_wear(item)          -> bool

    # Display
    self.equipment_cmd_output(header) -> str

    # Inventory helper
    self.get_carried() -> list
"""

from enum import Enum


class BaseWearslotsMixin:
    """
    Mixin that manages equipment wearslots on any Evennia object.

    Items stay in self.contents — the wearslot dict just references
    which items are currently equipped in which slots.
    """

    # ================================================================== #
    #  Initialization
    # ================================================================== #

    def at_wearslots_init(self):
        """
        Call from at_object_creation() to initialize wearslot storage.
        Safe to call multiple times — only sets defaults if not already present.

        Child classes MUST override this to define their specific slots,
        calling super().at_wearslots_init() first.
        """
        if self.db.wearslots is None:
            self.db.wearslots = {}

    # ================================================================== #
    #  Slot Queries
    # ================================================================== #

    def _get_item_slots(self, item):
        """
        Get the wearslot name(s) an item declares it can be worn in.

        Checks item.db.wearslot first (Evennia Attribute), then falls
        back to item.wearslot (AttributeProperty). Normalizes enum
        values to their .value strings. Returns a list of strings.

        Returns:
            list of str — slot name strings, or empty list if none
        """
        slots = item.db.wearslot
        if slots is None:
            slots = getattr(item, "wearslot", None)
        if slots is None:
            return []
        if isinstance(slots, Enum):
            return [slots.value]
        if isinstance(slots, str):
            return [slots]
        # List of enums or strings
        return [s.value if isinstance(s, Enum) else s for s in slots]

    def slot_is_available(self, item):
        """
        Check whether this object has an empty slot matching the item.

        Returns True if:
            1. The item declares at least one wearslot
            2. At least one of those slots exists on this object
            3. At least one matching slot is currently empty (None)
        """
        item_slots = self._get_item_slots(item)
        if not item_slots:
            return False

        wearslots = self.db.wearslots or {}
        for slot in item_slots:
            if slot in wearslots and wearslots[slot] is None:
                return True
        return False

    def get_available_slot(self, item):
        """
        Get the first empty slot that matches the item's declared wearslot(s).

        Returns:
            str — slot name, or None if no matching slot is available
        """
        item_slots = self._get_item_slots(item)
        if not item_slots:
            return None

        wearslots = self.db.wearslots or {}
        for slot in item_slots:
            if slot in wearslots and wearslots[slot] is None:
                return slot
        return None

    def is_worn(self, item):
        """
        Check if an item is currently equipped in any wearslot.

        Args:
            item: Evennia object to check

        Returns:
            bool — True if the item is in any wearslot
        """
        wearslots = self.db.wearslots or {}
        return item in wearslots.values()

    def get_slot(self, slot_name):
        """
        Get the item currently equipped in a specific slot.

        Args:
            slot_name: str or Enum — name of the slot to check

        Returns:
            obj or None — the equipped item, or None if slot is empty
        """
        if isinstance(slot_name, Enum):
            slot_name = slot_name.value
        wearslots = self.db.wearslots or {}
        return wearslots.get(slot_name)

    def get_all_worn(self):
        """
        Get all currently equipped items.

        Returns:
            dict — {slot_name: item} for occupied slots only
        """
        wearslots = self.db.wearslots or {}
        return {k: v for k, v in wearslots.items() if v is not None}

    # ================================================================== #
    #  Validation (must override in child classes)
    # ================================================================== #

    def can_wear(self, item):
        """
        Determine whether this object is allowed to wear the given item.

        This checks creature-type restrictions only (class, level, race,
        etc.). Slot availability is checked separately by wear() itself.

        Child classes MUST override this method. Even if there are no
        restrictions yet (just return True), the override forces a
        conscious decision about validation rules for each creature type.

        Args:
            item: Evennia object to validate

        Returns:
            bool — True if the item can be worn

        Raises:
            NotImplementedError if not overridden
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement can_wear()"
        )

    # ================================================================== #
    #  Wear / Remove
    # ================================================================== #

    def wear(self, item, target_slot=None):
        """
        Equip an item from contents into a wearslot.

        The item must be in self.contents and pass can_wear() validation.
        The item stays in contents — the wearslot dict just references it.
        After equipping, calls item.at_wear(self) so the item can apply
        stat effects to the wearer.

        Args:
            item: Evennia object to equip
            target_slot: optional str or Enum — override the slot the item
                goes into (e.g. dual-wield weapon → HOLD instead of WIELD).
                If None, routes via item.wearslot as normal.

        Returns:
            (bool, str) — (success, message)
        """
        # Validate item is in our contents
        if item not in self.contents:
            return (False, "You don't have that.")

        # Check if already worn
        if self.is_worn(item):
            return (False, f"You are already wearing {item.key}.")

        if target_slot is not None:
            # Explicit slot override (e.g. dual-wield weapon → HOLD)
            if isinstance(target_slot, Enum):
                target_slot = target_slot.value
            wearslots = self.db.wearslots or {}
            if target_slot not in wearslots:
                return (False, "You don't have a suitable equipment slot.")
            if wearslots[target_slot] is not None:
                display = target_slot.replace("_", " ").title()
                return (False, f"Your {display} slot is already occupied.")
            slot = target_slot
        else:
            # Check if item declares a wearslot
            item_slots = self._get_item_slots(item)
            if not item_slots:
                return (False, f"{item.key} is not something that can be worn.")

            # Check slot availability
            slot = self.get_available_slot(item)
            if slot is None:
                # Item declares valid slots but they're all occupied
                if len(item_slots) == 1:
                    display = item_slots[0].replace("_", " ").title()
                    return (False, f"Your {display} slot is already occupied.")
                return (False, f"All suitable slots for {item.key} are occupied.")

        # Check item usage restrictions (class, race, level, etc.)
        if hasattr(item, 'can_use'):
            allowed, reason = item.can_use(self)
            if not allowed:
                return (False, reason)

        # Run child class validation (creature-type restrictions)
        if not self.can_wear(item):
            return (False, f"You cannot wear {item.key}.")

        # Equip it
        self.db.wearslots[slot] = item
        display_slot = slot.replace("_", " ").title()

        # Let the item apply stat effects to the wearer
        item.at_wear(self)

        return (True, f"You wear {item.key} on your {display_slot}.")

    def remove(self, item):
        """
        Unequip an item from a wearslot back to contents.

        The item stays in contents — the wearslot reference is just cleared.
        After unequipping, calls item.at_remove(self) so the item can
        reverse stat effects on the wearer.

        Args:
            item: Evennia object to unequip

        Returns:
            (bool, str) — (success, message)
        """
        wearslots = self.db.wearslots or {}

        # Find which slot this item is in
        slot_name = None
        for slot, worn_item in wearslots.items():
            if worn_item == item:
                slot_name = slot
                break

        if slot_name is None:
            return (False, f"You are not wearing {item.key}.")

        # Unequip it
        self.db.wearslots[slot_name] = None
        display_slot = slot_name.replace("_", " ").title()

        # Let the item reverse stat effects on the wearer
        item.at_remove(self)

        return (True, f"You remove {item.key} from your {display_slot}.")

    # ================================================================== #
    #  Display
    # ================================================================== #

    def equipment_cmd_output(self, header="\n|wEquipped Items|n\n"):
        """
        Formatted display of all wearslots and what is equipped in them.

        Args:
            header: str — header line (e.g. "You are wearing:" or
                    "Cujo is wearing:" for pet commands)

        Returns:
            str — formatted multi-line string
        """
        wearslots = self.db.wearslots or {}
        if not wearslots:
            return f"{header}\n  Nothing — no equipment slots."

        lines = [header]

        # Fixed-width column: pad slot names to longest slot display width
        max_slot_len = max(
            len(s.replace("_", " ").title()) for s in wearslots
        )
        col_width = max_slot_len + 2  # +2 for angle brackets < >

        for slot, item in wearslots.items():
            display_slot = slot.replace("_", " ").title()
            slot_str = f"<|c{display_slot}|n>"
            if item is not None:
                # Pad after > to align item names (exclude ANSI codes from width calc)
                pad = col_width - len(display_slot) - 2
                condition = (
                    item.get_condition_label()
                    if hasattr(item, "get_condition_label")
                    else ""
                )
                line = f"  {slot_str}{' ' * pad} |w{item.key}|n"
                if condition:
                    line = f"{line}  ({condition})"
                lines.append(line)
            else:
                lines.append(f"  {slot_str}")
        return "\n".join(lines)

    # ================================================================== #
    #  Inventory Helper
    # ================================================================== #

    def get_carried(self):
        """
        Get items in contents that are NOT currently worn/equipped.

        Returns:
            list — Evennia objects in contents that aren't in any wearslot
        """
        worn = set(v for v in (self.db.wearslots or {}).values() if v is not None)
        return [obj for obj in self.contents if obj not in worn]
