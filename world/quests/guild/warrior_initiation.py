"""
Warrior Initiation — guild quest for joining the Warriors Guild.

The guildmaster sends the aspirant to prove themselves in combat by clearing
the rats from the Harvest Moon cellar. If the character has already completed
the rat_cellar quest (e.g. via Rowan), the guildmaster recognises this and
inducts them immediately.

Quest acceptance is gated on:
  - levels_to_spend > 0
  - Not already a warrior
  - Meets race/alignment/remort requirements
  - Meets multiclass ability requirements (STR 14, CON 12) if multiclassing
"""

from world.quests import register_quest
from world.quests.base_quest import FCMQuest


@register_quest
class WarriorInitiation(FCMQuest):
    key = "warrior_initiation"
    name = "Trial of Arms"
    desc = (
        "Sergeant Grimjaw looks you up and down. \"You want to join The Iron "
        "Company? Fine. Prove you can handle yourself. The bartender at the "
        "Harvest Moon — Rowan — has a rat problem in his cellar. Go clear "
        "it out. Then we'll talk.\""
    )
    quest_type = "guild"
    start_step = "clear_rats"
    reward_xp = 100

    help_clear_rats = (
        "Go to the Harvest Moon Inn and clear the rats from Rowan's cellar. "
        "Prove you can handle yourself in a fight, then return to the "
        "guildmaster."
    )
    help_completed = "You have proven your worth and joined the Warriors Guild."
    help_failed = (
        "You have no levels available to spend. Gain more experience "
        "and return to the Guildmaster."
    )

    # ── Acceptance checks ──

    @classmethod
    def can_accept(cls, character):
        """
        Check if character can accept this quest.

        Gates:
          - levels_to_spend > 0
          - Not already a warrior
          - Meets race/alignment/remort requirements
          - Meets multiclass ability requirements (if multiclassing)
        """
        can, reason = super().can_accept(character)
        if not can:
            return (False, reason)

        # Must have a level to spend
        if character.levels_to_spend <= 0:
            return (False,
                    "You have no levels to spend. Gain more experience "
                    "before seeking guild membership.")

        # Must not already be a warrior
        classes = character.db.classes or {}
        if "warrior" in classes:
            return (False, "You are already a member of the Warriors Guild.")

        # Check race/alignment/remort requirements
        from typeclasses.actors.char_classes import get_char_class
        char_class = get_char_class("warrior")
        if char_class and not char_class.char_can_take_class(character):
            return (False,
                    "You do not meet the basic requirements to become "
                    "a Warrior.")

        # Check multiclass ability requirements
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

    # ── Accept hook ──

    def on_accept(self):
        """Check if rat_cellar is already done — if so, instant completion."""
        if (hasattr(self.quester, "quests")
                and self.quester.quests.is_completed("rat_cellar")):
            self.quester.msg(
                "\n|ySergent Grimjaw nods slowly. \"I heard about what you "
                "did for Rowan over at the Harvest Moon. You're exactly the "
                "kind of person we need around here.\"|n\n"
            )
            self.complete()

    # ── Step method ──

    def step_clear_rats(self, *args, **kwargs):
        """Check if the rat_cellar quest is now complete."""
        if (hasattr(self.quester, "quests")
                and self.quester.quests.is_completed("rat_cellar")):
            self.quester.msg(
                "\n|ySergent Grimjaw nods slowly. \"I heard about what you "
                "did for Rowan over at the Harvest Moon. You're exactly the "
                "kind of person we need around here.\"|n\n"
            )
            self.complete()
        else:
            self.quester.msg(
                "|rSergeant Grimjaw shakes his head. \"The cellar's still "
                "full of rats, recruit. Go see Rowan at the Harvest Moon "
                "and sort it out. Then come back.\"|n"
            )

    # ── Completion ──

    def on_complete(self):
        """Grant warrior level 1 on quest completion."""
        character = self.quester

        # Re-check levels_to_spend (may have been spent elsewhere)
        if character.levels_to_spend <= 0:
            self.status = "failed"
            character.msg(
                "|rSergeant Grimjaw shakes his head. \"You've proven yourself, "
                "but you have no levels to spend on warrior training. Return "
                "when you have gained more experience.\"|n"
            )
            return

        # Deduct the level
        character.levels_to_spend -= 1

        # Grant warrior level 1
        from typeclasses.actors.char_classes import get_char_class
        char_class = get_char_class("warrior")
        char_class.at_char_first_gaining_class(character)

        character.msg(
            f"\n|g*** Sergeant Grimjaw clasps your forearm. \"Welcome to "
            f"The Iron Company, {character.key}. You've earned your place "
            f"among us.\" ***|n\n"
            f"You are now a level 1 Warrior.\n"
            f"Type |wguild|n to see your progress, or |wadvance|n to "
            f"spend additional levels."
        )

        if character.location:
            character.location.msg_contents(
                f"{character.key} has been inducted into the Warriors Guild!",
                exclude=[character],
                from_obj=character,
            )
