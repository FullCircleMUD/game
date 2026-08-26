"""Values callers need in order to use the telemetry API.

They live here rather than on the model so a caller naming a saturation
category does not have to import the model to do it.
"""

CATEGORY_SPELL = "spell"
CATEGORY_RECIPE = "recipe"
CATEGORY_ITEM = "item"

CATEGORY_CHOICES = [
    (CATEGORY_SPELL, "Spell"),
    (CATEGORY_RECIPE, "Recipe"),
    (CATEGORY_ITEM, "Item"),
]

# Rolling window used by every "average of recent hours" read.
DEFAULT_AVERAGE_HOURS = 24
