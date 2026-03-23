"""
map command — view district maps from inventory.

Usage:
    map              — list all maps in inventory with completion %
    map <key>        — render the ASCII map server-side
    maps             — alias for map (list)

Server-side rendering: unexplored cells are replaced with '░' before
the string is sent to the client. The full template with character
markers is never transmitted, preventing cheating via text selection.
"""

from evennia import Command


class CmdMap(Command):
    """
    View your district maps.

    Usage:
        map
        map <map name or key>

    With no argument, lists all maps in your inventory with their
    current completion percentage.

    With an argument, renders the named map — unexplored areas appear
    as '░' so you must survey rooms to reveal them.
    """

    key = "map"
    aliases = ["maps"]
    help_category = "Exploration"

    def func(self):
        caller = self.caller
        arg = self.args.strip().lower()

        from typeclasses.items.maps.district_map_nft_item import DistrictMapNFTItem

        maps_in_inv = [
            item for item in caller.contents
            if isinstance(item, DistrictMapNFTItem)
        ]

        if not maps_in_inv:
            caller.msg("You don't have any maps.")
            return

        if not arg:
            # List all maps
            lines = ["|wMaps in your inventory:|n"]
            for m in maps_in_inv:
                lines.append(f"  {m.get_display_name(caller)}")
            caller.msg("\n".join(lines))
            return

        # Find matching map
        from world.cartography.map_registry import get_map, render_map

        match = None
        for m in maps_in_inv:
            if arg in m.map_key.lower() or (
                get_map(m.map_key) and
                arg in get_map(m.map_key).get("display_name", "").lower()
            ):
                match = m
                break

        if match is None:
            caller.msg(f"You don't have a map matching '{self.args.strip()}'.")
            return

        map_def = get_map(match.map_key)
        if not map_def:
            caller.msg("That map has no template data.")
            return

        rendered = render_map(map_def, match.surveyed_points)
        name = match.get_display_name(caller)
        caller.msg(f"|w{name}|n\n{rendered}")
