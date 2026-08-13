"""FCM-specific targeting predicates.

Each predicate is a pure ``(obj, caller) -> bool`` function. They express
runtime-state filters Evennia's native ``search()`` cannot — caller
identity, typeclass EXCLUSION, mixin-based visibility, and runtime lock
checks. Compose them by filtering a candidate list before passing it to
``caller.search(candidates=...)``.

**Predicates are added only when a real consumer needs them.** Do not
pre-populate this module with speculative filters. See
docs/unified-search-system.md and the Evennia-first rule in CLAUDE.md.


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


def p_object_visible_to(obj, caller):
    """True if ``obj`` is not hidden/invisible to ``caller`` (stealth gate).

    Delegates to both object concealment mixins, and an object must
    clear both to be visible:

    - ``HiddenObjectMixin`` — hidden until this caller has discovered
      it, or holds ``true_sight``.
    - ``InvisibleObjectMixin`` — invisible unless the caller has the
      ``DETECT_INVIS`` condition.

    Objects composing neither mixin are visible by default, so items,
    actors, and plain exits pass through untouched.

    Evennia's ``use_locks=True`` (default) respects the static
    ``search`` lock, but these are per-caller runtime state (who
    discovered what, who can see invisible), which a static lock
    cannot express. Hence this predicate.

    This is the object-side counterpart to ``p_actor_visible_to``,
    which gates *actors* by condition. An actor can be HIDDEN by
    condition while a chest is hidden by mixin — independent systems,
    both composed by ``p_can_see``.

    **Visibility predicate family:**

    - ``p_object_visible_to`` (this) — object concealment only. Use in
      targeting resolvers where height is handled separately by range
      predicates.
    - ``p_height_visible_to`` — spatial only. Use when you need just
      the height gate.
    - ``p_actor_visible_to`` — actor conditions only.
    - ``p_can_see`` — composite of all three. Use for display and
      perception paths where "can this observer see it?" is the whole
      question.
    """
    for method in ("is_hidden_visible_to", "is_invis_visible_to"):
        check = getattr(obj, method, None)
        if check is None:
            continue
        try:
            if not check(caller):
                return False
        except Exception:
            continue
    return True


def p_height_visible_to(obj, caller):
    """True if ``obj`` is visible to ``caller`` given vertical position.

    Wraps ``HeightAwareMixin.is_height_visible_to`` — checks the room's
    visibility barriers against the object's size.  Objects small enough
    to be concealed by a barrier between observer and object are hidden.
    Same-height objects are always visible.

    Objects without the mixin are visible by default.

    This is a **spatial** visibility check, not a stealth check — see
    ``p_object_visible_to`` for hidden/invisible filtering.
    """
    check = getattr(obj, "is_height_visible_to", None)
    if check is None:
        return True
    try:
        return bool(check(caller))
    except Exception:
        return True


def p_actor_visible_to(obj, caller):
    """True if ``obj`` is not concealed from ``caller`` by a condition.

    Two independent concealment gates, each pierced by its own counter:

    - ``Condition.HIDDEN`` (physical stealth) — pierced only by the
      ``true_sight`` named effect.
    - ``Condition.INVISIBLE`` (magical) — pierced only by the
      ``Condition.DETECT_INVIS`` condition.

    **The gates compose — neither short-circuits the other.** An actor
    under both conditions is visible only to an observer holding both
    counters. True Sight's own mechanics text is explicit that it does
    not see invisible entities, and Detect Invisibility does not see
    through physical concealment, so holding one counter cannot excuse
    the other gate.

    Objects without ``has_condition`` (items, fixtures, exits) pass
    through unconditionally — this predicate only gates actors.

    This is separate from ``p_object_visible_to`` which handles
    ``HiddenObjectMixin`` (hidden objects with ``find_dc``). The two
    systems are independent: an actor can be HIDDEN (condition) while
    a chest can be hidden (mixin). ``p_can_see`` composes both.
    """
    has_cond = getattr(obj, "has_condition", None)
    if has_cond is None:
        return True  # not an actor — items pass through

    from enums.condition import Condition

    try:
        if has_cond(Condition.HIDDEN):
            has_effect = getattr(caller, "has_effect", None)
            if not (has_effect and has_effect("true_sight")):
                return False

        if has_cond(Condition.INVISIBLE):
            caller_cond = getattr(caller, "has_condition", None)
            if not (caller_cond and caller_cond(Condition.DETECT_INVIS)):
                return False
    except Exception:
        return True

    return True


def p_can_see(obj, caller):
    """True if ``caller`` can perceive ``obj`` — composite visibility gate.

    Combines all visibility checks into a single predicate:

    1. ``p_object_visible_to`` — stealth (hidden/invisible object mixin)
    2. ``p_height_visible_to`` — spatial (height-gated visibility)
    3. ``p_actor_visible_to`` — actor conditions (HIDDEN/INVISIBLE)

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
    return (
        p_object_visible_to(obj, caller)
        and p_height_visible_to(obj, caller)
        and p_actor_visible_to(obj, caller)
    )


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


