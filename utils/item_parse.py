"""
Shared item argument parser for all item-related commands.

Standardises on amount-first syntax everywhere:
    #7              → NFT by token ID
    50 gold         → 50 gold
    all gold        → all gold
    all wheat       → all wheat (resource)
    gold            → 1 gold (default amount)
    wheat           → 1 wheat (default amount)
    all             → everything
    sword           → item by name (for caller.search())
    iron longsword  → item by name

Used by: get, drop, give, deposit, withdraw, wear, wield, hold, remove.
NOT used by: junk, import, export (strict mode — use _bank_parse instead).
"""

from collections import namedtuple

from blockchain.xrpl.currency_cache import get_all_resource_types


ParsedItem = namedtuple(
    "ParsedItem",
    ["type", "amount", "resource_id", "resource_info", "token_id", "search_term"],
)


def _match_fungible(name):
    """
    Check if a name matches gold or a resource type.

    Returns:
        ("gold", None, None)              if name matches "gold"
        ("resource", resource_id, info)   if name matches a resource
        None                              if no match
    """
    name_lower = name.lower().strip()
    if name_lower == "gold":
        return ("gold", None, None)

    for rid, info in get_all_resource_types().items():
        if info["name"].lower() == name_lower:
            return ("resource", rid, info)

    return None


def parse_item_args(args):
    """
    Parse item command arguments into a structured result.

    Args:
        args: raw argument string from the command

    Returns:
        ParsedItem namedtuple or None if empty input.

        ParsedItem fields:
            type        — "token_id" | "gold" | "resource" | "all" | "item"
            amount      — int or None (None = "all of it")
            resource_id — int or None
            resource_info — dict or None
            token_id    — int or None
            search_term — str or None (for item name searches)
    """
    if not args or not args.strip():
        return None

    args = args.strip()

    # --- #<digits> → token ID ---
    if args.startswith("#") and args[1:].isdigit():
        return ParsedItem(
            type="token_id",
            amount=None,
            resource_id=None,
            resource_info=None,
            token_id=int(args[1:]),
            search_term=None,
        )

    words = args.split()

    # --- "all" prefix ---
    if words[0].lower() == "all":
        if len(words) == 1:
            # Bare "all"
            return ParsedItem(
                type="all",
                amount=None,
                resource_id=None,
                resource_info=None,
                token_id=None,
                search_term=None,
            )
        remainder = " ".join(words[1:])
        match = _match_fungible(remainder)
        if match:
            ftype, rid, info = match
            return ParsedItem(
                type=ftype,
                amount=None,  # None = all
                resource_id=rid,
                resource_info=info,
                token_id=None,
                search_term=None,
            )
        # "all <something>" where something isn't a fungible → item search
        return ParsedItem(
            type="item",
            amount=None,
            resource_id=None,
            resource_info=None,
            token_id=None,
            search_term=remainder,
        )

    # --- Leading number ---
    if words[0].isdigit():
        number = int(words[0])
        if len(words) == 1:
            # Bare number → token ID
            return ParsedItem(
                type="token_id",
                amount=None,
                resource_id=None,
                resource_info=None,
                token_id=number,
                search_term=None,
            )
        remainder = " ".join(words[1:])
        match = _match_fungible(remainder)
        if match:
            ftype, rid, info = match
            return ParsedItem(
                type=ftype,
                amount=number,
                resource_id=rid,
                resource_info=info,
                token_id=None,
                search_term=None,
            )
        # Number + non-fungible → pass whole string as item search
        # (lets NumberedTargetCommand handle stacking if applicable)
        return ParsedItem(
            type="item",
            amount=None,
            resource_id=None,
            resource_info=None,
            token_id=None,
            search_term=args,
        )

    # --- Multi-word fungible check (e.g. "iron ore", "iron ingot") ---
    match = _match_fungible(args)
    if match:
        ftype, rid, info = match
        return ParsedItem(
            type=ftype,
            amount=1,
            resource_id=rid,
            resource_info=info,
            token_id=None,
            search_term=None,
        )

    # --- Single-word fungible check (e.g. "gold", "wheat", "gold 50") ---
    match = _match_fungible(words[0])
    if match:
        ftype, rid, info = match
        amount = 1  # default
        if len(words) > 1:
            if words[1].lower() == "all":
                amount = None
            elif words[1].isdigit():
                amount = int(words[1])
        return ParsedItem(
            type=ftype,
            amount=amount,
            resource_id=rid,
            resource_info=info,
            token_id=None,
            search_term=None,
        )

    # --- Everything else → item search ---
    return ParsedItem(
        type="item",
        amount=None,
        resource_id=None,
        resource_info=None,
        token_id=None,
        search_term=args,
    )
