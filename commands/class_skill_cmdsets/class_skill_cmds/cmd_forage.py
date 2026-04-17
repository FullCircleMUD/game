"""
Forage command — search for food and water in the wilderness using SURVIVALIST.

Druid/Ranger class skill. Two parallel restoration paths:

Hunger: removes hunger levels directly (does NOT produce bread —
maintaining the farming→milling→baking economy). Scaling by mastery:
BASIC=1, SKILLED=2, EXPERT=3, MASTER=4, GM=5 hunger levels restored.
Solo: auto-applies all points to self. Party: interactive prompt.

Water: tops up any water containers in the FORAGER's inventory by N
drinks (same scaling as hunger). Most-empty container filled first,
spilling into others if any drinks remain. If the forager has no water
container, no water credit. Water credit is forager-only — it does NOT
participate in the party allocation prompt. Other party members can
forage their own.

Restrictions:
- Must be in forageable terrain (rural, forest, mountain, etc.)
- 15-minute cooldown (matches survival service interval)
- Does NOT grant hunger_free_pass_tick (bread retains economic advantage)
- Water tops up containers, never bypasses them (canteen/cask economy)

Usage:
    forage
    scavenge
"""

import time

from enums.hunger_level import HungerLevel
from enums.mastery_level import MasteryLevel
from enums.skills_enum import skills
from enums.terrain_type import TerrainType
from .cmd_skill_base import CmdSkillBase

# Terrains where foraging is allowed
FORAGEABLE_TERRAINS = {
    TerrainType.RURAL.value,
    TerrainType.FOREST.value,
    TerrainType.MOUNTAIN.value,
    TerrainType.DESERT.value,
    TerrainType.SWAMP.value,
    TerrainType.COASTAL.value,
    TerrainType.PLAINS.value,
    TerrainType.ARCTIC.value,
}

# Hunger points restored per mastery level
MASTERY_YIELD = {
    MasteryLevel.UNSKILLED.value: 0,
    MasteryLevel.BASIC.value: 1,
    MasteryLevel.SKILLED.value: 2,
    MasteryLevel.EXPERT.value: 3,
    MasteryLevel.MASTER.value: 4,
    MasteryLevel.GRANDMASTER.value: 5,
}

FORAGE_COOLDOWN = 900  # 15 minutes in seconds


