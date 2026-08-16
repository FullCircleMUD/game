"""
Reader — capacity and current-count queries that never materialise objects.

The spawn decision (which targets receive how much) is made on the router,
which the shards library runs unscoped: its ObjectDB queries return rows from
every shard. Iterating those rows as typeclass instances would pull the whole
cluster's spawnable world into the routing process's idmapper, which the
library forbids outright — consumer-constraints.md: "Cross-shard reads must
not pull objects into the reader's idmapper. Use .values() queries returning
dicts, not typeclass instances."

So every read here is a values projection. Nothing in this module returns an
Evennia object, and nothing calls .db on one.

Headroom is `read_capacity() - read_current()` per target pk. That pairing is
the input the allocator consumes.

Two things are load-bearing and easy to get wrong:

- ``db_category__isnull=True`` on every attribute join. ``target.db.x`` reads
  the attribute with ``category=None``; without the filter, a same-named
  attribute in another category joins as an extra row and silently corrupts
  the count.
- NFT counting uses the *contents* perspective, not the game's "inventory"
  perspective. Worn items stay in ``contents`` (only a ``db.wearslots``
  reference changes — see docs/inventory-equipment.md), and an equipped
  weapon still consumes its spawn slot. Counting by ``db_location`` therefore
  covers worn and unworn alike, which is what capacity means here.
"""

from blockchain.xrpl.services.spawn.log import spawn_log

# Tier hierarchy for the at-or-below rule on scrolls and recipes. A slot
# accepts items of its own tier or any lower one, so a gm slot is the most
# permissive and a basic slot the most restrictive.
TIER_ORDER = ["basic", "skilled", "expert", "master", "gm"]
TIER_RANK = {tier: i for i, tier in enumerate(TIER_ORDER)}

# Category -> the spawn_<category>_max attribute that declares capacity.
CATEGORY_MAX_ATTR = {
    "resources": "spawn_resources_max",
    "gold": "spawn_gold_max",
    "scrolls": "spawn_scrolls_max",
    "recipes": "spawn_recipes_max",
    "nfts": "spawn_nfts_max",
}

# Categories whose current count comes from inspecting contents rather than
# from an attribute on the target itself.
_NFT_CATEGORIES = ("scrolls", "recipes", "nfts")

# Typeclass path fragments identifying scroll and recipe items. Mirrors
# headroom._CATEGORY_TYPECLASS_FRAGMENTS, which the object path still uses.
_CATEGORY_TYPECLASS_FRAGMENTS = {
    "scrolls": "spell_scroll_nft_item",
    "recipes": "crafting_recipe_nft_item",
}


def query_targets(tag_name):
    """Return {pk: shard_id} for every object carrying a spawn tag.

    The owning shard comes back from the same query that finds the targets —
    one extra column on a read already being made, rather than a second pass
    to look up ownership afterwards.

    Objects marked global (``shard_id == "*"``) are excluded. They are
    visible to every shard's tenancy filter, so dispatching one anywhere
    would risk it being placed on by more than one process. Spawns land on
    shard-owned targets only.

    In monolith the ``shard_id`` column does not exist — ``evennia_shards``
    is deliberately absent from INSTALLED_APPS — so the column is not
    projected and every pk maps to None.

    Args:
        tag_name: e.g. "spawn_resources"

    Returns:
        dict[int, str | None] — pk to owning shard, no instances.
    """
    from evennia.objects.models import ObjectDB
    from evennia_shards import ROLE_MONOLITH, get_role

    targets = ObjectDB.objects.filter(db_tags__db_key=tag_name)

    if get_role() == ROLE_MONOLITH:
        return {
            pk: None
            for pk in targets.values_list("id", flat=True).distinct()
        }

    from evennia_shards.tenancy import GLOBAL_SHARD_ID

    rows = targets.values_list("id", "shard_id").distinct()
    excluded = 0
    shard_by_pk = {}
    for pk, shard_id in rows:
        if shard_id == GLOBAL_SHARD_ID or shard_id is None:
            excluded += 1
            continue
        shard_by_pk[pk] = shard_id

    if excluded:
        spawn_log(
            f"targets: {tag_name} excluded {excluded} global/unowned "
            f"target(s) — spawns land on shard-owned targets only",
            level="WARN",
        )
    return shard_by_pk


def _target_attributes(target_pks, attr_names):
    """Return {pk: {attr_name: value}} for the named uncategorised attributes.

    Missing attributes come back as None, matching what ``target.db.x`` yields
    for an attribute that was never set. Values arrive already decoded —
    PickledObjectField.from_db_value handles that on the way out — so dicts
    are plain dicts and ints are ints, with no unwrapping needed.
    """
    from evennia.objects.models import ObjectDB

    attrs = {pk: {name: None for name in attr_names} for pk in target_pks}
    if not target_pks:
        return attrs

    rows = ObjectDB.objects.filter(
        id__in=target_pks,
        db_attributes__db_key__in=attr_names,
        # Load-bearing: matches char.db.x semantics. Without it a same-named
        # attribute in another category joins as an extra row.
        db_attributes__db_category__isnull=True,
    ).values_list("id", "db_attributes__db_key", "db_attributes__db_value")

    for pk, attr_name, value in rows:
        attrs.setdefault(pk, {})[attr_name] = value

    return attrs


