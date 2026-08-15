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
from utils.busy import (
    FUMBLE_BUSY_MESSAGE,
    FUMBLE_MOVE_MESSAGE,
    check_busy,
    fumble_seconds,
    start_busy,
)
from utils.targeting.helpers import resolve_target
from utils.targeting.predicates import p_can_perceive
from utils.visibility import looker_is_blind


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
    aliases = []
    locks = "cmd:all()"
    help_category = "Items"

    def func(self):
        caller = self.caller

        if not self.args:
            caller.msg("Quaff what? Usage: quaff <potion>")
            return

        if check_busy(caller):
            return

        query = self.args.strip()

        # No sight check — your own pack is found by touch. Sightlessness
        # costs the time spent searching, and the search runs before the
        # outcome is known, so the wrong bottle costs the same as the
        # right one.
        if looker_is_blind(caller):
            start_busy(
                caller,
                fumble_seconds(),
                lambda: self._quaff(caller, query),
                self_msg="You fumble blindly through your pack...",
                busy_msg=FUMBLE_BUSY_MESSAGE,
                busy_move_msg=FUMBLE_MOVE_MESSAGE,
            )
            return

        self._quaff(caller, query)

    def _quaff(self, caller, query):
        """Find the potion and drink it. Success or failure both."""
        item, _ = resolve_target(
            caller, query, "items_inventory",
            extra_predicates=(p_can_perceive,),
        )
        if not item:
            caller.msg(f"You aren't carrying '{query}'.")
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
