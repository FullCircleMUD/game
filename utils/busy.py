"""
The busy lock — an action that takes time and takes both hands.

Harvesting, crafting, processing, repairing, groping about in the dark:
each announces itself, holds the character for a few seconds, and then
resolves. While held, every command that respects the lock refuses,
including attack via ``CombatMixin._can_start_fight_now()``.

Busy is busy regardless of the cause, so the refusal wording lives here
once. The *announcement* is per-action and passed in — "You begin
gathering...", "You grope about in the dark..." — while the refusal a
second command gets is always the same.

Being interrupted does not cancel a busy action: a character jumped
mid-harvest finishes the swing before they can react. That is the cost
the lock buys, and the reason it is a lock rather than a flag.

Usage::

    if check_busy(caller):
        return

    def _complete():
        ...the outcome, success and failure both...

    start_busy(caller, 5, _complete, self_msg="You begin gathering...")
"""

import random

from evennia.utils import delay

BUSY_MESSAGE = "You are busy. Wait until you finish what you're doing."

# How long a sightless character spends searching by touch. Long enough
# to matter in a fight, short enough not to be a punishment. Each command
# supplies its own wording — groping through a pack, feeling along a wall
# and finding a latch by touch are different pictures — but they all take
# the same time.
FUMBLE_SECONDS_MIN = 3
FUMBLE_SECONDS_MAX = 4


def fumble_seconds():
    """Return a randomised search-by-touch duration for ``start_busy``."""
    return random.uniform(FUMBLE_SECONDS_MIN, FUMBLE_SECONDS_MAX)


def check_busy(caller):
    """
    Refuse an action if the character is already occupied.

    Call at the top of any command that should wait its turn.

    Returns:
        bool: True if busy and the caller has been told so — the command
            should return immediately.
    """
    if caller.ndb.is_processing:
        caller.msg(BUSY_MESSAGE)
        return True
    return False


def start_busy(caller, seconds, on_complete, self_msg=None, room_msg=None):
    """
    Announce an action, hold the character for its duration, then resolve.

    Args:
        caller: the character being held.
        seconds (float): how long the action takes.
        on_complete (callable): run with no arguments once the time is up.
            Holds the whole outcome — success and failure both — so that
            nothing about the result escapes before the action finishes.
        self_msg (str, optional): announced to the character up front.
        room_msg (str, optional): announced to the rest of the room up
            front. Passed through ``msg_contents`` with ``from_obj``, so
            it is filtered for observers who cannot perceive the actor.

    Returns:
        bool: False if the character was already busy and nothing was
            started, True if the action is under way.

    The lock is released *before* ``on_complete`` runs, so an outcome
    that starts something else — combat, a second timed action — is not
    blocked by the action that produced it.
    """
    if check_busy(caller):
        return False

    if self_msg:
        caller.msg(self_msg)
    if room_msg and caller.location:
        caller.location.msg_contents(room_msg, exclude=[caller], from_obj=caller)

    caller.ndb.is_processing = True

    def _complete():
        caller.ndb.is_processing = False
        on_complete()

    delay(seconds, _complete)
    return True
