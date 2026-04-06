"""
Stable commands — stable, retrieve, and list stabled pets.

Usage:
    stable <pet>     — stable a pet here (costs 1 gold)
    retrieve <pet>   — retrieve a stabled pet
    stabled          — list your stabled pets at this stable
"""

from evennia import Command

from commands.command import FCMCommandMixin


class CmdStable(FCMCommandMixin, Command):
    """
    Stable a pet for safekeeping.

    Usage:
        stable <pet>

    Costs 1 gold. Stabled pets don't consume food and can't be
    attacked. Retrieve them when you're ready to adventure again.
    """

    key = "stable"
    locks = "cmd:all()"
    help_category = "Pets"

    def func(self):
        caller = self.caller
        room = caller.location

        if not self.args or not self.args.strip():
            caller.msg("Stable what? Usage: stable <pet name>")
            return

        pet_name = self.args.strip().lower()

        # Find the pet in the room
        pet = None
        for obj in room.contents:
            if (
                getattr(obj, "is_pet", False)
                and getattr(obj, "owner_key", None) == caller.key
                and obj.key.lower().startswith(pet_name)
            ):
                pet = obj
                break

        if not pet:
            caller.msg(f"You don't have a pet called '{self.args.strip()}' here.")
            return

        if pet.pet_state == "stabled":
            caller.msg(f"{pet.key} is already stabled.")
            return

        # Check gold
        fee = getattr(room, "stable_fee", 1)
        if hasattr(caller, "get_gold") and caller.get_gold() < fee:
            caller.msg(f"You need {fee} gold to stable {pet.key}.")
            return

        # Dismount if mounted
        if hasattr(pet, "is_mounted") and pet.is_mounted:
            pet.force_dismount()

        # Pay fee
        if fee > 0 and hasattr(caller, "_remove_gold"):
            caller._remove_gold(fee)

        # Stable the pet
        pet.stop_following()
        pet.pet_state = "stabled"
        pet.set_world_location(room)

        # Move pet out of the visible room (to a hidden holding spot)
        # Pet stays in the room but is hidden from display
        pet.db.stabled_at = room

        caller.msg(
            f"You stable {pet.key} for {fee} gold. "
            f"It will be safe here until you retrieve it."
        )
        if room:
            room.msg_contents(
                f"{caller.key} stables {pet.key}.",
                exclude=[caller], from_obj=caller,
            )


class CmdRetrieve(FCMCommandMixin, Command):
    """
    Retrieve a stabled pet.

    Usage:
        retrieve <pet>

    Free to retrieve. The pet will be waiting for you here.
    """

    key = "retrieve"
    locks = "cmd:all()"
    help_category = "Pets"

    def func(self):
        caller = self.caller
        room = caller.location

        if not self.args or not self.args.strip():
            caller.msg("Retrieve what? Usage: retrieve <pet name>")
            return

        pet_name = self.args.strip().lower()

        # Find stabled pet belonging to caller at this stable
        pet = None
        for obj in room.contents:
            if (
                getattr(obj, "is_pet", False)
                and getattr(obj, "owner_key", None) == caller.key
                and getattr(obj, "pet_state", None) == "stabled"
                and obj.key.lower().startswith(pet_name)
            ):
                pet = obj
                break

        if not pet:
            caller.msg(
                f"You don't have a pet called '{self.args.strip()}' stabled here. "
                f"Use |wstabled|n to see your stabled pets."
            )
            return

        # Retrieve
        pet.pet_state = "following"
        pet.start_following(caller)
        pet.db.stabled_at = None
        pet.feed()  # reset hunger timer on retrieval

        caller.msg(f"You retrieve {pet.key}. It begins following you.")
        if room:
            room.msg_contents(
                f"{caller.key} retrieves {pet.key} from the stable.",
                exclude=[caller], from_obj=caller,
            )


class CmdStabled(FCMCommandMixin, Command):
    """
    List your stabled pets at this stable.

    Usage:
        stabled
    """

    key = "stabled"
    locks = "cmd:all()"
    help_category = "Pets"

    def func(self):
        caller = self.caller
        room = caller.location

        stabled = [
            obj for obj in room.contents
            if getattr(obj, "is_pet", False)
            and getattr(obj, "owner_key", None) == caller.key
            and getattr(obj, "pet_state", None) == "stabled"
        ]

        if not stabled:
            caller.msg("You have no pets stabled here.")
            return

        lines = ["|w--- Stabled Pets ---|n"]
        for pet in stabled:
            lines.append(f"  |c{pet.key}|n — {pet.hp}/{pet.hp_max} HP")
        caller.msg("\n".join(lines))
