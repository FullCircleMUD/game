"""
CombatMob — killable enemy mobs with AI, combat handler, and respawn.

Base class for all hostile/neutral mobs in FCM. Extends BaseNPC with:
  - AI state machine (via StateMachineAIMixin)
  - TICKER_HANDLER-driven AI loop
  - Combat via shared execute_attack() — same path as players
  - Death + timed respawn
  - Area-restricted wandering

Mobs use the same command interface as players (CmdAttack via
CmdSetMobCombat). AI state methods call execute_cmd("attack target")
which creates a combat handler and queues repeating attacks.

Subclasses define:
  - ai_<state>() methods for specific behavior
  - at_new_arrival() for room entry reactions
  - Combat stats (damage_dice, attack_message, etc.)
"""

import random

from evennia import TICKER_HANDLER
from evennia.typeclasses.attributes import AttributeProperty
from evennia.utils.utils import delay

from typeclasses.actors.ai_handler import StateMachineAIMixin
from typeclasses.actors.npc import BaseNPC
from typeclasses.mixins.combat_mixin import CombatMixin


class CombatMob(CombatMixin, StateMachineAIMixin, BaseNPC):
    """
    Base class for killable mobs with AI behavior.

    Overrides BaseNPC defaults:
      - is_immortal = False (can die)
      - is_unique = False (can respawn)
    """

    # ── Override BaseNPC defaults ──
    is_immortal = AttributeProperty(False)
    is_unique = AttributeProperty(False)

    # ── Spawn/Area ──
    spawn_room_id = AttributeProperty(None)
    respawn_delay = AttributeProperty(60)
    corpse_despawn_delay = AttributeProperty(300)  # 5 minutes

    @property
    def area_tag(self):
        """Read area_tag from mob_area tag (indexed, used by AI wander + spawn counting)."""
        tags = self.tags.get(category="mob_area", return_list=True)
        return tags[0] if tags else None

    @area_tag.setter
    def area_tag(self, value):
        """Set area_tag as a mob_area tag. Clears old tag first."""
        self.tags.clear(category="mob_area")
        if value:
            self.tags.add(value, category="mob_area")

    # ── AI ──
    ai_tick_interval = AttributeProperty(10)
    is_alive = AttributeProperty(True)

    # ── Size (override in subclasses for large/huge mobs) ──
    # Stored as string value, not enum — Evennia can't serialize str enums.
    # Use ActorSize("medium") to convert back when needed.
    size = AttributeProperty("medium")

    # ── Simple Combat ──
    damage_dice = AttributeProperty("1d4")
    attack_message = AttributeProperty("bites")
    attack_delay_min = AttributeProperty(3)
    attack_delay_max = AttributeProperty(6)

    # Initiative speed for mobs — mirrors weapon speed for players.
    # Higher = faster / more agile. Used by roll_initiative() when the
    # combatant has no weapon (animal mobs, unarmed NPCs).
    # Scale: 0 (sluggish) to 4 (lightning fast).
    initiative_speed = AttributeProperty(0)

    # ── Aggro ──
    is_aggressive_to_players = AttributeProperty(False)
    aggro_hp_threshold = AttributeProperty(0.5)

    # ── Wander stacking limit ──
    # 0 = unlimited (default). Set to 1 to prevent same-type mobs
    # from wandering into a room that already has one of them.
    max_per_room = AttributeProperty(0)

    # ── Loot resources ──
    # Dict of {resource_id (int): max_amount (int)} defining which resources
    # this mob can carry as loot. The spawn system fills mobs up to these
    # caps over time. On death, all resources transfer to the corpse.
    # Override in subclasses (e.g. Wolf: {8: 1} for 1 hide).
    loot_resources = AttributeProperty({})

    # ── Gold loot ──
    # Max gold this mob can carry as loot. 0 = no gold.
    # Override in intelligent mob subclasses (kobolds, gnolls, etc.).
    # Animals (wolves, rabbits) should not carry gold.
    loot_gold_max = AttributeProperty(0)

    # ── Knowledge loot ──
    # Per-tier max dicts for scroll/recipe capacity. Empty = no scrolls/recipes.
    # Override in intelligent mob subclasses with explicit tier dicts, e.g.:
    #   spawn_scrolls_max = AttributeProperty({"basic": 1})
    # At-or-below filtering: a "basic" slot accepts basic-tier scrolls only,
    # a "skilled" slot accepts basic or skilled, etc.
    spawn_scrolls_max = AttributeProperty({})
    spawn_recipes_max = AttributeProperty({})

    def at_object_creation(self):
        super().at_object_creation()  # CombatMixin adds CmdSetMobCombat + call:false()
        if self.location:
            self.spawn_room_id = self.location.id

        # Unified spawn system: tag for target pooling, max dict for headroom.
        if self.loot_resources:
            self.tags.add("spawn_resources", category="spawn_resources")
            self.db.spawn_resources_max = dict(self.loot_resources)

        # Gold loot: plain int capacity.
        if self.loot_gold_max > 0:
            self.tags.add("spawn_gold", category="spawn_gold")
            self.db.spawn_gold_max = self.loot_gold_max

        # Knowledge loot: builder-set per-tier max dicts.
        if self.spawn_scrolls_max:
            self.tags.add("spawn_scrolls", category="spawn_scrolls")
            self.db.spawn_scrolls_max = dict(self.spawn_scrolls_max)
        if self.spawn_recipes_max:
            self.tags.add("spawn_recipes", category="spawn_recipes")
            self.db.spawn_recipes_max = dict(self.spawn_recipes_max)

    # ================================================================== #
    #  Appearance — HP condition when looked at
    # ================================================================== #

    def get_condition_text(self):
        """Return a coloured condition string based on HP percentage."""
        if not self.is_alive:
            return "|xis dead.|n"
        hp_max = self.hp_max or 1
        ratio = self.hp / hp_max
        if ratio >= 1.0:
            return "|gis in perfect condition.|n"
        elif ratio >= 0.75:
            return "|ghas a few minor scratches.|n"
        elif ratio >= 0.50:
            return "|yhas some cuts and bruises.|n"
        elif ratio >= 0.25:
            return "|yis bleeding from several wounds.|n"
        elif ratio >= 0.10:
            return "|ris badly wounded and struggling to stand.|n"
        else:
            return "|ris on the verge of death!|n"

    def return_appearance(self, looker, **kwargs):
        """Add HP condition line to the default appearance."""
        text = super().return_appearance(looker, **kwargs)
        condition = self.get_condition_text()
        name = self.get_display_name(looker)
        return f"{text}\n{name} {condition}"

    # ================================================================== #
    #  Ticker Management
    # ================================================================== #

    def start_ai(self):
        """Register with TICKER_HANDLER to start the AI loop."""
        if not self.is_alive:
            return
        self.ai.set_state("wander")
        TICKER_HANDLER.add(
            interval=self.ai_tick_interval,
            callback=self.ai_tick,
            idstring=f"mob_ai_{self.id}",
        )

    def stop_ai(self):
        """Unregister from TICKER_HANDLER."""
        try:
            TICKER_HANDLER.remove(
                interval=self.ai_tick_interval,
                callback=self.ai_tick,
                idstring=f"mob_ai_{self.id}",
            )
        except KeyError:
            pass  # ticker already removed

    def ai_tick(self, *args, **kwargs):
        """Called every ai_tick_interval seconds. Dispatches to current state."""
        if not self.is_alive:
            return
        self.ai.run()

    # ================================================================== #
    #  Room Notification
    # ================================================================== #

    def at_new_arrival(self, arriving_obj):
        """
        Called by RoomBase.at_object_receive() when something enters
        the mob's room. Override in subclasses for specific reactions.
        """
        pass

    # ================================================================== #
    #  Simple Combat
    # ================================================================== #

    # Backward-compat alias — callers should migrate to initiate_attack().
    mob_attack = CombatMixin.initiate_attack

    def _roll_damage(self):
        """Roll damage from damage_dice string like '1d4' or '2d6'."""
        parts = self.damage_dice.split("d")
        num_dice = int(parts[0])
        die_size = int(parts[1])
        return sum(random.randint(1, die_size) for _ in range(num_dice))

    # ================================================================== #
    #  Kill Hook
    # ================================================================== #

    def at_kill(self, victim):
        """Called when this mob kills something. Override for special behavior."""
        pass

    # hp_fraction and is_low_health are provided by CombatMixin

    # ================================================================== #
    #  Movement
    # ================================================================== #

    def wander(self):
        """Move to a random adjacent room within the mob's area."""
        if self.max_per_room > 0:
            my_type = type(self)
            exits = [
                exi for exi in self.ai.get_area_exits()
                if sum(1 for obj in exi.destination.contents
                       if type(obj) is my_type) < self.max_per_room
            ]
            exi = random.choice(exits) if exits else None
        else:
            exi = self.ai.pick_random_exit()
        if exi:
            self.move_to(exi.destination, quiet=False)

    def flee_to_random_room(self):
        """Flee to any adjacent room within the mob's area."""
        exi = self.ai.pick_random_exit()
        if exi:
            self.move_to(exi.destination, quiet=False)

    def retreat_to_spawn(self):
        """Move directly to spawn room (teleport, for retreat behavior)."""
        if not self.spawn_room_id:
            return
        from evennia import ObjectDB
        try:
            spawn_room = ObjectDB.objects.get(id=self.spawn_room_id)
        except ObjectDB.DoesNotExist:
            return

        if self.location == spawn_room:
            return

        if self.location:
            self.location.msg_contents(
                f"{self.key} retreats, wounded!",
                from_obj=self, exclude=[self],
            )
        self.move_to(spawn_room, quiet=True)
        if spawn_room:
            spawn_room.msg_contents(
                f"{self.key} arrives, looking wounded.",
                from_obj=self, exclude=[self],
            )

    # ================================================================== #
    #  Death & Respawn
    # ================================================================== #

    def die(self, cause="unknown", killer=None):
        """
        Handle mob death: stop AI, clean up combat, create corpse,
        award XP to killer.

        Common mobs (is_unique=False) are deleted — the ZoneSpawnScript
        handles respawning fresh objects. Unique mobs use the legacy
        delay-based _respawn() path.
        """
        if not self.is_alive:
            return  # already dead

        self.hp = 0
        self.is_alive = False
        self.stop_ai()

        # Clean up combat handler if present
        self.exit_combat()

        room = self.location  # capture before removing from world

        if room:
            room.msg_contents(
                f"|r{self.key} has been slain!|n",
                from_obj=self, exclude=[self],
            )
        self._death_cry()

        # Award XP to killer (10 per mob level)
        if killer and hasattr(killer, "at_gain_experience_points"):
            xp = self.level * 10
            killer.at_gain_experience_points(xp)
            killer.msg(f"|gYou gain {xp} experience.|n")

        # Create corpse with any carried items
        if room:
            self._create_corpse(room, cause)

        if self.is_unique:
            # Unique/boss mobs: park in limbo and respawn the same object
            self.location = None
            delay(self.respawn_delay, self._respawn)
        else:
            # Common mobs: delete — ZoneSpawnScript spawns a replacement
            self.delete()

    def _create_corpse(self, room, cause):
        """Create a lootable corpse and transfer all contents to it."""
        from evennia.utils.create import create_object
        from typeclasses.world_objects.corpse import Corpse

        # key="corpse" (not "corpse of {name}") so that searching for the
        # mob's name (e.g. "kill rat") doesn't match the corpse.  The full
        # display name "corpse of ..." comes from get_display_name() which
        # reads owner_name, and the loot command finds corpses via isinstance.
        corpse = create_object(
            Corpse,
            key="corpse",
            location=room,
        )
        corpse.owner_character_key = None
        corpse.owner_name = self.key
        corpse.cause_of_death = cause

        # Height transfer: flying mob's corpse falls to ground, underwater stays at depth
        actor_height = self.room_vertical_position
        if actor_height > 0:
            corpse.room_vertical_position = 0
            if room:
                room.msg_contents(
                    f"The corpse of {self.key} falls to the ground.",
                    from_obj=corpse,
                )
        elif actor_height < 0:
            corpse.room_vertical_position = actor_height

        # Unequip worn items first (future-proofing for mobs with wearslots)
        if hasattr(self, "get_all_worn"):
            for item in list(self.get_all_worn().values()):
                if item is not None:
                    self.remove(item)

        # Transfer all contents (items carried by the mob) to the corpse
        for obj in list(self.contents):
            obj.move_to(corpse, quiet=True, move_type="teleport")

        # Transfer gold and resources to the corpse
        gold = self.get_gold()
        if gold > 0:
            self.transfer_gold_to(corpse, gold)

        for rid, amt in list(self.get_all_resources().items()):
            if amt > 0:
                self.transfer_resource_to(corpse, rid, amt)

        corpse.start_mob_timers(self.corpse_despawn_delay)

    def _respawn(self):
        """Respawn at the spawn room after the delay."""
        if not self.pk:
            return  # object was deleted

        if not self.spawn_room_id:
            return

        from evennia import ObjectDB
        try:
            spawn_room = ObjectDB.objects.get(id=self.spawn_room_id)
        except ObjectDB.DoesNotExist:
            return

        # Reset stats
        self.hp = self.hp_max
        self.is_alive = True

        # Move to spawn room
        self.move_to(spawn_room, quiet=True)
        if spawn_room:
            spawn_room.msg_contents(
                f"A {self.key} appears.",
                from_obj=self, exclude=[self],
            )

        # Restart AI
        self.start_ai()

    # ================================================================== #
    #  Default AI States
    # ================================================================== #

    def ai_idle(self):
        """Default idle state — do nothing, wait for stimulus."""
        pass

    def ai_wander(self):
        """Default wander state — randomly move within area."""
        if random.random() < 0.3:
            self.wander()

    def ai_dead(self):
        """Dead state — do nothing (respawn handled by delay)."""
        pass
