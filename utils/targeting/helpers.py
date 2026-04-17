"""FCM-specific targeting helpers.

Thin wrappers over ``caller.search`` that pre-filter candidate lists
with FCM semantic predicates and then delegate string matching to
Evennia. Helpers are added only when a real consumer needs them — see
design/UNIFIED_SEARCH_SYSTEM.md and the Evennia-first rule in CLAUDE.md.
"""

from utils.targeting.predicates import (
    p_is_character,
    p_is_container,
    p_living,
    p_not_actor,
    p_not_exit,
    p_passes_lock,
    p_same_height_value,
    p_visible_to,
)


def walk_contents(caller, source, *predicates):
    """Walk ``source.contents`` once and return objects passing every predicate.

    Universal targeting primitive. The caller supplies the predicate
    stack they want; ``walk_contents`` runs it via short-circuit
    ``all()`` so the first failing predicate stops evaluation for
    that object.

    Each call site declares its own predicate stack explicitly —
    there is no shared "base" constant. This forces every resolver
    to evaluate what it actually needs to filter::

        # Room items — no actors, no exits, stealth-visible:
        walk_contents(caller, room, p_not_actor, p_not_exit, p_visible_to)

        # Room containers — same plus container check:
        walk_contents(caller, room, p_not_actor, p_not_exit, p_visible_to, p_is_container)

        # Inventory — no predicates needed (only items in contents):
        walk_contents(caller, caller)

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
    candidates = walk_contents(
        caller, source, p_not_actor, p_not_exit, p_visible_to,
    )
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
            caller, source,
            p_not_actor, p_not_exit, p_visible_to, p_is_container,
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


def _first_match_in_priority(caller, name, buckets, order):
    """Run ``caller.search`` against each bucket in priority order.

    Returns the first matching object. Short-circuits on the first
    non-empty bucket that yields a match. Buckets with no name match
    fall through to the next priority tier.

    Shared by the priority-bucketed attack resolvers. Private to this
    module — not part of the targeting public API.
    """
    for tier in order:
        candidates = buckets.get(tier, [])
        if not candidates:
            continue
        result = caller.search(name, candidates=candidates, quiet=True)
        if not result:
            continue
        if isinstance(result, list):
            result = result[0] if result else None
        if result is not None:
            return result
    return None


def _is_self_keyword(name):
    """True if ``name`` is a direct self-reference keyword.

    Evennia's ``get_search_direct_match`` intercepts ``me`` / ``self``
    and returns the searcher, but only if the searcher is in the
    candidate list. When we walk priority buckets, the caller is
    usually NOT in the first bucket's candidate list, and Evennia's
    direct-match path silently mutates ``searchdata`` to the caller
    object — which then prefix-matches against candidate keys
    downstream, returning the wrong actor. Intercepting these
    keywords at the resolver level bypasses that quirk entirely.
    """
    return isinstance(name, str) and name.lower() in ("me", "self")


#: Default priority order for out-of-combat attack targeting.
#: Stranger wins over groupmate wins over self. Exposed so friendly
#: / any spell wrappers can pass a reversed order and reuse the
#: same classifier machinery.
ATTACK_OUT_OF_COMBAT_ORDER = ("stranger", "groupmate", "self")


def resolve_attack_target_out_of_combat(caller, name, order=None, extra_predicates=()):
    """Find a hostile-action target for a caller not currently in combat.

    Walks ``caller.location`` for living, visible actors and buckets
    them by group membership relative to the caller. Default priority
    order (hostile intent):

        1. ``stranger``  — actors not in caller's follow-chain group
        2. ``groupmate`` — actors in caller's group plus
                           pets/mounts via ``is_pet`` + ``owner_key``
        3. ``self``      — the caller themselves (last-resort fallback)

    Name matching happens against each bucket in priority order via
    ``caller.search``, so a stranger "goblin" wins over a groupmate
    "goblin" even though both match the keyword. Only if no stranger
    matches does the search fall through to groupmates — that way a
    player whose pet shares a mob name can still choose to attack it
    by being explicit (no stranger goblin in the room).

    The ``self`` bucket is intentionally last priority under the
    default order. If a player types their own name while some other
    actor in the room matches it too, they almost certainly meant the
    other actor. Self only wins when nothing else matches. When it
    does, the command layer recognises ``target is caller`` and emits
    a friendly self-error ("You can't attack yourself"). The ``me`` /
    ``self`` keywords land here via Evennia's direct-match shortcut.

    ``order`` parameter: when None, uses ``ATTACK_OUT_OF_COMBAT_ORDER``
    (the default hostile-intent tuple). Friendly-intent wrappers
    (``resolve_friendly_target_out_of_combat``) pass a reversed tuple
    so "cast cure light goblin" prefers the groupmate goblin over a
    stranger goblin. The classifier is identical in both cases — only
    the fall-through priority differs.

    Consumers: ``cmd_attack`` (pre-combat), ``cmd_bash`` / ``cmd_pummel``
    / ``cmd_taunt`` when caller not in combat, hostile spells cast out
    of combat. Friendly-intent wrapper consumed by friendly spells.

    Reads group state via duck-typed ``get_group_leader()`` — no import
    from ``typeclasses`` or ``combat``. Targeting stays a leaf package.
    """
    room = caller.location
    if room is None:
        return None
    if _is_self_keyword(name):
        return caller
    caller_leader = (
        caller.get_group_leader() if hasattr(caller, "get_group_leader") else None
    )

    def classify(obj, _caller):
        if obj is caller:
            return "self"
        # Pets (including mounts) are groupmates — they're actors in the
        # room with owner_key pointing at the caller. MountMixin composes
        # into BasePet, so a mounted horse is already is_pet=True.
        if (getattr(obj, "is_pet", False)
                and getattr(obj, "owner_key", None) == caller.key):
            return "groupmate"
        other_leader = (
            obj.get_group_leader() if hasattr(obj, "get_group_leader") else None
        )
        if caller_leader and other_leader and caller_leader == other_leader:
            return "groupmate"
        return "stranger"

    if order is None:
        order = ATTACK_OUT_OF_COMBAT_ORDER

    buckets = bucket_contents(
        caller, room, classify,
        p_living, p_visible_to, *extra_predicates,
        order=order,
    )
    return _first_match_in_priority(caller, name, buckets, order)


#: Default priority order for in-combat attack targeting.
#: Enemy wins over bystander wins over ally wins over self. Exposed
#: so friendly / any spell wrappers can pass a reversed order and
#: reuse the same classifier machinery.
ATTACK_IN_COMBAT_ORDER = ("enemy", "bystander", "ally", "self")


def resolve_attack_target_in_combat(caller, name, order=None, extra_predicates=()):
    """Find a hostile-action target for a caller currently in combat.

    Walks ``caller.location`` for living, visible actors and buckets
    them by combat relationship. Default priority order (hostile intent):

        1. ``enemy``     — ``combat_side`` opposes caller's side (nonzero)
        2. ``bystander`` — no ``combat_handler``, or ``combat_side == 0``
        3. ``ally``      — same ``combat_side`` as caller
        4. ``self``      — the caller themselves (last-resort fallback)

    Name matching happens against each bucket in priority order via
    ``caller.search``, so an enemy "goblin" wins over a bystander
    "goblin" wins over an ally "goblin". A command issuing
    ``attack goblin`` mid-fight picks the hostile goblin even when an
    allied goblin shares the keyword.

    Returns ``None`` if the caller has no combat handler — callers
    should branch to the out-of-combat variant in that case.

    ``order`` parameter: when None, uses ``ATTACK_IN_COMBAT_ORDER``
    (the default hostile-intent tuple). Friendly-intent wrappers
    (``resolve_friendly_target_in_combat``) pass a reversed tuple so
    "cast cure light goblin" prefers an allied goblin over an enemy
    goblin. The classifier is identical in both cases — only the
    fall-through priority differs.

    Combat side is read directly from
    ``obj.scripts.get("combat_handler")[0].combat_side`` — no import
    from ``combat/``. Targeting stays a leaf package; combat imports
    from targeting, not the other way.

    Consumers: ``cmd_attack`` (mid-combat re-target), ``cmd_bash`` /
    ``cmd_pummel`` when already in combat, hostile spells cast in
    combat. Friendly-intent wrapper consumed by friendly spells.
    """
    room = caller.location
    if room is None:
        return None
    caller_handlers = caller.scripts.get("combat_handler")
    if not caller_handlers:
        return None
    if _is_self_keyword(name):
        return caller
    my_side = caller_handlers[0].combat_side

    def classify(obj, _caller):
        if obj is caller:
            return "self"
        handlers = obj.scripts.get("combat_handler")
        if not handlers:
            return "bystander"
        their_side = handlers[0].combat_side
        if their_side == 0:
            return "bystander"
        if their_side == my_side:
            return "ally"
        return "enemy"

    if order is None:
        order = ATTACK_IN_COMBAT_ORDER

    buckets = bucket_contents(
        caller, room, classify,
        p_living, p_visible_to, *extra_predicates,
        order=order,
    )
    return _first_match_in_priority(caller, name, buckets, order)


#: Priority order for in-combat friendly-intent targeting (heal, buff,
#: protect, etc). Reverse of ``ATTACK_IN_COMBAT_ORDER`` — self first,
#: then ally, then bystander, then enemy as last resort.
FRIENDLY_IN_COMBAT_ORDER = ("self", "ally", "bystander", "enemy")

#: Priority order for out-of-combat friendly-intent targeting.
#: Reverse of ``ATTACK_OUT_OF_COMBAT_ORDER`` — self first, then
#: groupmate, then stranger as last resort.
FRIENDLY_OUT_OF_COMBAT_ORDER = ("self", "groupmate", "stranger")


def resolve_friendly_target_in_combat(caller, name, extra_predicates=()):
    """Find a friendly-intent target for a caller currently in combat.

    Same classifier as ``resolve_attack_target_in_combat`` — buckets
    actors by combat relationship — but priority reversed:

        1. ``self``      — the caller themselves (highest priority)
        2. ``ally``      — same ``combat_side`` as caller
        3. ``bystander`` — no ``combat_handler``, or ``combat_side == 0``
        4. ``enemy``     — ``combat_side`` opposes caller's side

    Thin wrapper over ``resolve_attack_target_in_combat`` with the
    reversed-priority ``order`` kwarg. ``extra_predicates`` passed
    through for height filtering etc.

    Returns the matched actor or None.
    """
    return resolve_attack_target_in_combat(
        caller, name, order=FRIENDLY_IN_COMBAT_ORDER,
        extra_predicates=extra_predicates,
    )


def resolve_friendly_target_out_of_combat(caller, name, extra_predicates=()):
    """Find a friendly-intent target for a caller not currently in combat.

    Same classifier as ``resolve_attack_target_out_of_combat`` —
    buckets actors by group membership — but priority reversed:

        1. ``self``      — the caller themselves (highest priority)
        2. ``groupmate`` — actors in caller's follow-chain group +
                           pets/mounts via ``is_pet`` + ``owner_key``
        3. ``stranger``  — everyone else

    Thin wrapper over ``resolve_attack_target_out_of_combat`` with
    the reversed-priority ``order`` kwarg. ``extra_predicates`` passed
    through for height filtering etc.

    Returns the matched actor or None.
    """
    return resolve_attack_target_out_of_combat(
        caller, name, order=FRIENDLY_OUT_OF_COMBAT_ORDER,
        extra_predicates=extra_predicates,
    )


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





# ── AoE secondaries ─────────────────────────────────────────────────


def _resolve_aoe_secondaries(caster, primary_target, aoe):
    """Build the AoE secondaries list from the primary target's height.

    Collects living visible actors at the primary target's
    ``room_vertical_position``, filtered by the ``aoe`` type. The
    primary target is always excluded (they're already the primary).

    AoE types:

        ``"unsafe"``      — everyone at target's height, caster included.
        ``"unsafe_self"`` — everyone at target's height except caster.
        ``"safe"``        — enemies only at target's height (via
                            ``get_sides`` in combat, group membership
                            out of combat).
        ``"allies"``      — allies only at target's height, caster
                            included (mass heal heals you too).

    Returns an empty list if ``primary_target`` is None, ``caster``
    has no location, or ``aoe`` is not a recognised type.
    """
    if not primary_target or not caster.location:
        return []

    target_height = getattr(primary_target, "room_vertical_position", 0)
    height_pred = p_same_height_value(target_height)

    # Walk room for all living visible actors at target's height
    candidates = walk_contents(
        caster, caster.location, p_living, p_visible_to, height_pred,
    )

    if aoe == "unsafe":
        return [a for a in candidates if a is not primary_target]

    if aoe == "unsafe_all_heights":
        # Everyone in the room regardless of height — caster included.
        # Used by spells like Call Lightning where the effect passes
        # through all vertical levels.
        all_candidates = walk_contents(
            caster, caster.location, p_living, p_visible_to,
        )
        return [a for a in all_candidates if a is not primary_target]

    if aoe == "unsafe_self":
        return [
            a for a in candidates
            if a is not primary_target and a is not caster
        ]

    if aoe == "safe":
        handler = caster.scripts.get("combat_handler")
        if handler:
            from combat.combat_utils import get_sides
            _allies, enemies = get_sides(caster)
            enemy_set = set(id(e) for e in enemies)
            return [
                a for a in candidates
                if a is not primary_target and id(a) in enemy_set
            ]
        # Out of combat: non-groupmates are "enemies"
        caster_leader = (
            caster.get_group_leader()
            if hasattr(caster, "get_group_leader") else None
        )
        def _is_own_pet(obj):
            return (getattr(obj, "is_pet", False)
                    and getattr(obj, "owner_key", None) == caster.key)

        def _is_enemy(obj):
            if obj is caster or obj is primary_target:
                return False
            if _is_own_pet(obj):
                return False
            other_leader = (
                obj.get_group_leader()
                if hasattr(obj, "get_group_leader") else None
            )
            if caster_leader and other_leader and caster_leader == other_leader:
                return False
            return True

        return [a for a in candidates if _is_enemy(a)]

    if aoe == "allies":
        handler = caster.scripts.get("combat_handler")
        if handler:
            from combat.combat_utils import get_sides
            allies, _enemies = get_sides(caster)
            ally_set = set(id(a) for a in allies)
            return [
                a for a in candidates
                if a is not primary_target and id(a) in ally_set
            ]
        # Out of combat: groupmates + caster + pets/mounts are allies
        caster_leader = (
            caster.get_group_leader()
            if hasattr(caster, "get_group_leader") else None
        )

        def _is_own_pet_ally(obj):
            return (getattr(obj, "is_pet", False)
                    and getattr(obj, "owner_key", None) == caster.key)

        def _is_ally(obj):
            if obj is primary_target:
                return False
            if obj is caster or _is_own_pet_ally(obj):
                return True
            other_leader = (
                obj.get_group_leader()
                if hasattr(obj, "get_group_leader") else None
            )
            if caster_leader and other_leader and caster_leader == other_leader:
                return True
            return False

        return [a for a in candidates if _is_ally(a)]

    return []


# ── Spell target resolution ──────────────────────────────────────────


def resolve_target(caller, target_str, target_type, range="ranged", aoe=None,
                    extra_predicates=()):
    """Resolve a spell target by ``target_type``.

    Single entry point for all spell target resolution, used by
    ``cmd_cast`` and ``cmd_zap``. Routes to the appropriate targeting
    primitive based on the spell's ``target_type``.

    Returns ``(target, secondaries)`` — a tuple of the primary target
    and a list of AoE secondary targets. For non-AoE spells (``aoe=None``),
    ``secondaries`` is always ``[]``. On failure, returns ``(None, [])``
    with an error message already sent to the caller.

    ``range`` controls height filtering for actor target_types:
        ``"melee"``      — only actors at the caller's height
        ``"ranged"``     — any height (default)
        ``"ranged_only"``— only actors at a different height
        ``"self"``       — no target resolution (ignored)

    Target types — actors:

        ``"self"``           — returns caller, no resolution needed.
        ``"none"``           — returns None, no resolution needed.
        ``"actor_hostile"``        — attack-priority actor resolution
                               (enemy > bystander > ally > self),
                               self rejected.
        ``"actor_any"``      — same as hostile (attack priority,
                               self rejected).
        ``"actor_friendly"``       — friendly-priority actor resolution
                               (self > ally > bystander > enemy),
                               self allowed, empty target defaults
                               to self.

    Target types — items (``items_`` prefix, composable naming):

        ``"items_inventory"``
            Inventory only. Consumer: Create Water.
        ``"items_room_all_then_inventory"``
            Room (all visible objects + exits) first, inventory
            fallback. Consumer: Knock.
        ``"items_inventory_then_room_all"``
            Inventory first, room (all visible objects + exits)
            fallback. Consumer: Identify, Holy Insight.

    Defined, not yet implemented (``NotImplementedError``):

        ``"items_all_room"``
            Room only, no fallback.
        ``"items_gettable_room"``
            Gettable items in room only.
        ``"items_fixed_room"``
            Fixtures + exits in room only.
        ``"items_gettable_room_then_inventory"``
        ``"items_inventory_then_gettable_room"``
    """
    # ── Self / none: no resolution ──
    if target_type == "self":
        return caller, []
    if target_type == "none":
        return None, []

    target_str = (target_str or "").strip()

    # Friendly defaults to self when no target is given
    if not target_str:
        if target_type == "actor_friendly":
            secondaries = (
                _resolve_aoe_secondaries(caller, caller, aoe) if aoe else []
            )
            return caller, secondaries
        caller.msg("You need to specify a target.")
        return None, []

    if not caller.location and target_type != "items_inventory":
        caller.msg("You aren't anywhere where you could target that.")
        return None, []

    # range is accepted but no longer auto-mapped to predicates.
    # Commands and spells that need height filtering pass it
    # explicitly via extra_predicates or check at command layer.
    extra_predicates = tuple(extra_predicates)

    # ── Hostile / any_actor: attack-priority actor resolution ──
    if target_type in ("actor_hostile", "actor_any"):
        if caller.scripts.get("combat_handler"):
            target = resolve_attack_target_in_combat(
                caller, target_str, extra_predicates=extra_predicates,
            )
        else:
            target = resolve_attack_target_out_of_combat(
                caller, target_str, extra_predicates=extra_predicates,
            )
        if target is None:
            caller.msg(f"There's no '{target_str}' here.")
            return None, []
        # Self reached via self-bucket fallback or _is_self_keyword.
        # Do NOT reject here — return the caller so the command layer
        # can emit its own context-specific self-error ("You can't
        # attack yourself" vs "You can't cast that on yourself" etc).
        secondaries = (
            _resolve_aoe_secondaries(caller, target, aoe) if aoe else []
        )
        return target, secondaries

    # ── Friendly: friendly-priority actor resolution ──
    if target_type == "actor_friendly":
        if caller.scripts.get("combat_handler"):
            target = resolve_friendly_target_in_combat(
                caller, target_str, extra_predicates=extra_predicates,
            )
        else:
            target = resolve_friendly_target_out_of_combat(
                caller, target_str, extra_predicates=extra_predicates,
            )
        if target is None:
            caller.msg(f"There's no '{target_str}' here.")
            return None, []
        secondaries = (
            _resolve_aoe_secondaries(caller, target, aoe) if aoe else []
        )
        return target, secondaries


    # ============ ACTOR / ITEM DEMARCATION =============

    # ── items_inventory ─────────────────────────────────────────────
    #
    # Searches: caller.contents only.
    #
    # Returns: a single non-worn item matching target_str, or None.
    #
    # Structural filtering: none. Actors, exits and fixed world objects
    # cannot exist in a character's contents, so no predicates are 
    # needed to exclude them. 
    # The walk passes only caller-supplied extra_predicates.
    #
    # Worn/equipped items are excluded via Evennia's exclude_worn
    # search kwarg — this is NOT a predicate, it's handled by
    # caller.search() at the name-matching step.
    #
    # Height is not relevant in an inventory search
    #
    # Visibility, container checks etc. are the caller's
    # responsibility via extra_predicates.
    # ─────────────────────────────────────────────────────────────────
    if target_type == "items_inventory":
        candidates = walk_contents(caller, caller, *extra_predicates)
        if not candidates:
            return None, []
        target = caller.search(
            target_str, candidates=candidates,
            quiet=True, exclude_worn=True,
        )
        if isinstance(target, list):
            target = target[0] if target else None
        return target, []

    # ── items_equipped ───────────────────────────────────────────────
    #
    # Searches: caller.contents only — worn/equipped items.
    #
    # Returns: a single worn item matching target_str, or None.
    #
    # Structural filtering: none. Same rationale as items_inventory —
    # actors, fixed world items and exits cannot exist in a character's
    # contents. The walk passes only caller-supplied extra_predicates.
    #
    # ONLY worn items are returned. FCMCharacter.search supports an
    # ``only_worn=True`` kwarg that filters to items the character
    # has equipped via the wearslot system (``is_worn(obj)``).
    #
    # Height is not relevant in an equipment search.
    #
    # Visibility, type checks etc. are the caller's responsibility
    # via extra_predicates.
    # ─────────────────────────────────────────────────────────────────
    if target_type == "items_equipped":
        candidates = walk_contents(caller, caller, *extra_predicates)
        if not candidates:
            return None, []
        target = caller.search(
            target_str, candidates=candidates,
            quiet=True, only_worn=True,
        )
        if isinstance(target, list):
            target = target[0] if target else None
        return target, []

    # ── items_room_all ───────────────────────────────────────────────
    #
    # Searches: caller.location.contents — everything in the room
    # that is not an actor.
    #
    # Returns: a single non-actor object matching target_str, or None.
    # This includes exits, fixed fixtures, loose items, containers,
    # doors — every non-living object in the room.
    #
    # Structural filtering: p_not_actor only. Exits are deliberately
    # included — this is the broadest room item scope. Commands that
    # need exits excluded should use items_room_nonexit instead.
    #
    # Visibility, height, type checks etc. are the caller's
    # responsibility via extra_predicates.
    # ─────────────────────────────────────────────────────────────────
    if target_type == "items_room_all":
        if not caller.location:
            return None, []
        preds = [p_not_actor] + list(extra_predicates)
        candidates = walk_contents(caller, caller.location, *preds)
        if not candidates:
            return None, []
        target = caller.search(
            target_str, candidates=candidates, quiet=True,
        )
        if isinstance(target, list):
            target = target[0] if target else None
        return target, []

    # ── items_room_exits ─────────────────────────────────────────────
    #
    # Searches: caller.location — exits only, by NAME.
    #
    # Returns: a single exit matching target_str, or None.
    #
    # Structural filtering: uses Evennia's ``room.exits`` which is a
    # native filtered view of room.contents containing only
    # DefaultExit subclasses. No walk_contents needed — Evennia
    # already provides the candidate list.
    #
    # extra_predicates are applied as a post-filter on room.exits
    # so callers can add visibility, height accessibility etc.
    #
    # This is a NAME-BASED lookup ("find the exit called 'gate'").
    # It does NOT handle direction-based lookups ("find the exit
    # whose direction attribute is 'north'") or directional qualifier
    # parsing ("door south" → direction + name split). Those are
    # higher-level operations that live in the command layer or in
    # dedicated helpers like find_exit_target / _look_direction.
    #
    # Current consumers that find exits by direction (cmd_look
    # direction lookup, find_exit_target for open/close/lock/unlock)
    # need direction-aware logic on top of basic exit targeting.
    # ─────────────────────────────────────────────────────────────────
    if target_type == "items_room_exits":
        if not caller.location:
            return None, []
        candidates = list(caller.location.exits)
        if extra_predicates and candidates:
            candidates = [
                obj for obj in candidates
                if all(p(obj, caller) for p in extra_predicates)
            ]
        if not candidates:
            return None, []
        target = caller.search(
            target_str, candidates=candidates, quiet=True,
        )
        if isinstance(target, list):
            target = target[0] if target else None
        return target, []

    # ── items_room_nonexit ───────────────────────────────────────────
    #
    # Searches: caller.location.contents — everything in the room
    # that is not an actor and not an exit.
    #
    # Returns: a single non-actor, non-exit object matching target_str,
    # or None. This includes fixed fixtures (chests, signs, fountains),
    # loose items on the ground, containers — anything a player could
    # see, inspect, or interact with that isn't alive or a door.
    #
    # Structural filtering: p_not_actor, p_not_exit. This is the
    # standard scope for most item-interaction commands: look in,
    # get, drop target inspection, put target inspection, etc.
    # The key difference from items_room_all is that exits are
    # excluded — "get north" should not resolve to the north exit.
    #
    # Visibility, height, container, get-lock checks etc. are the
    # caller's responsibility via extra_predicates.
    # ─────────────────────────────────────────────────────────────────
    if target_type == "items_room_nonexit":
        if not caller.location:
            return None, []
        preds = [p_not_actor, p_not_exit] + list(extra_predicates)
        candidates = walk_contents(caller, caller.location, *preds)
        if not candidates:
            return None, []
        target = caller.search(
            target_str, candidates=candidates, quiet=True,
        )
        if isinstance(target, list):
            target = target[0] if target else None
        return target, []


    # ── items_room_gettable ─────────────────────────────────────────
    #
    # Searches: caller.location.contents — only items that can be
    # picked up.
    #
    # Returns: a single gettable item matching target_str, or None.
    #
    # Structural filtering: p_not_actor, p_not_exit, p_passes_lock("get").
    # This is the narrowest non-exit room scope — excludes actors,
    # exits, AND fixed objects (WorldFixtures with get:false() lock).
    # Only loose, takeable items remain.
    #
    # The difference from items_room_nonexit: nonexit finds a chest
    # bolted to the floor. gettable does not — the chest fails the
    # get lock. Use nonexit for inspection commands (look in, examine),
    # gettable for pickup commands (get, take, loot).
    #
    # Visibility, height etc. are the caller's responsibility via
    # extra_predicates.
    #
    # Accepts legacy name "items_gettable_room" for existing consumers
    # pending migration.
    # ─────────────────────────────────────────────────────────────────
    if target_type in ("items_room_gettable", "items_gettable_room"):
        if not caller.location:
            return None, []
        preds = [
            p_not_actor, p_not_exit, p_passes_lock("get"),
        ] + list(extra_predicates)
        candidates = walk_contents(caller, caller.location, *preds)
        if not candidates:
            return None, []
        target = caller.search(
            target_str, candidates=candidates, quiet=True,
        )
        if isinstance(target, list):
            target = target[0] if target else None
        return target, []


    # ── items_room_fixed ──────────────────────────────────────────────
    #
    # Searches: caller.location.contents — only objects that cannot be
    # picked up.
    #
    # Returns: a single non-gettable object matching target_str, or None.
    # This includes exits/doors, WorldFixtures (chests, signs, fountains,
    # levers, climbable objects), and any item with get:false() lock.
    #
    # Structural filtering: p_not_actor + inverse of p_passes_lock("get").
    # Exits ARE included — doors are fixed objects. Commands that want
    # fixed objects without exits should use items_room_fixed_nonexit.
    #
    # The inverse of items_room_gettable. Together they partition the
    # non-actor room contents: gettable ∪ fixed = all non-actor objects.
    #
    # Visibility, height etc. are the caller's responsibility via
    # extra_predicates.
    # ─────────────────────────────────────────────────────────────────
    if target_type == "items_room_fixed":
        if not caller.location:
            return None, []
        _gettable = p_passes_lock("get")

        def _not_gettable(obj, caller):
            return not _gettable(obj, caller)

        preds = [p_not_actor, _not_gettable] + list(extra_predicates)
        candidates = walk_contents(caller, caller.location, *preds)
        if not candidates:
            return None, []
        target = caller.search(
            target_str, candidates=candidates, quiet=True,
        )
        if isinstance(target, list):
            target = target[0] if target else None
        return target, []

    # ── items_room_fixed_nonexit ──────────────────────────────────────
    #
    # Searches: caller.location.contents — non-gettable objects that
    # are not exits.
    #
    # Returns: a single non-gettable, non-exit object matching
    # target_str, or None. This includes WorldFixtures (chests, signs,
    # fountains, levers, climbable objects) and any non-exit item
    # with get:false() lock.
    #
    # Structural filtering: p_not_actor, p_not_exit, inverse of
    # p_passes_lock("get"). The difference from items_room_fixed:
    # this excludes exits/doors. Use for commands that interact with
    # furniture but not doorways
    #
    # Visibility, height etc. are the caller's responsibility via
    # extra_predicates.
    # ─────────────────────────────────────────────────────────────────
    if target_type == "items_room_fixed_nonexit":
        if not caller.location:
            return None, []
        _gettable = p_passes_lock("get")

        def _not_gettable(obj, caller):
            return not _gettable(obj, caller)

        preds = [
            p_not_actor, p_not_exit, _not_gettable,
        ] + list(extra_predicates)
        candidates = walk_contents(caller, caller.location, *preds)
        if not candidates:
            return None, []
        target = caller.search(
            target_str, candidates=candidates, quiet=True,
        )
        if isinstance(target, list):
            target = target[0] if target else None
        return target, []


    # ======= SINGLE VS MULTI LOOKUP DEMARCATION ===================

    # ── items_room_all_then_inventory ────────────────────────────────
    #
    # Composite: items_room_all first, items_inventory fallback.
    #
    # Room step: all non-actor objects including exits (doors).
    # Inventory step: carried items (exclude_worn).
    # Both steps pass extra_predicates through.
    #
    # Consumer: Knock (unlock a door or chest).
    #
    # ─────────────────────────────────────────────────────────────────
    if target_type == "items_room_all_then_inventory":
        # Room step — items_room_all
        if caller.location:
            preds = [p_not_actor] + list(extra_predicates)
            candidates = walk_contents(caller, caller.location, *preds)
            if candidates:
                target = caller.search(
                    target_str, candidates=candidates, quiet=True,
                )
                if isinstance(target, list):
                    target = target[0] if target else None
                if target is not None:
                    return target, []
        # Inventory fallback — items_inventory
        candidates = walk_contents(caller, caller, *extra_predicates)
        if candidates:
            target = caller.search(
                target_str, candidates=candidates,
                quiet=True, exclude_worn=True,
            )
            if isinstance(target, list):
                target = target[0] if target else None
            if target is not None:
                return target, []
        return None, []

    # ── items_inventory_then_room_all: inventory first, room fallback ──
    if target_type == "items_inventory_then_room_all":
        target = resolve_item_in_source(
            caller, caller, target_str, quiet=True, exclude_worn=True,
        )
        if isinstance(target, list):
            target = target[0] if target else None
        if target is not None:
            return target, []
        if caller.location:
            target = _resolve_all_room(caller, target_str, quiet=True)
            if target is not None:
                return target, []
        caller.msg(f"You don't see '{target_str}' here.")
        return None, []

    # ── items_inventory_then_gettable_room: inventory first, room fallback ──
    if target_type == "items_inventory_then_gettable_room":
        # Inventory — no height filter, no exclude_worn (worn containers
        # are valid targets for inspection commands like "look in").
        target = resolve_item_in_source(
            caller, caller, target_str, quiet=True,
        )
        if isinstance(target, list):
            target = target[0] if target else None
        if target is not None:
            return target, []
        # Room fallback — no actors, no exits, visible + extra predicates.
        if caller.location:
            preds = [p_not_actor, p_not_exit, p_visible_to] + list(extra_predicates)
            candidates = walk_contents(caller, caller.location, *preds)
            if candidates:
                target = caller.search(
                    target_str, candidates=candidates, quiet=True,
                )
                if isinstance(target, list):
                    target = target[0] if target else None
                if target is not None:
                    return target, []
        caller.msg(f"You don't see '{target_str}' here.")
        return None, []

    # ── Future item types (convention-defined, not yet implemented) ──
    _FUTURE_ITEM_TYPES = (
        "items_all_room",
        "items_fixed_room",
        "items_gettable_room_then_inventory",
    )
    if target_type in _FUTURE_ITEM_TYPES:
        raise NotImplementedError(
            f"target_type '{target_type}' is defined in the naming "
            f"convention but not yet implemented. Add a consumer spell "
            f"first, then implement the branch."
        )

    # Unknown type — defensive
    caller.msg(f"Unknown target type '{target_type}'.")
    return None, []


def _resolve_world_item(caller, target_str, silent=False):
    """Find an object or exit in the caller's room by name.

    Delegates to ``find_exit_target`` which includes directional
    parsing ("door south" → direction + name decomposition). Used by
    the ``items_room_all_then_inventory`` branch for Knock and similar.

    When ``silent`` is True, uses ``_resolve_all_room`` instead to
    suppress error messages — used by fallback paths that emit their
    own errors.
    """
    if not caller.location:
        if not silent:
            caller.msg("You aren't anywhere where you could target that.")
        return None

    if silent:
        return _resolve_all_room(caller, target_str, quiet=True)

    from utils.find_exit_target import find_exit_target
    return find_exit_target(caller, target_str)


def _resolve_all_room(caller, target_str, quiet=False):
    """Find any visible non-actor object in the room, including exits.

    Single-pass walk over ``room.contents`` via ``walk_contents`` with
    ``(p_not_actor, p_visible_to)`` — includes exits, fixtures, loose
    items, containers. Excludes actors.

    Used by ``items_inventory_then_room_all`` (room fallback) and
    ``items_room_all_then_inventory`` (room step, silent mode).
    """
    candidates = walk_contents(
        caller, caller.location, p_not_actor, p_visible_to,
    )
    if not candidates:
        if not quiet:
            caller.msg(f"You don't see '{target_str}' here.")
        return None
    target = caller.search(target_str, candidates=candidates, quiet=True)
    if isinstance(target, list):
        target = target[0] if target else None
    if not target and not quiet:
        caller.msg(f"You don't see '{target_str}' here.")
    return target
