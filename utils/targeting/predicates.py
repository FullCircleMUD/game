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


def p_not_caller(obj, caller):
    """True if ``obj`` is not the caller themselves.

    Identity compare, trivially cheap. Used to exclude the caller from
    candidate lists where they would otherwise match their own key or
    aliases (e.g. a PC named "bob" searching for "bob").
    """
    return obj is not caller


def p_not_character(obj, caller):  # noqa: ARG001 — caller unused, uniform signature
    """True if ``obj`` is not a character (PC, NPC, or mob).

    Excludes anything deriving from ``DefaultCharacter``. Used by item
    lookups to keep actors out of the candidate pool — ``get sword``
    should not resolve to an NPC named "swordsmith".

    Evennia's ``typeclass=`` kwarg only supports positive filtering
    ("match these"), which is why this exclusion needs a predicate.
    """
    return not isinstance(obj, DefaultCharacter)


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
    """True if ``obj`` is visible to ``caller``.

    Respects FCM's ``HiddenObjectMixin`` — a hidden object returns
    False unless the caller has discovered it. Objects without the
    mixin are visible by default.

    Evennia's ``use_locks=True`` (default) respects the static
    ``search`` lock, but hidden-mixin visibility is per-caller runtime
    state (who discovered what), which a static lock cannot express.
    Hence this predicate.

    When ``InvisibleObjectMixin`` support is needed by a real consumer,
    extend this predicate to delegate to both mixins.
    """
    check = getattr(obj, "is_hidden_visible_to", None)
    if check is None:
        return True
    try:
        return bool(check(caller))
    except Exception:
        return True


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
