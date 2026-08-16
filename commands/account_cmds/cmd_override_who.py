import time

import evennia
from evennia.commands.default.account import CmdWho as _CmdWho
from evennia.utils import utils


class CmdWho(_CmdWho):
    """
    List who is currently online.

    Usage:
        who

    Shows online players with their character name, level, class, and race.
    Only shows players connected to THIS process — not cluster-wide. A
    player IC on a different shard won't appear here even though they
    are online elsewhere; see docs/scaling.md's open TBD on cross-shard
    presence.
    """

    help_category = "Communication"

    def func(self):
        from evennia_shards import ROLE_MONOLITH, ROLE_ROUTER, get_role, get_shard_id

        role = get_role()
        if role == ROLE_MONOLITH:
            process_label = "monolith"
        elif role == ROLE_ROUTER:
            process_label = "router"
        else:
            process_label = get_shard_id() or role

        account = self.account
        session_list = evennia.SESSION_HANDLER.get_sessions()
        session_list = sorted(session_list, key=lambda o: o.account.key)

        is_admin = account.check_permstring(
            "Developer"
        ) or account.check_permstring("Admins")

        if is_admin:
            table = self.styled_table(
                "|wName", "|wLvl", "|wClass", "|wRace", "|wIdle", "|wLocation",
            )
        else:
            table = self.styled_table(
                "|wName", "|wLvl", "|wClass", "|wRace", "|wIdle",
            )

        count = 0
        for session in session_list:
            if not session.logged_in:
                continue

            count += 1
            char = session.get_puppet()

            # Idle time
            idle_secs = time.time() - session.cmd_last_visible
            if idle_secs < 120:
                idle_str = ""
            elif idle_secs < 3600:
                idle_str = f"{int(idle_secs // 60)}m"
            else:
                idle_str = f"{int(idle_secs // 3600)}h"

            if char:
                afk_tag = " |r(AFK)|n" if getattr(char, "afk", False) else ""
                name = utils.crop(char.key, width=20) + afk_tag

                level = getattr(char, "total_level", 0)

                classes = getattr(char.db, "classes", None) or {}
                if classes:
                    class_parts = [
                        f"{ck.capitalize()} {cd.get('level', 0)}"
                        for ck, cd in classes.items()
                    ]
                    class_str = " / ".join(class_parts)
                else:
                    class_str = "No class"

                race = getattr(char, "race", None)
                race_str = (
                    race.value if hasattr(race, "value") else str(race)
                ).capitalize() if race else "-"

                location = char.location.key if char and char.location else "-"
            else:
                # OOC — not puppeting
                name = f"{session.get_account().key} |x(OOC)|n"
                level = "-"
                class_str = "-"
                race_str = "-"
                location = "-"

            if is_admin:
                table.add_row(name, level, class_str, race_str, idle_str, location)
            else:
                table.add_row(name, level, class_str, race_str, idle_str)

        is_one = count == 1
        self.msg(
            "|wPlayers Online|n (this process: %s)\n%s\n%s player%s online."
            % (process_label, table, "One" if is_one else count, "" if is_one else "s")
        )