def p_is_open_exit(obj, caller):  # noqa: ARG001 — caller unused, uniform signature
    """True if ``obj`` is not barred by its own door state.

    An exit with no door is always open, so this defaults to True where
    ``p_is_open`` defaults to False — the question here is "is anything
    blocking this exit?", and a plain passage blocks nothing. A door must
    be both unlocked and open.

    State check only. It says nothing about whether the caller can see or
    reach the exit; compose with ``p_can_see`` and
    ``p_passes_lock("traverse")`` for the whole "can I go this way?"
    question::

        traversable = p_passes_lock("traverse")
        ways_out = [
            ex for ex in room.exits
            if ex.destination
            and traversable(ex, caller)
            and p_can_see(ex, caller)
            and p_is_open_exit(ex, caller)
        ]

    Selection only — ``at_traverse`` on the exit remains the authority on
    whether a move is allowed, and applies gates this cannot see
    (encumbrance, size, traps). Use this to choose a candidate exit, never
    as a substitute for traversing one.

    Consumers: cmd_flee, cmd_retreat — both pick a random exit to escape
    through and must not offer one the actor cannot actually use.
    """
    if getattr(obj, "is_locked", False):
        return False
    return getattr(obj, "is_open", True)


def p_is_typeclass(*typeclasses):
    """Factory — returns a predicate matching any of the given typeclasses.

    The general form of the named type predicates. Reach for it when a
    call site needs a type check the library has no name for::

        # The urchin won't steal in front of the watch
        watch = self.ai.get_targets_in_room(p_is_typeclass(CityWatch), p_living)

    Prefer a named predicate where one exists — ``p_is_character`` says
    "player characters only, not NPCs or pets", which is meaning that
    ``p_is_typeclass(FCMCharacter)`` does not carry.

    The caller supplies the classes, so the library imports no typeclasses
    of its own and stays a leaf package.

    Pairs with ``p_not_typeclass``.
    """
    def _pred(obj, caller):  # noqa: ARG001 — caller unused, uniform signature
        return isinstance(obj, typeclasses)
    return _pred


def p_not_typeclass(*typeclasses):
    """Factory — returns a predicate rejecting any of the given typeclasses.

    The inverse of ``p_is_typeclass``. Its use is narrowing a positive type
    check by carving an exception out of it, which a single positive
    predicate cannot express::

        # Any actor, but not one of my own kind
        THREAT_PREDICATES = (
            p_is_typeclass(FCMCharacter, CombatMob),
            p_not_typeclass(Rabbit),
        )

    Named predicates still win where they exist — ``p_not_actor`` and
    ``p_not_exit`` say what they exclude and why.
    """
    def _pred(obj, caller):  # noqa: ARG001 — caller unused, uniform signature
        return not isinstance(obj, typeclasses)
    return _pred


def p_excluding(*excluded):
    """Factory — returns a predicate rejecting specific objects by identity.

    "Everything but these". Identity, not equality, so it is unaffected by
    any ``__eq__`` a typeclass defines::

        # The next living player other than the one just killed
        targets = self.ai.get_targets_in_room(
            p_is_character, p_living, p_excluding(victim)
        )

    Excluding the caller is not this predicate's job — helpers that should
    never return their own caller drop it themselves.
    """
    def _pred(obj, caller):  # noqa: ARG001 — caller unused, uniform signature
        return not any(obj is item for item in excluded)
    return _pred


def p_larger_than(actor):
    """Factory — returns a predicate matching objects bigger than ``actor``.

    Strict comparison on the ``Size`` scale, so equals do not pass. Takes
    the actor to compare *against*, not the caller doing the looking — the
    two differ whenever one actor sizes something up on another's behalf.

    The prey/predator axis: a mob flees what is larger and hunts what is
    smaller, without either rule naming a typeclass::

        threats = self.ai.get_targets_in_room(p_larger_than(self))

    An object with no ``size`` counts as ``MEDIUM``. An unrecognised size
    fails the comparison rather than guessing.

    Pairs with ``p_smaller_than``.
    """
    from enums.size import Size, bigger_than

    def _pred(obj, caller):  # noqa: ARG001 — caller unused, uniform signature
        try:
            return bigger_than(
                getattr(obj, "size", Size.MEDIUM),
                getattr(actor, "size", Size.MEDIUM),
            )
        except (ValueError, KeyError):
            return False
    return _pred


