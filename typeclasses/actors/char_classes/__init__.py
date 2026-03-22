"""
Character class registry — auto-collects all CharClassBase instances from
class definition files.

Adding a new class:
    1. Create typeclasses/actors/char_classes/my_class.py with MY_CLASS = CharClassBase(...)
    2. Add `from typeclasses.actors.char_classes.my_class import *` below
    3. The auto-collection loop picks it up — no manual register() call needed
    4. The CharClass enum is auto-generated from the registry — no separate enum needed

Lookup:
    from typeclasses.actors.char_classes import get_char_class, list_char_classes, CharClass
    warrior = get_char_class("warrior")
    warrior.at_char_first_gaining_class(character)
    CharClass.WARRIOR  # auto-generated enum member, value = "warrior"
"""

import sys
from enum import Enum

from typeclasses.actors.char_classes.char_class_base import CharClassBase
from typeclasses.actors.char_classes.warrior import *
from typeclasses.actors.char_classes.thief import *
from typeclasses.actors.char_classes.mage import *
from typeclasses.actors.char_classes.cleric import *
from typeclasses.actors.char_classes.paladin import *
from typeclasses.actors.char_classes.bard import *

# Auto-collect all CharClassBase instances into the registry.
# Scans this module's namespace for any CharClassBase instance with a non-empty key.
_module = sys.modules[__name__]
CLASS_REGISTRY = {}
for _name in dir(_module):
    _obj = getattr(_module, _name)
    if isinstance(_obj, CharClassBase):
        if _obj.key:  # skip the class default (key="")
            CLASS_REGISTRY[_obj.key] = _obj

# Auto-generate the CharClass enum from registry keys.
# This means adding a new class file automatically creates a new enum member
# (e.g. CharClass.WARRIOR with value "warrior"). No separate enum file needed.
CharClass = Enum("CharClass", {k.upper(): k for k in CLASS_REGISTRY})


def get_char_class(key):
    """Look up a character class by key. Returns CharClassBase instance or None."""
    return CLASS_REGISTRY.get(key)


def list_char_classes():
    """Return list of all character class keys."""
    return list(CLASS_REGISTRY.keys())


def get_available_char_classes(num_remorts=0):
    """Return dict of classes available at the given remort count."""
    return {k: v for k, v in CLASS_REGISTRY.items() if v.min_remort <= num_remorts}
