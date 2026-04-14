"""
ThirstLevel — discrete-state thirst meter for the survival system.

Twelve stages from REFRESHED (12, top of the meter) down to CRITICAL (1,
death zone). Wider range than HungerLevel (6 stages) so that, on the same
SURVIVAL_TICK_INTERVAL cadence, a full canteen lasts proportionally longer
in real-play minutes — avoids stacking two equally-naggy meters.

Penalty curve (mirrors hunger's):

    REFRESHED..AWARE   (12-7)  no penalty, just messaging
    DRY                (6)     regen halts (parallel to HUNGRY)
    THIRSTY..PARCHED   (5-3)   stat penalty + slow HP/MP/MV bleed
    DEHYDRATED         (2)     faster bleed (parallel to FAMISHED)
    CRITICAL           (1)     death-zone bleed (parallel to STARVING)

Death by `dehydration` is delivered through RegenerationService when a
character reaches CRITICAL and bleeds out, the same way starvation kills
through the regen loop.
"""

from enum import Enum


class ThirstLevel(Enum):
    REFRESHED = 12   # full container drunk, just refilled
    HYDRATED = 11
    QUENCHED = 10
    SLAKED = 9
    COMFORTABLE = 8
    AWARE = 7        # last "no penalty" stage
    DRY = 6          # parallel to HUNGRY — regen halts
    THIRSTY = 5
    VERY_THIRSTY = 4
    PARCHED = 3
    DEHYDRATED = 2   # parallel to FAMISHED — HP/MP/MV bleed
    CRITICAL = 1     # parallel to STARVING — fast bleed → death

    def get_thirst_message(self) -> str:
        """First-person message for this thirst level."""
        return _THIRST_MESSAGES.get(self, "Your thirst level is unknown.")

    def get_thirst_message_third_person(self, character_key: str) -> str:
        """Third-person message — what other characters in the room observe."""
        template = _THIRST_MESSAGES_THIRD_PERSON.get(
            self, f"{character_key} looks about the same as usual."
        )
        return template.format(name=character_key)

    def get_level(self, num):
        """Look up the ThirstLevel by its int value."""
        return _THIRST_REVERSE_LOOKUP[num]

    def get_name(self, num):
        """Look up the text name of the thirst level."""
        return _THIRST_NAME_LOOKUP[num]


_THIRST_MESSAGES = {
    ThirstLevel.REFRESHED:    "You feel completely refreshed and well-hydrated.",
    ThirstLevel.HYDRATED:     "You feel pleasantly hydrated.",
    ThirstLevel.QUENCHED:     "Your thirst is quenched.",
    ThirstLevel.SLAKED:       "You feel comfortable and your mouth is moist.",
    ThirstLevel.COMFORTABLE:  "You haven't thought about water in a while.",
    ThirstLevel.AWARE:        "You become aware of a slight dryness in your mouth.",
    ThirstLevel.DRY:          "Your mouth is dry — you could use a drink.",
    ThirstLevel.THIRSTY:      "You're thirsty.",
    ThirstLevel.VERY_THIRSTY: "Your throat is parched and you crave water.",
    ThirstLevel.PARCHED:      "Your lips are cracked and your tongue feels swollen.",
    ThirstLevel.DEHYDRATED:   "You're severely dehydrated. Your head pounds and your vision blurs.",
    ThirstLevel.CRITICAL:     "You are dying of thirst! Find water now or perish.",
}

_THIRST_MESSAGES_THIRD_PERSON = {
    ThirstLevel.REFRESHED:    "{name} looks bright-eyed and refreshed.",
    ThirstLevel.HYDRATED:     "{name} looks comfortable and well-watered.",
    ThirstLevel.QUENCHED:     "{name} appears at ease.",
    ThirstLevel.SLAKED:       "{name} looks fine.",
    ThirstLevel.COMFORTABLE:  "{name} licks their lips absently.",
    ThirstLevel.AWARE:        "{name} swallows and glances around.",
    ThirstLevel.DRY:          "{name}'s lips look a bit dry.",
    ThirstLevel.THIRSTY:      "{name} keeps swallowing — they look thirsty.",
    ThirstLevel.VERY_THIRSTY: "{name}'s mouth hangs slightly open and their breathing is dry.",
    ThirstLevel.PARCHED:      "{name}'s lips are cracked and bleeding slightly.",
    ThirstLevel.DEHYDRATED:   "{name} sways unsteadily and looks badly dehydrated.",
    ThirstLevel.CRITICAL:     "{name} is barely conscious, dying of thirst.",
}

_THIRST_REVERSE_LOOKUP = {
    1: ThirstLevel.CRITICAL,
    2: ThirstLevel.DEHYDRATED,
    3: ThirstLevel.PARCHED,
    4: ThirstLevel.VERY_THIRSTY,
    5: ThirstLevel.THIRSTY,
    6: ThirstLevel.DRY,
    7: ThirstLevel.AWARE,
    8: ThirstLevel.COMFORTABLE,
    9: ThirstLevel.SLAKED,
    10: ThirstLevel.QUENCHED,
    11: ThirstLevel.HYDRATED,
    12: ThirstLevel.REFRESHED,
}

_THIRST_NAME_LOOKUP = {
    1: "CRITICAL",
    2: "DEHYDRATED",
    3: "PARCHED",
    4: "VERY_THIRSTY",
    5: "THIRSTY",
    6: "DRY",
    7: "AWARE",
    8: "COMFORTABLE",
    9: "SLAKED",
    10: "QUENCHED",
    11: "HYDRATED",
    12: "REFRESHED",
}
