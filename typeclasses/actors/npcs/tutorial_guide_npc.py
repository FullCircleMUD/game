"""
TutorialGuideNPC — LLM-powered guide that walks players through tutorials.

Spawned by TutorialInstanceScript into the first room of each tutorial.
Follows the player via the follow system and speaks conversationally
about each room's mechanics using the room's ``guide_context`` attribute.

Falls back to static ``tutorial_text`` if the LLM is unavailable.
"""

from evennia.typeclasses.attributes import AttributeProperty

from typeclasses.actors.npcs.llm_roleplay_npc import LLMRoleplayNPC


class TutorialGuideNPC(LLMRoleplayNPC):
    """
    LLM-powered tutorial guide that walks alongside the player.

    Each tutorial room stores a ``guide_context`` attribute describing
    what the guide should teach. On room entry the guide injects this
    into its knowledge and generates conversational LLM speech.
    """

    llm_prompt_file = AttributeProperty("tutorial_guide.md")
    llm_hook_arrive = AttributeProperty(False)  # We handle room speech ourselves
    llm_speech_mode = AttributeProperty("name_match")
    llm_max_tokens = AttributeProperty(250)

    def at_object_creation(self):
        super().at_object_creation()
        self.locks.add("get:false()")
        self.db.tutorial_item = True  # Cleaned up on instance collapse

    def at_post_move(self, source_location, move_type="move", **kwargs):
        """Speak about the new room before super() processes follow guard."""
        if self.location and self.location != source_location:
            guide_context = getattr(self.location.db, "guide_context", None)
            last_room_id = self.ndb.last_guide_room_id
            if guide_context and self.location.id != last_room_id:
                self.ndb.last_guide_room_id = self.location.id
                self._speak_about_room(guide_context)

        super().at_post_move(source_location, move_type=move_type, **kwargs)

    def _speak_about_room(self, guide_context):
        """Generate LLM speech about the current room's mechanics."""
        player = self._get_tutorial_player()
        if not player:
            return

        # Temporarily inject room-specific context into knowledge
        base_knowledge = self.llm_knowledge or ""
        self.llm_knowledge = (
            f"{base_knowledge}\n\nCURRENT ROOM INSTRUCTIONS:\n{guide_context}"
        )

        self.llm_respond(
            player,
            f"We've entered {self.location.key}. Explain what the player "
            f"can do here.",
            interaction_type="arrive",
        )

        # Restore base knowledge
        self.llm_knowledge = base_knowledge

    def _get_tutorial_player(self):
        """Find the player character in the current room."""
        if self.location:
            for obj in self.location.contents:
                if getattr(obj, "is_pc", False):
                    return obj
        return None

    def llm_fallback_response(self, speaker, interaction_type):
        """Show static tutorial_text if LLM is unavailable."""
        if self.location:
            tutorial_text = getattr(self.location.db, "tutorial_text", None)
            if tutorial_text:
                speaker.msg(f"\n|y[Tutorial Hint]|n\n{tutorial_text}\n")
                return None  # Suppress generic emote
        return f"*{self.key} gestures around the room encouragingly*"