def p_smaller_than(actor):
    """Factory — returns a predicate matching objects smaller than ``actor``.

    The inverse of ``p_larger_than``, and strict in the same way, so an
    object of equal size passes neither. See that predicate for the rest.
    """
    from enums.size import Size, smaller_than

    def _pred(obj, caller):  # noqa: ARG001 — caller unused, uniform signature
        try:
            return smaller_than(
                getattr(obj, "size", Size.MEDIUM),
                getattr(actor, "size", Size.MEDIUM),
            )
        except (ValueError, KeyError):
            return False
    return _pred


def p_fits_through(actor):
    """Factory — returns a predicate that checks ``actor`` fits an exit.

    Wraps the ``max_size`` gate that ``ExitVerticalAware.at_traverse``
    enforces, so a caller choosing between exits can rule out ones the
    actor would be turned back from. An exit with no ``max_size`` admits
    anything.

    Note this takes the *actor to fit*, not the caller doing the looking —
    the two differ whenever one character picks an exit on another's
    behalf. A retreat leader choosing a way out for the whole party has to
    check the largest member, not themselves::

        biggest = max(group, key=lambda m: size_value(getattr(m, "size", Size.MEDIUM)))
        passable = [ex for ex in open_exits(leader) if p_fits_through(biggest)(ex, leader)]

    Selection only, like the rest of this family — ``at_traverse`` remains
    the authority.
    """
    from enums.size import Size, size_value

    def _pred(obj, caller):  # noqa: ARG001 — caller unused, uniform signature
        limit = getattr(obj, "max_size", None)
        if limit is None:
            return True
        try:
            return size_value(getattr(actor, "size", Size.MEDIUM)) <= size_value(limit)
        except (ValueError, KeyError):
            return True
    return _pred


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


def check_range(caller, target, range_value, source=None):
    """Apply a range constraint to an already-resolved target.

    Single source of truth for the spell/weapon range vocabulary
    (``"melee"`` | ``"ranged"`` | ``"ranged_only"`` | ``"self"`` | None).
    Emits a context-specific error message and returns ``False`` on
    fail; returns ``True`` when the constraint passes or when no
    constraint applies (``"ranged"`` / ``"self"`` / ``None``).

    ``source`` is the spell or weapon producing the attack — when
    present, its ``out_of_reach_message`` / ``too_close_message``
    attributes are used for failure flavour. Falls back to generic
    strings when ``source`` is ``None`` or has no override (e.g.
    unarmed attacks, innate mob attacks without flavour text).
    """
    if range_value == "melee":
        if not p_same_height(caller)(target, caller):
            caller.msg(_range_msg(
                source, "out_of_reach_message",
                "They are out of reach.",
            ))
            return False
    elif range_value == "ranged_only":
        if not p_different_height(caller)(target, caller):
            caller.msg(_range_msg(
                source, "too_close_message",
                "They are too close to use that effectively.",
            ))
            return False
    return True


def _range_msg(source, attr, default):
    return getattr(source, attr, None) or default


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


def p_involved_with(caster):
    """Factory — predicate matching actors involved with ``caster``.

    Returns a ``(obj, caller) -> bool`` predicate used to filter
    bystanders out of unsafe AOE secondaries in non-PvP rooms.

    In combat: returns True for any actor that also has a
    ``combat_handler`` script — i.e. a participant on either side of
    the fight. Bystanders (no handler) are excluded.

    Out of combat: returns True for actors in the caster's group
    (shared ``get_group_leader()``), including the caster themselves.
    Everyone outside the group is a bystander.

    The factory captures the caster's combat state and group leader
    at creation time, consistent with ``p_same_height(caller)`` which
    captures height at factory time.
    """
    in_combat = bool(
        getattr(caster, "scripts", None)
        and caster.scripts.get("combat_handler")
    )

    if in_combat:
        def _pred(obj, _caller):  # noqa: ARG001
            scripts = getattr(obj, "scripts", None)
            if scripts is None:
                return False
            return bool(scripts.get("combat_handler"))
        return _pred

    # Out of combat: group membership
    caster_leader = (
        caster.get_group_leader()
        if hasattr(caster, "get_group_leader") else caster
    )

    def _pred(obj, _caller):  # noqa: ARG001
        if obj is caster:
            return True
        other_leader = (
            obj.get_group_leader()
            if hasattr(obj, "get_group_leader") else None
        )
        return other_leader is not None and other_leader is caster_leader

    return _pred
