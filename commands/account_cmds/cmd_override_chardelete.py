"""
Override of Evennia's default chardelete command.

Before deletion, moves all character assets (worn equipment, inventory
NFTs, gold, resources) to the player's AccountBank so nothing is lost.
"""

from django.conf import settings

from evennia import utils, logger
from evennia.commands.default.account import CmdCharDelete as DefaultCmdCharDelete
from evennia.utils.evmenu import get_input

from blockchain.xrpl.currency_cache import get_resource_type
from commands.room_specific_cmds.bank.cmd_balance import ensure_bank
from typeclasses.items.base_nft_item import BaseNFTItem

GOLD = settings.GOLD_DISPLAY


class CmdCharDelete(DefaultCmdCharDelete):
    """
    delete a character - this cannot be undone!

    Usage:
        chardelete <charname>

    Permanently deletes one of your characters. Any items, gold, and
    resources will be moved to your account bank first — you can
    withdraw them on another character.
    """

    locks = "cmd:pperm(Player) and is_ooc()"
    help_category = "System"

    def func(self):
        account = self.account

        if not self.args:
            self.msg("Usage: chardelete <charactername>")
            return

        # Find the character
        match = [
            char
            for char in utils.make_iter(account.characters)
            if char.key.lower() == self.args.lower()
        ]
        if not match:
            self.msg("You have no such character to delete.")
            return
        elif len(match) > 1:
            self.msg(
                "Aborting - there are two characters with the same name. "
                "Ask an admin to delete the right one."
            )
            return

        char = match[0]

        # Check permission
        if not char.access(account, "delete"):
            self.msg("You do not have permission to delete this character.")
            return

        # --- Build asset summary ---
        nfts = [obj for obj in char.contents if isinstance(obj, BaseNFTItem)]
        gold = char.get_gold() if hasattr(char, "get_gold") else 0
        resources = {
            k: v
            for k, v in (char.db.resources or {}).items()
            if v > 0
        } if hasattr(char.db, "resources") else {}

        asset_lines = []
        if nfts or gold > 0 or resources:
            asset_lines.append(
                "\nThe following assets will be moved to your account bank:"
            )
            if nfts:
                asset_lines.append(
                    f"  NFT items: {len(nfts)} "
                    f"({', '.join(obj.key for obj in nfts)})"
                )
            if gold > 0:
                asset_lines.append(
                    f"  {GOLD['name']}: {gold} {GOLD['unit']}"
                )
            for rid, amt in resources.items():
                rt = get_resource_type(rid)
                name = rt["name"] if rt else f"Resource {rid}"
                asset_lines.append(f"  {name}: {amt}")

        asset_note = "\n".join(asset_lines) if asset_lines else ""

        # --- Confirmation ---
        account.ndb._char_to_delete = char

        def _callback(caller, callback_prompt, result):
            if result.lower() != "yes":
                self.msg("Deletion was aborted.")
                del caller.ndb._char_to_delete
                return

            delobj = caller.ndb._char_to_delete
            key = delobj.key

            # Ensure account bank exists
            bank = ensure_bank(caller)

            # 1. Remove all worn equipment back to inventory
            if hasattr(delobj, "get_all_worn"):
                for slot, item in list(delobj.get_all_worn().items()):
                    delobj.remove(item)

            # 2. Move all NFT items to account bank
            for obj in list(delobj.contents):
                if isinstance(obj, BaseNFTItem):
                    obj.move_to(bank, quiet=True, move_type="give")

            # 3. Transfer all gold to account bank
            if hasattr(delobj, "get_gold"):
                gold_amt = delobj.get_gold()
                if gold_amt > 0:
                    delobj.transfer_gold_to(bank, gold_amt)

            # 4. Transfer all resources to account bank
            if hasattr(delobj, "get_all_resources"):
                for rid, amt in list(delobj.get_all_resources().items()):
                    if amt > 0:
                        delobj.transfer_resource_to(bank, rid, amt)

            # 5. Delete character
            caller.characters.remove(delobj)
            deleted = delobj.delete()

            if deleted:
                self.msg(f"Character '{key}' was permanently deleted.")
                if nfts or gold > 0 or resources:
                    self.msg(
                        "Your assets have been moved to your account bank."
                    )
                logger.log_sec(
                    f"Character Deleted: {key} "
                    f"(Caller: {account}, IP: {self.session.address})."
                )
            else:
                self.msg(
                    f"|rFailed to delete '{key}'. "
                    f"Please contact an admin.|n"
                )

            del caller.ndb._char_to_delete

        prompt = (
            f"|rThis will permanently destroy '{char.key}'. "
            f"This cannot be undone.|n"
            f"{asset_note}"
            f"\n\nContinue yes/[no]?"
        )
        get_input(account, prompt, _callback)