def _capacity_from_max(category, type_key, max_value):
    """Interpret one target's spawn_<category>_max value as a capacity.

    Each category stores its cap differently, so the shape of max_value
    decides how it is read:

      resources  {resource_id: cap}          -> cap for this resource
      gold       int                         -> the int itself
      scrolls    {tier: slots}               -> slots at this item's tier or
      recipes                                   any higher one (at-or-below)
      nfts       {typeclass.prototype: cap}  -> exact match only
    """
    if max_value is None:
        return 0

    if category == "gold":
        # Gold is the one category storing a plain int rather than a dict.
        return int(max_value) if isinstance(max_value, int) else 0

    if not isinstance(max_value, dict):
        return 0

    if category == "resources":
        # Evennia may return dict keys as either int or str depending on how
        # the attribute was authored, so try both.
        return max_value.get(type_key, max_value.get(str(type_key), 0)) or 0

    if category == "nfts":
        return max_value.get(type_key, 0) or 0

    # scrolls / recipes — sum every slot this item's tier is allowed into.
    item_rank = TIER_RANK.get(_item_tier(type_key), 0)
    return sum(
        slots
        for tier, slots in max_value.items()
        if slots and TIER_RANK.get(tier, 0) >= item_rank
    )


def _item_tier(type_key):
    """Look up a knowledge item's tier from SPAWN_CONFIG. Defaults to basic."""
    from blockchain.xrpl.services.spawn.config import SPAWN_CONFIG

    return SPAWN_CONFIG.get(("knowledge", type_key), {}).get("tier", "basic")


def read_capacity(target_pks, category, type_key):
    """Return {pk: capacity} — how much of this item each target may hold.

    Capacity is the declared maximum, not the remaining room. Subtract
    read_current() for headroom.
    """
    attr_name = CATEGORY_MAX_ATTR.get(category)
    if not attr_name:
        return {pk: 0 for pk in target_pks}

    attrs = _target_attributes(target_pks, (attr_name,))
    return {
        pk: _capacity_from_max(category, type_key, values.get(attr_name))
        for pk, values in attrs.items()
    }


def read_current(target_pks, category, type_key):
    """Return {pk: current} — how much of this item each target already holds.

    Fungible categories read an attribute on the target. NFT categories count
    matching items in the target's contents, which includes worn items (see
    the module docstring on the contents-vs-inventory distinction).
    """
    if category in _NFT_CATEGORIES:
        return _read_current_nfts(target_pks, category, type_key)
    if category == "gold":
        return _read_current_gold(target_pks)
    if category == "resources":
        return _read_current_resources(target_pks, type_key)
    return {pk: 0 for pk in target_pks}


def _read_current_gold(target_pks):
    """Gold held, from the target's own ``gold`` attribute."""
    attrs = _target_attributes(target_pks, ("gold",))
    return {
        pk: int(values.get("gold") or 0)
        for pk, values in attrs.items()
    }


def _read_current_resources(target_pks, resource_id):
    """Resource units held.

    Harvest rooms are the exception: they embed resources in the environment
    and track a single ``resource_count`` int rather than using the
    FungibleInventoryMixin ``resources`` dict, so that players must harvest
    rather than pick up. A target with resource_count set is a harvest room.
    """
    attrs = _target_attributes(target_pks, ("resource_count", "resources"))

    current = {}
    for pk, values in attrs.items():
        room_count = values.get("resource_count")
        if room_count is not None:
            current[pk] = int(room_count or 0)
            continue
        resources = values.get("resources") or {}
        if not isinstance(resources, dict):
            current[pk] = 0
            continue
        current[pk] = int(
            resources.get(resource_id, resources.get(str(resource_id), 0)) or 0
        )
    return current


def _read_current_nfts(target_pks, category, type_key):
    """Count matching NFT items sitting in each target's contents.

    One query for the whole target set rather than one per target. Scrolls and
    recipes match on typeclass path; rare NFTs match on the item's
    prototype_key attribute.

    prototype_key is compared in Python rather than in the WHERE clause:
    db_value is a PickledObjectField, so SQL equality against it is not
    dependable.
    """
    from evennia.objects.models import ObjectDB

    current = {pk: 0 for pk in target_pks}
    if not target_pks:
        return current

    if category in _CATEGORY_TYPECLASS_FRAGMENTS:
        fragment = _CATEGORY_TYPECLASS_FRAGMENTS[category]
        rows = ObjectDB.objects.filter(
            db_location_id__in=target_pks,
            db_typeclass_path__contains=fragment,
        ).values_list("db_location_id", flat=True)
        for location_pk in rows:
            current[location_pk] = current.get(location_pk, 0) + 1
        return current

    # Rare NFTs — exact match on prototype_key.
    rows = ObjectDB.objects.filter(
        db_location_id__in=target_pks,
        db_attributes__db_key="prototype_key",
        db_attributes__db_category__isnull=True,
    ).values_list("db_location_id", "db_attributes__db_value")
    for location_pk, prototype_key in rows:
        if prototype_key == type_key:
            current[location_pk] = current.get(location_pk, 0) + 1
    return current
