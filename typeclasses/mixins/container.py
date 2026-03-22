"""
ContainerMixin — adds container behaviour to any Evennia object.

Containers hold NFT items and fungibles (gold/resources).  Weight is
tracked via `current_contents_weight` and optionally propagated to the
carrier when `transfer_weight` is True.

Ownership model (3 rules):
    1. Put INTO container → item transitions actor's ownership → container's
       current ownership.
    2. Take FROM container → item transitions container's ownership → actor's
       ownership.
    3. Container moves → everything inside cascades old → new ownership.

Same-owner transitions (same wallet address) are no-ops.

Weight propagation:
    When `transfer_weight=True` and the container is inside a character's
    inventory, changes to contents weight update the carrier's
    `current_weight_nfts` attribute.  When `transfer_weight=False` (e.g.
    panniers on a mule) only the container's own weight counts against
    the carrier.

MRO: ContainerMixin must come BEFORE FungibleInventoryMixin and
BaseNFTItem/WearableNFTItem so its hooks fire first.

Usage:
    class ContainerNFTItem(ContainerMixin, FungibleInventoryMixin, BaseNFTItem):
        def at_object_creation(self):
            super().at_object_creation()
            self.at_container_init()
            self.at_fungible_init()
"""

from evennia.typeclasses.attributes import AttributeProperty


