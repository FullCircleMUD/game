"""
LLMMixin — adds LLM-powered responses to any NPC or mob typeclass.

Mix into any BaseNPC or CombatMob subclass to give it the ability to
respond to speech, make combat decisions, or react to events via an LLM.

Speech detection modes (``llm_speech_mode``):
  - ``"name_match"`` — respond when the NPC's name appears in speech (free)
  - ``"llm_decide"``  — LLM decides if speech is relevant (costs 1 extra call)
  - ``"always"``      — respond to all speech in the room (expensive)
  - ``"whisper_only"`` — only respond to direct whispers (cheapest)

Hookable triggers (enabled per-NPC):
  - ``on_say_heard``        — someone spoke in the room
  - ``on_whisper_received`` — someone whispered to this NPC
  - ``on_player_arrive``    — player entered the room
  - ``on_player_leave``     — player left the room
  - ``on_combat_start``     — NPC was attacked

Memory is accessed through ``_store_memory`` / ``_get_relevant_memories``
which are designed as a swappable abstraction. Phase 1 uses a simple
rolling list; a future phase can swap in pgvector-backed semantic search.

Usage::

    class MySmartNPC(LLMMixin, BaseNPC):
        llm_prompt_file = AttributeProperty("roleplay_npc.md")
        llm_personality = AttributeProperty("A gruff but kind blacksmith...")

        def at_object_creation(self):
            super().at_object_creation()
            self.at_llm_init()
"""

import logging
import random
import re
import time

from evennia.typeclasses.attributes import AttributeProperty

logger = logging.getLogger("llm.mixin")


