"""FCM-specific targeting predicates.

Each predicate is a pure ``(obj, caller) -> bool`` function. They express
runtime-state filters Evennia's native ``search()`` cannot — caller
identity, typeclass EXCLUSION, mixin-based visibility, and runtime lock
checks. Compose them by filtering a candidate list before passing it to
``caller.search(candidates=...)``.

**Predicates are added only when a real consumer needs them.** Do not
pre-populate this module with speculative filters. See
design/UNIFIED_SEARCH_SYSTEM.md and the Evennia-first rule in CLAUDE.md.


============================================================================
BEFORE ADDING A NEW PREDICATE: check if Evennia handles it natively.
============================================================================

Many filters that look like they need a predicate are already one-line
Evennia search kwargs. If your filter fits any of these, use the native
form — DO NOT add a predicate:

• Match a tag:
      caller.search(target, tags=[("tagname", "category")])

• Match a typeclass (positive — "only these"):
      caller.search(target, typeclass="path.to.Class")
      caller.search(target, typeclass=[Class1, Class2])

• Match an attribute value:
      caller.search(target, attribute_name="foo")

• Respect the `search` lock (hide from non-staff):
      Default. ``use_locks=True`` is already on.

• Nick / alias substitution (player-built shortcuts):
      Default. ``use_nicks=True`` is already on.

• ``me`` / ``self`` / ``here`` keyword shortcuts:
      Automatic. Handled by ``get_search_direct_match`` before filtering.

• Dbref lookups (``#123``):
      Automatic when ``use_dbref`` permits (default: on for Builders).

• Stacking identical items:
      caller.search(target, stacked=N)

• Numeric multimatch disambiguation (``goblin-2``):
      Automatic via ``settings.SEARCH_MULTIMATCH_REGEX``.

• Case-insensitive substring / prefix matching:
      Default. ``FCMCharacter.search()`` adds a substring fallback pass
      on top of Evennia's built-in prefix match.

• Scope to inventory only:
      caller.search(target, location=caller)

• Scope to a specific room only (excludes inventory AND the room object):
      caller.search(target, location=room)

• Scope to a container's contents:
      caller.search(target, location=container)

• Filter against a pre-built candidate list:
      caller.search(target, candidates=[...])

• Look up the exits in a room (positive filter — only exits):
      room.exits  (Evennia provides a filtered view of room.contents)

Predicates exist ONLY for filters Evennia cannot express — runtime state
(hp, height, combat side), caller identity, typeclass EXCLUSION (not
inclusion), FCM mixin visibility, and runtime lock checks.
"""

from evennia.objects.objects import DefaultCharacter, DefaultExit


def p_not_actor(obj, caller):  # noqa: ARG001 — caller unused, uniform signature
    """True if ``obj`` is not an actor (not any ``DefaultCharacter`` subclass).

    Excludes player characters, NPCs, mobs, pets, and mounts — every
    entity that inherits ``DefaultCharacter``. Used by item lookups to
    keep living entities out of the candidate pool (``get sword`` must
    not resolve to an NPC named "swordsmith").

    Terminology: **actor** is the generic term for any living entity
    in the world. **Character** (see ``p_is_character``) means
    specifically a player character (``FCMCharacter``). Predicates use
    the two words consistently to avoid confusion.

    Evennia's ``typeclass=`` kwarg only supports positive filtering
    ("match these"), which is why this exclusion needs a predicate.
    """
    return not isinstance(obj, DefaultCharacter)


def p_is_character(obj, caller):  # noqa: ARG001 — caller unused, uniform signature
    """True if ``obj`` is a player character (``FCMCharacter`` instance).

    Matches ONLY player-controlled characters. NPCs, mobs, pets, and
    mounts inherit ``DefaultCharacter`` but are NOT ``FCMCharacter`` —
    use this predicate when a command legitimately only wants PCs
    (give, whisper, trade, party-invite, etc.).

    Uses a lazy import of ``FCMCharacter`` to avoid any circular-import
    risk between the targeting package and the character typeclass.
    """
    from typeclasses.actors.character import FCMCharacter
    return isinstance(obj, FCMCharacter)


def p_not_exit(obj, caller):  # noqa: ARG001 — caller unused, uniform signature
    """True if ``obj`` is not an exit.

    Excludes anything deriving from ``DefaultExit``. Used by item
    lookups so ``get north`` doesn't resolve to the north exit.

    If you want ONLY exits, use ``room.exits`` (Evennia provides a
    filtered view of ``room.contents``) — you don't need this predicate
    at all, you want the opposite lookup.
    """
    return not isinstance(obj, DefaultExit)


