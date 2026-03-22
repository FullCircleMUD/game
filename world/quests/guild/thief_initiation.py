"""
Thief Initiation — guild quest for joining the Thieves Guild.

The guildmaster sends the aspirant to prove themselves by reaching
the deepest room of the Cave of Trials dungeon (the "BINGO!" room).

This is a single-step VisitQuest: when the character enters a room
tagged with quest_tags=["thief_initiation"], the quest completes.
The boss room in cave_dungeon.py carries that tag.

Quest acceptance is gated on:
  - levels_to_spend > 0
  - Not already a thief
  - Meets race/alignment/remort requirements
  - Meets multiclass ability requirements (DEX 14) if multiclassing
"""

from world.quests import register_quest
from world.quests.templates.visit_quest import VisitQuest


@register_quest
class ThiefInitiation(VisitQuest):
    key = "thief_initiation"
    name = "The Shadow Trial"
    desc = (
        "The guildmaster leans close, voice barely a whisper. \"You want in? "
        "Then prove you can survive. Enter the Cave of Trials beneath us and "
        "reach the deepest chamber. If you make it back alive, you're one of "
        "us. If not... well, we'll barely notice you were gone.\""
    )
    quest_type = "guild"
    start_step = "visit"
    reward_xp = 100

    help_visit = (
        "Reach the deepest chamber of the Cave of Trials. Enter the "
        "dungeon below the Thieves Guild and navigate to the final room."
    )
    help_completed = "You have proven yourself and joined the Thieves Guild."
    help_failed = (
        "You have no levels available to spend. Gain more experience "
        "and return to the Guildmaster."
    )

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

    # ── Override visit step to grant thief class ──

    def step_visit(self, *args, **kwargs):
        """Triggered by QuestTagMixin.fire_quest_event on boss room entry."""
        event_type = kwargs.get("event_type")
        if event_type == "enter_room":
            self.quester.msg(
                "|yYou have reached the deepest chamber of the Cave of Trials!|n"
            )
            self.complete()

    # ── Completion ──

    def on_complete(self):
        """Grant thief level 1 on quest completion."""
        character = self.quester

        if character.levels_to_spend <= 0:
            self.status = "failed"
            character.msg(
                "|rThe Guildmaster shakes her head. \"You proved yourself, "
                "but you have no levels to spend on your training. Return "
                "when you have gained more experience.\"|n"
            )
            return

        character.levels_to_spend -= 1

        from typeclasses.actors.char_classes import get_char_class
        char_class = get_char_class("thief")
        char_class.at_char_first_gaining_class(character)

        character.msg(
            f"\n|g*** The Guildmaster nods approvingly. \"You survived. That "
            f"makes you one of us, {character.key}. Welcome to the shadows.\" "
            f"***|n\n"
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
