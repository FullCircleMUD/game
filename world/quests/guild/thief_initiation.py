"""
Thief Initiation — guild quest for joining the Thieves Guild.

The guildmaster (Gareth Stonefield) sends the aspirant to complete
the Thieves' Gauntlet — a static 3-room challenge off the Training
Alcove in the Thieves' Lair. The aspirant must navigate traps, find
hidden levers and keys, and retrieve a shadow guild token from a
locked chest at the end.

Return the token to Gareth to complete the quest and join the guild.

Quest acceptance is gated on:
  - levels_to_spend > 0
  - Not already a thief
  - Meets race/alignment/remort requirements
  - Meets multiclass ability requirements (DEX 14) if multiclassing
"""

from world.quests import register_quest
from world.quests.base_quest import FCMQuest


@register_quest
class ThiefInitiation(FCMQuest):
    key = "thief_initiation"
    name = "The Shadow Trial"
    desc = (
        "Gareth Stonefield leans close, his voice barely a whisper. "
        "\"You want in? Then prove you can think like one of us. The "
        "gauntlet is right here in the lair — find the hidden entrance "
        "in the Training Alcove. Don't go wandering off into the sewers "
        "looking for it, it's under your nose. Navigate what's inside, "
        "retrieve the guild token from the vault, and bring it back to "
        "me. If you make it back with the token, you're one of us.\""
    )
    quest_type = "guild"
    start_step = "retrieve"
    reward_xp = 100

    help_retrieve = (
        "Find the hidden entrance in the Training Alcove (it's right "
        "here in the Thieves' Lair — search carefully). Navigate the "
        "gauntlet, retrieve the shadow guild token from the vault chest, "
        "and return it to Gareth Stonefield."
    )
    help_completed = "You have proven yourself and joined the Thieves Guild."
    help_failed = (
        "You have no levels available to spend. Gain more experience "
        "and return to the Guildmaster."
    )

    # ── Token identification ──
    TOKEN_KEY = "a shadow guild token"

    # ── Acceptance checks ──

    @classmethod
    def can_accept(cls, character):
        can, reason = super().can_accept(character)
        if not can:
            return (can, reason)

        if character.levels_to_spend <= 0:
            return (False,
                    "You have no levels to spend. Gain more experience "
                    "before seeking guild membership.")

        classes = character.db.classes or {}
        if "thief" in classes:
            return (False, "You are already a member of the Thieves Guild.")

        from typeclasses.actors.char_classes import get_char_class
        char_class = get_char_class("thief")
        if char_class and not char_class.char_can_take_class(character):
            return (False,
                    "You do not meet the basic requirements to become "
                    "a Thief.")

        is_multiclass = len(classes) > 0
        if is_multiclass and char_class and char_class.multi_class_requirements:
            from enums.abilities_enum import Ability
            for ability, min_score in char_class.multi_class_requirements.items():
                current_score = getattr(character, ability.value, 0)
                if current_score < min_score:
                    return (False,
                            f"You need {ability.name} {min_score} to join "
                            f"this guild, but yours is only {current_score}.")

        return (True, "")

    # ── Progress check — do they have the token? ──

    def step_retrieve(self, *args, **kwargs):
        """Check if character has the guild token in inventory."""
        for obj in self.quester.contents:
            if obj.key == self.TOKEN_KEY:
                # Return the token to the vault chest
                self._return_token(obj)
                self.complete()
                return

    def _return_token(self, token):
        """Put token back and reset the gauntlet for the next aspirant."""
        from evennia import ObjectDB

        # Find the vault room in the sewers
        vault = None
        vaults = ObjectDB.objects.filter(db_key="The Vault")
        for v in vaults:
            if v.tags.get("millholm_sewers", category="district"):
                vault = v
                break

        if vault:
            # Return token to chest
            for obj in vault.contents:
                if obj.key == "a heavy iron chest":
                    token.move_to(obj, quiet=True)
                    # Re-lock the chest
                    if hasattr(obj, "is_locked"):
                        obj.is_locked = True
                        obj.is_open = False
                    break
            else:
                token.delete()
        else:
            token.delete()

        # Reset all gauntlet rooms — re-arm traps, re-hide fixtures,
        # close doors, re-hide the hidden lever and key
        gauntlet_keys = [
            "Narrow Corridor", "Damp Chamber", "The Vault",
        ]
        for room_key in gauntlet_keys:
            rooms = ObjectDB.objects.filter(db_key=room_key)
            for room in rooms:
                if not room.tags.get("millholm_sewers", category="district"):
                    continue
                for obj in room.contents:
                    # Re-arm traps
                    if hasattr(obj, "trap_armed") and hasattr(obj, "is_trapped"):
                        if obj.is_trapped:
                            obj.trap_armed = True
                            obj.trap_detected = False
                    # Re-hide hidden objects (lever, key)
                    if hasattr(obj, "is_hidden") and hasattr(obj, "find_dc"):
                        if obj.find_dc > 0:
                            obj.is_hidden = True
                            if hasattr(obj, "discovered_by"):
                                obj.discovered_by = set()
                    # Reset switch fixtures (levers)
                    if hasattr(obj, "is_activated"):
                        obj.is_activated = False
                    # Close and re-lock doors
                    if hasattr(obj, "is_open") and hasattr(obj, "set_direction"):
                        obj.is_open = False
                        if hasattr(obj, "is_locked"):
                            obj.is_locked = False  # doors aren't locked, just closed

        # Also reset the hidden entrance panel in Training Alcove
        alcoves = ObjectDB.objects.filter(db_key="Training Alcove")
        for alcove in alcoves:
            if not alcove.tags.get("millholm_sewers", category="district"):
                continue
            for obj in alcove.contents:
                if hasattr(obj, "is_hidden") and hasattr(obj, "find_dc"):
                    if obj.find_dc > 0:
                        obj.is_hidden = True
                        if hasattr(obj, "discovered_by"):
                            obj.discovered_by = set()

    # ── Completion ──

    def on_complete(self):
        """Grant thief level 1 on quest completion."""
        character = self.quester

        if character.levels_to_spend <= 0:
            self.status = "failed"
            character.msg(
                "|rGareth shakes his head. \"You proved yourself, "
                "but you have no levels to spend on your training. "
                "Return when you have gained more experience.\"|n"
            )
            return

        character.levels_to_spend -= 1

        from typeclasses.actors.char_classes import get_char_class
        char_class = get_char_class("thief")
        char_class.at_char_first_gaining_class(character)

        character.msg(
            f"\n|g*** Gareth Stonefield nods approvingly. \"You found the "
            f"door. You survived the traps. You retrieved the token. "
            f"That makes you one of us, {character.key}. Welcome to the "
            f"shadows.\" ***|n\n"
            f"You are now a level 1 Thief.\n"
            f"Type |wguild|n to see your progress, or |wadvance|n to "
            f"spend additional levels."
        )

        if character.location:
            character.location.msg_contents(
                f"{character.key} has been inducted into the Thieves Guild!",
                exclude=[character],
                from_obj=character,
            )
