"""
CarryingCapacityMixin — weight tracking and encumbrance for characters,
pets, and mounts.

Weight is split into two independently-tracked components:
    current_weight_nfts       — total weight of NFT items in contents
    current_weight_fungibles  — total weight of gold + resources

The property `current_weight_carried` is always the sum of the two.
This split means NFT and fungible weight changes never interfere.

NFT weight is tracked automatically via Evennia's at_object_receive()
and at_object_leave() hooks — no command-level code needed.

Fungible weight is tracked by overriding _at_balance_changed() from
FungibleInventoryMixin. If FungibleInventoryMixin is not present (e.g.
on a pet that only carries items), fungible weight stays at 0.

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

    # the amount the character is currently carrying in either nfts or fungibles
    # adjusted whena character moves item into or out of inventory
    # moving between inventory and equipped state does not 
    # alter this as character are still carrying equipped items
    current_weight_nfts = AttributeProperty(0.0)
    current_weight_fungibles = AttributeProperty(0.0)

    @property
    def current_weight_carried(self):
        """Total weight = NFT items + fungibles. Always the sum of the two."""
        return (self.current_weight_nfts or 0.0) + (self.current_weight_fungibles or 0.0)

    # ================================================================== #
    #  Initialization
    # ================================================================== #

    def at_carrying_capacity_init(self):
        """
        Call from at_object_creation(). Safe to call multiple times.
        Sets default capacity values.
        """
        self.max_carrying_capacity_kg = 50
        self.current_weight_nfts = 0.0
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
    #  NFT weight tracking (via Evennia hooks)
    # ================================================================== #

    def at_object_receive(self, moved_obj, source_location, **kwargs):
        """Update NFT weight when an object enters contents."""
        super().at_object_receive(moved_obj, source_location, **kwargs)
        weight = getattr(moved_obj, "weight", 0.0) or 0.0
        if weight > 0:
            self.current_weight_nfts = (self.current_weight_nfts or 0.0) + weight

    def at_object_leave(self, moved_obj, target_location, **kwargs):
        """Update NFT weight when an object leaves contents."""
        super().at_object_leave(moved_obj, target_location, **kwargs)
        weight = getattr(moved_obj, "weight", 0.0) or 0.0
        if weight > 0:
            self.current_weight_nfts = max(
                0.0, (self.current_weight_nfts or 0.0) - weight
            )

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

        Called on server restart via at_init() to catch any drift between
        the stored weight attributes and actual contents/balances.
        """
        # NFT weight from contents
        nft_total = 0.0
        for obj in self.contents:
            nft_total += getattr(obj, "weight", 0.0) or 0.0
        self.current_weight_nfts = nft_total

        # Fungible weight
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
