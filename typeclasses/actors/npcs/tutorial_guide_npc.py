"""
TutorialGuideNPC — tutorial guide placed in each tutorial room.

Each tutorial room has its own Pip. On player entry, Pip delivers
hardcoded instructions (from the room's ``tutorial_text``). If the
player then talks to Pip, the LLM handles follow-up questions using
the room's ``guide_context`` for FAQ-style answers.
"""

from evennia.typeclasses.attributes import AttributeProperty

from typeclasses.actors.npcs.llm_roleplay_npc import LLMRoleplayNPC


class TutorialGuideNPC(LLMRoleplayNPC):
    """
    Tutorial guide placed in each tutorial room.

    Arrival: shows hardcoded ``tutorial_text`` from the room.
    Follow-up: LLM-powered answers using room-specific knowledge
    baked into ``llm_knowledge`` at spawn time.
    """

    llm_prompt_file = AttributeProperty("tutorial_guide.md")
    llm_hook_arrive = AttributeProperty(False)  # We show static text ourselves
    llm_speech_mode = AttributeProperty("always")
    llm_max_tokens = AttributeProperty(250)

    def at_object_creation(self):
        super().at_object_creation()
        self.locks.add("get:false()")
        self.db.tutorial_item = True
        self.db.desc = (
            "A young adventurer with a ready grin and a well-worn satchel "
            "slung over one shoulder. Pip bounces on the balls of their "
            "feet, eager to show you around."
        )
        # The tutorial is instructional UI, not an NPC noticing you, so a
        # player experimenting with hide must still get the lesson. Rather
        # than exempt Pip from the arrival dispatcher's perception gate,
        # give him the counters that pass it: true_sight beats HIDDEN,
        # DETECT_INVIS beats INVISIBLE. duration=None is permanent.
        #
        # It also keeps a concealed player from dropping out of his
        # conversation context, which builds {nearby_characters} through
        # the same predicate.
        self.apply_true_sight(duration_seconds=None, detect_invis=True)

    def at_llm_player_arrive(self, player):
        """Show hardcoded tutorial instructions on room entry."""
        if not self.location:
            return
        tutorial_text = getattr(self.location.db, "tutorial_text", None)
        if tutorial_text:
            player.msg(
                f"\n|yPip turns to you and explains:|n\n{tutorial_text}\n"
            )

    def llm_fallback_response(self, speaker, interaction_type):
        """Show static tutorial_text if LLM call fails."""
        if self.location:
            tutorial_text = getattr(self.location.db, "tutorial_text", None)
            if tutorial_text:
                speaker.msg(f"\n|y[Tutorial Hint]|n\n{tutorial_text}\n")
                return None
        return f"*{self.key} gestures around the room encouragingly*"