class ContainerMixin:
    """
    Mixin providing container storage, capacity enforcement, and weight
    propagation for any Evennia object that can hold other items.
    """

    is_container = True

    max_container_capacity_kg = AttributeProperty(10.0)

    # True  = contents weight propagates to carrier (backpack)
    # False = only the container's own weight counts (panniers, bag of holding)
    transfer_weight = AttributeProperty(True)

    # Tracked weight of everything inside (NFTs + fungibles)
    current_contents_weight = AttributeProperty(0.0)

    # ================================================================== #
    #  Initialization
    # ================================================================== #

    def at_container_init(self):
        """
        Call from at_object_creation(). Safe to call multiple times.
        """
        self.current_contents_weight = 0.0

    # ================================================================== #
    #  Queries
    # ================================================================== #

    def can_hold(self, additional_kg):
        """
        Check if this container can accept additional weight.

        Args:
            additional_kg: float — weight to add (item weight or fungible weight)

        Returns:
            True if the container has room, False otherwise.
        """
        current = self.current_contents_weight or 0.0
        capacity = self.max_container_capacity_kg or 0.0
        return (current + additional_kg) <= capacity

    def can_hold_item(self, item):
        """
        Check if a specific item can be placed in this container.

        Rejects containers (no nesting) and checks capacity.
        """
        if getattr(item, "is_container", False):
            return False, "You can't put a container inside another container."
        weight = getattr(item, "weight", 0.0) or 0.0
        if not self.can_hold(weight):
            remaining = max(
                0.0,
                (self.max_container_capacity_kg or 0.0)
                - (self.current_contents_weight or 0.0),
            )
            return False, (
                f"{self.key} can't hold that much. "
                f"(Need: {weight:.1f} kg, Available: {remaining:.1f} kg)"
            )
        return True, None

    def get_remaining_container_capacity(self):
        """Return remaining container capacity in kg (clamped to 0)."""
        return max(
            0.0,
            (self.max_container_capacity_kg or 0.0)
            - (self.current_contents_weight or 0.0),
        )

    def get_container_contents(self):
        """Return list of NFT items inside this container."""
        from typeclasses.items.base_nft_item import BaseNFTItem

        return [obj for obj in self.contents if isinstance(obj, BaseNFTItem)]

    def is_empty(self):
        """Check if this container has no NFTs and no fungibles."""
        if self.contents:
            return False
        if hasattr(self, "get_gold") and self.get_gold() > 0:
            return False
        if hasattr(self, "get_all_resources"):
            for _rid, amt in self.get_all_resources().items():
                if amt > 0:
                    return False
        return True

    # ================================================================== #
    #  Display
    # ================================================================== #

    def get_container_display(self):
        """
        Return a formatted string showing container contents.

        Example:
            Leather Backpack (3.2 / 15.0 kg):
              Iron Longsword (2.5 kg)
              Leather Gloves (0.5 kg)
              Gold: 50 coins
              Wheat: 7 bushels
        """
        lines = []
        current = self.current_contents_weight or 0.0
        capacity = self.max_container_capacity_kg or 0.0
        lines.append(f"|w{self.key}|n ({current:.1f} / {capacity:.1f} kg):")

        # NFT items
        for obj in self.contents:
            weight = getattr(obj, "weight", 0.0) or 0.0
            lines.append(f"  {obj.key} ({weight:.1f} kg)")

        # Fungibles
        if hasattr(self, "get_fungible_display"):
            fungible_text = self.get_fungible_display()
            if fungible_text and fungible_text != "Nothing.":
                for line in fungible_text.split("\n"):
                    lines.append(f"  {line}")

        if len(lines) == 1:
            lines.append("  Empty.")

        return "\n".join(lines)

    # ================================================================== #
    #  Weight Tracking — NFT items via Evennia hooks
    # ================================================================== #

    def at_object_receive(self, moved_obj, source_location, **kwargs):
        """Track weight when an object enters this container."""
        super().at_object_receive(moved_obj, source_location, **kwargs)
        weight = getattr(moved_obj, "weight", 0.0) or 0.0
        if weight > 0:
            self.current_contents_weight = (
                (self.current_contents_weight or 0.0) + weight
            )
            self._propagate_weight_to_carrier(weight)

    def at_object_leave(self, moved_obj, target_location, **kwargs):
        """Track weight when an object leaves this container."""
        super().at_object_leave(moved_obj, target_location, **kwargs)
        weight = getattr(moved_obj, "weight", 0.0) or 0.0
        if weight > 0:
            self.current_contents_weight = max(
                0.0, (self.current_contents_weight or 0.0) - weight
            )
            self._propagate_weight_to_carrier(-weight)

    # ================================================================== #
    #  Weight Tracking — Fungibles via _at_balance_changed override
    # ================================================================== #

    def _at_balance_changed(self):
        """
        Called when gold/resources change. Recalculate the fungible portion
        of contents weight and propagate delta to carrier.
        """
        old_total = self.current_contents_weight or 0.0

        # Rebuild: NFT weight from contents + fungible weight
        nft_weight = 0.0
        for obj in self.contents:
            nft_weight += getattr(obj, "weight", 0.0) or 0.0

        fungible_weight = 0.0
        if hasattr(self, "get_total_fungible_weight"):
            fungible_weight = self.get_total_fungible_weight()

        new_total = nft_weight + fungible_weight
        self.current_contents_weight = new_total

        delta = new_total - old_total
        if delta != 0:
            self._propagate_weight_to_carrier(delta)

    # ================================================================== #
    #  Weight Propagation to Carrier
    # ================================================================== #

    def _propagate_weight_to_carrier(self, delta):
        """
        If transfer_weight is True and this container is carried by
        something with weight tracking, propagate the weight delta.
        """
        if not (self.transfer_weight and delta != 0):
            return
        carrier = self.location
        if carrier and hasattr(carrier, "current_weight_nfts"):
            carrier.current_weight_nfts = (
                carrier.current_weight_nfts or 0.0
            ) + delta
            # Clamp to 0 to avoid float drift
            if carrier.current_weight_nfts < 0:
                carrier.current_weight_nfts = 0.0

    # ================================================================== #
    #  Full Recalculation (safety net)
    # ================================================================== #

    def recalculate_contents_weight(self):
        """
        Rebuild contents weight from scratch. Called on server restart
        via at_init() to catch any drift.
        """
        nft_weight = 0.0
        for obj in self.contents:
            nft_weight += getattr(obj, "weight", 0.0) or 0.0

        fungible_weight = 0.0
        if hasattr(self, "get_total_fungible_weight"):
            fungible_weight = self.get_total_fungible_weight()

        self.current_contents_weight = nft_weight + fungible_weight

    def at_init(self):
        """Recalculate on every server restart/cache load."""
        super().at_init()
        self.recalculate_contents_weight()
