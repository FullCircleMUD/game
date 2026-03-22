"""
Junk command — permanently destroy items, gold, or resources.

Uses the strict _bank_parse parser (exact name or token ID only) because
destruction is irreversible. No fuzzy/substring matching.

Usage:
    junk #<id>              — destroy an NFT by token ID
    junk <id>               — destroy an NFT by token ID (bare number)
    junk gold [amount|all]  — destroy gold
    junk <resource> [amount|all] — destroy resources (e.g. junk wheat 3)
"""

from evennia import Command

from commands.room_specific_cmds.bank._bank_parse import parse_bank_args


class CmdJunk(Command):
    """
    Permanently destroy items, gold, or resources from your inventory.

    Usage:
        junk #<id>
        junk <id>
        junk gold [amount|all]
        junk <resource> [amount|all]

    Examples:
        junk #42
        junk gold 50
        junk wheat 3
        junk gold all

    Uses strict matching (token ID or exact fungible name only).
    Destroyed assets are returned to the game vault. This cannot be undone.
    """

    key = "junk"
    locks = "cmd:all()"
    help_category = "Items"

    def func(self):
        caller = self.caller

        if not self.args:
            caller.msg(
                "Usage: junk #<id> | junk gold [amount] | junk <resource> [amount]"
            )
            return

        parsed = parse_bank_args(self.args)

        if parsed is None:
            caller.msg(
                "Junk what? Use exact names or token IDs.\n"
                "  junk #42  |  junk gold 50  |  junk wheat 3"
            )
            return

        parsed_type = parsed[0]

        if parsed_type == "nft":
            yield from self._junk_nft(caller, parsed[1])
        elif parsed_type == "gold":
            yield from self._junk_gold(caller, parsed[1])
        else:  # resource
            yield from self._junk_resource(
                caller, parsed[1], parsed[2], parsed[3]
            )

    def _junk_nft(self, caller, token_id):
        """Junk an NFT item from inventory by token ID."""
        from typeclasses.items.base_nft_item import BaseNFTItem

        nft_item = None
        for obj in caller.contents:
            if isinstance(obj, BaseNFTItem) and obj.token_id == token_id:
                nft_item = obj
                break

        if nft_item is None:
            caller.msg(f"You aren't carrying an item with ID #{token_id}.")
            return

        if caller.is_worn(nft_item):
            caller.msg(f"You must remove {nft_item.key} first.")
            return

        # Container contents warning
        container_warning = ""
        if getattr(nft_item, "is_container", False):
            if not nft_item.is_empty():
                container_warning = (
                    f"\n|r{nft_item.key} is NOT empty!|n"
                    f"\n{nft_item.get_container_display()}"
                    f"\n|rAll contents will also be destroyed!|n"
                )

        answer = yield (
            f"\n|r--- WARNING ---|n"
            f"\nYou are about to permanently destroy:"
            f" |w{nft_item.key}|n (NFT #{nft_item.token_id})"
            + container_warning
            + f"\n|rThis cannot be undone.|n"
            f"\n\nAre you sure? Y/[N]"
        )

        if answer.lower() not in ("y", "yes"):
            caller.msg("Junk cancelled.")
            return

        name = nft_item.key
        try:
            nft_item.delete()
        except ValueError as err:
            caller.msg(f"|rError destroying NFT: {err}|n")
            return

        caller.msg(f"|y{name} has been destroyed.|n")

    def _junk_gold(self, caller, amount):
        """Junk gold from inventory."""
        from django.conf import settings

        current = caller.get_gold()

        if amount is None:
            amount = current  # "all"

        if amount <= 0:
            caller.msg("Amount must be positive.")
            return

        if current < amount:
            caller.msg(f"You only have {current} gold.")
            return

        GOLD = settings.GOLD_DISPLAY

        answer = yield (
            f"\n|r--- WARNING ---|n"
            f"\nYou are about to permanently destroy:"
            f" |w{amount} {GOLD['unit']}|n of {GOLD['name']}"
            f"\n|rThis cannot be undone.|n"
            f"\n\nAre you sure? Y/[N]"
        )

        if answer.lower() not in ("y", "yes"):
            caller.msg("Junk cancelled.")
            return

        try:
            caller.return_gold_to_sink(amount)
        except ValueError as err:
            caller.msg(f"|rError destroying gold: {err}|n")
            return

        caller.msg(f"|y{amount} {GOLD['unit']} of {GOLD['name']} destroyed.|n")

    def _junk_resource(self, caller, amount, resource_id, resource_info):
        """Junk resources from inventory."""
        current = caller.get_resource(resource_id)

        if amount is None:
            amount = current  # "all"

        if amount <= 0:
            caller.msg("Amount must be positive.")
            return

        if current < amount:
            caller.msg(
                f"You only have {current} {resource_info['unit']}"
                f" of {resource_info['name']}."
            )
            return

        answer = yield (
            f"\n|r--- WARNING ---|n"
            f"\nYou are about to permanently destroy:"
            f" |w{amount} {resource_info['unit']}|n of {resource_info['name']}"
            f"\n|rThis cannot be undone.|n"
            f"\n\nAre you sure? Y/[N]"
        )

        if answer.lower() not in ("y", "yes"):
            caller.msg("Junk cancelled.")
            return

        try:
            caller.return_resource_to_sink(resource_id, amount)
        except ValueError as err:
            caller.msg(f"|rError destroying resource: {err}|n")
            return

        caller.msg(
            f"|y{amount} {resource_info['unit']}"
            f" of {resource_info['name']} destroyed.|n"
        )
