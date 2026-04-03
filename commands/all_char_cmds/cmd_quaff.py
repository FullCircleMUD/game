"""
Quaff command — consume a potion NFT to apply its effects.

Usage:
    quaff <item>        — drink a potion from your inventory
    drink <item>        — alias for quaff

The potion NFT is consumed (returned to game reserve) on success.
"""

from evennia import Command

from commands.command import FCMCommandMixin
from typeclasses.items.consumables.potion_nft_item import PotionNFTItem


class CmdQuaff(FCMCommandMixin, Command):
    """
    Drink a potion from your inventory.

    Usage:
        quaff <potion>
        drink <potion>

    Examples:
        quaff potion
        drink life's essence
        qu potion

    The potion is consumed when drunk.
    """

    key = "quaff"
    aliases = ["qu", "drink", "dr"]
    locks = "cmd:all()"
    help_category = "Items"

    def func(self):
        caller = self.caller

        if not self.args:
            caller.msg("Quaff what? Usage: quaff <potion>")
            return

        candidates = [
            obj for obj in caller.contents
            if isinstance(obj, PotionNFTItem)
        ]

        if not candidates:
            caller.msg("You aren't carrying any potions.")
            return

        item = caller.search(
            self.args.strip(),
            candidates=candidates,
            quiet=True,
        )

        if not item:
            caller.msg("You don't have a potion by that name.")
            return

        # handle list vs single result — just use the first match
        if isinstance(item, list):
            item = item[0]

        success, msg = item.consume(caller)
        caller.msg(msg)

        if success:
            caller.location.msg_contents(
                f"{caller.key} quaffs a potion.",
                exclude=[caller],
                from_obj=caller,
            )
