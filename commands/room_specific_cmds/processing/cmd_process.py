"""
Process command — convert raw resources into refined ones.

Available in processing rooms (windmill, bakery, smelter, sawmill, tannery,
textile mill, apothecary). Each room has one or more processing recipes.

Usage:
    process [amount]            — single-recipe rooms (mill, bakery, etc.)
    process <resource> [amount] — multi-recipe rooms (smelter, etc.)

    mill [amount]       — mill wheat into flour
    bake [amount]       — bake flour + wood into bread
    smelt <ingot> [amount] — smelt ore into ingots / alloys
    saw [amount]        — saw wood into timber
    tan [amount]        — tan hide into leather
    weave [amount]      — weave cotton into cloth
    distill [amount]    — distill moonpetal into essence

    amount defaults to 1. Use 'all' to process as many as possible.
"""

from evennia import Command
from evennia.utils import delay

from blockchain.xrpl.currency_cache import get_resource_type
from commands.command import FCMCommandMixin

# ── Easy-to-change delay between each processing tick ──
PROCESS_DELAY_SECONDS = 2


def _get_resource_name(res_id):
    """Look up a resource name by ID, with fallback."""
    rt = get_resource_type(res_id)
    return rt["name"] if rt else f"Resource #{res_id}"


def _find_recipe(recipes, query):
    """
    Match a query string against recipe **output** resource names.

    Returns (recipe, None) on unique match, or (None, error_message) on
    zero or ambiguous matches.
    """
    query_lower = query.lower()
    matches = []

    for recipe in recipes:
        out_name = _get_resource_name(recipe["output"]).lower()
        if query_lower in out_name:
            matches.append(recipe)

    if len(matches) == 1:
        return matches[0], None

    if not matches:
        return None, f"No recipe found matching '{query}'. Type 'rates' to see available recipes."

    # Ambiguous — list the matches
    lines = [f"Multiple recipes match '{query}':"]
    for m in matches:
        out_name = _get_resource_name(m["output"])
        input_parts = []
        for res_id, res_amount in m["inputs"].items():
            input_parts.append(f"{res_amount} {_get_resource_name(res_id)}")
        lines.append(f"  {' + '.join(input_parts)} → {m['amount']} {out_name}")
    lines.append("Be more specific.")
    return None, "\n".join(lines)


def _list_recipes(recipes, room):
    """Build a display string listing all available recipes."""
    lines = [f"\n|c--- {room.key} Recipes ---|n"]
    for recipe in recipes:
        cost = recipe.get("cost", room.process_cost)
        out_name = _get_resource_name(recipe["output"])
        input_parts = []
        for res_id, res_amount in recipe["inputs"].items():
            input_parts.append(f"{res_amount} {_get_resource_name(res_id)}")
        lines.append(
            f"  {' + '.join(input_parts)} + {cost} gold |w→|n "
            f"{recipe['amount']} {out_name}"
        )
    lines.append(f"|c--- End of Recipes ---|n")
    return "\n".join(lines)


