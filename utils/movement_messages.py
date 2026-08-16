"""
Wording for inter-room movement messages.

The verb rules and direction phrasing behind ``BaseActor.announce_move_from()``
and ``announce_move_to()`` — the single seam every inter-room movement message
passes through, so that a caller passing ``quiet=True`` genuinely silences the
move. Intra-room height changes (climb, fly/swim up or down) never call
``move_to()`` and are not part of this.

Adding a movement mode means appending a rule to ``MOVEMENT_RULES``, not
editing a conditional. See ``docs/movement-messages.md``.
"""


from collections import namedtuple


def _airborne(mover, room):
    """Above the ground under their own power."""
    return getattr(mover, "room_vertical_position", 0) > 0


def _in_water(mover, room):
    """
    Below the surface, or floating on a room that has depth.

    Height alone cannot decide this: position 0 is the water's surface in a
    room with depth, and the ground in a room without, so the room's
    ``max_depth`` has to be read alongside the mover's position.
    """
    position = getattr(mover, "room_vertical_position", 0)
    if position < 0:
        return True
    return position == 0 and (getattr(room, "max_depth", 0) or 0) < 0


#: How a move reads once a rule matches. ``end`` is the sentence terminator,
#: so a rule can be urgent without the caller knowing.
MovementRule = namedtuple("MovementRule", "matches departure arrival end")

#: How the mover is travelling — first match wins, falling through to walking.
#:
#: Predicates take ``(mover, room)`` and nothing else. These describe state the
#: seam can observe for itself, which is what makes them usable on the common
#: path: a plain walk goes command -> at_traverse() -> move_to(), so no caller
#: is in a position to say anything about it.
#:
#: Nothing keyed on *how a move was requested* belongs here. A caller that
#: knows something the seam can't see passes its own text instead, via
#: msg_from/msg_to — see BaseActor.announce_move_from.
MOVEMENT_RULES = [
    MovementRule(_airborne, "flies", "flies in", "."),
    MovementRule(_in_water, "swims", "swims in", "."),
]

#: Used when no rule matches.
DEFAULT_RULE = MovementRule(None, "leaves", "arrives", ".")

#: Shared wording for callers that must not drift apart. cmd_flee and
#: combat_handler both flee and should read the same, so they pass this rather
#: than each spelling it out.
FLEE_MESSAGES = {
    "msg_from": "{name} flees {direction}!",
    "msg_to": "{name} flees in {direction}!",
}


def resolve_rule(mover, room):
    """Return the :class:`MovementRule` describing how this move reads."""
    for rule in MOVEMENT_RULES:
        if rule.matches(mover, room):
            return rule
    return DEFAULT_RULE


def arrival_phrase(direction):
    """
    Phrase describing where someone arrived from.

    ``direction`` is the way *back* to where they came from — the reciprocal
    exit's own direction, or the opposite of the exit they traversed when
    there is no reciprocal. So a party whose way back is ``down`` came from
    below.
    """
    if direction == "down":
        return "from below"
    if direction == "up":
        return "from above"
    return f"from the {direction}"


def follows(obj, leader, max_hops=10):
    """
    True if ``obj``'s follow chain reaches ``leader``.

    Walks indirect chains (A follows B follows the leader), with a hop limit
    and a seen-set so a cycle cannot spin.
    """
    seen = set()
    current = getattr(obj, "following", None)
    while current is not None and current not in seen and len(seen) < max_hops:
        if current is leader:
            return True
        seen.add(current)
        current = getattr(current, "following", None)
    return False


def followers_in(leader, room):
    """
    Followers of ``leader`` currently standing in ``room``.

    Room-scoped and query-free. Takes the room as an argument rather than
    reading ``leader.location``, because ``announce_move_to()`` runs after the
    move while the followers are still behind in the source room.
    """
    if not room:
        return []
    return [obj for obj in room.contents if obj is not leader and follows(obj, leader)]
