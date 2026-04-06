"""
Pet command — routing layer for pet interactions.

Finds the owner's active pet(s) in the room and delegates subcommands.
With multiple pets, use dot syntax to target a specific one.

Usage:
    pet                        — show status of all your pets here
    pet <command>              — command your pet (or first pet if multiple)
    pet.<name> <command>       — command a specific pet by name

    Commands:
        follow, stay, feed, status, attack <target>, mount, dismount

Examples:
    pet follow                 — first pet follows you
    pet.horse mount            — mount the horse specifically
    pet.dog attack goblin      — dog attacks goblin
    pet.mule stay              — mule stays here
"""

from evennia import Command

from commands.command import FCMCommandMixin


class CmdPet(FCMCommandMixin, Command):
    """
    Interact with your pet.

    Usage:
        pet                    — show all pet status
        pet <command>          — command first/only pet
        pet.<name> <command>   — command a specific pet

    Commands: follow, stay, feed, status, attack <target>, mount, dismount

    Examples:
        pet follow
        pet.horse mount
        pet.dog attack goblin
    """

    key = "pet"
    locks = "cmd:all()"
    help_category = "Pets"
    # Match "pet" and "pet.anything"
    arg_regex = r"(?:\.\w+)?\s|(?:\.\w+)?$"

    def func(self):
        caller = self.caller
        raw = self.args or ""

        # ── Parse dot syntax: "pet.horse mount" → pet_name="horse", args="mount"
        pet_name = None
        if raw.startswith("."):
            # ".horse mount" or ".horse"
            parts = raw.split(None, 1)
            pet_name = parts[0][1:].lower()  # strip leading dot
            args = parts[1].strip().lower() if len(parts) > 1 else ""
        else:
            args = raw.strip().lower()

        # Find owner's pets in this room
        pets = self._find_my_pets(caller)

        if not pets:
            caller.msg("You don't have a pet here.")
            return

        # Select pet — by name if dot syntax, else first
        if pet_name:
            pet = None
            for p in pets:
                if p.key.lower().startswith(pet_name):
                    pet = p
                    break
            if not pet:
                caller.msg(f"You don't have a pet called '{pet_name}' here.")
                return
        else:
            pet = pets[0]

        # ── Show all pets if no command
        if not args or args == "status":
            if not pet_name and len(pets) > 1:
                # Show all pets
                for p in pets:
                    self._show_status(caller, p)
                return
            self._show_status(caller, pet)
        elif args == "follow":
            self._cmd_follow(caller, pet)
        elif args == "stay":
            self._cmd_stay(caller, pet)
        elif args == "feed":
            self._cmd_feed(caller, pet)
        elif args.startswith("attack"):
            target_str = args[6:].strip()
            self._cmd_attack(caller, pet, target_str)
        elif args == "mount":
            self._cmd_mount(caller, pet)
        elif args == "dismount":
            self._cmd_dismount(caller, pet)
        else:
            caller.msg(
                "Unknown pet command. Try: follow, stay, feed, status, "
                "attack <target>, mount, dismount"
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

    def _cmd_mount(self, caller, pet):
        """Mount the pet."""
        if not hasattr(pet, "mount"):
            caller.msg(f"{pet.key} can't be ridden.")
            return

        # Already mounted on something?
        current_mount = caller.db.mounted_on
        if current_mount:
            caller.msg(f"You are already riding {current_mount.key}. Dismount first.")
            return

        success, msg = pet.mount(caller)
        caller.msg(msg)
        if success and caller.location:
            caller.location.msg_contents(
                f"{caller.key} mounts {pet.key}.",
                exclude=[caller], from_obj=caller,
            )

    def _cmd_dismount(self, caller, pet):
        """Dismount the pet."""
        if not hasattr(pet, "dismount"):
            caller.msg(f"You aren't riding {pet.key}.")
            return

        success, msg = pet.dismount(caller)
        caller.msg(msg)
        if success and caller.location:
            caller.location.msg_contents(
                f"{caller.key} dismounts {pet.key}.",
                exclude=[caller], from_obj=caller,
            )
