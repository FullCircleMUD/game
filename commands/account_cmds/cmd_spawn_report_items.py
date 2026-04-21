"""
Superuser command: show spawned knowledge NFTs and spell scrolls.

Queries the mirror DB for all NFTs currently in SPAWNED location,
grouped by item type and typeclass (scroll vs recipe vs other).
"""

from evennia import Command


class CmdSpawnReportItems(Command):
    """
    Show all spawned NFTs in the game world.

    Usage:
        spawn_report_items

    Displays counts of all NFT items currently spawned (on mobs,
    in rooms, in chests) grouped by type. Useful for checking
    whether the spawn system is distributing knowledge NFTs.
    """

    key = "spawn_report_items"
    locks = "cmd:id(1)"
    help_category = "Economy"

    def func(self):
        from collections import defaultdict
        from blockchain.xrpl.models import NFTGameState, NFTItemType

        # All spawned NFTs
        spawned = NFTGameState.objects.filter(
            location=NFTGameState.LOCATION_SPAWNED,
            item_type__isnull=False,
        ).select_related("item_type")

        if not spawned.exists():
            self.msg("No NFTs currently spawned in the game world.")
            return

        # Group by typeclass category and item name
        scrolls = defaultdict(int)
        recipes = defaultdict(int)
        other = defaultdict(int)

        for nft in spawned:
            name = nft.item_type.name if nft.item_type else "Unknown"
            tc = nft.item_type.typeclass if nft.item_type else ""

            if "spell_scroll" in tc:
                scrolls[name] += 1
            elif "crafting_recipe" in tc:
                recipes[name] += 1
            else:
                other[name] += 1

        # Display
        self.msg("|w=== Spawned NFT Report ===|n")

        if scrolls:
            self.msg(f"\n|wSpell Scrolls|n ({sum(scrolls.values())} total):")
            for name, count in sorted(scrolls.items()):
                self.msg(f"  {name}: {count}")

        if recipes:
            self.msg(f"\n|wCrafting Recipes|n ({sum(recipes.values())} total):")
            for name, count in sorted(recipes.items()):
                self.msg(f"  {name}: {count}")

        if other:
            self.msg(f"\n|wOther NFTs|n ({sum(other.values())} total):")
            for name, count in sorted(other.items()):
                self.msg(f"  {name}: {count}")

        total = sum(scrolls.values()) + sum(recipes.values()) + sum(other.values())
        self.msg(f"\n|wTotal spawned:|n {total}")