def p_visible_to(obj, caller):
    """True if ``obj`` is not hidden/invisible to ``caller`` (stealth gate).

    Respects FCM's ``HiddenObjectMixin`` — a hidden object returns
    False unless the caller has discovered it. Objects without the
    mixin are visible by default.

    Evennia's ``use_locks=True`` (default) respects the static
    ``search`` lock, but hidden-mixin visibility is per-caller runtime
    state (who discovered what), which a static lock cannot express.
    Hence this predicate.

    When ``InvisibleObjectMixin`` support is needed by a real consumer,
    extend this predicate to delegate to both mixins.

    **Visibility predicate family:**

    - ``p_visible_to`` (this) — stealth only. Use in targeting
      resolvers where height is handled separately by range predicates.
    - ``p_height_visible_to`` — spatial only. Use when you need just
      the height gate (e.g. room display methods that have their own
      stealth logic).
    - ``p_can_see`` — composite of both. Use for display/perception
      paths (look, scan) where "can the player see this?" is the
      question and there is no separate stealth filtering.
    """
    check = getattr(obj, "is_hidden_visible_to", None)
    if check is None:
        return True
    try:
        return bool(check(caller))
    except Exception:
        return True


def p_height_visible_to(obj, caller):
    """True if ``obj`` is visible to ``caller`` given vertical position.

    Wraps ``HeightAwareMixin.is_height_visible_to`` — checks the room's
    visibility barriers against the object's size.  Objects small enough
    to be concealed by a barrier between observer and object are hidden.
    Same-height objects are always visible.

    Objects without the mixin are visible by default.

    This is a **spatial** visibility check, not a stealth check — see
    ``p_visible_to`` for hidden/invisible filtering.
    """
    check = getattr(obj, "is_height_visible_to", None)
    if check is None:
        return True
    try:
        return bool(check(caller))
    except Exception:
        return True


def p_can_see(obj, caller):
    """True if ``caller`` can perceive ``obj`` — composite visibility gate.

    Combines all visibility checks into a single predicate:

    1. ``p_visible_to`` — stealth (hidden/invisible mixin)
    2. ``p_height_visible_to`` — spatial (height-gated visibility)

    Use this for **display/perception** paths: room appearance, look
    command, scan command — anywhere the question is "can the player
    see this thing right now?"

    Targeting resolvers should generally use the specific predicates
    instead, since they handle height through range predicates
    (``p_same_height`` / ``p_different_height``) separately from
    stealth visibility.

    Extensible — when a new visibility gate is introduced (e.g.
    ethereal, phased, fog-of-war), add it here and all display
    consumers pick it up automatically.
    """
    return p_visible_to(obj, caller) and p_height_visible_to(obj, caller)


def p_living(obj, caller):  # noqa: ARG001 — caller unused, uniform signature
    """True if ``obj`` has ``hp > 0``.

    General "living actor" filter. Excludes corpses, items (``hp=None``),
    dead mobs, and anything else without positive hp. Matches PCs,
    NPCs, mobs, pets, mounts — anything that can be alive and take
    actions.

    Commonly composed with ``p_in_combat`` for combat queries
    (``get_sides`` wants living combatants), or with other actor
    predicates for spell targeting and damage application.

    Defensive on type: returns False if ``hp`` is missing, None, or
    non-numeric. Never raises.
    """
    hp = getattr(obj, "hp", None)
    if hp is None:
        return False
    try:
        return int(hp) > 0
    except (TypeError, ValueError):
        return False


def p_in_combat(obj, caller):  # noqa: ARG001 — caller unused, uniform signature
    """True if ``obj`` has a ``combat_handler`` script attached.

    Combat-specific runtime-state filter. First consumer is
    ``combat.combat_utils.get_sides``; future consumers will include
    any combat-aware query (AI threat detection, mob awareness,
    broadcast-to-combatants, flee state introspection, etc).

    Checks the raw script handler list. The handler may be running
    or stopped — in practice combat handlers are either attached and
    running or detached and deleted, so the distinction is theoretical
    but worth noting if a future consumer needs a stricter "currently
    active" check.
    """
    scripts = getattr(obj, "scripts", None)
    if scripts is None:
        return False
    try:
        return bool(scripts.get("combat_handler"))
    except Exception:
        return False


