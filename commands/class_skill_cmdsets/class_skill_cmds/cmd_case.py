"""
Case command — study a target to reveal what they're carrying.

Part of the SUBTERFUGE skill (thief/ninja/bard). A thief must case a
target before pickpocketing them. Each item in the target's inventory
has a mastery-dependent % chance of being revealed. Results are cached
for 5 minutes — repeating the command shows the same results until
the cache expires.

Casing is passive observation: does NOT break HIDDEN.

Usage:
    case <target>
"""

import random
import time

from blockchain.xrpl.currency_cache import get_resource_type
from enums.condition import Condition
from enums.mastery_level import MasteryLevel
from enums.skills_enum import skills
from .cmd_skill_base import CmdSkillBase

# Cache duration in seconds
CASE_CACHE_DURATION = 300  # 5 minutes

# Per-mastery chance of seeing each item (0-100)
_MASTERY_CHANCE = {
    MasteryLevel.BASIC.value: 50,
    MasteryLevel.SKILLED.value: 60,
    MasteryLevel.EXPERT.value: 70,
    MasteryLevel.MASTER.value: 80,
    MasteryLevel.GRANDMASTER.value: 90,
}


def _gold_description(amount):
    """Return a vague description of a gold amount."""
    if amount <= 10:
        return "a few coins"
    elif amount <= 50:
        return "some gold"
    elif amount <= 200:
        return "a decent purse of gold"
    elif amount <= 1000:
        return "a heavy coin purse"
    else:
        return "a fortune in gold"


def _resource_name(resource_id):
    """Look up a resource name by ID, with fallback."""
    rt = get_resource_type(resource_id)
    return rt["name"].lower() if rt else f"resource #{resource_id}"


class CmdCase(CmdSkillBase):
    """
    Study a target to see what they're carrying.

    Usage:
        case <target>

    Carefully observe a target to determine what items, gold, and
    resources they carry. Each thing has a chance of being spotted
    based on your subterfuge mastery. Results are cached — repeating
    the command within 5 minutes shows the same results.

    Must case a target before you can pickpocket them.
    """

    key = "case"
    skill = skills.SUBTERFUGE.value
    help_category = "Stealth"
    allow_while_sleeping = True

    def func(self):
        caller = self.caller

        if not self.args:
            caller.msg("Case who?")
            return

        target_name = self.args.strip()

        # Can't case yourself
        if target_name.lower() in ("me", "self"):
            caller.msg("You can't case yourself.")
            return

        # Find target in room
        target = caller.search(target_name)
        if not target:
            return

        if target == caller:
            caller.msg("You can't case yourself.")
            return

        # Must be an actor (has hp) — not objects/items
        if not hasattr(target, "hp"):
            caller.msg("You can't case that.")
            return

        # Can't case in combat
        if caller.scripts.get("combat_handler"):
            caller.msg("You can't case someone while in combat!")
            return

        # Can't case hidden targets
        if hasattr(target, "has_condition") and target.has_condition(Condition.HIDDEN):
            caller.msg("You can't see them well enough to case them.")
            return

        # Mastery check — UNSKILLED can't case
        mastery_int = caller.get_skill_mastery(self.skill) if hasattr(caller, 'get_skill_mastery') else 0
        if mastery_int <= 0:
            caller.msg(
                "You have no idea how to case a mark. "
                "You need training in subterfuge."
            )
            return

        # Check cache — return same results within 5 minutes
        cached = self._get_cached_results(caller, target)
        if cached is not None:
            self._display_results(caller, target, cached)
            return

        # Fresh roll — determine what the thief can see
        chance = _MASTERY_CHANCE.get(mastery_int, 50)
        results = self._roll_case(target, chance)

        # Cache results
        self._cache_results(caller, target, results)

        # Display
        self._display_results(caller, target, results)

    def _get_cached_results(self, caller, target):
        """Return cached case results if still valid, else None."""
        cache = getattr(caller.ndb, "case_results", None)
        if not cache:
            return None
        entry = cache.get(target.id)
        if not entry:
            return None
        if time.time() - entry["timestamp"] >= CASE_CACHE_DURATION:
            return None
        return entry

    def _cache_results(self, caller, target, results):
        """Store case results on the caller."""
        if not caller.ndb.case_results:
            caller.ndb.case_results = {}
        caller.ndb.case_results[target.id] = results

    def _roll_case(self, target, chance):
        """Roll visibility for each thing the target carries."""
        results = {"timestamp": time.time()}

        # Gold
        gold = target.get_gold() if hasattr(target, "get_gold") else 0
        if gold > 0 and random.randint(1, 100) <= chance:
            results["gold_visible"] = True
            results["gold_desc"] = _gold_description(gold)
        else:
            results["gold_visible"] = False
            results["gold_desc"] = ""

        # Resources
        resources_visible = {}
        if hasattr(target, "get_all_resources"):
            for rid, amt in target.get_all_resources().items():
                if amt > 0 and random.randint(1, 100) <= chance:
                    resources_visible[rid] = True
                else:
                    resources_visible[rid] = False
        results["resources_visible"] = resources_visible

        # Inventory items (not equipped)
        items_visible = {}
        for obj in target.contents:
            # Skip equipped items — those are visible via look
            if getattr(obj, "worn", False):
                continue
            if random.randint(1, 100) <= chance:
                items_visible[obj.id] = True
            else:
                items_visible[obj.id] = False
        results["items_visible"] = items_visible

        return results

    def _display_results(self, caller, target, results):
        """Format and display case results to the caller."""
        lines = []

        if results.get("gold_visible"):
            lines.append(f"  {results['gold_desc']}")

        for rid, visible in results.get("resources_visible", {}).items():
            if visible:
                lines.append(f"  some {_resource_name(rid)}")

        for item_id, visible in results.get("items_visible", {}).items():
            if visible:
                # Find the item object to get its display name
                item = None
                for obj in target.contents:
                    if obj.id == item_id:
                        item = obj
                        break
                if item:
                    lines.append(f"  {item.get_display_name(caller)}")

        target_name = target.get_display_name(caller)
        if lines:
            caller.msg(
                f"You carefully study {target_name}...\n"
                f"They appear to be carrying:\n" + "\n".join(lines)
            )
        else:
            caller.msg(
                f"You carefully study {target_name}...\n"
                f"You can't make out what they're carrying."
            )

    # Mastery stubs — not used (func overridden)
    def unskilled_func(self):
        pass

    def basic_func(self):
        pass

    def skilled_func(self):
        pass

    def expert_func(self):
        pass

    def master_func(self):
        pass

    def grandmaster_func(self):
        pass
