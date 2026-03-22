"""
In-memory cache for CurrencyType records.

Loads all rows from the database on first access, holds them in dicts
keyed by resource_id and currency_code. Cleared on evennia reload
(Python module state resets).

Usage:
    from blockchain.xrpl.currency_cache import (
        get_currency_type, get_all_currency_types,
        get_currency_code, get_resource_id,
    )

    rt = get_currency_type(1)
    # {"name": "Wheat", "unit": "bushels", "currency_code": "FCMWheat", ...}

    code = get_currency_code(1)    # "FCMWheat"
    rid = get_resource_id("FCMWheat")  # 1
"""

_by_resource_id = {}
_by_currency_code = {}


def _load():
    """Load all CurrencyType rows into the module-level caches."""
    from blockchain.xrpl.models import CurrencyType

    for ct in CurrencyType.objects.all():
        info = {
            "name": ct.name,
            "unit": ct.unit,
            "currency_code": ct.currency_code,
            "description": ct.description,
            "weight_per_unit_kg": float(ct.weight_per_unit_kg),
            "is_gold": ct.is_gold,
            "resource_id": ct.resource_id,
        }
        if ct.resource_id is not None:
            _by_resource_id[ct.resource_id] = info
        _by_currency_code[ct.currency_code] = info


def get_currency_type(resource_id):
    """Return display info dict for a single resource_id, or None."""
    if not _by_resource_id:
        _load()
    return _by_resource_id.get(resource_id)


def get_all_currency_types():
    """Return the full {resource_id: info_dict} cache."""
    if not _by_resource_id:
        _load()
    return _by_resource_id


def get_currency_code(resource_id):
    """Return the XRPL currency code for a resource_id, or None."""
    info = get_currency_type(resource_id)
    return info["currency_code"] if info else None


def get_resource_id(currency_code):
    """Return the resource_id for a currency_code, or None."""
    if not _by_currency_code:
        _load()
    info = _by_currency_code.get(currency_code)
    return info["resource_id"] if info else None


# Compatibility aliases — game code uses these names (from polygon.resource_cache)
get_resource_type = get_currency_type
get_all_resource_types = get_all_currency_types