class CmdProcess(FCMCommandMixin, Command):
    """
    Process raw resources into refined materials.

    Usage:
        process [amount]             — single-recipe rooms
        process <resource> [amount]  — multi-recipe rooms
        mill / bake / smelt / saw / tan / weave / distill

    Converts input resources into output resources for a gold fee.
    Use 'all' to process as many as you can afford.
    Type 'rates' to see this room's conversion rates.
    """

    key = "process"
    aliases = ("pro", "proc", "mill", "bake", "smelt", "saw", "tan", "weave", "distill", "distil", "di", "dis", "dist")
    locks = "cmd:all()"
    help_category = "Crafting"

    def func(self):
        caller = self.caller
        room = caller.location

        # --- Busy check ---
        if caller.ndb.is_processing:
            caller.msg("You are already processing something. Wait until it finishes.")
            return

        recipes = room.recipes
        if not recipes:
            caller.msg("This room has no processing recipes configured.")
            return

        # --- Parse args: optional <resource_query> + optional <amount> ---
        args = self.args.strip()
        query = None
        amount = 1
        process_all = False

        if not args:
            # No args — single recipe auto-selects, multi recipe lists
            if len(recipes) > 1:
                caller.msg(_list_recipes(recipes, room))
                return
            # Single recipe, amount=1
        elif args.lower() == "all":
            process_all = True
            if len(recipes) > 1:
                caller.msg("Specify what to process: e.g. 'smelt iron ingot all'")
                return
        else:
            # Try entire string as a number (single-recipe shortcut)
            try:
                amount = int(args)
                if amount <= 0:
                    caller.msg("Amount must be a positive number.")
                    return
                if len(recipes) > 1:
                    caller.msg("Specify what to process: e.g. 'smelt iron ingot 5'")
                    return
            except ValueError:
                # Not a bare number — split into query + optional amount
                tokens = args.rsplit(None, 1)
                last = tokens[-1].lower()

                if last == "all" and len(tokens) > 1:
                    query = tokens[0]
                    process_all = True
                elif len(tokens) > 1:
                    try:
                        amount = int(last)
                        if amount <= 0:
                            caller.msg("Amount must be a positive number.")
                            return
                        query = tokens[0]
                    except ValueError:
                        # Entire string is the query
                        query = args
                else:
                    query = args

        # --- Resolve recipe ---
        if query:
            recipe, err = _find_recipe(recipes, query)
            if err:
                caller.msg(err)
                return
        else:
            recipe = recipes[0]

        inputs = recipe["inputs"]
        output_resource = recipe["output"]
        output_amount = recipe["amount"]
        process_cost = recipe.get("cost", room.process_cost)

        # --- Resolve 'all' — find max processes possible ---
        if process_all:
            max_by_gold = caller.get_gold() // process_cost if process_cost > 0 else 999
            max_by_resource = 999
            for res_id, res_amount in inputs.items():
                available = caller.get_resource(res_id)
                max_for_this = available // res_amount if res_amount > 0 else 999
                max_by_resource = min(max_by_resource, max_for_this)
            amount = min(max_by_gold, max_by_resource)
            if amount <= 0:
                caller.msg("You don't have the resources or gold to process anything.")
                return

        # --- Validate resources ---
        for res_id, res_amount in inputs.items():
            needed = res_amount * amount
            available = caller.get_resource(res_id)
            if available < needed:
                caller.msg(
                    f"You need {needed} {_get_resource_name(res_id)} "
                    f"but only have {available}."
                )
                return

        # --- Validate gold ---
        total_gold = process_cost * amount
        if not caller.has_gold(total_gold):
            caller.msg(
                f"You need {total_gold} gold but only have {caller.get_gold()}."
            )
            return

        # --- Consume inputs and gold upfront (committed) ---
        for res_id, res_amount in inputs.items():
            caller.return_resource_to_sink(res_id, res_amount * amount)

        caller.return_gold_to_sink(total_gold)

        # --- Build display names for progress messages ---
        out_name = _get_resource_name(output_resource)

        input_parts = []
        for res_id, res_amount in inputs.items():
            input_parts.append(f"{res_amount * amount} {_get_resource_name(res_id)}")
        input_desc = " and ".join(input_parts)

        # Use the room's processing_type to pick the right verb
        _PROCESSING_VERBS = {
            "windmill": "mill",
            "bakery": "bake",
            "smelter": "smelt",
            "sawmill": "saw",
            "tannery": "tan",
            "textile mill": "weave",
            "textilemill": "weave",
            "distillery": "distill",
            "apothecary": "distill",
        }
        verb = _PROCESSING_VERBS.get(
            getattr(room, "processing_type", ""), self.cmdstring
        )
        total_output = output_amount * amount

        # --- Lock and start processing ---
        caller.ndb.is_processing = True
        caller.msg(f"You begin to {verb} {input_desc}...")
        caller.location.msg_contents_with_invis_alt(
            f"{caller.key} begins working at the {room.processing_type}.",
            f"The {room.processing_type} seems to be operating itself... "
            f"making {out_name}.",
            from_obj=caller,
        )

        # --- Chain delayed progress ticks ---
        def _tick(step):
            if step < amount:
                caller.msg(f"Processing {out_name}... {step} of {amount}")
                delay(PROCESS_DELAY_SECONDS, _tick, step + 1)
            else:
                # Final tick — produce output and send summary
                caller.msg(f"Processing {out_name}... Done!")
                caller.receive_resource_from_reserve(
                    output_resource, total_output
                )
                caller.msg(
                    f"|gYou {verb} {input_desc} into "
                    f"{total_output} {out_name} for {total_gold} gold.|n"
                )

                # Award XP if configured
                xp = room.process_xp
                if xp and xp > 0:
                    total_xp = xp * amount
                    caller.at_gain_experience_points(total_xp)

                caller.ndb.is_processing = False

        # Start first tick
        delay(PROCESS_DELAY_SECONDS, _tick, 1)
