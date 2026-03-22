# Character Classes — Auto-Collecting Registry

This directory uses an **auto-collecting registry** pattern. Each class is defined
as a `CharClassBase` instance in its own file, and `__init__.py` automatically
discovers and registers them at import time.

## How it works

1. Each class file (e.g. `warrior.py`) creates a module-level `CharClassBase` instance
2. `__init__.py` imports all class files via `from ... import *`
3. A loop scans the module namespace for `CharClassBase` instances and adds them to `CLASS_REGISTRY`
4. A `CharClass` enum is auto-generated from the registry keys (e.g. `CharClass.WARRIOR`)
5. No manual `register()` calls needed — just create the file and add the import

## Adding a new class

1. Create a new file: `typeclasses/actors/char_classes/my_class.py`
2. Define a `CharClassBase` instance with a unique `key`:
   ```python
   from enums.abilities_enum import Ability
   from typeclasses.actors.char_classes.char_class_base import CharClassBase

   PROGRESSION = {
       1: {"weapon_skill_pts": 2, "class_skill_pts": 3, "general_skill_pts": 2,
           "hp_gain": 10, "mana_gain": 8, "move_gain": 4},
       # ... levels 2-40
   }

   MY_CLASS = CharClassBase(
       key="my_class",
       display_name="My Class",
       description="...",
       prime_attribute=Ability.INT,
       level_progression=PROGRESSION,
   )
   ```
3. Add one import line to `__init__.py`:
   ```python
   from typeclasses.actors.char_classes.my_class import *
   ```
4. Done — `get_char_class("my_class")` and `CharClass.MY_CLASS` will now work

## Lookup API

```python
from typeclasses.actors.char_classes import (
    get_char_class, list_char_classes, get_available_char_classes, CharClass
)

warrior = get_char_class("warrior")          # CharClassBase instance or None
keys = list_char_classes()                   # ["warrior", "thief"]
available = get_available_char_classes(0)    # classes with min_remort <= 0
CharClass.WARRIOR                            # auto-generated enum, value = "warrior"
```

## Important

- The variable name (e.g. `WARRIOR`) doesn't matter — the `key` field is what registers it
- Each `key` must be unique across all class files
- Level progression tables must cover levels 1-40
- Don't put non-class `CharClassBase` instances in these files — the auto-collector picks up everything
