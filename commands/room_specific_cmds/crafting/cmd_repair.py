"""
Repair command — restore durability on a damaged item at a crafting station.

Available in the same crafting rooms as the craft command. Requires the
character to know the recipe for the item and have sufficient mastery.

Repair cost is derived from the crafting recipe:
    - If the recipe has explicit 'repair_ingredients', use those.
    - Otherwise: total_materials - 1, distributed across resource ingredients
      only (NFT ingredients are never consumed for repair).

Room fee (craft_cost gold) always applies, even when material cost is 0.

Validation:
    1. Item in inventory, has durability, not already full, is repairable
    2. Character knows the recipe for this item
    3. Character has requisite mastery + room supports it
    4. Character has required repair resources + gold

On success: consumes resources + gold, delays with progress bar,
resets durability to max_durability. Awards 50% of craft XP.
"""

from evennia import Command
from evennia.utils import delay

from blockchain.xrpl.currency_cache import get_resource_type
from commands.command import FCMCommandMixin
from enums.room_crafting_type import RoomCraftingType
from world.recipes import get_recipe_by_output_prototype, compute_repair_cost


# ── Repair delay configuration (mirrors cmd_craft.py) ──
REPAIR_TICK_SECONDS = 3

_TICKS_BY_MASTERY = {
    1: 2,   # BASIC:        6 seconds
    2: 4,   # SKILLED:     12 seconds
    3: 6,   # EXPERT:      18 seconds
    4: 8,   # MASTER:      24 seconds
    5: 10,  # GRANDMASTER: 30 seconds
}

_BAR_WIDTH = 10

_CRAFT_XP_BY_MASTERY = {
    1: 5,    # BASIC
    2: 15,   # SKILLED
    3: 30,   # EXPERT
    4: 50,   # MASTER
    5: 75,   # GRANDMASTER
}


