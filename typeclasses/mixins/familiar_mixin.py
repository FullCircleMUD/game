"""
FamiliarMixin — adds remote control (scouting) to any pet.

Composable mixin that lets the owner see through the familiar's eyes,
move it room to room remotely, and receive room descriptions from the
familiar's location.

Usage:
    class FamiliarRat(FamiliarMixin, BasePet):
        ...

Attributes:
    is_familiar: bool marker for filtering
    creator_key: character_key of the caster who summoned this familiar
    is_scouting: True when being remote-controlled away from owner
"""

from evennia.typeclasses.attributes import AttributeProperty


# Direction aliases for remote movement
_DIRECTION_ALIASES = {
    "n": "north", "s": "south", "e": "east", "w": "west",
    "u": "up", "d": "down",
    "ne": "northeast", "nw": "northwest",
    "se": "southeast", "sw": "southwest",
    "north": "north", "south": "south", "east": "east", "west": "west",
    "up": "up", "down": "down",
    "northeast": "northeast", "northwest": "northwest",
    "southeast": "southeast", "southwest": "southwest",
}


class FamiliarMixin:
    """Mixin adding remote control / scouting to a pet."""

    is_familiar = True
    creator_key = AttributeProperty(None)
    is_scouting = AttributeProperty(False)

    def enter_scouting(self):
        """Enter scouting mode — stop following, allow remote control."""
        self.following = None
        self.is_scouting = True
        self.pet_state = "scouting"

    def exit_scouting(self):
        """Exit scouting mode."""
        self.is_scouting = False

    def remote_look(self, caster):
        """Send the familiar's current room description to the caster."""
        room = self.location
        if not room:
            caster.msg(f"|w[Through {self.key}'s eyes]|n Nothing — your familiar is nowhere.")
            return

        # Get the room appearance as the familiar sees it
        appearance = room.return_appearance(self)
        caster.msg(f"|w[Through {self.key}'s eyes]|n\n{appearance}")

    def remote_move(self, caster, direction):
        """Move the familiar in a direction and auto-look."""
        room = self.location
        if not room:
            caster.msg(f"{self.key} is nowhere — cannot move.")
            return False

        # Normalize direction
        canonical = _DIRECTION_ALIASES.get(direction.lower())
        if not canonical:
            caster.msg(f"'{direction}' is not a valid direction.")
            return False

        # Enter scouting mode if not already
        if not self.is_scouting:
            self.enter_scouting()

        # Find the exit
        target_exit = None
        for ex in room.exits:
            if ex.key.lower() == canonical or canonical in [a.lower() for a in getattr(ex, "aliases", [])]:
                target_exit = ex
                break

        if not target_exit:
            caster.msg(
                f"|w[Through {self.key}'s eyes]|n "
                f"There is no exit {canonical} from here."
            )
            return False

        # Check if exit is passable (closed doors etc.)
        if hasattr(target_exit, "is_open") and not target_exit.is_open:
            caster.msg(
                f"|w[Through {self.key}'s eyes]|n "
                f"The way {canonical} is blocked."
            )
            return False

        # Move the familiar
        old_room = room
        self.move_to(target_exit.destination, quiet=True, move_type="scout")

        # Announce in old room
        if old_room:
            old_room.msg_contents(
                f"{self.key} scurries {canonical}.",
                exclude=[self],
                from_obj=self,
            )

        # Announce in new room
        if self.location and self.location != old_room:
            self.location.msg_contents(
                f"{self.key} arrives.",
                exclude=[self],
                from_obj=self,
            )

        # Auto-look from new location
        self.remote_look(caster)
        return True

    def remote_return(self, caster):
        """Teleport the familiar back to the caster and resume following."""
        if self.location == caster.location and not self.is_scouting:
            caster.msg(f"{self.key} is already here.")
            return

        old_room = self.location

        # Announce departure
        if old_room and old_room != caster.location:
            old_room.msg_contents(
                f"{self.key} vanishes, returning to its master.",
                exclude=[self],
                from_obj=self,
            )

        # Teleport to caster
        self.move_to(caster.location, quiet=True, move_type="teleport")
        self.exit_scouting()
        self.start_following(caster)

        caster.msg(f"{self.key} returns to your side.")
        if caster.location:
            caster.location.msg_contents(
                f"{self.key} appears at {caster.key}'s side.",
                exclude=[caster],
                from_obj=self,
            )

    @classmethod
    def is_direction(cls, word):
        """Check if a word is a valid direction for remote movement."""
        return word.lower() in _DIRECTION_ALIASES
