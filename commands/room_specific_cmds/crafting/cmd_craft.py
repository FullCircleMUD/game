"""
Craft command — produce NFT items from learned recipes in crafting rooms.

Available in skilled crafting rooms (smithy, woodshop, leathershop, tailor,
apothecary, jeweller). The command verb matches the room type:

    forge <recipe>     — in a smithy
    carve <recipe>     — in a woodshop
    sew <recipe>       — in a tailor shop
    brew <recipe>      — in an apothecary
    enchant <recipe>   — in a wizard's workshop
    craft <recipe>     — generic (works in any crafting room)

Validation:
    1. Character knows the recipe
    2. Recipe matches this room's crafting_type
    3. Room mastery_level >= recipe min_mastery
    4. Character has required ingredients (resources)
    5. Character has required gold (room craft_cost)

On success: consumes ingredients + gold, delays with progress bar,
spawns NFT item into inventory. Crafting time scales with recipe
difficulty (mastery level).
"""

from evennia import Command
from evennia.utils import delay

from blockchain.xrpl.currency_cache import get_resource_type
from commands.command import FCMCommandMixin
from enums.room_crafting_type import RoomCraftingType
from enums.skills_enum import skills
from enums.potion_quality import PotionQuality
from typeclasses.items.base_nft_item import BaseNFTItem


def _get_crafting_mastery(character, skill):
    """Read a character's mastery for a crafting skill.

    Most crafting skills live in ``general_skill_mastery_levels``.
    Enchanting is a mage class skill and lives in
    ``class_skill_mastery_levels`` with a nested ``{"mastery": int}``
    entry. This helper reads from whichever dict the skill belongs to.
    """
    if skill == skills.ENCHANTING:
        class_levels = character.db.class_skill_mastery_levels or {}
        entry = class_levels.get(skill.value, 0)
        if hasattr(entry, "get"):
            return entry.get("mastery", 0)
        return int(entry or 0)

    return (character.db.general_skill_mastery_levels or {}).get(skill.value, 0)


# ── Crafting delay configuration ──
CRAFT_TICK_SECONDS = 3

# Ticks per mastery level (total_time = ticks × CRAFT_TICK_SECONDS)
_TICKS_BY_MASTERY = {
    1: 2,   # BASIC:        6 seconds
    2: 4,   # SKILLED:     12 seconds
    3: 6,   # EXPERT:      18 seconds
    4: 8,   # MASTER:      24 seconds
    5: 10,  # GRANDMASTER: 30 seconds
}

_BAR_WIDTH = 10

# Base XP awarded per craft, scaled by recipe mastery level
_CRAFT_XP_BY_MASTERY = {
    1: 5,    # BASIC
    2: 15,   # SKILLED
    3: 30,   # EXPERT
    4: 50,   # MASTER
    5: 75,   # GRANDMASTER
}

# Map room crafting types to their verb for display messages
_VERB_MAP = {
    RoomCraftingType.SMITHY.value: "forge",
    RoomCraftingType.WOODSHOP.value: "carve",
    RoomCraftingType.LEATHERSHOP.value: "craft",
    RoomCraftingType.TAILOR.value: "sew",
    RoomCraftingType.APOTHECARY.value: "brew",
    RoomCraftingType.JEWELLER.value: "craft",
    RoomCraftingType.WIZARDS_WORKSHOP.value: "enchant",
    RoomCraftingType.SHIPYARD.value: "build",
}

# Gerund forms for progress messages
_GERUND_MAP = {
    RoomCraftingType.SMITHY.value: "Forging",
    RoomCraftingType.WOODSHOP.value: "Carving",
    RoomCraftingType.LEATHERSHOP.value: "Crafting",
    RoomCraftingType.TAILOR.value: "Sewing",
    RoomCraftingType.APOTHECARY.value: "Brewing",
    RoomCraftingType.JEWELLER.value: "Crafting",
    RoomCraftingType.WIZARDS_WORKSHOP.value: "Enchanting",
    RoomCraftingType.SHIPYARD.value: "Building",
}


