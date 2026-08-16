"""
The busy lock — an action that takes time and takes both hands.

Harvesting, crafting, processing, repairing, groping about in the dark:
each announces itself, holds the character for a few seconds, and then
resolves. While held, every command that respects the lock refuses,
including attack via ``CombatMixin._can_start_fight_now()``.

Every message is the action's to choose. The announcement — "You begin
gathering...", "You grope about in the dark..." — and the refusal a
second command gets are both passed in. The refusal falls back to
``BUSY_MESSAGE``, which is right for the ordinary case of a job taking
both hands, and wrong often enough to be worth overriding.

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

# What a held character is told when they try to walk away. Read by
# ``FCMCharacter.at_pre_move``, which is the other half of the lock —
# busy refuses commands and refuses movement, so both defaults live here.
BUSY_MOVE_MESSAGE = "You can't leave in the middle of a job! Wait for it to finish."

# How long a sightless character spends searching by touch. Long enough
# to matter in a fight, short enough not to be a punishment. Each command
# supplies its own wording — groping through a pack, feeling along a wall
# and finding a latch by touch are different pictures — but they all take
# the same time.
FUMBLE_SECONDS_MIN = 3
FUMBLE_SECONDS_MAX = 4


# Searching by touch is one situation across a dozen commands, so it
# refuses in one voice. Pass these with ``fumble_seconds()`` — groping
# through a pack is not "a job", and a character who walks off mid-search
# has lost the thing they were feeling for.
FUMBLE_BUSY_MESSAGE = "You are still feeling about in the dark."
FUMBLE_MOVE_MESSAGE = "You would lose your bearings in the dark. Finish first."


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
        caller.msg(caller.ndb.busy_msg or BUSY_MESSAGE)
        return True
    return False


def progress_bar(step, total, width=10):
    """Render ``[####------]``-style progress, filled in proportion."""
    filled = width * step // total if total else width
    return "#" * filled + "-" * (width - filled)


def _announce(caller, self_msg, room_msg, room_alt_msg):
    """Say what is starting, to the actor and to the room."""
    if self_msg:
        caller.msg(self_msg)
    if not room_msg or not caller.location:
        return
    if room_alt_msg:
        caller.location.msg_contents_with_invis_alt(
            room_msg, room_alt_msg, from_obj=caller,
        )
    else:
        caller.location.msg_contents(room_msg, exclude=[caller], from_obj=caller)


def start_busy_ticks(caller, ticks, interval, on_complete, progress=None,
                     done_msg=None, self_msg=None, room_msg=None,
                     room_alt_msg=None, busy_msg=None, busy_move_msg=None):
    """
    Hold the character across several ticks, reporting progress as it goes.

    The general form of the lock. ``start_busy`` is this with one tick and
    nothing to report, so both shapes share one implementation and one
    definition of what "busy" means.

    Args:
        caller: the character being held.
        ticks (int): how many intervals the action takes.
        interval (float): seconds per tick.
        on_complete (callable): run with no arguments once the last tick
            passes. Holds the whole outcome — success and failure both —
            so nothing about the result escapes before the action finishes.
        progress (callable, optional): ``(step, total) -> str``, sent to
            the character before each wait. Called with step 0 first, so
            an empty bar or a "0 of 5" appears immediately. Every caller
            words this itself: a bar for crafting, a count for processing.
        done_msg (str, optional): sent on the final tick, before
            ``on_complete``.
        self_msg (str, optional): announced to the character up front.
        room_msg (str, optional): announced to the rest of the room up
            front, filtered so observers who cannot perceive the actor do
            not receive it.
        room_alt_msg (str, optional): what those observers get instead —
            tools moving by themselves rather than a person using them.
            Supplying it switches the announcement to
            ``msg_contents_with_invis_alt``.
        busy_msg (str, optional): what a *second* command is refused with
            while this one holds the lock, in place of ``BUSY_MESSAGE``.
            Supply it where the generic wording would read wrong — being
            lost in a book is not "a job". Cleared on release, so it
            never answers for the action that follows.
        busy_move_msg (str, optional): the same, for a held character
            trying to walk away, in place of ``BUSY_MOVE_MESSAGE``. A
            separate string because the two refusals answer different
            questions and rarely word the same.

    Returns:
        bool: False if the character was already busy and nothing was
            started, True if the action is under way.

    The lock is released *before* ``on_complete`` runs, so an outcome that
    starts something else — combat, a second timed action — is not blocked
    by the action that produced it.
    """
    if check_busy(caller):
        return False

    _announce(caller, self_msg, room_msg, room_alt_msg)
    caller.ndb.is_processing = True
    caller.ndb.busy_msg = busy_msg
    caller.ndb.busy_move_msg = busy_move_msg

    def _tick(step):
        if step < ticks:
            if progress:
                caller.msg(progress(step, ticks))
            delay(interval, _tick, step + 1)
            return
        if done_msg:
            caller.msg(done_msg)
        caller.ndb.is_processing = False
        caller.ndb.busy_msg = None
        caller.ndb.busy_move_msg = None
        on_complete()

    if progress:
        caller.msg(progress(0, ticks))
    delay(interval, _tick, 1)
    return True


def start_busy(caller, seconds, on_complete, self_msg=None, room_msg=None,
               room_alt_msg=None, busy_msg=None, busy_move_msg=None):
    """
    Announce an action, hold the character for its duration, then resolve.

    The single-tick case of ``start_busy_ticks``, for actions short enough
    that a progress report would be noise. See that function for the
    arguments, which are the same minus the progress reporting.
    """
    return start_busy_ticks(
        caller, 1, seconds, on_complete,
        self_msg=self_msg, room_msg=room_msg, room_alt_msg=room_alt_msg,
        busy_msg=busy_msg, busy_move_msg=busy_move_msg,
    )
