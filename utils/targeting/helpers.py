"""FCM-specific targeting helpers.

Thin wrappers over ``caller.search`` that pre-filter candidate lists
with FCM semantic predicates and then delegate string matching to
Evennia. Helpers are added only when a real consumer needs them — see
design/UNIFIED_SEARCH_SYSTEM.md and the Evennia-first rule in CLAUDE.md.
"""

from utils.targeting.predicates import (
    p_is_character,
    p_is_container,
    p_not_actor,
    p_not_exit,
    p_visible_to,
)


#: The universal "item-like" filter stack. Any lookup that wants
#: "things in source.contents that could be items the caller might
#: act on" combines these with additional filters as needed. Excludes
#: actors (PCs, NPCs, mobs, pets, mounts — anything living), exits,
#: and objects the caller can't currently see (HiddenObjectMixin).
BASE_ITEM_PREDICATES = (p_not_actor, p_not_exit, p_visible_to)


def walk_contents(caller, source, *predicates):
    """Walk ``source.contents`` once and return objects passing every predicate.

    Universal targeting primitive. The caller supplies the predicate
    stack they want; ``walk_contents`` runs it via short-circuit
    ``all()`` so the first failing predicate stops evaluation for
    that object.

    Compose with ``BASE_ITEM_PREDICATES`` for the standard "item-like"
    filter, or pass a custom stack for specialised lookups::

        # Standard item filter:
        walk_contents(caller, source, *BASE_ITEM_PREDICATES)

        # Item filter plus container requirement:
        walk_contents(
            caller, source, *BASE_ITEM_PREDICATES, p_is_container,
        )

        # Custom filter ignoring the base stack entirely:
        walk_contents(caller, source, p_is_mob)

    Returns an empty list if ``source`` is ``None`` or has no
    ``.contents`` attribute, so callers can iterate the result
    unconditionally.

    Predicate order matters for efficiency: place cheap predicates
    (identity/attribute checks) before expensive ones (method calls,
    lock checks) so short-circuit eval pays off.
    """
    if source is None:
        return []
    contents = getattr(source, "contents", None)
    if not contents:
        return []
    return [
        obj for obj in contents
        if all(p(obj, caller) for p in predicates)
    ]


def bucket_contents(caller, source, key_fn, *predicates, order=None):
    """Walk ``source.contents`` once, filter via predicates, bucket via key_fn.

    Single-pass sibling of ``walk_contents``. Objects that pass every
    predicate are passed to ``key_fn(obj, caller)``, which returns:

    - A hashable bucket name (string, enum, int) — ``obj`` is
      appended to that bucket.
    - ``None`` — ``obj`` is skipped entirely (not appended to any
      bucket).

    Returns a dict ``{bucket_name: [objects]}``. Buckets are created
    lazily via ``setdefault`` — if no object maps to bucket "X" and
    "X" is not in ``order``, that key will not be in the returned
    dict. Callers should use ``buckets.get("X", [])`` to retrieve
    safely.

    **Ordered iteration via ``order``**: When a caller supplies a
    priority tuple ``order=("caster", "healer", ...)``, the returned
    dict pre-populates those keys (with empty lists where no object
    was classified) and preserves insertion order so iterating the
    dict follows the caller's priority. Extra buckets the classifier
    produced that aren't in ``order`` are appended at the end in
    classification order (they are NOT dropped — the caller can
    filter post-hoc if needed).

    This makes the common AI threat / priority-tier pattern idiomatic::

        tiers = bucket_contents(
            mob, mob.location, classify_by_role,
            p_living, p_is_enemy,
            order=("caster", "healer", "ranged", "melee"),
        )
        for priority, targets in tiers.items():
            if targets:
                return pick(targets)

    Design rules:

    - Use ``walk_contents`` when you want a flat filtered list and
      don't need to partition the results.
    - Use ``bucket_contents`` when matching objects need to be
      partitioned into multiple named groups by a per-object key
      (e.g. combat allies vs enemies, AI threat tiers, faction
      membership).
    - Pass ``order`` when callers care about iteration priority or
      want empty buckets to be present in the result for
      fall-through logic.

    Performance: single pass over ``source.contents``. Predicates
    short-circuit via ``all()`` before ``key_fn`` runs, so
    expensive classifier work only touches objects that survive
    filtering. Pre-populating ``order`` buckets is O(len(order))
    and happens once before the walk — negligible for typical
    priority tuples of 2–10 entries.

    The primary consumer is ``combat.combat_utils.get_sides`` which
    partitions living combatants into allies / enemies buckets. Also
    designed for future AI threat bucketing and multi-faction combat.

    Args:
        caller: The actor driving the query. Used for visibility
            predicates and forwarded to ``key_fn``.
        source: Any object with a ``.contents`` attribute. May be
            ``None`` — the helper returns ``{}`` rather than raising.
        key_fn: Callable ``(obj, caller) -> str | None`` that
            classifies an object into a bucket. Returning ``None``
            skips the object.
        *predicates: Zero or more ``(obj, caller) -> bool`` filters
            applied before ``key_fn``.
        order: Optional iterable of bucket names. When supplied,
            those buckets are pre-populated (empty if no match) and
            the returned dict preserves the specified order. Extra
            buckets from the classifier are appended after.

    Returns:
        A dict mapping bucket names to lists of objects. Keys from
        ``order`` (if supplied) come first in the specified
        sequence; additional buckets from the classifier follow.
        Empty dict if ``source`` is ``None`` or has no
        ``.contents`` (and ``order`` was not supplied).
    """
    if source is None:
        return dict.fromkeys(order, []) if order else {}
    contents = getattr(source, "contents", None)
    if not contents:
        # Still honour the order contract: if caller passed an
        # order tuple, return pre-populated empty buckets so their
        # fall-through iteration logic works without a .get() wrap.
        return {name: [] for name in order} if order else {}

    buckets = {}
    if order is not None:
        # Pre-populate with empty lists. Insertion order is preserved
        # in Python 3.7+, so iterating buckets.items() will follow
        # the caller's priority sequence.
        for name in order:
            buckets[name] = []

    for obj in contents:
        if not all(p(obj, caller) for p in predicates):
            continue
        key = key_fn(obj, caller)
        if key is None:
            continue
        buckets.setdefault(key, []).append(obj)
    return buckets


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
            ``None`` or have no ``.contents`` — ``walk_contents``
            returns an empty list in those cases and the helper
            forwards that empty list to ``caller.search`` (which
            handles it correctly; see below).
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
    # Unconditional delegation to caller.search, even when the
    # filtered candidate list is empty. Evennia's search handles
    # empty candidates natively — no match → emits ``nofound_string``
    # (if passed) or the default "not found" error, then returns
    # None. An earlier version of this helper short-circuited on
    # empty candidates, which had the side effect of silently
    # suppressing ``nofound_string`` when inventory/source was
    # empty. Commands that passed a custom error wording saw
    # nothing on the empty path until the short-circuit was
    # removed.
    candidates = walk_contents(caller, source, *BASE_ITEM_PREDICATES)
    return caller.search(search_term, candidates=candidates, **kwargs)