class LLMMixin:
    """Mixin providing LLM-powered responses for NPCs and mobs."""

    # ── LLM Configuration ────────────────────────────────────────────

    llm_prompt_file = AttributeProperty(None)
    """Prompt template filename in ``llm/prompts/`` (e.g. ``"roleplay_npc.md"``)."""

    llm_prompt_inline = AttributeProperty(None)
    """Inline system prompt string. Overrides ``llm_prompt_file`` if set."""

    llm_personality = AttributeProperty("")
    """Injected into ``{personality}`` template variable."""

    llm_knowledge = AttributeProperty("")
    """Injected into ``{knowledge}`` — NPC-specific facts, prices, lore."""

    llm_model = AttributeProperty(None)
    """OpenRouter model ID. ``None`` = use ``settings.LLM_DEFAULT_MODEL``."""

    llm_max_tokens = AttributeProperty(150)
    """Max response tokens. Keep low for NPC dialogue."""

    llm_temperature = AttributeProperty(0.8)
    """LLM creativity (0.0 = deterministic, 1.0 = creative)."""

    llm_enabled = AttributeProperty(True)
    """Per-NPC kill switch. Set False to disable LLM for this NPC."""

    # ── Speech Detection Mode ─────────────────────────────────────────

    llm_speech_mode = AttributeProperty("name_match")
    """How this NPC detects relevant speech in the room.

    Options:
        ``"name_match"``   — respond when NPC's name appears in speech (free)
        ``"llm_decide"``   — LLM decides if speech is relevant (1 extra call)
        ``"always"``       — respond to all speech in room (expensive)
        ``"whisper_only"`` — only respond to direct whispers (cheapest)
    """

    # ── Hook Enables ──────────────────────────────────────────────────
    # Each hook can be enabled/disabled per-NPC. All default to a
    # sensible "service NPC" baseline (responds to speech, ignores
    # arrivals). Override for different NPC personalities.

    llm_hook_say = AttributeProperty(True)
    """React to ``say`` speech in the room (filtered by ``llm_speech_mode``)."""

    llm_hook_whisper = AttributeProperty(True)
    """React to ``whisper`` directed at this NPC."""

    llm_hook_arrive = AttributeProperty(False)
    """React when a player enters the room. E.g. hermit, guard."""

    llm_hook_leave = AttributeProperty(False)
    """React when a player leaves the room. E.g. clingy NPC."""

    llm_hook_combat = AttributeProperty(False)
    """LLM decides combat actions via ``at_combat_tick``."""

    # ── Memory ────────────────────────────────────────────────────────

    llm_memory_max_entries = AttributeProperty(20)
    """Max conversation history entries (oldest trimmed first)."""

    llm_use_vector_memory = AttributeProperty(False)
    """Use the ai_memory vector database for this NPC. Default False =
    rolling list only. Set True for NPCs that need long-term semantic
    recall across server restarts and game DB wipes."""

    # ── Lore ──────────────────────────────────────────────────────────

    llm_use_lore = AttributeProperty(False)
    """Query LoreMemory for world knowledge relevant to the conversation.
    Scope is determined by the NPC's room tags and faction tags."""

    llm_lore_tags = AttributeProperty(None, autocreate=False)
    """Explicit lore scope tag override. ``None`` = derive from room +
    faction tags automatically. Set to a list to override, e.g.
    ``["millholm", "mages_guild"]``."""

    # ── Conversation Engagement ────────────────────────────────────────

    llm_engagement_timeout = AttributeProperty(60)
    """Seconds to stay engaged with a speaker after responding.
    While engaged, ``name_match`` mode responds without requiring the
    NPC's name — enabling natural follow-up conversation."""

    # ── Rate Limiting ─────────────────────────────────────────────────

    llm_cooldown_seconds = AttributeProperty(5)
    """Minimum seconds between LLM calls for this NPC."""

    # ── Thinking Emote ────────────────────────────────────────────────

    llm_thinking_emote = AttributeProperty(None, autocreate=False)
    """Custom room-visible emote sent while the NPC waits for the LLM.
    ``None`` = random phrase from ``_THINKING_PHRASES``.
    Example: ``"strokes his beard thoughtfully..."``"""

    _THINKING_PHRASES = [
        "pauses for a moment, seeming to think...",
        "looks thoughtful, considering your words...",
        "gazes into the middle distance briefly...",
        "nods slowly, mulling that over...",
        "furrows their brow, thinking...",
    ]

    # ==================================================================
    #  Initialization
    # ==================================================================

    def at_llm_init(self):
        """Initialize LLM storage. Call from ``at_object_creation()``."""
        if self.db.llm_conversation_history is None:
            self.db.llm_conversation_history = []
        if self.db.llm_last_call_time is None:
            self.db.llm_last_call_time = 0.0

    # ==================================================================
    #  System Prompt Assembly
    # ==================================================================

    def get_llm_system_prompt(self):
        """
        Build the full system prompt for this NPC.

        Priority: ``llm_prompt_inline`` > ``llm_prompt_file`` > hardcoded fallback.
        Template variables are filled from ``_get_context_variables()``.
        """
        template = self.llm_prompt_inline
        if not template and self.llm_prompt_file:
            from llm.prompt_loader import render_prompt

            rendered = render_prompt(
                self.llm_prompt_file, self._get_context_variables()
            )
            if rendered:
                return rendered

        if not template:
            template = self._default_system_prompt()

        try:
            from llm.prompt_loader import _DefaultDict

            return template.format_map(_DefaultDict(self._get_context_variables()))
        except Exception:
            return template

    def _get_lore_scope_tags(self):
        """
        Collect this NPC's lore access tags from room and own tags.

        Returns a list of scope tags used to filter ``LoreMemory`` queries.
        Geographic scope (zone, district) is inherited from the room.
        Faction scope comes from the NPC's own tags.
        ``llm_lore_tags`` overrides everything if set.
        """
        # Explicit override takes priority
        if self.llm_lore_tags:
            return list(self.llm_lore_tags)

        tags = []
        room = self.location
        if room:
            zone = room.tags.get(category="zone")
            if zone:
                tags.append(zone)
            district = room.tags.get(category="district")
            if district:
                tags.append(district)

        # Faction tags on the NPC itself
        faction_tags = self.tags.get(category="faction", return_list=True)
        if faction_tags:
            tags.extend(faction_tags)

        return tags

    def _get_context_variables(self):
        """
        Return a dict of template variables gathered from NPC state.

        Available: ``{name}``, ``{personality}``, ``{knowledge}``,
        ``{location}``, ``{room_desc}``, ``{nearby_characters}``,
        ``{memories}``, ``{lore_context}``, ``{hp_current}``, ``{hp_max}``,
        ``{hp_status}``
        """
        location = self.location
        room_name = location.key if location else "unknown"
        room_desc = ""
        if location and hasattr(location, "db"):
            room_desc = location.db.desc or ""

        nearby = []
        if location:
            for obj in location.contents:
                if obj == self:
                    continue
                if getattr(obj, "is_pc", False):
                    nearby.append(obj.key)
        nearby_str = ", ".join(nearby) if nearby else "nobody"

        hp = getattr(self, "hp", 0)
        hp_max = getattr(self, "hp_max", 1)
        if hp_max > 0:
            ratio = hp / hp_max
            hp_status = "healthy" if ratio > 0.75 else "injured" if ratio > 0.4 else "critical"
        else:
            hp_status = "unknown"

        memories = self._format_memories()
        available_commands = self._get_available_commands()

        # Build last_seen context for the current speaker (if vector memory)
        last_seen = ""
        current_speaker = getattr(self.ndb, "_llm_current_speaker", None)
        if self.llm_use_vector_memory and current_speaker:
            try:
                from ai_memory.services import get_last_interaction_time

                dt, time_ago = get_last_interaction_time(
                    npc_id=self.id,
                    speaker_id=current_speaker.id,
                    npc_name=self.key,
                    speaker_name=current_speaker.key,
                )
                if dt:
                    last_seen = (
                        f"You last spoke to {current_speaker.key} "
                        f"{time_ago}."
                    )
            except Exception:
                pass

        # Build lore context (if enabled)
        lore_context = ""
        if getattr(self, "llm_use_lore", False):
            current_message = getattr(self.ndb, "_llm_current_message", None)
            if current_message:
                try:
                    from ai_memory.services import search_lore

                    lore_results = search_lore(
                        current_message, self._get_lore_scope_tags(), top_k=3
                    )
                    if lore_results:
                        lore_context = "\n".join(
                            f"- {r['content']}" for r in lore_results
                        )
                except Exception:
                    logger.exception(
                        "Lore search failed for %s", self.key
                    )

        return {
            "name": self.key,
            "personality": self.llm_personality or "",
            "knowledge": self.llm_knowledge or "",
            "lore_context": lore_context,
            "location": room_name,
            "room_desc": room_desc,
            "nearby_characters": nearby_str,
            "memories": memories,
            "available_commands": available_commands,
            "last_seen": last_seen,
            "hp_current": str(hp),
            "hp_max": str(hp_max),
            "hp_status": hp_status,
        }

    def _get_available_commands(self):
        """Return a comma-separated list of commands this NPC can perform."""
        try:
            cmdset = self.cmdset.all()
            cmd_keys = sorted({cmd.key for cmd in cmdset if cmd.key and not cmd.key.startswith("@")})
            return ", ".join(cmd_keys) if cmd_keys else "none"
        except Exception:
            return "none"

    def _default_system_prompt(self):
        """Hardcoded fallback system prompt."""
        return (
            "You are {name}, a character in a fantasy text-based game.\n\n"
            "{personality}\n\n"
            "Keep responses SHORT (1-3 sentences). Stay in character.\n"
            "NEVER mention being an AI."
        )

    # ==================================================================
    #  Core LLM Call (async via deferToThread)
    # ==================================================================

    def llm_respond(self, speaker, message, interaction_type="say", callback=None):
        """
        Generate an LLM response and deliver it as in-game speech.

        Non-blocking: uses ``deferToThread`` to call LLMService, then
        ``reactor.callFromThread`` to deliver the response on the main thread.

        Args:
            speaker: the character/object that triggered this
            message: what they said or did
            interaction_type: ``"say"``, ``"whisper"``, ``"arrive"``,
                              ``"leave"``, ``"combat"``
            callback: optional callable(response_text) for custom handling
        """
        from twisted.internet import reactor, threads

        if not self.llm_enabled:
            return

        # Per-NPC cooldown check
        now = time.time()
        last_call = self.db.llm_last_call_time or 0.0
        if now - last_call < self.llm_cooldown_seconds:
            self._deliver_fallback(speaker, interaction_type)
            return

        self.db.llm_last_call_time = now

        # Stash speaker and message so _get_context_variables can build
        # {last_seen} and {lore_context}
        self.ndb._llm_current_speaker = speaker
        self.ndb._llm_current_message = message

        # Build LLM messages
        system_prompt = self.get_llm_system_prompt()
        history = self._get_relevant_memories(speaker, message)
        user_message = self._format_user_message(speaker, message, interaction_type)

        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(history)
        messages.append({"role": "user", "content": user_message})

        npc_key = str(self.dbref)

        def _do_llm_call():
            from llm.service import LLMService

            return LLMService.chat_completion(
                messages=messages,
                model=self.llm_model,
                max_tokens=self.llm_max_tokens,
                temperature=self.llm_temperature,
                npc_key=npc_key,
            )

        def _on_response(response_text):
            if response_text:
                self._store_memory(speaker.key, message, response_text)
                if callback:
                    callback(response_text)
                else:
                    self._deliver_response(speaker, response_text, interaction_type)
            else:
                self._deliver_fallback(speaker, interaction_type)

        def _on_error(failure):
            logger.exception("LLM error for %s: %s", self.key, failure)
            self._deliver_fallback(speaker, interaction_type)

        d = threads.deferToThread(_do_llm_call)
        d.addCallback(lambda result: reactor.callFromThread(_on_response, result))
        d.addErrback(lambda failure: reactor.callFromThread(_on_error, failure))

    # ==================================================================
    #  Hook: Say (room speech)
    # ==================================================================

    def at_llm_say_heard(self, speaker, message, language="common", target=None):
        """
        Called when someone uses ``say`` in this NPC's room.

        Applies ``llm_speech_mode`` to decide if the NPC should respond:
          - ``"name_match"`` — responds if NPC's name appears in message
            OR if the speaker directed speech at this NPC (``say to <npc>``)
          - ``"llm_decide"`` — asks LLM if this speech is relevant
          - ``"always"``     — always responds
          - ``"whisper_only"`` — ignores all say speech

        Args:
            speaker: the character who spoke
            message: what they said
            language: the language spoken in
            target: the object the speech was directed at via ``say to <target>``,
                or None for undirected speech
        """
        from twisted.internet import reactor

        if not self.llm_enabled or not self.llm_hook_say:
            return

        if language != "common":
            return

        mode = self.llm_speech_mode

        if mode == "whisper_only":
            return

        if mode == "always":
            reactor.callLater(0, self._emote_and_respond, speaker, message, "say")
            return

        if mode == "name_match":
            addressed = (
                target == self
                or self._name_mentioned_in(message)
                or self._is_engaged_with(speaker)
            )
            if addressed:
                reactor.callLater(0, self._emote_and_respond, speaker, message, "say")
            return

        if mode == "llm_decide":
            # Use a cheap LLM call to decide relevance, then respond if yes
            reactor.callLater(0, self._emote_and_decide, speaker, message)
            return

    def _name_mentioned_in(self, message):
        """Check if any part of this NPC's name appears in the message."""
        msg_lower = message.lower()
        # Check full key
        if self.key.lower() in msg_lower:
            return True
        # Check individual words of the key (e.g. "Greta" from "Greta the Innkeeper")
        for word in self.key.split():
            if len(word) >= 3 and word.lower() in msg_lower:
                return True
        return False

    def _is_engaged_with(self, speaker):
        """Check if NPC is still engaged in conversation with this speaker."""
        engaged = getattr(self.ndb, "llm_engaged_with", None)
        if not engaged:
            return False
        if engaged["speaker_id"] != speaker.id:
            return False
        elapsed = time.time() - engaged["time"]
        if elapsed > self.llm_engagement_timeout:
            self.ndb.llm_engaged_with = None
            return False
        return True

    def _llm_decide_and_respond(self, speaker, message):
        """Ask LLM if this speech is relevant, then respond if yes."""
        from twisted.internet import reactor, threads

        now = time.time()
        last_call = self.db.llm_last_call_time or 0.0
        if now - last_call < self.llm_cooldown_seconds:
            return

        decision_prompt = (
            f"You are {self.key}. {self.llm_personality}\n\n"
            f'{speaker.key} just said to the room: "{message}"\n\n'
            "Would you respond to this? Consider:\n"
            "- Is it directed at you or relevant to you?\n"
            "- Does your personality make you likely to interject?\n\n"
            'Answer with ONLY "yes" or "no".'
        )

        npc_key = str(self.dbref)

        def _do_decision():
            from llm.service import LLMService

            return LLMService.chat_completion(
                messages=[{"role": "user", "content": decision_prompt}],
                model=self.llm_model,
                max_tokens=5,
                temperature=0.3,
                npc_key=npc_key,
            )

        def _on_decision(result):
            if result and "yes" in result.strip().lower():
                self.llm_respond(speaker, message, interaction_type="say")

        d = threads.deferToThread(_do_decision)
        d.addCallback(lambda r: reactor.callFromThread(_on_decision, r))
        d.addErrback(lambda f: None)  # silently ignore errors on decision

    # ==================================================================
    #  Hook: Whisper
    # ==================================================================

    def at_llm_whisper_received(self, speaker, message):
        """
        Called when someone whispers to this NPC.

        Whispers are always treated as directed. Response defaults to
        whisper back, unless the LLM's response indicates otherwise.

        Args:
            speaker: the character who whispered
            message: what they whispered
        """
        from twisted.internet import reactor

        if not self.llm_enabled or not self.llm_hook_whisper:
            return
        reactor.callLater(0, self._emote_and_respond, speaker, message, "whisper")

    # ==================================================================
    #  Hook: Player Arrive / Leave
    # ==================================================================

    def at_llm_player_arrive(self, player):
        """
        Called when a player enters this NPC's room.

        Override for NPCs that react to arrivals (hermit, guard, greeter).
        Disabled by default (``llm_hook_arrive = False``).

        Args:
            player: the arriving FCMCharacter
        """
        if not self.llm_enabled or not self.llm_hook_arrive:
            return
        self.llm_respond(
            player,
            f"{player.key} has just entered the room.",
            interaction_type="arrive",
        )

    def at_llm_player_leave(self, player):
        """
        Called when a player leaves this NPC's room.

        Override for clingy NPCs that call after departing players.
        Disabled by default (``llm_hook_leave = False``).

        Args:
            player: the departing FCMCharacter
        """
        if not self.llm_enabled or not self.llm_hook_leave:
            return
        self.llm_respond(
            player,
            f"{player.key} is leaving the room.",
            interaction_type="leave",
        )

    # ==================================================================
    #  Response Delivery
    # ==================================================================

    def _deliver_thinking_emote(self, speaker):
        """Send an immediate thinking room message before async LLM work starts."""
        if not self.location:
            return
        custom = self.llm_thinking_emote
        phrase = custom if custom else random.choice(self._THINKING_PHRASES)
        self.location.msg_contents(f"|c{self.key}|n {phrase}", from_obj=self)

    def _emote_and_respond(self, speaker, message, interaction_type):
        """Deferred helper: send thinking emote then kick off llm_respond."""
        self._deliver_thinking_emote(speaker)
        self.llm_respond(speaker, message, interaction_type=interaction_type)

    def _emote_and_decide(self, speaker, message):
        """Deferred helper: send thinking emote then kick off llm_decide."""
        self._deliver_thinking_emote(speaker)
        self._llm_decide_and_respond(speaker, message)

    def _deliver_response(self, speaker, response_text, interaction_type):
        """
        Deliver the LLM response as in-game speech.

        Matches the incoming speech mode by default:
          - say → says back
          - whisper → whispers back
          - arrive/leave → says to the room

        In dark rooms, listeners who can't see hear "Someone" instead
        of the NPC's name.
        """
        clean = self._sanitize_response(response_text)
        if not clean or not self.location:
            return

        # Track engagement — NPC stays engaged with this speaker
        self.ndb.llm_engaged_with = {
            "speaker_id": speaker.id,
            "time": time.time(),
        }

        if interaction_type == "whisper":
            # Whisper back to the speaker (only they see it)
            speaker.msg(f'|c{self.key} whispers to you:|n "{clean}"')
        elif interaction_type in ("arrive", "leave"):
            # Ambient reaction — per-listener dark-awareness
            self._msg_room_dark_aware(
                f'|c{self.key} says:|n "{clean}"',
                f'|cSomeone says:|n "{clean}"',
            )
        else:
            # Say — respond to the room, directed at speaker
            self._msg_room_dark_aware(
                f'|c{self.key} says to {speaker.key}:|n "{clean}"',
                f'|cSomeone says:|n "{clean}"',
            )

    def _msg_room_dark_aware(self, lit_msg, dark_msg):
        """
        Send a message to all room occupants, using ``dark_msg`` for
        listeners who can't see in the dark.
        """
        room = self.location
        if not room:
            return
        for obj in room.contents:
            if not obj.has_account:
                continue
            if hasattr(room, "is_dark") and room.is_dark(obj):
                obj.msg(dark_msg)
            else:
                obj.msg(lit_msg)

    def _deliver_fallback(self, speaker, interaction_type):
        """Deliver a hardcoded fallback when LLM is unavailable."""
        response = self.llm_fallback_response(speaker, interaction_type)
        if not response or not self.location:
            return

        if interaction_type == "whisper":
            speaker.msg(f"{self.key} {response}")
        else:
            self.location.msg_contents(f"{self.key} {response}", exclude=[])

    def llm_fallback_response(self, speaker, interaction_type):
        """
        Return a hardcoded fallback string. Override in subclasses.

        Called when LLM is rate-limited, fails, or disabled.
        Return ``None`` to stay silent.
        """
        if interaction_type in ("say", "whisper"):
            return f"*nods at {speaker.key} thoughtfully*"
        return None

    # ==================================================================
    #  User Message Formatting
    # ==================================================================

    def _format_user_message(self, speaker, message, interaction_type):
        """Format the user's message for the LLM."""
        if interaction_type == "whisper":
            return f'{speaker.key} whispers to you: "{message}"'
        if interaction_type == "arrive":
            return message  # already formatted by caller
        if interaction_type == "leave":
            return message
        # Default: say
        return f'{speaker.key} says to you: "{message}"'

    # ==================================================================
    #  Memory Abstraction
    #
    #  Dual system, chosen per NPC via ``llm_use_vector_memory``:
    #    False (default) → rolling list in Evennia db attributes
    #    True            → ai_memory Django app with vector embeddings
    # ==================================================================

    def _store_memory(self, speaker_name, user_message, assistant_response):
        """
        Store a conversation exchange in memory.

        Routes to vector memory DB or rolling list based on
        ``self.llm_use_vector_memory``.
        """
        if self.llm_use_vector_memory:
            self._store_memory_vector(speaker_name, user_message, assistant_response)
        else:
            self._store_memory_rolling(speaker_name, user_message, assistant_response)

    def _get_relevant_memories(self, speaker, context):
        """
        Retrieve relevant conversation history for the LLM messages array.

        Routes to vector search or rolling list based on
        ``self.llm_use_vector_memory``.
        """
        if self.llm_use_vector_memory:
            return self._get_memories_vector(speaker, context)
        return self._get_memories_rolling()

    def _format_memories(self):
        """Format memory for injection into system prompt ``{memories}`` variable."""
        if self.llm_use_vector_memory:
            return self._format_memories_vector()
        return self._format_memories_rolling()

    # ── Rolling List (default) ────────────────────────────────────────

    def _store_memory_rolling(self, speaker_name, user_message, assistant_response):
        """Append to self.db.llm_conversation_history (rolling list)."""
        history = list(self.db.llm_conversation_history or [])
        now = time.time()
        history.append(
            {
                "role": "user",
                "speaker": speaker_name,
                "content": user_message,
                "timestamp": now,
            }
        )
        history.append(
            {
                "role": "assistant",
                "content": assistant_response,
                "timestamp": now,
            }
        )
        max_entries = self.llm_memory_max_entries
        if len(history) > max_entries:
            history = history[-max_entries:]
        self.db.llm_conversation_history = history

    def _get_memories_rolling(self):
        """Return last N entries as chat messages."""
        history = self.db.llm_conversation_history or []
        return [
            {"role": entry["role"], "content": entry["content"]} for entry in history
        ]

    def _format_memories_rolling(self):
        """Format rolling list for {memories} template variable."""
        history = self.db.llm_conversation_history or []
        if not history:
            return "(No previous conversations)"

        lines = []
        for entry in history[-10:]:
            speaker = entry.get("speaker", "")
            content = entry["content"]
            if entry["role"] == "user":
                lines.append(f"  {speaker}: {content}")
            else:
                lines.append(f"  You: {content}")
        return "\n".join(lines)

    # ── Vector Memory (opt-in) ────────────────────────────────────────

    def _store_memory_vector(self, speaker_name, user_message, assistant_response):
        """Store to ai_memory database with embedding."""
        speaker = getattr(self.ndb, "_llm_current_speaker", None)
        try:
            from ai_memory.services import store_memory

            store_memory(
                npc=self,
                speaker=speaker if speaker else type("S", (), {"id": 0, "key": speaker_name})(),
                user_msg=user_message,
                assistant_msg=assistant_response,
                interaction_type="say",
            )
        except Exception:
            logger.exception("Vector memory store failed for %s — falling back to rolling list", self.key)
            self._store_memory_rolling(speaker_name, user_message, assistant_response)

    def _get_memories_vector(self, speaker, context):
        """Semantic search for relevant memories, formatted as chat messages."""
        try:
            from ai_memory.services import search_memories

            results = search_memories(
                npc_id=self.id,
                query_text=context,
                top_k=5,
                speaker_id=speaker.id if speaker else None,
                npc_name=self.key,
            )
            if results:
                messages = []
                for mem in results:
                    messages.append(
                        {"role": "user", "content": f'{mem["speaker_name"]}: {mem["user_message"]}'}
                    )
                    messages.append(
                        {"role": "assistant", "content": mem["assistant_message"]}
                    )
                return messages
        except Exception:
            logger.exception("Vector memory search failed for %s", self.key)

        # Fallback to rolling list
        return self._get_memories_rolling()

    def _format_memories_vector(self):
        """Format vector memories with timestamps for {memories} variable."""
        try:
            from ai_memory.services import get_recent_memories

            results = get_recent_memories(
                npc_id=self.id, limit=10, npc_name=self.key
            )
            if results:
                lines = []
                for mem in results:
                    time_ago = mem.get("time_ago", "")
                    time_prefix = f"({time_ago}) " if time_ago else ""
                    lines.append(
                        f"  {time_prefix}{mem['speaker_name']}: {mem['user_message']}"
                    )
                    lines.append(f"  You: {mem['assistant_message']}")
                return "\n".join(lines)
        except Exception:
            logger.exception("Vector memory format failed for %s", self.key)

        # Fallback to rolling list
        return self._format_memories_rolling()

    def clear_llm_memory(self):
        """Admin utility: wipe this NPC's conversation history."""
        self.db.llm_conversation_history = []

    # ==================================================================
    #  Response Sanitization
    # ==================================================================

    @staticmethod
    def _sanitize_response(text):
        """
        Clean LLM output for safe delivery as in-game speech.

        - Strip surrounding quotes
        - Remove command-like prefixes (say, tell, whisper, etc.)
        - Truncate to 500 characters
        - Collapse newlines to spaces
        """
        if not text:
            return ""

        text = text.strip()

        # Strip surrounding quotes
        if len(text) >= 2 and text[0] == '"' and text[-1] == '"':
            text = text[1:-1].strip()

        # Remove command-like prefixes the LLM might have included
        text = re.sub(
            r"^(say|sayto|tell|whisper|shout|attack|flee|cast)\s+",
            "",
            text,
            flags=re.IGNORECASE,
        )

        # Collapse newlines to spaces
        text = re.sub(r"\s*\n\s*", " ", text)

        # Truncate
        if len(text) > 500:
            text = text[:497] + "..."

        return text.strip()
