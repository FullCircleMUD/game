"""
Pickpocket command — steal items, gold, or resources from a target.

Part of the SUBTERFUGE skill (thief/ninja/bard). Requires casing the
target first (cmd_case). Contested roll: d20 + DEX mod + SUBTERFUGE
mastery bonus vs 10 + target's effective perception bonus.

If HIDDEN when attempting, the thief gets advantage (roll twice, take
best). HIDDEN always breaks after the attempt regardless of outcome.

Failure alerts the target and triggers aggro from aggressive mobs.
Only allowed in combat-enabled rooms (failure starts a fight). Player
targets require a PvP-flagged room.

Usage:
    pickpocket <thing> from <target>
    pp <thing> from <target>
"""

import time

from blockchain.xrpl.currency_cache import get_all_resource_types
from enums.condition import Condition
from enums.mastery_level import MasteryLevel
from enums.skills_enum import skills
from utils.dice_roller import dice
from .cmd_skill_base import CmdSkillBase

# Cooldown per target in seconds
PICKPOCKET_COOLDOWN = 60


class CmdPickpocket(CmdSkillBase):
    """
    Attempt to steal something from a target.

    Usage:
        pickpocket <thing> from <target>
        pp <thing> from <target>

    You must case the target first to see what they carry.
    Stealing requires a skill check against the target's perception.
    Being hidden gives advantage on the roll.

    Failure alerts the target and may start a fight.
    """

    key = "pickpocket"
    aliases = []
    skill = skills.SUBTERFUGE.value
    help_category = "Stealth"

    def func(self):
        caller = self.caller
        room = caller.location

        # ── Parse: <thing> from <target> ──
        if not self.args or " from " not in self.args:
            caller.msg("Usage: pickpocket <thing> from <target>")
            return

        parts = self.args.strip().rsplit(" from ", 1)
        if len(parts) != 2 or not parts[0].strip() or not parts[1].strip():
            caller.msg("Usage: pickpocket <thing> from <target>")
            return

        thing_name = parts[0].strip()
        target_name = parts[1].strip()

        # ── Find target ──
        target = caller.search(target_name)
        if not target:
            return

        # ── Gate checks ──
        if target == caller:
            caller.msg("You can't pickpocket yourself.")
            return

        if not hasattr(target, "hp"):
            caller.msg("You can't pickpocket that.")
            return

        if caller.scripts.get("combat_handler"):
            caller.msg("You can't pickpocket while in combat!")
            return

        if not room or not room.allow_combat:
            caller.msg("You can't pickpocket here.")
            return

        from typeclasses.actors.npc import BaseNPC
        if not isinstance(target, BaseNPC) and not room.allow_pvp:
            caller.msg("You can't pickpocket players here.")
            return

        # Mastery check — UNSKILLED can't pickpocket
        mastery_int = caller.get_skill_mastery(self.skill) if hasattr(caller, 'get_skill_mastery') else 0
        if mastery_int <= 0:
            caller.msg(
                "You have no idea how to pick a pocket. "
                "You need training in subterfuge."
            )
            return

        # Immortal NPCs — don't try
        if getattr(target, "is_immortal", False):
            caller.msg("You wouldn't dare try that.")
            return

        # Must have cased the target first
        case_cache = getattr(caller.ndb, "case_results", None) or {}
        case_entry = case_cache.get(target.id)
        if not case_entry:
            caller.msg("You need to case them first.")
            return

        # Per-target cooldown
        cooldowns = getattr(caller.ndb, "pickpocket_cooldowns", None) or {}
        last_attempt = cooldowns.get(target.id, 0)
        remaining = PICKPOCKET_COOLDOWN - (time.time() - last_attempt)
        if remaining > 0:
            caller.msg(
                f"You need to wait {int(remaining)} seconds before "
                f"trying to pickpocket them again."
            )
            return

        # ── Resolve what to steal ──
        steal_type, steal_target = self._resolve_thing(
            caller, target, thing_name, case_entry
        )
        if steal_type is None:
            return  # message already sent

        # ── Roll ──
        mastery_bonus = MasteryLevel(mastery_int).bonus
        dex_mod = caller.get_attribute_bonus(caller.dexterity)
        total_bonus = dex_mod + mastery_bonus

        is_hidden = caller.has_condition(Condition.HIDDEN)

        # Advantage from HIDDEN or non-combat assist; disadvantage from debuffs
        has_adv = is_hidden or getattr(caller.db, "non_combat_advantage", False)
        has_dis = getattr(caller.db, "non_combat_disadvantage", False)
        roll = dice.roll_with_advantage_or_disadvantage(advantage=has_adv, disadvantage=has_dis)
        caller.db.non_combat_advantage = False
        caller.db.non_combat_disadvantage = False
        roll_detail = f"{roll}(adv)" if (has_adv and not has_dis) else str(roll)

        total = roll + total_bonus
        dc = 10 + target.effective_perception_bonus

        # Always break HIDDEN after attempt
        if is_hidden:
            caller.remove_condition(Condition.HIDDEN)

        # Set cooldown
        if not caller.ndb.pickpocket_cooldowns:
            caller.ndb.pickpocket_cooldowns = {}
        caller.ndb.pickpocket_cooldowns[target.id] = time.time()

        # ── Success ──
        if total >= dc:
            self._apply_steal(
                caller, target, steal_type, steal_target, mastery_bonus,
                roll_detail, total_bonus, total, dc,
            )
        else:
            self._handle_failure(
                caller, target, roll_detail, total_bonus, total, dc
            )

    def _resolve_thing(self, caller, target, thing_name, case_entry):
        """
        Resolve what the thief is trying to steal.

        Returns (steal_type, steal_target) or (None, None) on error.
        steal_type is "gold", "resource", or "item".
        steal_target is None (gold), resource_id (resource), or item obj (item).
        """
        thing_lower = thing_name.lower()

        # Gold
        if thing_lower in ("gold", "coins", "coin", "money"):
            if not case_entry.get("gold_visible"):
                caller.msg("You didn't spot any gold on them.")
                return None, None
            if not hasattr(target, "get_gold") or target.get_gold() <= 0:
                caller.msg("They don't have any gold.")
                return None, None
            return "gold", None

        # Resource — match by name
        if hasattr(target, "get_all_resources"):
            all_resources = get_all_resource_types()
            for rid, info in all_resources.items():
                if info["name"].lower() == thing_lower:
                    vis = case_entry.get("resources_visible", {})
                    if not vis.get(rid):
                        caller.msg(f"You didn't spot any {info['name'].lower()} on them.")
                        return None, None
                    if target.get_resource(rid) <= 0:
                        caller.msg(f"They don't have any {info['name'].lower()}.")
                        return None, None
                    return "resource", rid

        # Item — match by name in target's non-equipped contents
        item_vis = case_entry.get("items_visible", {})
        for obj in target.contents:
            if getattr(obj, "worn", False):
                continue
            if obj.id in item_vis and item_vis[obj.id]:
                if thing_lower in obj.key.lower() or any(
                    thing_lower in alias.lower()
                    for alias in (obj.aliases.all() if hasattr(obj.aliases, "all") else [])
                ):
                    return "item", obj

        caller.msg(f"You didn't spot '{thing_name}' on them.")
        return None, None

    def _apply_steal(self, caller, target, steal_type, steal_target,
                     mastery_bonus, roll_detail, total_bonus, total, dc):
        """Apply a successful steal."""
        target_name = target.get_display_name(caller)

        if steal_type == "gold":
            amount = max(1, dice.roll("1d6") + mastery_bonus)
            amount = min(amount, target.get_gold())
            target.transfer_gold_to(caller, amount)
            caller.msg(
                f"|gYou deftly lift {amount} gold from {target_name}.|n "
                f"(Pickpocket: {roll_detail} + {total_bonus} = {total} vs DC {dc})"
            )

        elif steal_type == "resource":
            rid = steal_target
            amount = max(1, dice.roll("1d4") + (mastery_bonus // 2))
            amount = min(amount, target.get_resource(rid))
            rt = get_all_resource_types().get(rid, {})
            res_name = rt.get("name", f"resource #{rid}").lower()
            target.transfer_resource_to(caller, rid, amount)
            caller.msg(
                f"|gYou deftly lift {amount} {res_name} from {target_name}.|n "
                f"(Pickpocket: {roll_detail} + {total_bonus} = {total} vs DC {dc})"
            )

        elif steal_type == "item":
            item = steal_target
            item_name = item.get_display_name(caller)
            item.move_to(caller, quiet=True)
            caller.msg(
                f"|gYou deftly lift {item_name} from {target_name}.|n "
                f"(Pickpocket: {roll_detail} + {total_bonus} = {total} vs DC {dc})"
            )

    def _handle_failure(self, caller, target, roll_detail, total_bonus,
                        total, dc):
        """Handle a failed pickpocket attempt."""
        target_name = target.get_display_name(caller)
        caller.msg(
            f"|rYour hand slips and you fail to steal anything from "
            f"{target_name}.|n "
            f"(Pickpocket: {roll_detail} + {total_bonus} = {total} vs DC {dc})"
        )

        # Alert target
        target.msg("You feel someone's hand near your belongings!")

        # Room message
        if caller.location:
            caller.location.msg_contents(
                f"$You() $conj(get) caught trying to pickpocket {target_name}!",
                from_obj=caller,
                exclude=[caller, target],
            )

        # Aggressive mob aggro
        if (hasattr(target, "initiate_attack")
                and getattr(target, "is_aggressive_to_players", False)):
            target.initiate_attack(caller)

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
