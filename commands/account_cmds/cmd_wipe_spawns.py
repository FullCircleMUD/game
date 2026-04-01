"""
Superuser command: clear all spawned items from the game world.

Wipes all non-player-owned NFTs, gold, and resources from rooms,
mobs, and containers. Returns everything to RESERVE in the mirror DB.
Player-owned items (on characters and in account banks) are never touched.

Use before soft_deploy_world if needed, or to manually reset the
spawn state. Normal server restarts do NOT clear spawns.
"""

from evennia import Command


class CmdWipeSpawns(Command):
    """
    Clear all spawned items from the game world.

    Usage:
        wipe_spawns

    Removes all non-player-owned NFTs, gold, and resources from the
    game world and returns them to RESERVE. Player inventory and
    account banks are never touched.

    This is a destructive operation — all mob loot, room gold,
    harvest node resources, and chest contents will be wiped.
    The spawn system will redistribute over the next hour.
    """

    key = "wipe_spawns"
    locks = "cmd:id(1)"
    help_category = "Economy"

    def func(self):
        from utils.spawn_cleanup import clear_spawned_items

        self.msg("|yClearing all spawned items from the game world...|n")
        clear_spawned_items()
        self.msg("|gSpawn wipe complete. Items returned to RESERVE.|n")
        self.msg("The spawn system will redistribute over the next hour.")
