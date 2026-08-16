"""
Superuser command: clear all spawned items from the game world.

DISABLED under sharding — see func() below. Was: wipes all
non-player-owned NFTs, gold, and resources from rooms, mobs, and
containers, returning everything to RESERVE in the mirror DB.
Player-owned items (on characters and in account banks) were never
touched.
"""

from evennia import Command


class CmdWipeSpawns(Command):
    """
    Clear all spawned items from the game world.

    DISABLED — see func().

    Usage:
        wipe_spawns
    """

    key = "wipe_spawns"
    locks = "cmd:id(1)"
    help_category = "Economy"

    def func(self):
        # Disabled under sharding: utils.spawn_cleanup.clear_spawned_items()'s
        # sweep 2 resets NFTGameState/FungibleGameState rows still marked
        # SPAWNED with no shard filter at all — those are global,
        # unpartitioned tables. Running this on even a single shard would
        # desync the mirror DB for items still legitimately spawned and
        # alive on OTHER shards, not just the shard it was run on. Needs
        # sweep 2 split out from sweeps 1+3 (which are safely shard-scoped
        # already) before this command can be re-enabled. See
        # ops/DEVELOPMENT/ADMIN_COMMAND_SHARD_AUDIT.md.
        #
        # from utils.spawn_cleanup import clear_spawned_items
        #
        # self.msg("|yClearing all spawned items from the game world...|n")
        # clear_spawned_items()
        # self.msg("|gSpawn wipe complete. Items returned to RESERVE.|n")
        # self.msg("The spawn system will redistribute over the next hour.")

        self.msg(
            "|rwipe_spawns is disabled under sharding.|n\n"
            "Its cleanup logic resets global mirror-DB state with no "
            "shard filter — running it on one shard would desync items "
            "still spawned and alive on other shards. Needs a rework "
            "before it can be safely re-enabled."
        )
