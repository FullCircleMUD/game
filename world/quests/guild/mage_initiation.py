"""
Mage Initiation — guild quest for joining the Mages Guild.

The guildmaster requires a Ruby as proof of arcane aptitude:
  Step 1: Bring 1 Ruby

The resource is consumed on delivery. On completion, the character is
inducted as a level 1 Mage (consuming one levels_to_spend).

Quest acceptance is gated on:
  - levels_to_spend > 0
  - Not already a mage
  - Meets race/alignment/remort requirements
  - Meets multiclass ability requirements (INT 14) if multiclassing
"""

from world.quests import register_quest
from world.quests.base_quest import FCMQuest


# Resource IDs (from seeded resource types)
RUBY_ID = 33


@register_quest
class MageInitiation(FCMQuest):
    key = "mage_initiation"
    name = "The Arcane Offering"
    desc = (
        "High Magus Elara studies you with piercing eyes. \"The arcane arts "
        "demand sacrifice, aspirant. Bring me a Ruby — a conduit of raw "
        "magical energy. Only then will I know you possess the will to walk "
        "the path of the arcane.\""
    )
    quest_type = "guild"
    start_step = "ruby"
    reward_xp = 100

    help_ruby = (
        "Bring 1 Ruby to the Guildmaster. \"A Ruby, aspirant. Find one "
        "and bring it to me as proof of your dedication.\""
    )
    help_completed = "You have proven your worth and joined the Mages Guild."
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
        if "mage" in classes:
            return (False, "You are already a member of the Mages Guild.")

        from typeclasses.actors.char_classes import get_char_class
        char_class = get_char_class("mage")
        if char_class and not char_class.char_can_take_class(character):
            return (False,
                    "You do not meet the basic requirements to become "
                    "a Mage.")

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

    def step_ruby(self, *args, **kwargs):
        if not self.quester.has_resource(RUBY_ID, 1):
            self.quester.msg(
                "|rYou need 1 Ruby. Come back when you have it.|n"
            )
            return

        self.quester.return_resource_to_sink(RUBY_ID, 1)
        self.quester.msg(
            "|gHigh Magus Elara accepts your Ruby, its facets "
            "glowing briefly in her hands.|n"
        )
        self.complete()

    # ── Completion ──

    def on_complete(self):
        """Grant mage level 1 on quest completion."""
        character = self.quester

        if character.levels_to_spend <= 0:
            self.status = "failed"
            character.msg(
                "|rHigh Magus Elara sighs. \"You have shown your worth, "
                "but you have no levels to spend on arcane training. Return "
                "when you have gained more experience.\"|n"
            )
            return

        character.levels_to_spend -= 1

        from typeclasses.actors.char_classes import get_char_class
        char_class = get_char_class("mage")
        char_class.at_char_first_gaining_class(character)

        character.msg(
            f"\n|g*** High Magus Elara traces a glowing sigil in the air. "
            f"\"Welcome to the Mages Guild, {character.key}. The arcane "
            f"mysteries are now yours to unravel.\" ***|n\n"
            f"You are now a level 1 Mage.\n"
            f"Type |wguild|n to see your progress, or |wadvance|n to "
            f"spend additional levels."
        )

        if character.location:
            character.location.msg_contents(
                f"{character.key} has been inducted into the Mages Guild!",
                exclude=[character],
                from_obj=character,
            )
