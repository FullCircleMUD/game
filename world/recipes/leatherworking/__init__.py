"""
Leatherworking recipes — auto-collected from every .py file in this folder.

Each recipe file defines a RECIPE_* dict at module level. This __init__
walks every sibling module and pulls those dicts into the package namespace
so world.recipes.__init__ can register them in the RECIPES lookup.
"""

import importlib as _importlib
import pkgutil as _pkgutil

for _finder, _name, _ispkg in _pkgutil.iter_modules(__path__):
    if _ispkg or _name.startswith("_"):
        continue
    _mod = _importlib.import_module(f"{__name__}.{_name}")
    for _attr in dir(_mod):
        if _attr.startswith("RECIPE_"):
            globals()[_attr] = getattr(_mod, _attr)

del _importlib, _pkgutil
