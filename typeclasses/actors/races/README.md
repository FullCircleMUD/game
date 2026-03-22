# Races — Auto-Collecting Registry

This directory uses an **auto-collecting registry** pattern. Each race is defined
as a `RaceBase` instance in its own file, and `__init__.py` automatically discovers
and registers them at import time.

## How it works

1. Each race file (e.g. `dwarf.py`) creates a module-level `RaceBase` instance
2. `__init__.py` imports all race files via `from ... import *`
3. A loop scans the module namespace for `RaceBase` instances and adds them to `RACE_REGISTRY`
4. No manual `register()` calls needed — just create the file and add the import

## Adding a new race

1. Create a new file: `typeclasses/actors/races/my_race.py`
2. Define a `RaceBase` instance with a unique `key`:
   ```python
   from enums.actor_size import ActorSize
   from typeclasses.actors.races.race_base import RaceBase

   MY_RACE = RaceBase(
       key="my_race",
       display_name="My Race",
       description="...",
       size=ActorSize.MEDIUM,
       base_hp=10,
       base_mana=10,
       base_move=50,
   )
   ```
3. Add one import line to `__init__.py`:
   ```python
   from typeclasses.actors.races.my_race import *
   ```
4. Done — `get_race("my_race")` will now find it

## Lookup API

```python
from typeclasses.actors.races import get_race, list_races, get_available_races

dwarf = get_race("dwarf")           # RaceBase instance or None
keys = list_races()                  # ["human", "dwarf", "elf"]
available = get_available_races(0)   # races with min_remort <= 0
```

## Important

- The variable name (e.g. `DWARF`) doesn't matter — the `key` field is what registers it
- Each `key` must be unique across all race files
- Don't put non-race `RaceBase` instances in these files — the auto-collector picks up everything
