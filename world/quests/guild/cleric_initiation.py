"""
Cleric Initiation — guild quest for joining the Temple.

Brother Aldric asks the aspirant to demonstrate compassion by baking
bread and giving it to the beggar in Beggar's Alley behind the temple.

Flow:
  1. Accept quest via ``quest accept`` at Brother Aldric (Shrine)
  2. Bake or acquire bread (resource ID 3)
  3. Walk into Beggar's Alley (room tagged ``quest_tags=["cleric_initiation"]``)
  4. QuestTagMixin fires ``step_feed_beggar(event_type="enter_room")``
  5. If player has bread → consume it, narrative, complete

On completion, the character is inducted as a level 1 Cleric (consuming
one levels_to_spend).

Quest acceptance is gated on:
  - levels_to_spend > 0
  - Not already a cleric
  - Meets race/alignment/remort requirements (no evil alignments)
  - Meets multiclass ability requirements (WIS 14) if multiclassing
"""

from world.quests import register_quest
from world.quests.base_quest import FCMQuest


# Resource IDs (from seeded resource types)
BREAD_ID = 3


@register_quest
class ClericInitiation(FCMQuest):
    key = "cleric_initiation"
    name = "Feed the Hungry"
    desc = (
        "Brother Aldric regards you with gentle, searching eyes. \"Those who "
        "serve the divine must first serve the people. There is a beggar who "
        "shelters in the alley behind our temple — hungry, forgotten by most. "
        "Bake a loaf of bread and bring it to him. Not to me — to him. Show "
        "me that compassion lives in your heart.\""
    )
    quest_type = "guild"
    start_step = "feed_beggar"
    reward_xp = 100

    help_feed_beggar = (
        "Bake a loaf of bread and bring it to the beggar in Beggar's Alley "
        "behind the temple. Visit the alley with bread in your inventory."
    )
    help_completed = "You have proven your compassion and joined the Temple."
    help_failed = (
        "You have no levels available to spend. Gain more experience "
        "and return to Brother Aldric."
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
        if "cleric" in classes:
            return (False, "You are already a member of the Temple.")

        from typeclasses.actors.char_classes import get_char_class
        char_class = get_char_class("cleric")
        if char_class and not char_class.char_can_take_class(character):
            return (False,
                    "You do not meet the basic requirements to become "
                    "a Cleric.")

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

    # ── Step method ──

    def step_feed_beggar(self, *args, **kwargs):
        """
        Triggered by QuestTagMixin when player enters Beggar's Alley,
        or by ``quest`` command at the guildmaster.
        """
        event_type = kwargs.get("event_type")
        if event_type == "enter_room":
            # Entered Beggar's Alley — check for bread
            if not self.quester.has_resource(BREAD_ID, 1):
                self.quester.msg(
                    "|yThe beggar looks up at you with hollow, hungry eyes.|n"
                )
                return
            # Has bread — feed the beggar
            self.quester.return_resource_to_sink(BREAD_ID, 1)
            self.quester.msg(
                "|gYou kneel beside the beggar and offer him the bread. His "
                "trembling hands close around the loaf and he stares at it "
                "for a long moment before tearing off a piece. \"Bless you,\" "
                "he whispers, his voice cracking. \"Bless you.\"|n"
            )
            self.complete()
        else:
            # Triggered by 'quest' command at the guildmaster
            self.quester.msg(
                "|yBake a loaf of bread and bring it to the beggar in "
                "Beggar's Alley, behind the temple.|n"
            )

    # ── Completion ──

    def on_complete(self):
        """Grant cleric level 1 on quest completion."""
        character = self.quester

        if character.levels_to_spend <= 0:
            self.status = "failed"
            character.msg(
                "|rBrother Aldric shakes his head gently. \"Your heart "
                "is willing, but you have no levels to spend on divine "
                "training. Return when you have gained more experience.\"|n"
            )
            return

        character.levels_to_spend -= 1

        from typeclasses.actors.char_classes import get_char_class
        char_class = get_char_class("cleric")
        char_class.at_char_first_gaining_class(character)

        character.msg(
            f"\n|g*** Brother Aldric places a hand on your brow. "
            f"\"The divine light welcomes you, {character.key}. You fed "
            f"the hungry not because you were told to, but because it was "
            f"right. Go forth and bring healing to a wounded world.\" ***|n\n"
            f"You are now a level 1 Cleric.\n"
            f"Type |wguild|n to see your progress, or |wadvance|n to "
            f"spend additional levels."
        )

        if character.location:
            character.location.msg_contents(
                f"{character.key} has been inducted into the Temple!",
                exclude=[character],
                from_obj=character,
            )