def resolve_container(caller, name):
    """Find a container by name — inventory first, then room.

    Scopes the search to:
        1. ``caller.contents`` (the caller's inventory)
        2. ``caller.location.contents`` (the room) — only if step 1
           returns nothing

    Filter stack (on top of the shared item-candidate filter):
        - p_is_container — must expose ``is_container = True``
          (inherited from ``ContainerMixin``)

    Does NOT check open/closed state. The helper's job is
    identification, not access-gating. Commands decide for themselves
    whether a found container is usable — ``get from`` needs open,
    ``picklock`` needs closed, ``smash`` doesn't care.

    Args:
        caller: The actor doing the lookup.
        name: The keyword typed by the player.

    Returns:
        The matched container object, or ``None``. Never raises.
        Callers own all error messaging and all state checks (open,
        locked, trapped, etc.).
    """
    for source in (caller, caller.location):
        if source is None:
            continue
        candidates = walk_contents(
            caller, source, *BASE_ITEM_PREDICATES, p_is_container,
        )
        if not candidates:
            continue
        result = caller.search(name, candidates=candidates, quiet=True)
        if result:
            if isinstance(result, list):
                result = result[0] if result else None
            if result is not None:
                return result
    return None


def resolve_character_in_room(caller, name):
    """Find a player character in the caller's current room by name.

    Matches ``FCMCharacter`` instances only — NPCs, mobs, pets, and
    mounts are excluded upstream by ``p_is_character``. The caller is
    NOT excluded; commands that want a "not self" check apply it
    themselves as a command-layer policy so they can emit
    command-specific error messages (e.g. "You can't give things to
    yourself").

    Scope suffix (``_in_room``) distinguishes this from future scope
    variants (``_in_game``, ``_in_zone``, ``_in_district``). Those
    variants will use different execution models (DB queries rather
    than in-memory walks) and will be separate helpers when their
    consumers appear.

    Args:
        caller: The actor doing the lookup. Used for visibility
            checks and delegating string matching to ``caller.search``.
        name: Keyword typed by the player. Matched against character
            key and aliases via Evennia's built-in search.

    Returns:
        The matched ``FCMCharacter`` or ``None``. Returns ``None``
        if the caller has no location, if no characters are in the
        room, or if no candidate's name matches. Never raises.
    """
    room = caller.location
    if room is None:
        return None
    candidates = walk_contents(caller, room, p_is_character)
    if not candidates:
        return None
    result = caller.search(name, candidates=candidates, quiet=True)
    if isinstance(result, list):
        result = result[0] if result else None
    return result
