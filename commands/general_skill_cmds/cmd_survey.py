"""
survey command — cartographer action to add a room to a district map NFT.

Any character with CARTOGRAPHY BASIC+ can survey any tagged room they
physically reach. No mastery gate beyond BASIC.

Timer: ~3-4 seconds. Cancelled by leaving the room.
Multi-map: if the room carries multiple map_cell tags, ALL matching
inventory maps update simultaneously.
"""

from evennia import Command
from evennia.utils.utils import delay

from commands.command import FCMCommandMixin
from enums.mastery_level import MasteryLevel
from enums.skills_enum import skills


class CmdSurvey(FCMCommandMixin, Command):
    """
    Survey the current room and add it to your district map.

    Usage:
        survey

    Spend a few moments carefully studying the area and marking it
    on your parchment map. If the room is on a predefined map and
    you carry that map, the room is added to your surveyed points.

    Movement cancels the survey in progress.
    """

    key = "survey"
    aliases = ["sur", "surv"]
    help_category = "Exploration"

    def func(self):
        caller = self.caller

        # Check CARTOGRAPHY BASIC+
        mastery_levels = caller.db.general_skill_mastery_levels or {}
        cart_level = mastery_levels.get(skills.CARTOGRAPHY.value, 0)
        if cart_level < MasteryLevel.BASIC.value:
            caller.msg("You have no training in cartography.")
            return

        # Can't survey in combat
        if caller.scripts.get("combat_handler"):
            caller.msg("You can't survey while fighting!")
            return

        room = caller.location
        if room is None:
            return

        from world.cartography.map_registry import get_map_keys_for_room
        room_map_pairs = get_map_keys_for_room(room)

        if not room_map_pairs:
            caller.msg("There's nothing notable to map here.")
            return

        # Collect all (map_nft, point_key) pairs — include already-surveyed
        # rooms so adjacent revelation still fires on re-survey.
        targets = []
        for map_key, point_key in room_map_pairs:
            map_nft = self._get_map(caller, map_key)
            if map_nft is None:
                continue
            targets.append((map_nft, point_key))

        if not targets:
            caller.msg("There's nothing to map here.")
            return

        # Check if re-surveying would reveal any new adjacent cells.
        # If current room AND all adjacents are already surveyed, skip.
        from world.cartography.map_registry import get_map_keys_for_room as _get_keys, get_map
        has_new = any(pk not in nft.surveyed_points for nft, pk in targets)
        if not has_new:
            # Check adjacents for district-scale maps
            for exit_obj in room.exits:
                dest = exit_obj.destination
                if not dest:
                    continue
                for adj_map_key, adj_pk in _get_keys(dest):
                    adj_nft = self._get_map(caller, adj_map_key)
                    if not adj_nft:
                        continue
                    adj_map_def = get_map(adj_map_key)
                    if adj_map_def and adj_map_def.get("scale") == "region":
                        continue
                    if adj_pk not in adj_nft.surveyed_points:
                        has_new = True
                        break
                if has_new:
                    break
            if not has_new:
                caller.msg("You've already mapped everything notable here.")
                return

        # Notify room
        caller.msg(
            "You kneel down, unfurling your map. "
            "The scratch of charcoal on parchment echoes quietly..."
        )
        room.msg_contents(
            f"$You() $conj(kneel) and begin carefully surveying the area.",
            from_obj=caller,
            exclude=[caller],
        )

        room_id = room.id
        delay(3, _finish_survey, caller, targets, room_id)

    @staticmethod
    def _get_map(caller, map_key):
        """Return the first matching DistrictMapNFTItem in caller's inventory."""
        from typeclasses.items.maps.district_map_nft_item import DistrictMapNFTItem
        for item in caller.contents:
            if isinstance(item, DistrictMapNFTItem) and item.map_key == map_key:
                return item
        return None


def _finish_survey(caller, targets, room_id):
    """Callback fired after the survey timer."""
    # Safety checks
    if not caller or not caller.location:
        return
    if caller.location.id != room_id:
        caller.msg("|yYou moved before finishing the survey.|n")
        return

    from world.cartography.map_registry import get_map, get_map_keys_for_room

    # Batch point_keys per map object so we record (and persist to the NFT
    # mirror) once per map instead of once per point.
    batches = {}  # id(map_nft) -> [map_nft, [point_keys...]]

    def _add(map_nft, point_key):
        entry = batches.get(id(map_nft))
        if entry is None:
            entry = [map_nft, []]
            batches[id(map_nft)] = entry
        entry[1].append(point_key)

    map_nfts_by_key = {}
    for map_nft, point_key in targets:
        _add(map_nft, point_key)
        map_nfts_by_key[map_nft.map_key] = map_nft

    # Reveal adjacent rooms — district-scale maps only
    for exit_obj in caller.location.exits:
        dest = exit_obj.destination
        if not dest:
            continue
        for adj_map_key, adj_point_key in get_map_keys_for_room(dest):
            map_nft = map_nfts_by_key.get(adj_map_key)
            if not map_nft:
                continue
            adj_map_def = get_map(adj_map_key)
            if adj_map_def and adj_map_def.get("scale") == "region":
                continue
            _add(map_nft, adj_point_key)

    # Record (which also persists to mirror metadata) and report.
    updated = []
    for map_nft, point_keys in batches.values():
        map_nft.record_survey_points(point_keys)
        map_def = get_map(map_nft.map_key)
        name = map_def["display_name"] if map_def else map_nft.map_key
        pct = map_nft.completion_pct
        updated.append(f"{name}: {pct}%")

    if updated:
        caller.msg(f"|gRoom added to your map. ({', '.join(updated)})|n")
