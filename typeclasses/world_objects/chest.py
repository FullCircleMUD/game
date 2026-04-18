"""
WorldChest — an immovable container that can be opened, closed, and locked.

Holds NFT items (via Evennia containment) and fungibles (via
FungibleInventoryMixin). Container access is gated on open/closed state.

MRO: ContainerMixin before FungibleInventoryMixin, closeable/lockable
before WorldFixture so can_open() override chains correctly.

Usage (build script / prototype):
    chest = create_object(WorldChest, key="an iron chest",
                          location=room)
    chest.is_locked = True
    chest.lock_dc = 20
    chest.key_tag = "iron_chest_key"
    chest.relock_seconds = 300  # re-locks after 5 minutes
"""

from evennia import AttributeProperty

from enums.size import Size
from typeclasses.mixins.closeable import CloseableMixin
from typeclasses.mixins.container import ContainerMixin
from typeclasses.mixins.fungible_inventory import FungibleInventoryMixin
from typeclasses.mixins.lockable import LockableMixin
from typeclasses.mixins.smashable import SmashableMixin
from typeclasses.world_objects.base_fixture import WorldFixture


class WorldChest(
    SmashableMixin,
    LockableMixin,
    CloseableMixin,
    ContainerMixin,
    FungibleInventoryMixin,
    WorldFixture,
):
    """
    An immovable container with open/close and lock/unlock support.

    Chests start closed (override CloseableMixin default).
    Contents are only accessible when open.
    """

    size = AttributeProperty(Size.SMALL.value)

    # Override CloseableMixin default — chests start closed
    is_open = AttributeProperty(False)

    # ── Spawn capacity ──
    # Max gold this chest can hold for the spawn system. 0 = no gold.
    loot_gold_max = AttributeProperty(0)
    # Per-tier max dicts for scroll/recipe capacity. Empty = none.
    # e.g. {"basic": 1} = one basic-tier scroll.
    spawn_scrolls_max = AttributeProperty({})
    spawn_recipes_max = AttributeProperty({})

    def at_object_creation(self):
        super().at_object_creation()
        self.at_smashable_init()
        self.at_closeable_init()
        self.at_lockable_init()
        self.at_container_init()
        self.at_fungible_init()

        # Unified spawn system: gold tag
        if self.loot_gold_max > 0:
            self.tags.add("spawn_gold", category="spawn_gold")
            self.db.spawn_gold_max = self.loot_gold_max

        # Knowledge loot: scrolls and recipes
        if self.spawn_scrolls_max:
            self.tags.add("spawn_scrolls", category="spawn_scrolls")
            self.db.spawn_scrolls_max = dict(self.spawn_scrolls_max)
        if self.spawn_recipes_max:
            self.tags.add("spawn_recipes", category="spawn_recipes")
            self.db.spawn_recipes_max = dict(self.spawn_recipes_max)

    # ------------------------------------------------------------------ #
    #  Access gating on open/closed state
    # ------------------------------------------------------------------ #

    def at_object_receive(self, moved_obj, source_location, **kwargs):
        """Only accept items when open."""
        if not self.is_open:
            # Silently reject — command layer should check first
            return
        super().at_object_receive(moved_obj, source_location, **kwargs)

    # ------------------------------------------------------------------ #
    #  Display
    # ------------------------------------------------------------------ #

    def return_appearance(self, looker, **kwargs):
        """Show chest state and contents when open."""
        name = self.get_display_name(looker)
        state = "open" if self.is_open else "closed"
        locked = " and locked" if self.is_locked else ""

        lines = [f"|w{name}|n ({state}{locked})"]

        if self.db.desc:
            lines.append(self.db.desc)

        if self.is_open:
            # Show contents
            contents_display = self.get_container_display()
            # get_container_display includes the name header — strip it
            # and just show the content lines
            content_lines = contents_display.split("\n")[1:]  # skip header
            if content_lines:
                lines.append("\nContents:")
                lines.extend(content_lines)
            else:
                lines.append("\nIt's empty.")
        else:
            lines.append("It is closed.")

        return "\n".join(lines)
