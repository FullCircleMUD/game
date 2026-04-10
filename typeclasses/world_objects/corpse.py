"""
Corpse object — spawned when a character dies.

Holds the dead character's NFT items (in contents), gold, and resources
(via FungibleInventoryMixin). Two timed phases:

    0-5 min:  owner-only looting (locked to the character who died)
    5-10 min: anyone can loot
    10 min:   corpse despawns, all contents returned to RESERVE

Timestamps are persisted so timers can be recalculated on server restart.
"""

from datetime import datetime, timezone as dt_timezone

from evennia import AttributeProperty
from evennia.objects.objects import DefaultObject
from evennia.utils.utils import delay

from enums.death_cause import DeathCause
from typeclasses.mixins.fungible_inventory import FungibleInventoryMixin
from typeclasses.mixins.height_aware_mixin import HeightAwareMixin

# Timer durations in seconds
UNLOCK_DELAY = 300   # 5 minutes — after this, anyone can loot
DESPAWN_DELAY = 600  # 10 minutes — corpse disappears


class Corpse(HeightAwareMixin, FungibleInventoryMixin, DefaultObject):
    """
    A corpse left behind when a character dies.

    NFT items are stored in self.contents (standard Evennia containment).
    Gold and resources are stored via FungibleInventoryMixin.
    """

    owner_character_key = AttributeProperty(None)
    owner_name = AttributeProperty("someone")
    cause_of_death = AttributeProperty("unknown")
    unlock_at = AttributeProperty(None)    # datetime: when anyone can loot
    despawn_at = AttributeProperty(None)   # datetime: when corpse disappears
    is_unlocked = AttributeProperty(False)

    def at_object_creation(self):
        super().at_object_creation()
        self.at_fungible_init()
        self.locks.add("get:false()")

    # ------------------------------------------------------------------ #
    #  Display
    # ------------------------------------------------------------------ #

    def get_display_name(self, looker=None, **kwargs):
        return f"corpse of {self.owner_name}"

    def get_display_desc(self, looker, **kwargs):
        try:
            cause = DeathCause(self.cause_of_death)
        except ValueError:
            cause = DeathCause.UNKNOWN
        return cause.corpse_desc(self.owner_name)

    def return_appearance(self, looker, **kwargs):
        """Show corpse description plus contents when looked at."""
        lines = [self.get_display_desc(looker)]

        # NFT items
        items = [obj for obj in self.contents if obj != looker]
        if items:
            lines.append("\nItems:")
            for item in items:
                lines.append(f"  {item.get_display_name(looker)}")

        # Fungibles
        fungible_display = self.get_fungible_display()
        if fungible_display and fungible_display != "Nothing.":
            lines.append(f"\n{fungible_display}")

        return "\n".join(lines)

    # ------------------------------------------------------------------ #
    #  Timers
    # ------------------------------------------------------------------ #

    def start_timers(self):
        """Schedule the unlock and despawn timers. Store timestamps."""
        now = datetime.now(dt_timezone.utc)
        self.unlock_at = now.timestamp() + UNLOCK_DELAY
        self.despawn_at = now.timestamp() + DESPAWN_DELAY

        delay(UNLOCK_DELAY, self.unlock)
        delay(DESPAWN_DELAY, self.despawn)

    def start_mob_timers(self, despawn_seconds=300):
        """Schedule despawn only — mob corpses are immediately lootable."""
        now = datetime.now(dt_timezone.utc)
        self.is_unlocked = True
        self.despawn_at = now.timestamp() + despawn_seconds
        delay(despawn_seconds, self.despawn)

    def restart_timers(self):
        """
        Recalculate and reschedule timers after a server restart.
        Called from at_server_startstop.
        """
        now = datetime.now(dt_timezone.utc).timestamp()

        # Despawn check first — if past despawn time, clean up immediately
        if self.despawn_at and now >= self.despawn_at:
            self.despawn()
            return

        # Unlock check
        if self.unlock_at and now >= self.unlock_at:
            self.unlock()
        elif self.unlock_at:
            remaining = max(1, int(self.unlock_at - now))
            delay(remaining, self.unlock)

        # Despawn timer
        if self.despawn_at:
            remaining = max(1, int(self.despawn_at - now))
            delay(remaining, self.despawn)

    def unlock(self):
        """Allow anyone to loot this corpse."""
        if not self.pk:
            return  # already deleted
        if self.is_unlocked:
            return
        self.is_unlocked = True
        if self.location:
            self.location.msg_contents(
                f"The corpse of {self.owner_name} can now be looted by anyone."
            )

    def despawn(self):
        """Return all contents to RESERVE and delete the corpse."""
        if not self.pk:
            return  # already deleted

        from typeclasses.items.base_nft_item import BaseNFTItem

        # Return NFT items to reserve (delete triggers at_object_delete → NFTService)
        for obj in list(self.contents):
            if isinstance(obj, BaseNFTItem):
                obj.delete()

        # Return gold to reserve
        gold = self.get_gold()
        if gold > 0:
            self.return_gold_to_reserve(gold)

        # Return resources to reserve
        for rid, amt in list(self.get_all_resources().items()):
            if amt > 0:
                self.return_resource_to_reserve(rid, amt)

        if self.location:
            self.location.msg_contents(
                f"The corpse of {self.owner_name} crumbles to dust."
            )
        self.delete()

    # ------------------------------------------------------------------ #
    #  Loot access check
    # ------------------------------------------------------------------ #

    def can_loot(self, character):
        """
        Check if a character is allowed to loot this corpse.
        Owner can always loot. Others only after unlock.
        """
        if (
            self.owner_character_key is not None
            and hasattr(character, "db")
            and character.key == self.owner_character_key
        ):
            return True
        return self.is_unlocked
