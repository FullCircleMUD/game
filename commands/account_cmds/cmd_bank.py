"""
Account-level bank display — shows everything in the player's AccountBank.

Available from the OOC menu (account-level command). Shows all assets
that could be exported to the player's personal wallet.

Usage:
    bank
"""

from evennia import Command
from django.conf import settings

from blockchain.xrpl.currency_cache import get_resource_type
from commands.room_specific_cmds.bank.cmd_balance import ensure_bank
from typeclasses.items.base_nft_item import BaseNFTItem
from typeclasses.items.untakeables.world_anchored_nft_item import WorldAnchoredNFTItem

GOLD = settings.GOLD_DISPLAY


class CmdBank(Command):
    """
    View your in-game bank account.

    Shows all assets stored in your account bank, including gold,
    resources, and NFT items. These are the assets available for
    export to your personal wallet.

    Usage:
        bank
    """

    key = "bank"
    locks = "cmd:is_ooc()"
    help_category = "Bank"

    def func(self):
        account = self.caller

        bank = ensure_bank(account)

        # --- Collect bank contents ---
        gold = bank.get_gold()
        resources = bank.db.resources or {}
        all_nfts = [obj for obj in bank.contents if isinstance(obj, BaseNFTItem)]
        # Split BaseNFTItem instances into regular items vs world-anchored
        # (ships, future property). Ships have their own section so they
        # don't clutter the regular Items list.
        nft_items = [
            obj for obj in all_nfts if not isinstance(obj, WorldAnchoredNFTItem)
        ]
        ships = [
            obj for obj in all_nfts if isinstance(obj, WorldAnchoredNFTItem)
        ]
        stabled_pets = [
            obj for obj in bank.contents if getattr(obj, "is_pet", False)
        ]

        has_anything = (
            gold > 0
            or any(v > 0 for v in resources.values())
            or nft_items
            or stabled_pets
            or ships
        )

        if not has_anything:
            account.msg(
                "|c--- Account Bank ---|n\n"
                "Your bank is empty.\n"
                "|c--- End of Bank ---|n"
            )
            return

        # --- Build display ---
        lines = ["|c--- Account Bank ---|n"]

        # Gold
        if gold > 0:
            lines.append(f"  {GOLD['name']}: {gold} {GOLD['unit']}")

        # Resources
        for resource_id in sorted(resources.keys()):
            amount = resources[resource_id]
            if amount <= 0:
                continue
            rt = get_resource_type(resource_id)
            if rt:
                lines.append(f"  {rt['name']}: {amount} {rt['unit']}")
            else:
                lines.append(f"  Resource {resource_id}: {amount}")

        # NFT items
        if nft_items:
            lines.append("")
            lines.append("|wItems:|n")
            for obj in nft_items:
                token_label = f" |w[#{obj.id}]|n" if obj.token_id else ""
                condition = (
                    obj.get_condition_label()
                    if hasattr(obj, "get_condition_label")
                    else ""
                )
                cond_suffix = f"  ({condition})" if condition else ""
                lines.append(f"  {obj.key}{token_label}{cond_suffix}")

        # Stabled pets
        if stabled_pets:
            lines.append("")
            lines.append("|wPets:|n")
            for pet in stabled_pets:
                pet_type = getattr(pet, "pet_type", "")
                type_str = f" ({pet_type})" if pet_type else ""
                hp = getattr(pet, "hp", None)
                hp_max = getattr(pet, "hp_max", None)
                hp_str = f" — {hp}/{hp_max} HP" if hp is not None and hp_max else ""
                lines.append(f"  {pet.key}{type_str}{hp_str}")

        # Ships (and future world-anchored items like property)
        if ships:
            lines.append("")
            lines.append("|wShips:|n")
            for ship in ships:
                if hasattr(ship, "get_owned_display"):
                    lines.append(ship.get_owned_display())
                else:
                    token_label = f" |w[#{ship.id}]|n" if ship.token_id else ""
                    lines.append(f"  {ship.key}{token_label}")

        lines.append("")
        lines.append(
            "|yItems carried by your characters are not shown here.|n\n"
            "|yTo export an item from a character, deposit it at a bank first.|n"
        )
        lines.append("")
        lines.append(
            "Use |wexport <token_id>|n or |wexport gold 50|n"
            " to move assets to your wallet."
        )
        lines.append("|c--- End of Bank ---|n")
        account.msg("\n".join(lines))