class CmdCraft(FCMCommandMixin, Command):
    """
    Craft an item from a learned recipe.

    Usage:
        craft <recipe name>
        forge / carve / sew / brew / enchant / build <recipe name>

    You must know the recipe (learn it from a recipe scroll first) and
    be in the correct type of crafting room. Type 'available' to see what
    you can craft here.

    Crafting time depends on recipe difficulty — more advanced recipes
    take longer to craft.
    """

    key = "craft"
    aliases = ["forge", "carve", "sew", "brew", "enchant", "build"]
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
            caller.msg("Craft what? Usage: craft <recipe name>")
            return

        recipe_name = self.args.strip()

        # --- Get room crafting type ---
        crafting_type_str = room.crafting_type
        try:
            crafting_type = RoomCraftingType(crafting_type_str)
        except ValueError:
            caller.msg("This room isn't set up for crafting.")
            return

        # --- Find matching recipe from character's known recipes ---
        known = caller.get_known_recipes(crafting_type=crafting_type)

        if not known:
            caller.msg("You don't know any recipes for this workshop.")
            return

        # Match by recipe name (case-insensitive)
        match = None
        search_lower = recipe_name.lower()
        for key, recipe in known.items():
            if recipe["name"].lower() == search_lower:
                match = recipe
                break

        # Fall back to substring match
        if not match:
            matches = [
                r for r in known.values()
                if search_lower in r["name"].lower()
            ]
            if len(matches) == 1:
                match = matches[0]
            elif len(matches) > 1:
                names = ", ".join(f"|w{r['name']}|n" for r in matches)
                caller.msg(f"Which recipe? {names}")
                return

        if not match:
            caller.msg("You don't know a recipe by that name for this workshop.")
            return

        recipe = match

        # --- Check character's skill mastery ---
        craft_skill = recipe["skill"]
        char_mastery = _get_crafting_mastery(caller, craft_skill)
        if char_mastery < recipe["min_mastery"].value:
            mastery_name = recipe["min_mastery"].name
            skill_name = craft_skill.value.replace("_", " ").title()
            caller.msg(
                f"You need at least |w{mastery_name}|n mastery in "
                f"|w{skill_name}|n to craft {recipe['name']}."
            )
            return

        # --- Check room mastery level ---
        if room.mastery_level < recipe["min_mastery"].value:
            caller.msg(
                f"This workshop isn't advanced enough to craft {recipe['name']}. "
                f"You need a workshop with mastery level "
                f"{recipe['min_mastery'].name} or higher."
            )
            return

        # --- Check resource ingredients (bank-funded if flagged) ---
        ingredients = recipe.get("ingredients", {})
        bank_funded = recipe.get("bank_funded", False)
        bank = None
        resource_split = {}  # {res_id: (from_inv, from_bank)}

        if bank_funded and caller.account:
            bank = caller.account.db.bank  # None if no bank exists yet

        missing = []
        for res_id, needed in ingredients.items():
            inv_available = caller.get_resource(res_id)
            bank_available = bank.get_resource(res_id) if bank else 0
            total = inv_available + bank_available
            if total < needed:
                rt = get_resource_type(res_id)
                name = rt["name"] if rt else f"Resource #{res_id}"
                if bank_funded:
                    missing.append(
                        f"{needed} {name} (have {inv_available} carried"
                        f" + {bank_available} banked = {total})"
                    )
                else:
                    missing.append(f"{needed} {name} (have {inv_available})")
            else:
                from_inv = min(inv_available, needed)
                from_bank = needed - from_inv
                resource_split[res_id] = (from_inv, from_bank)

        # --- Check NFT item ingredients ---
        nft_ingredients = recipe.get("nft_ingredients", {})
        nft_to_consume = {}  # proto_key -> list of items to consume

        if nft_ingredients:
            # Exclude equipped items from consumption
            equipped = set()
            wearslots = caller.db.wearslots
            if wearslots:
                equipped = {v for v in wearslots.values() if v is not None}

            for proto_key, needed in nft_ingredients.items():
                owned = [
                    obj for obj in caller.contents
                    if (getattr(obj, "db", None)
                        and getattr(obj.db, "prototype_key", None) == proto_key
                        and obj not in equipped)
                ]
                if len(owned) < needed:
                    display = proto_key.replace("_", " ").title()
                    missing.append(
                        f"{needed} {display} (have {len(owned)})"
                    )
                else:
                    nft_to_consume[proto_key] = owned[:needed]

        if missing:
            caller.msg(
                f"You don't have enough materials to craft {recipe['name']}:\n"
                + "\n".join(f"  - {m}" for m in missing)
            )
            return

        # --- Check gold (workshop fee × mastery tier) ---
        mastery_tier = recipe.get("min_mastery", 1)
        if hasattr(mastery_tier, "value"):
            mastery_tier = mastery_tier.value
        total_gold = room.craft_cost * mastery_tier

        if not caller.has_gold(total_gold):
            caller.msg(
                f"You need {total_gold} gold (workshop fee) "
                f"but only have {caller.get_gold()}."
            )
            return

        # --- Wand pre-paid mana check (Phase 2) ---
        # Wand recipes set _wand_spell_key and _wand_charges when the
        # dynamic generator emits them. The enchanter pays the spell's
        # mana cost × total charges up-front; zaps are free thereafter.
        wand_mana_cost = 0
        if recipe.get("_wand_spell_key"):
            from world.spells.registry import SPELL_REGISTRY
            spell = SPELL_REGISTRY.get(recipe["_wand_spell_key"])
            if spell is None:
                caller.msg("That spell no longer exists in the registry.")
                return
            spell_tier = spell.min_mastery.value
            per_charge_mana = spell.mana_cost.get(spell_tier, 0)
            wand_mana_cost = per_charge_mana * recipe["_wand_charges"]
            if caller.mana < wand_mana_cost:
                caller.msg(
                    f"Enchanting this wand requires {wand_mana_cost} mana "
                    f"({per_charge_mana} per charge × {recipe['_wand_charges']} charges) — "
                    f"you only have {caller.mana}."
                )
                return

        # --- Build cost summary for confirmation ---
        ingredient_lines = []
        for res_id, needed in ingredients.items():
            rt = get_resource_type(res_id)
            name = rt["name"] if rt else f"Resource #{res_id}"
            from_inv, from_bank = resource_split.get(res_id, (needed, 0))
            if from_bank > 0:
                ingredient_lines.append(
                    f"  {needed} {name} ({from_inv} carried + {from_bank} from bank)"
                )
            else:
                ingredient_lines.append(f"  {needed} {name}")
        for proto_key, needed in nft_ingredients.items():
            display = proto_key.replace("_", " ").title()
            ingredient_lines.append(f"  {needed} {display} (item)")

        cost_display = "\n".join(ingredient_lines)
        verb = _VERB_MAP.get(crafting_type_str, "craft")
        gerund = _GERUND_MAP.get(crafting_type_str, "Crafting")
        num_ticks = _TICKS_BY_MASTERY.get(recipe["min_mastery"].value, 2)
        total_time = num_ticks * CRAFT_TICK_SECONDS

        mana_line = ""
        if wand_mana_cost > 0:
            mana_line = f"\nMana cost: {wand_mana_cost} (pre-paid into the wand)"

        answer = yield (
            f"\n|y--- Craft {recipe['name']} ---|n"
            f"\nMaterials:\n{cost_display}"
            f"\nWorkshop fee: {total_gold} gold"
            f"{mana_line}"
            f"\nCrafting time: {total_time} seconds ({recipe['min_mastery'].name})"
            f"\n\n{verb.capitalize()} {recipe['name']}? Y/[N]"
        )

        if not answer or answer.lower() not in ("y", "yes"):
            caller.msg("Crafting cancelled.")
            return

        # --- Re-validate after confirmation (resources could change) ---
        resource_split = {}  # rebuild split with current amounts
        for res_id, needed in ingredients.items():
            inv_available = caller.get_resource(res_id)
            bank_available = bank.get_resource(res_id) if bank else 0
            total = inv_available + bank_available if bank_funded else inv_available
            if total < needed:
                caller.msg("You no longer have the required materials.")
                return
            from_inv = min(inv_available, needed)
            from_bank = needed - from_inv
            resource_split[res_id] = (from_inv, from_bank)

        if nft_ingredients:
                equipped = set()
                wearslots = caller.db.wearslots
                if wearslots:
                    equipped = {v for v in wearslots.values() if v is not None}

                nft_to_consume = {}
                for proto_key, needed in nft_ingredients.items():
                    owned = [
                        obj for obj in caller.contents
                        if (getattr(obj, "db", None)
                            and getattr(obj.db, "prototype_key", None) == proto_key
                            and obj not in equipped)
                    ]
                    if len(owned) < needed:
                        caller.msg("You no longer have the required materials.")
                        return
                    nft_to_consume[proto_key] = owned[:needed]

        if not caller.has_gold(total_gold):
            caller.msg("You no longer have enough gold.")
            return

        # --- Consume resource ingredients (inventory first, bank remainder) ---
        # Bank resources: transfer to character first, then sink from character.
        for res_id, needed in ingredients.items():
            from_inv, from_bank = resource_split.get(res_id, (needed, 0))
            if from_bank > 0:
                bank.transfer_resource_to(caller, res_id, from_bank)
            caller.return_resource_to_sink(res_id, needed)

        # --- Consume NFT item ingredients ---
        consumed_nft_info = []  # (item_type_name,) for refund on failure
        for proto_key, items in nft_to_consume.items():
            for item in items:
                consumed_nft_info.append(item.key)
                item.delete()

        # --- Consume gold ---
        caller.return_gold_to_sink(total_gold)

        # --- Deduct pre-paid wand mana (Phase 2) ---
        if wand_mana_cost > 0:
            caller.mana -= wand_mana_cost

        # --- Lock and start crafting ---
        caller.ndb.is_processing = True
        # Wand recipes use a generic "Enchanted Wand" NFTItemType with
        # per-instance spell_key + charges metadata. Other recipes
        # default to using the recipe name as the NFTItemType name.
        item_type_name = recipe.get("output_item_type") or recipe["name"]

        # Mastery-tiered recipes (potions) route to a tier-specific NFTItemType
        if recipe.get("mastery_tiered"):
            mastery = _get_crafting_mastery(caller, recipe["skill"])
            item_type_name = (
                f"{PotionQuality(mastery).prefix} {recipe['name']}"
            )

        caller.location.msg_contents_with_invis_alt(
            f"{caller.key} begins crafting at the {room.key}.",
            f"Tools seem to fly around the {room.key} on their own, "
            f"apparently making something...",
            from_obj=caller,
        )

        # --- Chain delayed progress ticks ---
        def _tick(step):
            if step < num_ticks:
                filled = _BAR_WIDTH * step // num_ticks
                bar = '#' * filled + '-' * (_BAR_WIDTH - filled)
                caller.msg(f"{gerund} {recipe['name']}... [{bar}]")
                delay(CRAFT_TICK_SECONDS, _tick, step + 1)
            else:
                # Final tick — spawn item
                bar = '#' * _BAR_WIDTH
                caller.msg(f"{gerund} {recipe['name']}... [{bar}] Done!")

                try:
                    token_id = BaseNFTItem.assign_to_blank_token(item_type_name)
                    item = BaseNFTItem.spawn_into(token_id, caller)

                    # Apply gem enchantment for roll-table recipes
                    output_table = recipe.get("output_table")
                    if output_table and item:
                        from world.recipes.enchanting.gem_tables import (
                            roll_gem_enchantment,
                        )
                        mastery = (
                            caller.db.general_skill_mastery_levels or {}
                        ).get(recipe["skill"].value, 1)
                        effects, restrictions = roll_gem_enchantment(
                            output_table, mastery
                        )
                        item.db.gem_effects = effects
                        item.db.gem_restrictions = restrictions

                    # Apply wand binding (Phase 2) — bind the spell and
                    # install charges. Dual-persist into mirror metadata.
                    if item and recipe.get("_wand_spell_key"):
                        item.spell_key = recipe["_wand_spell_key"]
                        item.charges_max = recipe["_wand_charges"]
                        item.charges_remaining = recipe["_wand_charges"]
                        item.key = recipe["name"]  # "Wand of Fireball"
                        persist = getattr(item, "persist_wand_state", None)
                        if persist is not None:
                            persist()
                except Exception as err:
                    # Refund on spawn failure
                    for res_id, needed in ingredients.items():
                        caller.receive_resource_from_reserve(res_id, needed)
                    caller.receive_gold_from_reserve(total_gold)
                    # Refund pre-paid wand mana
                    if wand_mana_cost > 0:
                        caller.mana += wand_mana_cost
                    # Best-effort refund of consumed NFT items
                    for nft_name in consumed_nft_info:
                        try:
                            tid = BaseNFTItem.assign_to_blank_token(nft_name)
                            BaseNFTItem.spawn_into(tid, caller)
                        except Exception:
                            caller.msg(
                                f"|rFailed to refund {nft_name}.|n"
                            )
                    caller.msg(f"|rCrafting failed: {err}|n")
                    caller.ndb.is_processing = False
                    return

                display_name = item.key if item else recipe["name"]
                caller.msg(f"|gYou {verb} a {display_name}!|n")

                # Award XP based on recipe mastery, scaled by room multiplier
                base_xp = _CRAFT_XP_BY_MASTERY.get(recipe["min_mastery"].value, 5)
                multiplier = room.craft_xp_multiplier or 1.0
                xp = int(base_xp * multiplier)
                if xp > 0:
                    caller.at_gain_experience_points(xp)

                caller.location.msg_contents_with_invis_alt(
                    f"{caller.key} finishes crafting at the {room.key}.",
                    f"The tools at the {room.key} clatter to a stop. "
                    f"A newly crafted item sits on the workbench.",
                    from_obj=caller,
                )
                caller.ndb.is_processing = False

        # Show initial empty progress bar immediately, then start delayed ticks
        bar = '-' * _BAR_WIDTH
        caller.msg(f"{gerund} {recipe['name']}... [{bar}]")
        delay(CRAFT_TICK_SECONDS, _tick, 1)
