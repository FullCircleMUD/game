"""
Race registry — auto-collects all RaceBase instances from race definition files.

Adding a new race:
    1. Create typeclasses/actors/races/my_race.py with MY_RACE = RaceBase(...)
    2. Add `from typeclasses.actors.races.my_race import *` below
    3. The auto-collection loop picks it up — no manual register() call needed
    4. The Race enum is auto-generated from the registry — no separate enum file needed

Lookup:
    from typeclasses.actors.races import get_race, list_races, get_available_races, Race
    dwarf = get_race("dwarf")
    dwarf.at_taking_race(character)
    Race.DWARF  # auto-generated enum member, value = "dwarf"
"""

import sys
from enum import Enum

from typeclasses.actors.races.race_base import RaceBase
from typeclasses.actors.races.human import *
from typeclasses.actors.races.dwarf import *
from typeclasses.actors.races.elf import *
from typeclasses.actors.races.halfling import *
from typeclasses.actors.races.aasimar import *

# Auto-collect all RaceBase instances into the registry.
# Scans this module's namespace for any RaceBase instance with a non-empty key.
_module = sys.modules[__name__]
RACE_REGISTRY = {}
for _name in dir(_module):
    _obj = getattr(_module, _name)
    if isinstance(_obj, RaceBase):
        if _obj.key:  # skip the class default (key="")
            RACE_REGISTRY[_obj.key] = _obj

# Auto-generate the Race enum from registry keys.
# This replaces the old static enums/race_enum.py — adding a new race file
# automatically creates a new enum member (e.g. Race.DWARF with value "dwarf").
# Usage: Race.HUMAN, Race.DWARF, Race.ELF — values match the registry keys.
Race = Enum("Race", {k.upper(): k for k in RACE_REGISTRY})


def get_race(key):
    """Look up a race by key. Returns RaceBase instance or None."""
    return RACE_REGISTRY.get(key)


def list_races():
    """Return list of all race keys."""
    return list(RACE_REGISTRY.keys())


def get_available_races(num_remorts=0):
    """Return dict of races available at the given remort count."""
    return {k: v for k, v in RACE_REGISTRY.items() if v.min_remort <= num_remorts}
