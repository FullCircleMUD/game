"""
Pet command — routing layer for pet interactions.

Finds the owner's active pet(s) in the room and delegates subcommands
to them. Phase 1 supports a single pet; future phases will add dot
syntax for multiple pets (pet.dog, pet.horse).

Usage:
    pet                     — show status of your pet(s) in the room
    pet follow              — pet starts following you
    pet stay                — pet stops following, waits here
    pet feed                — feed the pet (resets hunger timer)
    pet status              — show pet name, state, hunger
    pet attack <target>     — pet attacks a target (combat pets only)
"""

from evennia import Command

from commands.command import FCMCommandMixin


class CmdPet(FCMCommandMixin, Command):
    """
    Interact with your pet.

    Usage:
        pet                 — show pet status
        pet follow          — pet follows you
        pet stay            — pet waits here
        pet feed            — feed your pet
        pet status          — detailed pet status
        pet attack <target> — pet attacks (combat pets only)

    Your pet must be in the same room as you.
    """

    key = "pet"
    locks = "cmd:all()"
    help_category = "Pets"

    def func(self):
        caller = self.caller
        args = self.args.strip().lower() if self.args else ""

        # Find owner's pets in this room
        pets = self._find_my_pets(caller)

        if not pets:
            caller.msg("You don't have a pet here.")
            return

        # Phase 1: single pet (first found)
        pet = pets[0]

        if not args or args == "status":
            self._show_status(caller, pet)
        elif args == "follow":
            self._cmd_follow(caller, pet)
        elif args == "stay":
            self._cmd_stay(caller, pet)
        elif args == "feed":
            self._cmd_feed(caller, pet)
        elif args.startswith("attack"):
            target_str = args[6:].strip()  # strip "attack"
            self._cmd_attack(caller, pet, target_str)
        else:
            caller.msg(
                "Unknown pet command. Try: pet follow, pet stay, "
                "pet feed, pet status, pet attack <target>"
            )

    def _find_my_pets(self, caller):
        """Find all pets owned by caller in the same room."""
        if not caller.location:
            return []
        return [
            obj for obj in caller.location.contents
            if getattr(obj, "is_pet", False)
            and getattr(obj, "owner_key", None) == caller.key
        ]

    def _show_status(self, caller, pet):
        """Display pet status."""
        lines = [f"\n|w{pet.key}|n"]
        lines.append(f"  State:  {pet.pet_state.capitalize()}")
        lines.append(f"  Health: {pet.hp}/{pet.hp_max}")
        lines.append(f"  Hunger: {pet.get_hunger_display()}")
        lines.append(f"  Size:   {pet.size.capitalize()}")
        caller.msg("\n".join(lines))

    def _cmd_follow(self, caller, pet):
        """Tell the pet to follow."""
        if pet.pet_state == "following" and pet.following == caller:
            caller.msg(f"{pet.key} is already following you.")
            return
        pet.start_following(caller)
        caller.msg(f"{pet.key} begins following you.")
        if caller.location:
            caller.location.msg_contents(
                f"{pet.key} begins following {caller.key}.",
                exclude=[caller], from_obj=pet,
            )

    def _cmd_stay(self, caller, pet):
        """Tell the pet to stay."""
        if pet.pet_state == "waiting":
            caller.msg(f"{pet.key} is already waiting here.")
            return
        pet.stop_following()
        caller.msg(f"You tell {pet.key} to stay.")
        if caller.location:
            caller.location.msg_contents(
                f"{caller.key} tells {pet.key} to stay.",
                exclude=[caller], from_obj=caller,
            )

    def _cmd_feed(self, caller, pet):
        """Feed the pet."""
        # Phase 1: free feeding, no food item required
        pet.feed()
        caller.msg(f"You feed {pet.key}. It looks content.")
        if caller.location:
            caller.location.msg_contents(
                f"{caller.key} feeds {pet.key}.",
                exclude=[caller], from_obj=caller,
            )

    def _cmd_attack(self, caller, pet, target_str):
        """Command the pet to attack a target."""
        if not hasattr(pet, "initiate_attack"):
            caller.msg(f"{pet.key} doesn't know how to fight.")
            return

        if not target_str:
            caller.msg("Attack what? Usage: pet attack <target>")
            return

        target = caller.search(target_str, location=caller.location)
        if not target:
            return

        if target == pet:
            caller.msg(f"{pet.key} looks at you, confused.")
            return

        if target == caller:
            caller.msg(f"{pet.key} refuses to attack you.")
            return

        if getattr(target, "hp", None) is None or target.hp <= 0:
            caller.msg("That's not a valid target.")
            return

        pet.initiate_attack(target)
        caller.msg(f"You command {pet.key} to attack {target.key}!")
