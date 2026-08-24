"""
Evicting an object's cached Attributes after a rolled-back transaction.

A rollback restores the rows and nothing else. Evennia's AttributeHandler is
still holding the Attribute instances it wrote, so the object keeps reporting
values the database no longer has — and nothing raises to say so.

See design/database.md § Transactions and Split Aliases for where this comes
up: any failure path that follows a transaction over Evennia state needs it.
"""


def discard_cached_attributes(obj):
    """
    Drop an object's cached Attributes so the next read hits the database.

    ``reset_cache()`` alone is not enough — the re-fetch goes through the
    idmapper, which hands back the very same Attribute instances. They have
    to be evicted from there first.

    Args:
        obj (Object): the object whose attribute cache is now stale.
    """
    for attr in list(obj.attributes.backend._cache.values()):
        if attr is not None:
            attr.flush_from_cache(force=True)
    obj.attributes.reset_cache()
