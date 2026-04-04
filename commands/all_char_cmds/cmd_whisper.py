"""
Language-aware whisper command.

Replaces Evennia's default ``whisper`` with per-language support.
``whisper Char = message`` whispers in Common.
``whisper/dwarven Char = message`` whispers in Dwarven.

Listeners who don't know the language hear deterministic gibberish.
"""

from evennia import Command

from commands.command import FCMCommandMixin
from enums.condition import Condition
from enums.languages import Languages
from utils.garble import garble

# Build switch-to-language mappings from the Languages enum.
_SWITCH_MAP = {}
for _lang in Languages:
    _SWITCH_MAP[_lang.value] = _lang.value
    _SWITCH_MAP[_lang.value[:2]] = _lang.value


class CmdWhisper(FCMCommandMixin, Command):
    """
    Whisper privately to another character.

    Usage:
        whisper <character> = <message>          — whisper in Common
        whisper/dwarven <character> = <message>   — whisper in Dwarven
        whisper/dw <character> = <message>        — short alias

    Only the target hears the whisper. Others in the room see nothing.
    If the target doesn't know the language, they hear garbled speech.
    """

    key = "whisper"
    locks = "cmd:all()"
    help_category = "Communication"
    allow_while_sleeping = True

    def parse(self):
        """Extract language switch and split target = message."""
        super().parse()
        self.switches = []
        if "/" in self.cmdname:
            # Test harness path
            parts = self.cmdname.split("/", 1)
            self.switches = [s.strip() for s in parts[1].split("/") if s.strip()]
        elif self.args and self.args.lstrip().startswith("/"):
            # Live game path: Evennia base Command puts "/dw target = msg" in args
            args = self.args.lstrip()
            parts = args.split(None, 1)
            self.switches = [parts[0][1:]]
            self.args = parts[1] if len(parts) > 1 else ""

        # Split on '=' for target = message
        self.whisper_target = ""
        self.whisper_message = ""
        if "=" in self.args:
            target_str, msg_str = self.args.split("=", 1)
            self.whisper_target = target_str.strip()
            self.whisper_message = msg_str.strip()

    def func(self):
        caller = self.caller
        room = caller.location

        if not self.whisper_target or not self.whisper_message:
            # Helpful hint if they typed "whisper Bob hello" without "="
            args = self.args.strip() if self.args else ""
            if args and " " not in args:
                caller.msg(f"Whisper what to {args}? Usage: |wwhisper {args} = <message>|n")
            elif args:
                caller.msg(f"Usage: |wwhisper <character> = <message>|n")
            else:
                caller.msg("Usage: |wwhisper <character> = <message>|n")
            return

        # --- Determine language from switch ---
        language = "common"
        if self.switches:
            switch = self.switches[0].lower()
            if switch in _SWITCH_MAP:
                language = _SWITCH_MAP[switch]
            else:
                valid = ", ".join(sorted(_SWITCH_MAP.keys()))
                caller.msg(f"Unknown language switch '{switch}'. Valid: {valid}")
                return

        # --- Check caller knows the language ---
        caller_languages = set(caller.db.languages or set())
        if language not in caller_languages:
            lang_display = language.capitalize()
            caller.msg(f"You don't know how to speak {lang_display}.")
            return

        # --- Check SILENCED condition ---
        if hasattr(caller, "has_condition") and caller.has_condition(Condition.SILENCED):
            caller.msg("You can't speak while silenced.")
            return

        # --- Find target(s) — support comma-separated ---
        target_names = [t.strip() for t in self.whisper_target.split(",")]
        receivers = []
        for name in target_names:
            if not name:
                continue
            found = caller.search(name, location=room)
            if found:
                receivers.append(found)
        if not receivers:
            return

        # --- AFK notification ---
        for recv in receivers:
            if getattr(recv, "afk", False):
                caller.msg(f"|y{recv.key} is currently AFK.|n")

        speech = self.whisper_message
        is_common = language == "common"
        lang_display = language.capitalize()

        # --- Determine visibility ---
        is_invisible = (
            hasattr(caller, "has_condition")
            and caller.has_condition(Condition.INVISIBLE)
        )

        # --- Caller message ---
        target_names_display = ", ".join(r.key for r in receivers)
        if is_common:
            caller.msg(f'|cYou whisper to {target_names_display}:|n "{speech}"')
        else:
            caller.msg(
                f'|cYou whisper in {lang_display} to {target_names_display}:|n "{speech}"'
            )

        # --- Per-receiver messages ---
        for recv in receivers:
            # DEAF receivers hear nothing
            if hasattr(recv, "has_condition") and recv.has_condition(Condition.DEAF):
                continue

            # Determine speaker name — can't identify if invisible or in the dark.
            room = caller.location
            listener_in_dark = (
                room and hasattr(room, "is_dark") and room.is_dark(recv)
            )
            if is_invisible:
                if hasattr(recv, "has_condition") and recv.has_condition(
                    Condition.DETECT_INVIS
                ):
                    speaker_name = caller.key
                else:
                    speaker_name = "Someone"
            elif listener_in_dark:
                speaker_name = "Someone"
            else:
                speaker_name = caller.key

            # Determine if receiver understands the language
            recv_languages = set(getattr(recv.db, "languages", None) or set())
            has_comprehend = hasattr(recv, "has_condition") and recv.has_condition(
                Condition.COMPREHEND_LANGUAGES
            )
            understands = is_common or language in recv_languages or has_comprehend

            heard = speech if understands else garble(speech, language)

            if is_common:
                recv.msg(f'|c{speaker_name} whispers to you:|n "{heard}"')
            else:
                recv.msg(
                    f'|c{speaker_name} whispers in {lang_display} to you:|n "{heard}"'
                )

            # Notify LLM NPCs (Common only, matching say behavior)
            if is_common and hasattr(recv, "at_llm_whisper_received"):
                recv.at_llm_whisper_received(speaker=caller, message=speech)
