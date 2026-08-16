"""
Search command — search the current room for hidden objects, characters,
and traps.

Uses ALERTNESS skill (perception). Rolls d20 + effective perception bonus
against each hidden object's find_dc, hidden characters' passive stealth,
and trap find_dc on trapped objects/exits/rooms.

Failed searches trigger a 120-second cooldown to prevent spam.

A searcher who cannot see does it by touch instead: the busy lock holds
them for a few seconds and every roll is made at disadvantage.

Usage:
    search
"""

import time

from evennia import Command

from commands.command import FCMCommandMixin
from enums.condition import Condition
from utils.busy import (
    FUMBLE_BUSY_MESSAGE,
    FUMBLE_MOVE_MESSAGE,
    check_busy,
    fumble_seconds,
    start_busy,
)
from utils.dice_roller import dice
from utils.visibility import looker_is_blind

_SEARCH_COOLDOWN = 120  # seconds after a failed search


class CmdSearch(FCMCommandMixin, Command):
    """
    Search the room for hidden objects and characters.

    Usage:
        search

    Rolls your perception (d20 + effective perception bonus)
    against the difficulty of each hidden object and the stealth
    of any hidden characters in the room.
    """

    key = "search"
    aliases = ()
    locks = "cmd:all()"
    arg_regex = r"\s|$"

    def func(self):
        caller = self.caller
        room = caller.location

        if not room:
            caller.msg("You have nowhere to search.")
            return

        if check_busy(caller):
            return

        # Searching without sight is slow, not impossible — you go over
        # the place by hand. The time is spent before the outcome is
        # known, so an empty room costs the same as one with something
        # in it. Sightlessness, not darkness: a blind character in a lit
        # room fumbles as much as a sighted one in the dark, and
        # darkvision passes straight through.
        if looker_is_blind(caller):
            start_busy(
                caller,
                fumble_seconds(),
                lambda: self._search(caller, sightless=True),
                self_msg="You feel your way over the room in the dark, "
                         "searching by touch...",
                busy_msg=FUMBLE_BUSY_MESSAGE,
                busy_move_msg=FUMBLE_MOVE_MESSAGE,
            )
            return

        self._search(caller)

    def _search(self, caller, sightless=False):
        """Resolve the search. Reached directly, or after a blind fumble."""
        room = caller.location
        if not room:
            return

        # Cooldown after failed searches — same message to avoid leaking info
        cooldown_until = getattr(caller.ndb, "search_cooldown_until", 0) or 0
        if time.time() < cooldown_until:
            caller.msg("You search but find nothing unusual.")
            return

        perception_bonus = caller.effective_perception_bonus

        # Find all hidden objects in the room (objects + exits)
        # Exits are in both room.contents and room.exits — use a set to dedupe
        hidden_objects = []
        seen_ids = set()
        for obj in list(room.contents) + list(room.exits):
            if obj.id in seen_ids:
                continue
            seen_ids.add(obj.id)
            if (
                hasattr(obj, "is_hidden")
                and obj.is_hidden
                and hasattr(obj, "is_hidden_visible_to")
                and not obj.is_hidden_visible_to(caller)
            ):
                hidden_objects.append(obj)

        # Find all hidden characters in the room
        hidden_chars = [
            obj for obj in room.contents
            if obj != caller
            and hasattr(obj, "has_condition")
            and obj.has_condition(Condition.HIDDEN)
        ]

        # Find all trapped objects/exits with undetected traps
        trapped_objects = []
        for obj in list(room.contents) + list(room.exits):
            if (
                hasattr(obj, "is_trapped")
                and obj.is_trapped
                and hasattr(obj, "trap_armed")
                and obj.trap_armed
                and hasattr(obj, "trap_detected")
                and not obj.trap_detected
            ):
                trapped_objects.append(obj)

        # Check room itself (pressure plates)
        if (
            hasattr(room, "is_trapped")
            and room.is_trapped
            and hasattr(room, "trap_armed")
            and room.trap_armed
            and hasattr(room, "trap_detected")
            and not room.trap_detected
        ):
            trapped_objects.append(room)

        if not hidden_objects and not hidden_chars and not trapped_objects:
            caller.msg("You search but find nothing unusual.")
            caller.ndb.search_cooldown_until = time.time() + _SEARCH_COOLDOWN
            return

        found_any = False

        # Consume non-combat advantage/disadvantage once for the whole search
        has_adv = getattr(caller.db, "non_combat_advantage", False)
        has_dis = getattr(caller.db, "non_combat_disadvantage", False)
        caller.db.non_combat_advantage = False
        caller.db.non_combat_disadvantage = False

        # Searching by touch is harder, expressed the way the game
        # already expresses harder. Note the standing resolution rule:
        # advantage and disadvantage cancel, so someone steadying a blind
        # searcher's hands restores a normal roll rather than stacking.
        if sightless:
            has_dis = True

        # Roll against each hidden object
        for obj in hidden_objects:
            roll = dice.roll_with_advantage_or_disadvantage(
                advantage=has_adv, disadvantage=has_dis
            )
            total = roll + perception_bonus
            dc = obj.find_dc

            if total >= dc:
                obj.discover(caller)
                found_any = True

        # Roll against each hidden character
        for target in hidden_chars:
            roll = dice.roll_with_advantage_or_disadvantage(
                advantage=has_adv, disadvantage=has_dis
            )
            total = roll + perception_bonus
            dc = 10 + target.effective_stealth_bonus

            if total >= dc:
                target.remove_condition(Condition.HIDDEN)
                caller.msg(
                    f"|gYou spot {target.key} lurking in the shadows!|n"
                )
                found_any = True

        # Roll against each trapped object
        for obj in trapped_objects:
            roll = dice.roll_with_advantage_or_disadvantage(
                advantage=has_adv, disadvantage=has_dis
            )
            total = roll + perception_bonus
            dc = obj.trap_find_dc

            if total >= dc:
                obj.detect_trap(caller)
                trap_desc = getattr(obj, "trap_description", "a trap")
                target_name = obj.key if obj != room else "the floor"
                caller.msg(
                    f"|rYou notice {trap_desc} on {target_name}!|n"
                )
                found_any = True

        if not found_any:
            caller.msg("You search but find nothing unusual.")
            caller.ndb.search_cooldown_until = time.time() + _SEARCH_COOLDOWN