class CmdForage(CmdSkillBase):
    key = "forage"
    aliases = []
    skill = skills.SURVIVALIST.value
    help_category = "Nature"

    def func(self):
        """Override base dispatch — forage uses mastery for yield amount."""
        caller = self.caller
        room = caller.location

        # --- Terrain check ---
        terrain = room.get_terrain() if hasattr(room, "get_terrain") else None
        if not terrain or terrain not in FORAGEABLE_TERRAINS:
            caller.msg("There is nothing to forage here.")
            return

        # --- Cooldown check ---
        last_forage = caller.db.last_forage_time or 0
        elapsed = time.time() - last_forage
        if elapsed < FORAGE_COOLDOWN:
            remaining = int(FORAGE_COOLDOWN - elapsed)
            minutes = remaining // 60
            seconds = remaining % 60
            if minutes > 0:
                caller.msg(
                    f"You have already foraged recently. "
                    f"You can forage again in {minutes}m {seconds}s."
                )
            else:
                caller.msg(
                    f"You have already foraged recently. "
                    f"You can forage again in {seconds}s."
                )
            return

        # --- Mastery check ---
        mastery_level = caller.get_skill_mastery(self.skill) if hasattr(caller, 'get_skill_mastery') else 0
        hunger_points = MASTERY_YIELD.get(mastery_level, 0)

        if hunger_points == 0:
            caller.msg(
                "You search around but have no idea what is safe to eat. "
                "You need training in survivalism before you can forage."
            )
            return

        # --- Set cooldown ---
        caller.db.last_forage_time = time.time()

        # --- Determine group ---
        leader = caller.get_group_leader()
        followers = leader.get_followers(same_room=True)
        group = [leader] + followers
        # Only include members in the same room
        group = [m for m in group if m.location == room]

        if len(group) <= 1:
            # Solo — apply all points to self
            self._apply_forage_solo(caller, hunger_points)
        else:
            # Party — interactive allocation
            yield from self._apply_forage_party(caller, group, hunger_points)

    def _apply_forage_solo(self, caller, points):
        """Apply foraged hunger points + water credit to the caller."""
        current = caller.hunger_level
        new_value = min(current.value + points, HungerLevel.FULL.value)
        new_level = HungerLevel(new_value)
        caller.hunger_level = new_level
        # NO hunger_free_pass_tick — bread retains its advantage

        restored = new_value - current.value
        if restored > 0:
            caller.msg(
                f"You forage for edible plants and berries, "
                f"restoring {restored} hunger level{'s' if restored != 1 else ''}."
            )
        else:
            caller.msg(
                "You forage for edible plants and berries, "
                "but you are already full."
            )

        caller.msg(new_level.get_hunger_message())

        # Water credit — top up the forager's containers
        self._distribute_water_to_forager(caller, points)

        # Room message
        if caller.location:
            caller.location.msg_contents(
                "$You() $conj(forage) for food in the surroundings.",
                from_obj=caller, exclude=[caller],
            )

    @staticmethod
    def _distribute_water_to_forager(caller, drinks):
        """
        Top up the caller's water containers by `drinks` total drinks with
        a forage-flavoured summary message. Delegates the actual fill logic
        to `distribute_water_to_containers` so forage and spell callers
        share the same most-empty-first semantics.

        No-op (silent) if the caller carries no water containers — keeps
        the forage output uncluttered for non-water-carriers.
        """
        from typeclasses.mixins.water_container import (
            distribute_water_to_containers,
        )

        drinks_added, topped_up = distribute_water_to_containers(caller, drinks)

        if drinks_added > 0:
            if len(topped_up) == 1:
                container, added = topped_up[0]
                caller.msg(
                    f"You spot a clear stream and top up {container.key} "
                    f"({added} drink{'s' if added != 1 else ''})."
                )
            else:
                summary = ", ".join(
                    f"{c.key} (+{added})" for c, added in topped_up
                )
                caller.msg(
                    f"You spot a clear stream and top up your water "
                    f"containers: {summary}."
                )

        return drinks_added

    def _apply_forage_party(self, caller, group, total_points):
        """Interactive prompt to allocate hunger points across the group."""
        # Show party status
        lines = [
            f"You forage enough food to restore |w{total_points}|n hunger "
            f"level{'s' if total_points != 1 else ''}.",
            "",
            "|cYour group:|n",
        ]
        for member in group:
            hunger_name = member.hunger_level.name.lower()
            lines.append(f"  |w{member.key}|n — {hunger_name}")

        lines.append("")
        lines.append(
            "Allocate points (e.g. |wbob 2 alice 1|n) or |wall|n to "
            "distribute evenly:"
        )
        caller.msg("\n".join(lines))

        # Get response
        response = yield ("Enter allocation: ")
        if not response:
            # No response — auto-apply to self
            self._apply_forage_solo(caller, total_points)
            return

        response = response.strip().lower()

        # "all" — distribute evenly
        if response == "all":
            self._distribute_evenly(caller, group, total_points)
            return

        # Parse name/amount pairs
        allocations = self._parse_allocations(caller, group, response, total_points)
        if allocations is None:
            return  # error already messaged

        # Apply allocations
        for member, points in allocations.items():
            current = member.hunger_level
            new_value = min(current.value + points, HungerLevel.FULL.value)
            new_level = HungerLevel(new_value)
            member.hunger_level = new_level
            # NO hunger_free_pass_tick

            restored = new_value - current.value
            if member == caller:
                if restored > 0:
                    caller.msg(
                        f"You eat some foraged food, restoring {restored} "
                        f"hunger level{'s' if restored != 1 else ''}."
                    )
                else:
                    caller.msg("You are already full.")
                caller.msg(new_level.get_hunger_message())
            else:
                if restored > 0:
                    member.msg(
                        f"{caller.key} shares some foraged food with you, "
                        f"restoring {restored} hunger "
                        f"level{'s' if restored != 1 else ''}."
                    )
                    member.msg(new_level.get_hunger_message())
                    caller.msg(
                        f"You share foraged food with {member.key} "
                        f"({restored} level{'s' if restored != 1 else ''})."
                    )
                else:
                    caller.msg(f"{member.key} is already full.")

        # Water credit — only the forager's own containers are topped up.
        # Other party members must forage their own water.
        self._distribute_water_to_forager(caller, total_points)

        # Room message
        if caller.location:
            caller.location.msg_contents(
                "$You() $conj(forage) for food and $conj(share) it with "
                "the group.",
                from_obj=caller, exclude=[caller],
            )

    def _distribute_evenly(self, caller, group, total_points):
        """Distribute points as evenly as possible across the group."""
        base = total_points // len(group)
        remainder = total_points % len(group)

        allocations = {}
        for i, member in enumerate(group):
            points = base + (1 if i < remainder else 0)
            if points > 0:
                allocations[member] = points

        # Apply
        for member, points in allocations.items():
            current = member.hunger_level
            new_value = min(current.value + points, HungerLevel.FULL.value)
            new_level = HungerLevel(new_value)
            member.hunger_level = new_level

            restored = new_value - current.value
            if member == caller:
                if restored > 0:
                    caller.msg(
                        f"You eat some foraged food, restoring {restored} "
                        f"hunger level{'s' if restored != 1 else ''}."
                    )
                caller.msg(new_level.get_hunger_message())
            else:
                if restored > 0:
                    member.msg(
                        f"{caller.key} shares some foraged food with you, "
                        f"restoring {restored} hunger "
                        f"level{'s' if restored != 1 else ''}."
                    )
                    member.msg(new_level.get_hunger_message())

        # Water credit — forager's containers only.
        self._distribute_water_to_forager(caller, total_points)

        if caller.location:
            caller.location.msg_contents(
                "$You() $conj(forage) for food and $conj(share) it with "
                "the group.",
                from_obj=caller, exclude=[caller],
            )

    def _parse_allocations(self, caller, group, text, total_points):
        """
        Parse 'bob 2 alice 1' into {member: points} dict.
        Returns None on error (error already messaged to caller).
        """
        tokens = text.split()
        if len(tokens) % 2 != 0:
            caller.msg(
                "Invalid format. Use: |wname amount name amount|n "
                "(e.g. |wbob 2 alice 1|n)"
            )
            return None

        # Build a lookup of group members by lowercase key
        member_lookup = {m.key.lower(): m for m in group}

        allocations = {}
        points_used = 0

        for i in range(0, len(tokens), 2):
            name = tokens[i]
            try:
                amount = int(tokens[i + 1])
            except ValueError:
                caller.msg(f"'{tokens[i + 1]}' is not a valid number.")
                return None

            if amount < 0:
                caller.msg("You can't allocate negative points.")
                return None

            if amount == 0:
                continue

            member = member_lookup.get(name)
            if not member:
                caller.msg(f"'{name}' is not in your group here.")
                return None

            if member in allocations:
                allocations[member] += amount
            else:
                allocations[member] = amount
            points_used += amount

        if points_used > total_points:
            caller.msg(
                f"You only foraged {total_points} point"
                f"{'s' if total_points != 1 else ''}, "
                f"but tried to allocate {points_used}."
            )
            return None

        return allocations

    # Mastery level stubs — not used (func() overridden above)
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