def p_is_container(obj, caller):  # noqa: ARG001 — caller unused, uniform signature
    """True if ``obj`` inherits from ``ContainerMixin``.

    Containers expose a class attribute ``is_container = True`` set by
    ``ContainerMixin`` (see ``typeclasses/mixins/container.py``). This
    predicate is the canonical way to ask "is this a container" across
    FCM — backpacks, wearable containers, world chests, and trap chests
    all pass; plain items, characters, exits, and corpses do not.

    This predicate checks TYPE only — it does NOT check whether the
    container is currently open. Open/closed state is a command-layer
    policy concern (``get from`` needs open; ``picklock`` needs closed;
    ``smash`` doesn't care). Callers are responsible for that check.

    Corpses are NOT containers — they use ``FungibleInventoryMixin``
    directly and have their own loot gate (``can_loot()``). Use a
    different predicate/helper when adding corpse-loot support.
    """
    return getattr(obj, "is_container", False)


def p_is_lockable(obj, caller):  # noqa: ARG001 — caller unused, uniform signature
    """True if ``obj`` has the ``is_locked`` attribute (``LockableMixin``).

    Type check — "can this object be locked/unlocked?" Does NOT check
    current lock state. Use ``p_is_locked`` for that.

    Consumers: Knock spell, cmd_lock, cmd_unlock, cmd_picklock — all
    use this as vocabulary at the command layer for specific error
    messaging ("cannot be unlocked" vs "not here").
    """
    return hasattr(obj, "is_locked")


def p_is_locked(obj, caller):  # noqa: ARG001 — caller unused, uniform signature
    """True if ``obj`` is currently locked.

    State check — requires ``is_lockable`` to be meaningful. A non-lockable
    object returns False (not locked because it can't be).
    """
    return getattr(obj, "is_locked", False)


def p_is_openable(obj, caller):  # noqa: ARG001 — caller unused, uniform signature
    """True if ``obj`` has the ``is_open`` attribute (``CloseableMixin``).

    Type check — "can this object be opened/closed?" Does NOT check
    current open/closed state. Use ``p_is_open`` for that.
    """
    return hasattr(obj, "is_open")


def p_is_open(obj, caller):  # noqa: ARG001 — caller unused, uniform signature
    """True if ``obj`` is currently open.

    State check — requires ``is_openable`` to be meaningful. A non-openable
    object returns False.
    """
    return getattr(obj, "is_open", False)


def p_passes_lock(lock_type):
    """Factory — returns a predicate that checks an Evennia access lock.

    Wraps ``obj.access(caller, lock_type)``. Pre-filters candidates by
    whether the caller can perform a given action on them. Common lock
    types: ``"get"``, ``"view"``, ``"enter"``, ``"puppet"``,
    ``"traverse"``.

    Example::

        gettable = p_passes_lock("get")
        candidates = [o for o in room.contents if gettable(o, caller)]

    Note: Evennia's ``use_locks=True`` kwarg on ``search()`` applies
    the ``search`` lock specifically. Use this predicate for any OTHER
    lock type that needs to gate candidates before string matching.
    """
    def _pred(obj, caller):
        try:
            return obj.access(caller, lock_type)
        except Exception:
            return False
    return _pred


def p_same_height(caller):
    """Factory — returns a predicate matching actors at ``caller``'s height.

    Compares ``obj.room_vertical_position`` against the caller's value
    at factory-creation time. Objects without the attribute default to
    height 0 (ground level).

    Used by melee-range spells so the targeting resolver only considers
    actors the caster can physically reach. Ranged spells skip this
    predicate entirely.
    """
    caller_height = getattr(caller, "room_vertical_position", 0)

    def _pred(obj, _caller):  # noqa: ARG001
        return getattr(obj, "room_vertical_position", 0) == caller_height

    return _pred


def p_different_height(caller):
    """Factory — returns a predicate matching actors NOT at ``caller``'s height.

    Inverse of ``p_same_height``. Used by ``ranged_only`` spells that
    can only target actors at a different vertical position (e.g. aerial
    bombardment, sniper abilities). No current consumer — built for
    future use alongside the melee/ranged height system.
    """
    caller_height = getattr(caller, "room_vertical_position", 0)

    def _pred(obj, _caller):  # noqa: ARG001
        return getattr(obj, "room_vertical_position", 0) != caller_height

    return _pred


def p_same_height_value(height):
    """Factory — returns a predicate matching actors at an explicit height.

    Unlike ``p_same_height(caller)`` which captures the caller's height,
    this factory takes a raw height value. Used by AoE secondaries
    building where the height comes from the **primary target's**
    position, not the caster's — a ranged fireball cast from height 2
    at a goblin at height 0 cascades to all actors at height 0.
    """
    def _pred(obj, _caller):  # noqa: ARG001
        return getattr(obj, "room_vertical_position", 0) == height

    return _pred
