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
from typeclasses.mixins.familiar_mixin import FamiliarMixin


class CmdPet(FCMCommandMixin, Command):
    """
    Interact with your pet.

    Usage:
        pet                    — show all pet status
        pet <command>          — command first/only pet
        pet.<name> <command>   — command a specific pet

    Commands: follow, stay, feed, status, attack <target>, mount, dismount,
             look, <direction>, return, dismiss, name <newname>

    Examples:
        pet follow
        pet.horse mount
        pet.dog attack goblin
        pet look                — see through familiar's eyes
        pet north               — move familiar north (remote scout)
        pet return              — recall familiar to your side
        pet dismiss             — dismiss a summoned familiar
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
                # Match against custom name (key) or type name (pet_type)
                if p.key.lower().startswith(pet_name):
                    pet = p
                    break
                pet_type = getattr(p, "pet_type", "")
                if pet_type and pet_type.lower().startswith(pet_name):
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
        elif args.startswith("name"):
            new_name = args[4:].strip()
            self._cmd_name(caller, pet, new_name)
        elif args == "look":
            self._cmd_remote_look(caller, pet)
        elif args == "return":
            self._cmd_remote_return(caller, pet)
        elif args == "dismiss":
            self._cmd_dismiss(caller, pet)
        elif FamiliarMixin.is_direction(args):
            self._cmd_remote_move(caller, pet, args)
        else:
            caller.msg(
                "Unknown pet command. Try: follow, stay, feed, status, "
                "attack <target>, mount, dismount, name <newname>, "
                "look, return, dismiss, <direction>"
            )

    def _find_my_pets(self, caller):
        """Find all pets owned by caller in the same room, plus scouting familiars."""
        pets = []
        if caller.location:
            pets = [
                obj for obj in caller.location.contents
                if getattr(obj, "is_pet", False)
                and getattr(obj, "owner_key", None) == caller.key
            ]

        # Also find scouting familiars (may be in another room)
        if not pets or not any(getattr(p, "is_familiar", False) for p in pets):
            from evennia import ObjectDB
            scouting = ObjectDB.objects.filter(
                db_tags__db_key="familiar",
                db_tags__db_category="pet_type",
            )
            for obj in scouting:
                if (getattr(obj, "is_familiar", False)
                        and getattr(obj, "owner_key", None) == caller.key
                        and getattr(obj, "is_scouting", False)
                        and obj not in pets):
                    pets.append(obj)

        return pets

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

    def _cmd_name(self, caller, pet, new_name):
        """Rename the pet."""
        if not new_name:
            caller.msg(f"Name it what? Usage: pet name <newname>")
            return

        # Capitalize and limit length
        new_name = new_name.strip()[:20].title()
        old_name = pet.key
        pet.key = new_name
        caller.msg(f"You name your {pet.pet_type or 'pet'} '{new_name}'.")
        if caller.location:
            caller.location.msg_contents(
                f"{caller.key} names their {pet.pet_type or 'pet'} '{new_name}'.",
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

    # ================================================================== #
    #  Familiar Remote Control
    # ================================================================== #

    def _cmd_remote_look(self, caller, pet):
        """See through the familiar's eyes."""
        if not getattr(pet, "is_familiar", False):
            caller.msg(f"{pet.key} isn't a familiar — you can't see through its eyes.")
            return
        pet.remote_look(caller)

    def _cmd_remote_move(self, caller, pet, direction):
        """Move the familiar in a direction remotely."""
        if not getattr(pet, "is_familiar", False):
            caller.msg(f"{pet.key} isn't a familiar — you can't control it remotely.")
            return
        pet.remote_move(caller, direction)

    def _cmd_remote_return(self, caller, pet):
        """Recall the familiar to the caster."""
        if not getattr(pet, "is_familiar", False):
            caller.msg(f"{pet.key} isn't a familiar — it can't be recalled.")
            return
        pet.remote_return(caller)

    def _cmd_dismiss(self, caller, pet):
        """Dismiss a summoned pet (magical pets only)."""
        creator_key = getattr(pet, "creator_key", None)
        if not creator_key:
            caller.msg(
                f"You can't dismiss {pet.key} — it isn't a magically "
                f"summoned creature."
            )
            return

        name = pet.key
        pet.delete()
        caller.msg(f"|C{name} vanishes in a shimmer of arcane energy.|n")
        if caller.location:
            caller.location.msg_contents(
                f"|C{name} vanishes in a shimmer of arcane energy.|n",
                exclude=[caller], from_obj=caller,
            )
