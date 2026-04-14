"""
WaterContainerMixin — adds drinkable-water capacity to any object.

Used by canteens, casks, and any future container that holds water as a
numeric `current` state rather than as Evennia child objects. Mix into a
typeclass alongside `BaseNFTItem` (or whatever base) and call
`at_water_container_init()` from `at_object_creation()`.

The container does NOT live in the HOLD slot. It sits in `character.contents`
like bread or potions, and the `drink` command finds it by walking the
inventory. This means the player can drink without putting down their
weapon or torch — same model as eating bread mid-combat.

Container state (`current`, `max_capacity`) is persisted to the NFT mirror
metadata via the standard `persist_metadata()` helper, so a half-full
canteen survives bank/withdraw and chain export/import cycles.

Child classes MUST:
    1. Call at_water_container_init() from at_object_creation().
    2. Set `max_capacity` (in drinks) at the class or prototype level.
"""

from evennia.typeclasses.attributes import AttributeProperty


class WaterContainerMixin:
    """
    Mixin that gives an object a finite quantity of drinkable water.

    Attributes (db):
        max_capacity (int): Maximum drinks the container holds.
        current (int): Drinks remaining. Decrements on `drink_from()`,
            resets to `max_capacity` on `refill_to_full()`.

    Class-level:
        is_water_container (bool): Always True — used by command lookups.
    """

    is_water_container = True

    max_capacity = AttributeProperty(0)
    current = AttributeProperty(0)

    def at_water_container_init(self):
        """
        Initialize state from `max_capacity`. Call from at_object_creation().
        Safe to call multiple times. New containers spawn full.
        """
        if self.current == 0 and self.max_capacity > 0:
            self.current = self.max_capacity

    @property
    def is_empty(self):
        return self.current <= 0

    @property
    def is_full(self):
        return self.current >= self.max_capacity

    def drink_from(self, character):
        """
        Consume one drink and step the character's thirst meter up by one
        stage. No-op + message if empty or if the character has no thirst
        meter.

        Returns:
            (bool, str): (success, message)
        """
        if self.is_empty:
            return False, f"{self.key} is empty."

        thirst_level = getattr(character, "thirst_level", None)
        if thirst_level is None:
            return False, f"You can't drink from {self.key} right now."

        from enums.thirst_level import ThirstLevel
        if not isinstance(thirst_level, ThirstLevel):
            return False, f"You can't drink from {self.key} right now."

        # Step thirst up one stage (capped at REFRESHED).
        new_value = min(thirst_level.value + 1, ThirstLevel.REFRESHED.value)
        character.thirst_level = ThirstLevel(new_value)

        # If they hit REFRESHED via the drink, give them a free-pass tick so
        # they don't immediately drop one stage on the next survival tick.
        if character.thirst_level == ThirstLevel.REFRESHED:
            character.thirst_free_pass_tick = True

        self.current -= 1
        self._persist_water_state()

        return True, f"You drink from {self.key}."

    def refill_to_full(self):
        """
        Fill the container to max_capacity.

        Returns:
            (bool, str): (success, message)
        """
        if self.max_capacity <= 0:
            return False, f"{self.key} cannot hold water."
        if self.is_full:
            return False, f"{self.key} is already full."

        self.current = self.max_capacity
        self._persist_water_state()
        return True, f"{self.key} is full."

    def get_water_display(self):
        """Return a human-readable 'N/M drinks' string for inventory display."""
        if self.max_capacity <= 0:
            return ""
        return f"{self.current}/{self.max_capacity} drinks"

    def _persist_water_state(self):
        """
        Propagate `current` and `max_capacity` to the NFT mirror metadata.
        Silently no-ops on non-NFT consumers (e.g. mob-only or test fixtures)
        that lack NFTMirrorMixin.persist_metadata.
        """
        persist = getattr(self, "persist_metadata", None)
        if persist is None:
            return
        persist({
            "current": self.current,
            "max_capacity": self.max_capacity,
        })
