"""
Weapon prototypes — auto-collected from every .py file in this folder.

Each prototype file defines an UPPERCASE dict with a "prototype_key" entry.
This __init__ walks every sibling module and pulls those dicts into the
package namespace so Evennia's prototype discovery picks them up via the
wildcard import in world.prototypes.__init__.
"""

import importlib as _importlib
import pkgutil as _pkgutil

for _finder, _name, _ispkg in _pkgutil.iter_modules(__path__):
    if _ispkg or _name.startswith("_"):
        continue
    _mod = _importlib.import_module(f"{__name__}.{_name}")
    for _attr in dir(_mod):
        if _attr.isupper():
            _val = getattr(_mod, _attr)
            if isinstance(_val, dict) and "prototype_key" in _val:
                globals()[_attr] = _val

del _importlib, _pkgutil
