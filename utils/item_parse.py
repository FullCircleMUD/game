"""
Shared item argument parser for all item-related commands.

Supports both space-delimited and dot syntax:
    #7              → NFT by token ID
    50 gold         → 50 gold
    50.gold         → 50 gold (dot syntax)
    all gold        → all gold
    all.gold        → all gold (dot syntax)
    all wheat       → all wheat (resource)
    all.wheat       → all wheat (dot syntax)
    gold            → 1 gold (default amount)
    wheat           → 1 wheat (default amount)
    all             → everything
    sword           → item by name (for caller.search())
    5.sword         → 5th sword (dot syntax for items)
    all.sword       → all swords (dot syntax for items)
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

QuantifiedArgs = namedtuple("QuantifiedArgs", ["quantity", "subject"])

#: What ``quantity`` holds when the player asked for everything.
ALL = "all"


def split_quantity(args):
    """Split "how many" from "of what".

    The first question every command with a countable argument asks,
    whatever it goes on to search — inventory, a room, a container, a
    corpse. ``get all gold``, ``drop 5 wheat`` and ``deposit all wheat``
    differ in scope, not in shape, so the splitting belongs in one
    place and the searching belongs to the command.

    **Counts lead.** ``5 wheat``, never ``wheat 5``. One order across
    every command, so a player who learns it once has learned it
    everywhere. A trailing number is part of the name, which also keeps
    an item called "key 3" reachable by that name.

    Accepted forms, space or dot::

        cap             → (None, "cap")
        5 wheat         → (5, "wheat")
        5.wheat         → (5, "wheat")
        all wheat       → (ALL, "wheat")
        all.wheat       → (ALL, "wheat")
        all             → (ALL, None)

    Judges nothing. It does not know what stacks, what the caller
    holds, or whether the command accepts a count at all — a count on
    something that cannot be counted is rejected downstream, where the
    answer is known. Zero and a subject of "5" are reported as typed
    for the same reason.

    Args:
        args: the raw argument string, or None.

    Returns:
        ``QuantifiedArgs(quantity, subject)`` where ``quantity`` is an
        int, ``ALL``, or None, and ``subject`` is a string or None
        (bare "all"). Returns None for empty input, matching
        ``parse_item_args``.
    """
    if not args or not args.strip():
        return None

    text = args.strip()
    head, sep, tail = text.partition(".")
    if not sep:
        head, _, tail = text.partition(" ")

    quantity = None
    if head.lower() == ALL:
        quantity = ALL
    elif head.isdigit():
        quantity = int(head)

    subject = " ".join(tail.split()) or None

    # A number with nothing to count is a name, however odd — only
    # "all" carries meaning on its own.
    if quantity is None or (subject is None and quantity is not ALL):
        return QuantifiedArgs(None, " ".join(text.split()))

    return QuantifiedArgs(quantity, subject)


def _match_fungible(name):
    """
    Check if a name matches gold or a resource type.

    Returns:
        ("gold", None, None)              if name matches "gold"
        ("resource", resource_id, info)   if name matches a resource
        None                              if no match
    """
    name_lower = name.lower().strip()
    if name_lower in ("gold", "coins", "coin", "gold coins", "gold coin"):
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

    # --- Dot syntax: "5.bread", "all.wheat", "all.sword" ---
    # Check first word only — rest may be container ("5.bread bag")
    words = args.split()
    first = words[0]
    if "." in first and not first.startswith(".") and not first.endswith("."):
        prefix, dot_target = first.split(".", 1)
        remainder_words = words[1:]  # anything after (container, target, etc.)

        if prefix.lower() == "all":
            dot_amount = None  # None = all
        elif prefix.isdigit():
            dot_amount = int(prefix)
        else:
            dot_amount = None  # not a valid dot prefix, skip to normal parsing
            prefix = None

        if prefix is not None:
            # Rebuild remaining args without the dot-syntax token
            remaining = " ".join(remainder_words) if remainder_words else ""

            match = _match_fungible(dot_target)
            if match:
                ftype, rid, info = match
                return ParsedItem(
                    type=ftype,
                    amount=dot_amount,
                    resource_id=rid,
                    resource_info=info,
                    token_id=None,
                    search_term=remaining or None,
                )
            # Dot syntax for items: "5.sword" or "all.corpse"
            # Rejoin target + remaining for search
            search = dot_target + (" " + remaining if remaining else "")
            return ParsedItem(
                type="item",
                amount=dot_amount,
                resource_id=None,
                resource_info=None,
                token_id=None,
                search_term=search,
            )

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
