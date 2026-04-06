"""
MountMixin — composable mounting capability for pets.

Compose onto any BasePet subclass that can be ridden. Tracks mounted
state and provides mount/dismount methods. The character's at_pre_move
and at_post_move check mounted state for room restrictions and
movement cost reduction.

Usage:
    class Horse(CombatCompanionMixin, MountMixin, BasePet):
        mount_movement_bonus = AttributeProperty(3)
"""

from evennia.typeclasses.attributes import AttributeProperty


class MountMixin:
    """Mixin that makes a pet rideable."""

    is_mounted = AttributeProperty(False)
    mounted_by = AttributeProperty(None)  # character key of rider
    mount_movement_bonus = AttributeProperty(3)  # move cost divisor when mounted

    def mount(self, rider):
        """
        Rider mounts this animal.

        Args:
            rider: the character mounting

        Returns:
            (bool, str) — (success, message)
        """
        if self.is_mounted:
            return (False, f"{self.key} is already being ridden.")

        if getattr(rider, "hp", 0) <= 0:
            return (False, "You can't mount anything in your state.")

        self.is_mounted = True
        self.mounted_by = rider.key
        rider.db.mounted_on = self

        return (True, f"You mount {self.key}.")

    def dismount(self, rider):
        """
        Rider dismounts.

        Args:
            rider: the character dismounting

        Returns:
            (bool, str) — (success, message)
        """
        if not self.is_mounted or self.mounted_by != rider.key:
            return (False, f"You are not riding {self.key}.")

        self.is_mounted = False
        self.mounted_by = None
        rider.db.mounted_on = None

        return (True, f"You dismount {self.key}.")

    def force_dismount(self):
        """Force dismount — used on pet death or emergency."""
        if not self.is_mounted:
            return
        # Find the rider and clear their state
        rider_key = self.mounted_by
        self.is_mounted = False
        self.mounted_by = None
        if rider_key:
            from evennia import search_object
            riders = [
                o for o in search_object(rider_key, exact=True)
                if getattr(o, "is_pc", False)
            ]
            for rider in riders:
                rider.db.mounted_on = None
                rider.msg(f"You are thrown from {self.key}!")
