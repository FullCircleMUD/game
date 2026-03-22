"""
Eat command — consume food to restore hunger.

Currently only Bread (resource ID 3) is edible. The argument is
kept so new food types can be added later.

Usage:
    eat <food>
    eat bread
"""

from evennia import Command

from enums.hunger_level import HungerLevel

# Map of edible food names to their resource IDs
EDIBLE_FOODS = {
    "bread": 3,
}


class CmdEat(Command):
    """
    Eat food to restore hunger.

    Usage:
        eat <food>
        eat bread

    Consuming food increases your hunger level by one step.
    """

    key = "eat"
    locks = "cmd:all()"
    help_category = "Items"
    arg_regex = r"\s|$"

    def func(self):
        caller = self.caller

        if not self.args:
            caller.msg("Eat what?")
            return

        food_name = self.args.strip().lower()

        resource_id = EDIBLE_FOODS.get(food_name)
        if resource_id is None:
            caller.msg("You can't eat that.")
            return

        if not caller.has_resource(resource_id, 1):
            caller.msg(f"You don't have any {food_name}.")
            return

        current = caller.hunger_level
        if current == HungerLevel.FULL:
            caller.msg("You are already full.")
            return

        # consume 1 bread — consumed into game sink
        caller.return_resource_to_sink(resource_id, 1)

        # increase hunger level by 1
        new_level = HungerLevel(current.value + 1)
        caller.hunger_level = new_level

        # if eating brought them to FULL, grant a free pass on the next hunger tick
        if new_level == HungerLevel.FULL:
            caller.hunger_free_pass_tick = True

        caller.msg(f"You eat some {food_name}.")
        caller.msg(new_level.get_hunger_message())
