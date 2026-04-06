"""
Stable commands — stable, retrieve, and list stabled pets.

Stabling moves the pet to the character's AccountBank (same as banking
an item). Retrieving moves it back to the room. The NFTPetMirrorMixin
handles all mirror DB transitions via at_post_move hooks.

Usage:
    stable <pet>     — stable a pet here (dynamic cost)
    retrieve <pet>   — retrieve a stabled pet
    stabled          — list your stabled pets
"""

from evennia import Command

from commands.command import FCMCommandMixin
from commands.room_specific_cmds.bank.cmd_balance import ensure_bank


class CmdStable(FCMCommandMixin, Command):
    """
    Stable a pet for safekeeping.

    Usage:
        stable <pet>

    Cost: 1 gold base + feeding/healing if needed.
    Stabled pets are safe, fed, and healed.
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

        # Calculate dynamic cost
        base_fee = 1
        feed_cost = 0
        heal_cost = 0

        # Feed cost: 1 gold per hunger tier past fed
        if hasattr(pet, "check_hunger"):
            hunger = pet.check_hunger()
            if hunger == "hungry":
                feed_cost = 1
            elif hunger == "starving":
                feed_cost = 2

        # Heal cost: 1 gold per 20% HP missing
        hp_max = getattr(pet, "hp_max", 1) or 1
        hp_missing_pct = max(0, (hp_max - pet.hp) / hp_max)
        heal_cost = int(hp_missing_pct / 0.2)  # 0-5 gold

        total_fee = base_fee + feed_cost + heal_cost

        # Show cost breakdown
        breakdown = [f"  Stabling: {base_fee} gold"]
        if feed_cost > 0:
            breakdown.append(f"  Feeding:  {feed_cost} gold")
        if heal_cost > 0:
            breakdown.append(f"  Healing:  {heal_cost} gold")

        # Check gold
        if hasattr(caller, "get_gold") and caller.get_gold() < total_fee:
            caller.msg(
                f"Stabling {pet.key} costs {total_fee} gold:\n"
                + "\n".join(breakdown)
                + f"\nYou only have {caller.get_gold()} gold."
            )
            return

        # Dismount if mounted
        if hasattr(pet, "is_mounted") and pet.is_mounted:
            pet.force_dismount()

        # Pay fee
        if total_fee > 0 and hasattr(caller, "_remove_gold"):
            caller._remove_gold(total_fee)

        # Heal and feed before stabling
        pet.stop_following()
        pet.feed()
        pet.hp = hp_max

        # Move pet to account bank — at_post_move fires ROOM→ACCOUNT → bank()
        account = caller.account
        if not account:
            caller.msg("Something went wrong — no account found.")
            return
        bank = ensure_bank(account)
        pet.move_to(bank, quiet=True)

        caller.msg(
            f"You stable {pet.key} for {total_fee} gold:\n"
            + "\n".join(breakdown)
            + f"\n{pet.key} is fed, healed, and safe."
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

    Free to retrieve. The pet will appear here and follow you.
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
        account = caller.account
        if not account:
            caller.msg("Something went wrong — no account found.")
            return
        bank = ensure_bank(account)

        # Find stabled pet in bank contents — match by name or pet_type
        pet = None
        for obj in bank.contents:
            if (
                getattr(obj, "is_pet", False)
                and obj.key.lower().startswith(pet_name)
            ):
                pet = obj
                break

        if not pet:
            for obj in bank.contents:
                if (
                    getattr(obj, "is_pet", False)
                    and getattr(obj, "pet_type", "").lower().startswith(pet_name)
                ):
                    pet = obj
                    break

        if not pet:
            caller.msg(
                f"You don't have a pet called '{self.args.strip()}' stabled. "
                f"Use |wstabled|n to see your stabled pets."
            )
            return

        # Move pet from bank to room — at_post_move fires ACCOUNT→ROOM → unbank()
        pet.move_to(room, quiet=True)

        # Start following owner and reset hunger
        pet.start_following(caller)
        pet.feed()

        caller.msg(f"You retrieve {pet.key}. It begins following you.")
        if room:
            room.msg_contents(
                f"{caller.key} retrieves {pet.key} from the stable.",
                exclude=[caller], from_obj=caller,
            )


class CmdStabled(FCMCommandMixin, Command):
    """
    List your stabled pets.

    Usage:
        stabled
    """

    key = "stabled"
    locks = "cmd:all()"
    help_category = "Pets"

    def func(self):
        caller = self.caller
        account = caller.account
        if not account:
            caller.msg("You don't have a bank account.")
            return
        bank = ensure_bank(account)

        stabled = [
            obj for obj in bank.contents
            if getattr(obj, "is_pet", False)
        ]

        if not stabled:
            caller.msg("You have no pets stabled.")
            return

        lines = ["|w--- Stabled Pets ---|n"]
        for pet in stabled:
            pet_type = getattr(pet, "pet_type", "")
            type_str = f" ({pet_type})" if pet_type else ""
            lines.append(f"  |c{pet.key}|n{type_str} — {pet.hp}/{pet.hp_max} HP")
        caller.msg("\n".join(lines))
