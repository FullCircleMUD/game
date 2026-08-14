"""
Who is behind the bar, and whether they will serve you.

Shared by ``ale`` and ``stew``. Both used to ask whether the *caller* was
HIDDEN or INVISIBLE, which is the wrong question twice over: it reads the
customer's own state rather than what the server can tell, so a bartender
with DETECT_INVIS still refused, and a blind one still served.

The question is asked of the bartender, and it has three answers, which
are the same three the rest of the visibility work settled on:

- **Cannot perceive you** — hidden or invisible. He has no idea anyone is
  there, so an order arrives as a voice from nowhere. No service.
- **Perceives but cannot see you** — he is blinded, or the inn is unlit
  and he has no darkvision. He knows someone came in and asks who. The
  challenge *is* the refusal; there is no second line.
- **Sees you** — served.

A room with nobody behind the bar serves anyone. Bobbin's Kitchen says so
on the ale barrel: "Take What You Need — Pay What You Can."
"""

import time

from typeclasses.actors.npcs.bartender_npc import BartenderNPC
from utils.targeting.predicates import p_can_perceive, p_can_see


# The blind challenge broadcasts to the whole room, and a command fires as
# fast as a player can type — unlike the arrival hook, which fires once per
# arrival. Without this, spamming `ale` in a dark inn turns into a chorus.
CHALLENGE_COOLDOWN_SECONDS = 30

VOICE_FROM_NOWHERE = (
    "The bartender looks around wildly, trying to identify "
    "where the voice is coming from. No service."
)


def find_bartender(room):
    """Return the ``BartenderNPC`` working this room, or ``None``.

    ``None`` means self-service, not an error — see the module docstring.
    """
    if not room:
        return None
    for obj in room.contents:
        if isinstance(obj, BartenderNPC):
            return obj
    return None


def bartender_refuses(caller):
    """True when the caller gets no service, having already been told why.

    Callers put this at the top of ``func()`` and return on True.
    """
    bartender = find_bartender(caller.location)
    if bartender is None:
        return False

    if not p_can_perceive(caller, bartender):
        caller.msg(VOICE_FROM_NOWHERE)
        return True

    if not p_can_see(caller, bartender):
        _challenge(bartender, caller)
        return True

    return False


def _challenge(bartender, caller):
    """Ask who is there — or say nothing much, if he asked recently."""
    now = time.time()
    last = bartender.db.last_blind_challenge_at or 0.0

    if now - last < CHALLENGE_COOLDOWN_SECONDS:
        # get_display_name rather than key: a caller in the dark cannot
        # see the bartender either, and reads him as "someone".
        name = bartender.get_display_name(caller)
        name = name[0].upper() + name[1:] if name else name
        caller.msg(f"{name} does not seem to have heard you.")
        return

    bartender.db.last_blind_challenge_at = now
    bartender._deliver_blind_challenge()
