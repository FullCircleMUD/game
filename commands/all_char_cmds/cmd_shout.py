"""
Language-aware shout command.

``shout <message>`` shouts in Common.
``shout/dwarven <message>`` shouts in Dwarven.

Heard at full volume in the current room and as a muffled partial
message in all adjacent rooms (connected via exits), with the
direction the shout came from.
"""

from evennia import Command

from commands.command import FCMCommandMixin
from enums.condition import Condition
from enums.languages import Languages
from utils.exit_helpers import OPPOSITES
from utils.garble import garble
from utils.speech import caller_can_speak, listener_understands

# Build switch-to-language mappings from the Languages enum.
_SWITCH_MAP = {}
for _lang in Languages:
    _SWITCH_MAP[_lang.value] = _lang.value
    _SWITCH_MAP[_lang.value[:2]] = _lang.value

# Number of words to include in the muffled adjacent-room message.
_MUFFLE_WORDS = 3


def _muffle(text: str) -> str:
    """Truncate text to the first few words, appending '...'."""
    words = text.split()
    if len(words) <= _MUFFLE_WORDS:
        return text
    return " ".join(words[:_MUFFLE_WORDS]) + "..."


class CmdShout(FCMCommandMixin, Command):
    """
    Shout to the room and adjacent rooms.

    Usage:
        shout <message>              — shout in Common
        shout/dwarven <message>      — shout in Dwarven
        shout/dw <message>           — short alias

    Everyone in the room hears you clearly. Characters in
    adjacent rooms hear a muffled version of your shout.
    """

    key = "shout"
    locks = "cmd:all()"
    help_category = "Communication"
    allow_while_sleeping = False

    def parse(self):
        """Extract language switch from cmdname or leading /switch in args."""
        super().parse()
        self.switches = []
        if "/" in self.cmdname:
            # Test harness path
            parts = self.cmdname.split("/", 1)
            self.switches = [s.strip() for s in parts[1].split("/") if s.strip()]
        elif self.args and self.args.lstrip().startswith("/"):
            # Live game path: Evennia base Command puts "/dw msg" in args
            args = self.args.lstrip()
            parts = args.split(None, 1)
            self.switches = [parts[0][1:]]
            self.args = parts[1] if len(parts) > 1 else ""

    def func(self):
        caller = self.caller
        room = caller.location

        if not self.args.strip():
            caller.msg("Shout what?")
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
        if not caller_can_speak(caller, language):
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

        is_common = language == "common"
        lang_display = language.capitalize()

        # --- Caller's own message ---
        if is_common:
            caller.msg(f'You shout: "{speech}"')
        else:
            caller.msg(f'You shout in {lang_display}: "{speech}"')

        # --- Same-room listeners ---
        for obj in room.contents:
            if obj == caller or not obj.has_account:
                continue

            if hasattr(obj, "has_condition") and obj.has_condition(Condition.DEAF):
                continue
            if getattr(obj, "position", None) == "sleeping":
                continue

            # Speaker name — can't identify if invisible or in the dark.
            listener_in_dark = (
                hasattr(room, "is_dark") and room.is_dark(obj)
            )
            if is_invisible:
                if hasattr(obj, "has_condition") and obj.has_condition(
                    Condition.DETECT_INVIS
                ):
                    speaker_name = caller.key
                else:
                    speaker_name = "Someone"
            elif listener_in_dark:
                speaker_name = "Someone"
            else:
                speaker_name = caller.key

            # Language comprehension
            understands = listener_understands(obj, language)

            # Animal-language non-listeners hear no speech framing.
            if language == "animal" and not understands:
                obj.msg(
                    f"{speaker_name} bellows a series of guttural animal noises."
                )
                continue

            heard = speech if understands else garble(speech, language)

            if is_common:
                obj.msg(f'{speaker_name} shouts: "{heard}"')
            else:
                obj.msg(f'{speaker_name} shouts in {lang_display}: "{heard}"')

        # --- Notify LLM NPCs in same room ---
        for obj in room.contents:
            if obj == caller and not hasattr(obj, "at_llm_say_heard"):
                continue
            if hasattr(obj, "at_llm_say_heard"):
                obj.at_llm_say_heard(
                    speaker=caller, message=speech, language=language
                )

        # --- Adjacent room listeners (muffled) ---
        exits = room.contents_get(content_type="exit")
        seen_rooms = set()
        for ex in exits:
            adj_room = ex.destination
            if not adj_room or adj_room.id in seen_rooms:
                continue
            seen_rooms.add(adj_room.id)

            # Determine direction label ("from the south")
            exit_direction = getattr(ex, "direction", None)
            if exit_direction and exit_direction in OPPOSITES:
                from_dir = f"from the {OPPOSITES[exit_direction]}"
            else:
                from_dir = "from nearby"

            muffled = _muffle(speech)

            for obj in adj_room.contents:
                if not obj.has_account:
                    continue

                if hasattr(obj, "has_condition") and obj.has_condition(Condition.DEAF):
                    continue
                if getattr(obj, "position", None) == "sleeping":
                    continue

                # Language comprehension for adjacent listeners
                understands = listener_understands(obj, language)

                # Animal-language non-listeners hear only sounds, not "shouting".
                if language == "animal" and not understands:
                    obj.msg(
                        f"You hear a series of guttural animal noises {from_dir}."
                    )
                    continue

                heard = muffled if understands else garble(muffled, language)

                if is_common:
                    obj.msg(
                        f'You hear a muffled shout {from_dir}: "{heard}"'
                    )
                else:
                    obj.msg(
                        f'You hear a muffled shout in {lang_display} {from_dir}: "{heard}"'
                    )
