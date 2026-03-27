"""
CarryingCapacityMixin — weight tracking and encumbrance for characters,
pets, and mounts.

Weight is split into two independently-tracked components:
    items_weight            — total weight of NFT items in contents
    current_weight_fungibles  — total weight of gold + resources

The property `current_weight_carried` is always the sum of the two.
This split means NFT and fungible weight changes never interfere.

Both components use a nuclear recalculate pattern — every weight-changing
event triggers a full rebuild from scratch.  This eliminates drift from
missed hooks (e.g. item.delete() not firing at_object_leave) or
double-fired hooks.

Item weight includes direct content items plus the contents weight of
containers with transfer_weight=True (e.g. backpacks).

Fungible weight is recalculated via get_total_fungible_weight() from
FungibleInventoryMixin.

MRO: CarryingCapacityMixin must come BEFORE FungibleInventoryMixin so
its _at_balance_changed() override wins.

Usage:
    class FCMCharacter(CarryingCapacityMixin, FungibleInventoryMixin,
                       HumanoidWearslotsMixin, DefaultCharacter):
        def at_object_creation(self):
            ...
            self.at_carrying_capacity_init()
"""

from evennia.typeclasses.attributes import AttributeProperty


class CarryingCapacityMixin:
    """
    Mixin providing weight tracking and carrying capacity enforcement.
    """

    # equipment/spell bonuses ONLY — strength modifier is added at check time
    # e.g. effective_capacity = max_carrying_capacity_kg + get_attribute_bonus(strength) * 5
    # See BaseActor and FCMCharacter.apply_effect() for the universal pattern.
    max_carrying_capacity_kg = AttributeProperty(50)

    # Total weight of NFT items in contents (including container contents
    # for containers with transfer_weight=True).  Rebuilt from scratch by
    # _recalculate_item_weight() on every item gain/loss.
    items_weight = AttributeProperty(0.0)

    # Total weight of fungibles (gold + resources).  Rebuilt from scratch
    # by _at_balance_changed() on every gold/resource change.
    current_weight_fungibles = AttributeProperty(0.0)

    @property
    def current_weight_carried(self):
        """Total weight = items + fungibles. Always the sum of the two."""
        return (self.items_weight or 0.0) + (self.current_weight_fungibles or 0.0)

    # ================================================================== #
    #  Initialization
    # ================================================================== #

    def at_carrying_capacity_init(self):
        """
        Call from at_object_creation(). Safe to call multiple times.
        Sets default capacity values.
        """
        self.max_carrying_capacity_kg = 50
        self.items_weight = 0.0
        self.current_weight_fungibles = 0.0

    # ================================================================== #
    #  Queries
    # ================================================================== #

    def get_current_weight(self):
        """Return total weight currently carried."""
        return self.current_weight_carried

    def get_max_capacity(self):
        """Return maximum carrying capacity in kg."""
        return self.max_carrying_capacity_kg or 0

    def get_remaining_capacity(self):
        """Return remaining carrying capacity in kg (clamped to 0)."""
        return max(0, self.get_max_capacity() - self.current_weight_carried)

    def can_carry(self, additional_kg):
        """Check if this carrier can take on additional weight."""
        return (self.current_weight_carried + additional_kg) <= self.get_max_capacity()

    @property
    def is_encumbered(self):
        """True if current weight exceeds maximum carrying capacity."""
        return self.current_weight_carried > self.get_max_capacity()

    # ================================================================== #
    #  Item weight — nuclear recalculate (via Evennia hooks)
    # ================================================================== #

    def _recalculate_item_weight(self, exclude=None):
        """
        Rebuild item weight from contents (nuclear recalculate).

        Includes the .weight of every direct content object, plus the
        current_contents_weight of containers with transfer_weight=True.

        Args:
            exclude: optional object to skip (used by at_object_leave
                     because Evennia fires the hook before the item is
                     actually removed from contents).
        """
        total = 0.0
        for obj in self.contents:
            if obj is exclude:
                continue
            total += getattr(obj, "weight", 0.0) or 0.0
            if (getattr(obj, "is_container", False)
                    and getattr(obj, "transfer_weight", False)):
                total += getattr(obj, "current_contents_weight", 0.0) or 0.0
        self.items_weight = total

    def at_object_receive(self, moved_obj, source_location, **kwargs):
        """Recalculate item weight when an object enters contents."""
        super().at_object_receive(moved_obj, source_location, **kwargs)
        self._recalculate_item_weight()

    def at_object_leave(self, moved_obj, target_location, **kwargs):
        """Recalculate item weight when an object leaves contents."""
        super().at_object_leave(moved_obj, target_location, **kwargs)
        self._recalculate_item_weight(exclude=moved_obj)

    # ================================================================== #
    #  Fungible weight tracking (override FungibleInventoryMixin hook)
    # ================================================================== #

    def _at_balance_changed(self):
        """Recalculate fungible weight when gold/resources change."""
        if hasattr(self, "get_total_fungible_weight"):
            self.current_weight_fungibles = self.get_total_fungible_weight()
        else:
            self.current_weight_fungibles = 0.0

    # ================================================================== #
    #  Full recalculation (safety net / init)
    # ================================================================== #

    def recalculate_weight(self):
        """
        Rebuild both weight components from scratch.

        Called on server restart via at_init() and by the recalc command.
        """
        self._recalculate_item_weight()
        if hasattr(self, "get_total_fungible_weight"):
            self.current_weight_fungibles = self.get_total_fungible_weight()
        else:
            self.current_weight_fungibles = 0.0

    def at_init(self):
        """Recalculate on every server restart/cache load to catch drift."""
        super().at_init()
        self.recalculate_weight()

    # ================================================================== #
    #  Display
    # ================================================================== #

    def get_encumbrance_display(self):
        """Return a formatted encumbrance string, e.g. 'Carrying: 12.5 / 50.0 kg'."""
        return (
            f"|wCarrying:|n {self.current_weight_carried:.1f} / "
            f"{self.get_max_capacity():.1f} kg"
        )
