"""FCM-specific targeting helpers.

Thin wrappers over ``caller.search`` that pre-filter candidate lists
with FCM semantic predicates and then delegate string matching to
Evennia. Helpers are added only when a real consumer needs them — see
design/UNIFIED_SEARCH_SYSTEM.md and the Evennia-first rule in CLAUDE.md.
"""

from utils.targeting.predicates import (
    p_not_character,
    p_not_exit,
    p_visible_to,
)


def resolve_item_in_source(caller, source, search_term, **kwargs):
    """Identify an item inside a source object's contents.

    Pre-filters ``source.contents`` via FCM targeting predicates, then
    delegates string matching to ``caller.search`` with the filtered
    candidate list. Does not perform any action — callers decide what
    to do with the returned object(s).

    Source-agnostic: ``source`` can be a room, a container (chest,
    backpack, corpse), the caller themselves (for inventory lookup),
    or any object with a ``.contents`` attribute. The same helper is
    reusable across ``cmd_get``, ``cmd_drop``, "get from container",
    looting, and future commands.

    Filters applied to ``source.contents`` (in short-circuit order,
    cheapest first):
        1. p_not_character — exclude PCs, NPCs, mobs (also excludes
                             the caller, who is always a character)
        2. p_not_exit      — exclude exits
        3. p_visible_to    — exclude hidden objects the caller has
                             not discovered (HiddenObjectMixin)

    Filters explicitly NOT applied:
        - The ``get`` access lock. Callers keep that check so they
          can emit custom per-item error messages (e.g. "the chest
          is bolted to the floor" vs "you can't get that").
        - Fungible lookup. Gold/resources are handled elsewhere —
          this helper is item-only.

    Args:
        caller: The actor doing the identification. Used for both
            visibility checks and delegating to ``caller.search``.
        source: Any object with a ``.contents`` attribute. May be
            ``None`` or have no ``.contents`` — the helper returns
            ``None`` in either case rather than raising.
        search_term: The keyword typed by the player, already
            stripped of amount syntax (e.g. ``"sword"``, not
            ``"5.sword"``). Amount is passed separately via
            ``stacked=N`` in kwargs when required. Parsing is the
            command layer's job via ``utils.item_parse.parse_item_args``.
        **kwargs: Forwarded unchanged to ``caller.search``. Commonly
            used: ``stacked`` (for quantity), ``quiet`` (caller
            handles error messages), ``nofound_string`` /
            ``multimatch_string`` (custom error wording).

    Returns:
        Whatever ``caller.search`` returns given the filtered
        candidates: a single Evennia Object, a list of stacked
        Objects (when ``stacked=N`` is passed), or ``None`` when
        no match is found.
    """
    if source is None:
        return None
    contents = getattr(source, "contents", None)
    if not contents:
        return None

    candidates = [
        obj for obj in contents
        if p_not_character(obj, caller)
        and p_not_exit(obj, caller)
        and p_visible_to(obj, caller)
    ]

    if not candidates:
        return None

    return caller.search(search_term, candidates=candidates, **kwargs)
