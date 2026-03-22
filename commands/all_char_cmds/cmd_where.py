from evennia import Command


class CmdWhere(Command):
    """
    Show your current location, district, and zone.

    Usage:
        where
    """

    key = "where"
    aliases = ["whe"]
    locks = "cmd:all()"
    help_category = "Character"

    def func(self):
        caller = self.caller
        room = caller.location

        if not room:
            caller.msg("You are nowhere.")
            return

        room_name = room.key
        district = getattr(room, "get_district", lambda: None)()
        zone = getattr(room, "get_zone", lambda: None)()

        caller.msg("\n|c--- Where ---|n")
        caller.msg(f"  Room:     {room_name}")
        caller.msg(f"  District: {district.replace('_', ' ').title() if district else '|xUnknown|n'}")
        caller.msg(f"  Zone:     {zone.replace('_', ' ').title() if zone else '|xUnknown|n'}")
