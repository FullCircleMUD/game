"""Shared visibility predicate for darkness-aware name display.

Used by BaseActor.get_display_name() and RoomBase.get_display_name() so
the "can this looker currently see anything?" check lives in one place
instead of being duplicated per typeclass.
"""

from enums.condition import Condition


def looker_is_blind(looker):
    """
    Return True if looker cannot currently see their own surroundings.

    True when either:
    - looker's current location is dark for looker (no light source,
      no DARKVISION), or
    - looker has the BLINDED condition (independent of room lighting).

    Used to redact names in messages the looker receives to generic
    placeholders ("Someone"/"Somewhere"), regardless of which specific
    object/room is actually being named.
    """
    if hasattr(looker, "has_condition") and looker.has_condition(Condition.BLINDED):
        return True

    location = getattr(looker, "location", None)
    if not location or not hasattr(location, "is_dark"):
        return False
    return location.is_dark(looker)