class CmdRepair(FCMCommandMixin, Command):
    """
    Repair a damaged item using a crafting station.

    Usage:
        repair <item name>

    You must know the recipe for the item and be in the correct type
    of crafting room. The item must be in your inventory and have
    durability damage. Repair cost is less than crafting cost.
    """

    key = "repair"
    aliases = ["rep", "repa", "repai"]
    locks = "cmd:all()"
    help_category = "Crafting"

    def func(self):
        caller = self.caller
        room = caller.location

        # --- Busy check ---
        if caller.ndb.is_processing:
            caller.msg(
                "You are already busy. Wait until your current task finishes."
            )
            return

        if not self.args:
            caller.msg("Repair what? Usage: repair <item name>")
            return

        # --- Find item in inventory ---
        item = caller.search(self.args.strip(), location=caller)
        if not item:
            return  # search() already sends "Could not find" message

        # --- Durability checks ---
        if not hasattr(item, "max_durability") or item.max_durability == 0:
            caller.msg(f"{item.key} is unbreakable and needs no repair.")
            return

        if item.durability is None:
            item.at_durability_init()
        if item.durability >= item.max_durability:
            caller.msg(f"{item.key} is already in pristine condition.")
            return

        if hasattr(item, "repairable") and not item.repairable:
            caller.msg(f"{item.key} cannot be repaired.")
            return

        # --- Get room crafting type ---
        crafting_type_str = room.crafting_type
        try:
            crafting_type = RoomCraftingType(crafting_type_str)
        except (ValueError, AttributeError):
            caller.msg("This room isn't set up for crafting.")
            return

        # --- Find the recipe for this item ---
        # Uses db.prototype_key set by BaseNFTItem.spawn_into() — NOT the
        # Evennia from_prototype tag (which is not set by our spawn path).
        prototype_key = getattr(item.db, "prototype_key", None)
        if not prototype_key:
            caller.msg(
                f"You don't know how to repair {item.key}."
            )
            return

        recipe = get_recipe_by_output_prototype(prototype_key)
        if not recipe:
            caller.msg(
                f"You don't know how to repair {item.key}."
            )
            return

        # --- Recipe must match this room's crafting type ---
        if recipe["crafting_type"] != crafting_type:
            room_name = crafting_type.value.replace("_", " ").title()
            needed_name = recipe["crafting_type"].value.replace("_", " ").title()
            caller.msg(
                f"{item.key} needs a |w{needed_name}|n to repair, "
                f"not a {room_name}."
            )
            return

        # --- Character must know the recipe ---
        if not caller.knows_recipe(recipe["recipe_key"]):
            caller.msg(
                f"You don't know the recipe for {recipe['name']}. "
                f"You can't repair what you can't craft."
            )
            return

        # --- Check character's skill mastery ---
        craft_skill = recipe["skill"]
        char_mastery = (caller.db.general_skill_mastery_levels or {}).get(
            craft_skill.value, 0
        )
        if char_mastery < recipe["min_mastery"].value:
            mastery_name = recipe["min_mastery"].name
            skill_name = craft_skill.value.replace("_", " ").title()
            caller.msg(
                f"You need at least |w{mastery_name}|n mastery in "
                f"|w{skill_name}|n to repair {item.key}."
            )
            return

        # --- Check room mastery level ---
        if room.mastery_level < recipe["min_mastery"].value:
            caller.msg(
                f"This workshop isn't advanced enough to repair {item.key}. "
                f"You need a workshop with mastery level "
                f"{recipe['min_mastery'].name} or higher."
            )
            return

        # --- Compute repair cost ---
        repair_ingredients = compute_repair_cost(recipe)

        # --- Check resource ingredients ---
        missing = []
        for res_id, needed in repair_ingredients.items():
            available = caller.get_resource(res_id)
            if available < needed:
                rt = get_resource_type(res_id)
                name = rt["name"] if rt else f"Resource #{res_id}"
                missing.append(f"{needed} {name} (have {available})")

        if missing:
            caller.msg(
                f"You don't have enough materials to repair {item.key}:\n"
                + "\n".join(f"  - {m}" for m in missing)
            )
            return

        # --- Check gold (workshop fee) ---
        total_gold = room.craft_cost

        if not caller.has_gold(total_gold):
            caller.msg(
                f"You need {total_gold} gold (workshop fee) "
                f"but only have {caller.get_gold()}."
            )
            return

        # --- Build cost summary for confirmation ---
        ingredient_lines = []
        for res_id, needed in repair_ingredients.items():
            rt = get_resource_type(res_id)
            name = rt["name"] if rt else f"Resource #{res_id}"
            ingredient_lines.append(f"  {needed} {name}")

        if ingredient_lines:
            cost_display = "\n".join(ingredient_lines)
            materials_section = f"\nMaterials:\n{cost_display}"
        else:
            materials_section = "\nMaterials: none (workshop fee only)"

        num_ticks = _TICKS_BY_MASTERY.get(recipe["min_mastery"].value, 2)
        total_time = num_ticks * REPAIR_TICK_SECONDS
        condition = item.get_condition_label()

        answer = yield (
            f"\n|y--- Repair {item.key} ---|n"
            f"\nCondition: {condition} "
            f"({item.durability}/{item.max_durability})"
            f"{materials_section}"
            f"\nWorkshop fee: {total_gold} gold"
            f"\nRepair time: {total_time} seconds ({recipe['min_mastery'].name})"
            f"\n\nRepair {item.key}? Y/[N]"
        )

        if answer.lower() not in ("y", "yes"):
            caller.msg("Repair cancelled.")
            return

        # --- Re-validate after confirmation ---
        for res_id, needed in repair_ingredients.items():
            if caller.get_resource(res_id) < needed:
                caller.msg("You no longer have the required materials.")
                return

        if not caller.has_gold(total_gold):
            caller.msg("You no longer have enough gold.")
            return

        if item.durability >= item.max_durability:
            caller.msg(f"{item.key} has already been repaired.")
            return

        # --- Consume resource ingredients ---
        for res_id, needed in repair_ingredients.items():
            caller.return_resource_to_sink(res_id, needed)

        # --- Consume gold ---
        caller.return_gold_to_sink(total_gold)

        # --- Lock and start repairing ---
        caller.ndb.is_processing = True

        caller.location.msg_contents_with_invis_alt(
            f"{caller.key} begins repairing at the {room.key}.",
            f"Tools clatter at the {room.key} as unseen hands "
            f"work on something...",
            from_obj=caller,
        )

        # --- Chain delayed progress ticks ---
        def _tick(step):
            if step < num_ticks:
                filled = _BAR_WIDTH * step // num_ticks
                bar = '#' * filled + '-' * (_BAR_WIDTH - filled)
                caller.msg(f"Repairing {item.key}... [{bar}]")
                delay(REPAIR_TICK_SECONDS, _tick, step + 1)
            else:
                bar = '#' * _BAR_WIDTH
                caller.msg(f"Repairing {item.key}... [{bar}] Done!")

                item.repair_to_full()

                caller.msg(
                    f"|gYou repair {item.key} to pristine condition!|n"
                )

                # Award 50% of craft XP
                base_xp = _CRAFT_XP_BY_MASTERY.get(
                    recipe["min_mastery"].value, 5
                )
                multiplier = room.craft_xp_multiplier or 1.0
                xp = int(base_xp * multiplier) // 2
                if xp > 0:
                    caller.at_gain_experience_points(xp)

                caller.location.msg_contents_with_invis_alt(
                    f"{caller.key} finishes repairing at the {room.key}.",
                    f"The tools at the {room.key} clatter to a stop.",
                    from_obj=caller,
                )
                caller.ndb.is_processing = False

        # Start first tick
        delay(REPAIR_TICK_SECONDS, _tick, 1)
