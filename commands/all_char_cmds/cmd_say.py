"""
Language-aware say command.

Overrides Evennia's default ``say`` with per-language speech.
Plain ``say <message>`` speaks in Common.  Use switches to speak
in other languages: ``say/dwarven <message>`` or ``say/dw <message>``.

Listeners who don't know the language see deterministic gibberish
flavoured to that language.  The COMPREHEND_LANGUAGES condition
lets a listener understand everything.
"""

from evennia import Command

from enums.condition import Condition
from enums.languages import Languages
from utils.garble import garble

# Build switch-to-language mappings from the Languages enum.
# Full names: say/dwarven   Short aliases: say/dw (first 2 chars)
_SWITCH_MAP = {}
for lang in Languages:
    _SWITCH_MAP[lang.value] = lang.value              # "dwarven" -> "dwarven"
    _SWITCH_MAP[lang.value[:2]] = lang.value           # "dw" -> "dwarven"

# Set of valid language values for quick membership checks.
_VALID_LANGUAGES = {lang.value for lang in Languages}


class CmdSay(Command):
    """
    Speak to the room, optionally in a specific language.

    Usage:
        say <message>              — speak in Common
        say/dwarven <message>      — speak in Dwarven
        say/dw <message>           — short alias for Dwarven
        "<message>                 — shortcut for say (Common)

    Available languages: common, dwarven, elfish, kobold, goblin, dragon.
    Short aliases: co, dw, el, ko, go, dr.

    Characters who don't know the language hear garbled speech.
    """

    key = "say"
    aliases = ['"']
    locks = "cmd:all()"
    help_category = "Communication"

    def parse(self):
        """Extract language switch from cmdname or leading /switch in args."""
        super().parse()
        self.switches = []
        if "/" in self.cmdname:
            # Test harness path: cmdstring explicitly set to "say/dw"
            parts = self.cmdname.split("/", 1)
            self.switches = [s.strip() for s in parts[1].split("/") if s.strip()]
        elif self.args and self.args.lstrip().startswith("/"):
            # Live game path: Evennia base Command puts "/dw msg" in args
            args = self.args.lstrip()
            parts = args.split(None, 1)
            self.switches = [parts[0][1:]]  # strip leading "/"
            self.args = parts[1] if len(parts) > 1 else ""

    def func(self):
        caller = self.caller
        room = caller.location

        if not self.args.strip():
            caller.msg("Say what?")
            return

        speech = self.args.strip()

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

        # --- Determine visibility ---
        is_invisible = (
            hasattr(caller, "has_condition")
            and caller.has_condition(Condition.INVISIBLE)
        )

        # --- Build language display ---
        is_common = language == "common"
        lang_display = language.capitalize()

        # --- Caller's own message ---
        if is_common:
            caller.msg(f'|cYou say:|n "{speech}"')
        else:
            caller.msg(f'|cYou say in {lang_display}:|n "{speech}"')

        # --- Per-listener messages ---
        for obj in room.contents:
            if obj == caller or not obj.has_account:
                continue

            # DEAF listeners hear nothing.
            if hasattr(obj, "has_condition") and obj.has_condition(Condition.DEAF):
                continue

            # Determine the speaker name this listener sees.
            # Can't see the speaker if invisible or if the room is dark.
            listener_in_dark = (
                hasattr(room, "is_dark") and room.is_dark(obj)
            )
            if is_invisible:
                if hasattr(obj, "has_condition") and obj.has_condition(Condition.DETECT_INVIS):
                    speaker_name = caller.key
                else:
                    speaker_name = "Someone"
            elif listener_in_dark:
                speaker_name = "Someone"
            else:
                speaker_name = caller.key

            # Determine if listener understands the language.
            listener_languages = set(getattr(obj.db, "languages", None) or set())
            has_comprehend = (
                hasattr(obj, "has_condition")
                and obj.has_condition(Condition.COMPREHEND_LANGUAGES)
            )
            understands = is_common or language in listener_languages or has_comprehend

            if understands:
                heard = speech
            else:
                heard = garble(speech, language)

            if is_common:
                obj.msg(f'|c{speaker_name} says:|n "{heard}"')
            else:
                obj.msg(f'|c{speaker_name} says in {lang_display}:|n "{heard}"')

        # --- Notify LLM-enabled NPCs in the room ---
        for obj in room.contents:
            if obj == caller:
                continue
            if hasattr(obj, "at_llm_say_heard"):
                obj.at_llm_say_heard(
                    speaker=caller, message=speech, language=language
                )
