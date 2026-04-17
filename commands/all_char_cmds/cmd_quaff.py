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
from utils.targeting.helpers import resolve_target
from utils.targeting.predicates import p_can_see


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

        # Darkness — can't identify items without sight
        room = caller.location
        if room and hasattr(room, "is_dark") and room.is_dark(caller):
            caller.msg("It's too dark to see anything.")
            return

        item, _ = resolve_target(
            caller, self.args.strip(), "items_inventory",
            extra_predicates=(p_can_see,),
        )
        if not item:
            caller.msg(f"You aren't carrying '{self.args.strip()}'.")
            return

        # Type check — must be a potion
        if not isinstance(item, PotionNFTItem):
            caller.msg(f"{item.key} is not a potion.")
            return

        success, msg = item.consume(caller)
        caller.msg(msg)

        if success:
            caller.location.msg_contents(
                f"{caller.key} quaffs a potion.",
                exclude=[caller],
                from_obj=caller,
            )
