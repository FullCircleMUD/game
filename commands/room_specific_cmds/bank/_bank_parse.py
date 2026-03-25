"""
Strict parse helper for irreversible/costly commands (junk, import, export).

These commands require exact name or item ID — NO fuzzy matching.
This prevents accidental destruction or gas-costing operations on the
wrong item. For reversible commands (get, drop, give, deposit, withdraw,
wear, wield, hold, remove), use utils.item_parse.parse_item_args() instead.

Syntax:
    <fungible> [amount|all]    — gold/resource with optional amount (default 1)
    #<id>                      — NFT by Evennia object ID (number)
"""

from blockchain.xrpl.currency_cache import get_all_resource_types


def parse_bank_args(args):
    """
    Strict parser for irreversible/costly commands (junk, import, export).

    Args:
        args: raw argument string from the command

    Returns:
        ("nft", item_id, None, None)             — NFT by Evennia object ID
        ("gold", amount, None, None)             — gold (amount=1 default)
        ("resource", amount, resource_id, info)  — resource (amount=1 default)
        None                                     — no match

    amount is None when "all" is specified.
    """
    if not args or not args.strip():
        return None

    args = args.strip()
    words = args.split()
    first = words[0].lower()

    # --- #<digits> → NFT by Evennia object ID ---
    if first.startswith("#") and first[1:].isdigit():
        return ("nft", int(first[1:]), None, None)

    # --- Number first → NFT by Evennia object ID ---
    try:
        item_id = int(first)
        return ("nft", item_id, None, None)
    except ValueError:
        pass

    # --- Determine amount from second word ---
    if len(words) >= 2:
        second = words[1].lower()
        if second == "all":
            amount = None  # None signals "all"
        else:
            try:
                amount = int(second)
                if amount <= 0:
                    return None
            except ValueError:
                return None  # second word is neither a number nor "all"
    else:
        amount = 1  # default: 1

    # --- Check if first word is gold ---
    if first == "gold":
        return ("gold", amount, None, None)

    # --- Check if first word is a resource name ---
    all_types = get_all_resource_types()
    for rid, info in all_types.items():
        if info["name"].lower() == first:
            return ("resource", amount, rid, info)

    return None
