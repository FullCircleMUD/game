"""
CombatMob — killable enemy mobs with AI, combat handler, and respawn.
LLMCombatMob — CombatMob + LLM-powered dialogue.

CombatMob is the base class for all hostile/neutral mobs in FCM.
LLMCombatMob extends it with LLMMixin for mobs that can talk
(townspeople, named bosses, fightable guards, etc.).

Both classes extend BaseNPC with:
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

from enums.damage_type import DamageType
from enums.size import Size
from typeclasses.actors.ai_handler import StateMachineAIMixin
from typeclasses.actors.npc import BaseNPC
from typeclasses.mixins.combat_mixin import CombatMixin
from typeclasses.mixins.followable import FollowableMixin
from typeclasses.mixins.fungible_inventory import FungibleInventoryMixin
from typeclasses.mixins.llm_mixin import LLMMixin
from typeclasses.mixins.loot_mob_mixin import LootMobMixin


class CombatMob(CombatMixin, StateMachineAIMixin, FungibleInventoryMixin, FollowableMixin, LootMobMixin, BaseNPC):

    #: Most mobs are animals — a wolf in the dark is "something", not
    #: "Someone". Humanoid mobs set this back, in code or from a spawn rule.
    unseen_name = AttributeProperty("something")
    """
    Base class for killable mobs with AI behavior.

    Overrides BaseNPC defaults:
      - is_immortal = False (can die)
    """

    # ── Override BaseNPC defaults ──
    is_immortal = AttributeProperty(False)

    # ── Spawn/Area ──
    spawn_room_id = AttributeProperty(None)
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

    #: Whether this mob is alive. **Not redundant with ``hp``** — it
    #: serves two purposes, and the first cannot be derived from hp at
    #: all. Keep it.
    #:
    #: **1. The death latch.** It records that death has been
    #: *processed*. ``die()`` zeroes hp itself, so afterwards hp cannot
    #: distinguish "the death pipeline has already run" from "hp just
    #: reached zero". Both ``die()`` implementations open by testing
    #: this and returning early — see ``BaseMob.die`` below and
    #: ``BasePet.die`` — which is what stops a mob corpsing twice and a
    #: pet notifying its owner twice. ``BaseActor.take_damage`` folds it
    #: into its ``already_dead`` guard alongside ``_dying``, the
    #: character-side equivalent: mobs and pets latch on this flag,
    #: characters latch on ``FCMCharacter._dying``, and the ``getattr``
    #: defaults there let one guard serve both. ``Corren`` writes True
    #: back when it refuses a death outright.
    #:
    #: **2. The mob liveness predicate.** Around two dozen sites read it
    #: to decide whether a mob should act: the AI hooks in this class,
    #: ``aggressive_mixin`` (which lists it as a required attribute of
    #: its host in that module's header), ``pack_courage_mixin``,
    #: ``rampage_mixin``, ``mob_followable_mixin``, the mob subclasses,
    #: and ``at_server_startstop`` when deciding which mobs to restart.
    #: Several ask it of *another* object — a wolf about a rabbit, an
    #: urchin about a watchman — so this is a settled second role, not
    #: drift to be tidied away.
    #:
    #: **Declared on mobs only.** A character has no ``is_alive``;
    #: liveness for a PC is ``hp > 0``. Readers that may be handed
    #: either kind of actor therefore need a ``getattr`` default, and
    #: the default they choose decides what happens to characters. The
    #: counter-attack trigger in ``combat_utils`` defaults it **False**
    #: deliberately: ``initiate_attack`` engages by running the
    #: ``attack`` command as the actor, so a mob answering a blow is the
    #: AI acting, while a character answering one would be the server
    #: typing for the player. Failing that test is how a PC is put into
    #: combat on ``hold`` and left to choose. Do not "fix" it to True.
    is_alive = AttributeProperty(True)

    # ── Simple Combat ──
    damage_dice = AttributeProperty("1d4")
    damage_type = AttributeProperty(DamageType.BLUDGEONING)
    attack_message = AttributeProperty("bites")
    attack_delay_min = AttributeProperty(3)
    attack_delay_max = AttributeProperty(6)

    # Initiative speed for mobs — mirrors weapon speed for players.
    # Higher = faster / more agile. Used by roll_initiative() when the
    # combatant has no weapon (animal mobs, unarmed NPCs).
    # Scale: 0 (sluggish) to 4 (lightning fast).
    initiative_speed = AttributeProperty(0)

    # ── Alignment ──
    # Mob's moral alignment: -1000 (Pure Evil) to +1000 (Pure Good).
    # Defaults to 0 (Neutral). Override in subclasses.
    alignment_score = AttributeProperty(0)

    @property
    def alignment(self):
        """Alignment tier derived from score — same as FCMCharacter."""
        from enums.alignment import Alignment
        s = self.alignment_score
        if s >= 700:
            return Alignment.PURE_GOOD
        elif s >= 300:
            return Alignment.GOOD
        elif s > -300:
            return Alignment.NEUTRAL
        elif s > -700:
            return Alignment.EVIL
        return Alignment.PURE_EVIL

    @property
    def alignment_influence(self):
        """Kill impact on the killer's alignment. Derived from mob's alignment."""
        return -(self.alignment_score // 50)

    # ── Aggro ──
    is_aggressive_to_players = AttributeProperty(False)
    aggro_hp_threshold = AttributeProperty(0.5)

    # ── Wander stacking limit ──
    # 0 = unlimited (default). Set to 1 to prevent same-type mobs
    # from wandering into a room that already has one of them.
    max_per_room = AttributeProperty(0)

    # ── Loot ──
    # Loot lives in the spawn rule YAML (mob-spawner library), not on the
    # typeclass. Each rule that wants its mob to drop loot declares the
    # runtime values directly: spawn_resources_max / spawn_gold_max /
    # spawn_scrolls_max / spawn_recipes_max as `attrs`, plus the matching
    # spawn_* tags so the unified-spawn distributor finds the mob.
    # No typeclass defaults, no derivation at creation time.

    # ── XP override ──
    # Optional per-mob XP award. When None, _die uses level * 10 (default
    # progression). Set on subclasses where a flat level-based award
    # doesn't fit — e.g. tier-1 filler mobs that should award less than
    # the formula, or bosses that should award more.
    xp_award = AttributeProperty(None)

    def at_object_creation(self):
        super().at_object_creation()  # CombatMixin adds CmdSetMobCombat + call:false()
        # FungibleInventoryMixin and HumanoidWearslotsMixin init handled
        # by BaseNPC.at_object_creation() conditional hasattr checks.
        if self.location:
            self.spawn_room_id = self.location.id

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
        """Add HP condition line and visible equipment to appearance."""
        text = super().return_appearance(looker, **kwargs)
        condition = self.get_condition_text()
        name = self.get_display_name(looker)
        text = f"{text}\n{name} {condition}"
        # Kit, for mobs that wear any. The renderer lives on the wearslots
        # mixin beside the equipment sheet, so both views answer visibility
        # the same way.
        if hasattr(self, "worn_summary"):
            equip_text = self.worn_summary(looker)
            if equip_text:
                text = f"{text}\n{equip_text}"
        return text

    # ================================================================== #
    #  Ticker Management
    # ================================================================== #

    def start_ai(self):
        """Register with TICKER_HANDLER to start the AI loop.

        Defaults the AI to ``"wander"`` on first start, but respects a
        pre-existing ``ai_state`` attribute. This lets spawn rules
        declare a non-default initial state (e.g. ``ai_state: idle``
        for stationary NPCs) and lets mobs resume their last-known
        state across server restarts.
        """
        if not self.is_alive:
            return
        if not self.attributes.has("ai_state", category="ai_state"):
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
            exi.at_traverse(self, exi.destination)

    def flee_to_random_room(self):
        """Flee to any adjacent room within the mob's area."""
        exi = self.ai.pick_random_exit()
        if exi:
            exi.at_traverse(self, exi.destination, move_type="flee")

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

        # Who we were fighting, read before the move — once we have left
        # the room there is no way to ask. Same shape as flee_from_combat,
        # which is the only other way out of a fight that isn't death.
        handlers = self.scripts.get("combat_handler")
        handler = handlers[0] if handlers else None
        if handler:
            from combat.combat_utils import get_sides
            _, enemies = get_sides(self)
        else:
            enemies = []

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

        # Retreating leaves the fight, so the handler has to go with it —
        # otherwise the mob heals up at the den and wanders off still
        # position="fighting" with a live handler attached. Each enemy is
        # then asked to re-check; _check_stop_combat only ends anything if
        # the room has no enemies left, so a wider brawl carries on.
        if handler:
            handler.stop_combat()
            for enemy in enemies:
                enemy_handlers = enemy.scripts.get("combat_handler")
                if enemy_handlers:
                    enemy_handlers[0]._check_stop_combat()

    # ================================================================== #
    #  Death & Respawn
    # ================================================================== #

    def die(self, cause="unknown", killer=None):
        """
        Handle mob death: stop AI, clean up combat, create corpse,
        award XP to killer, then delete. The mob-spawner library
        observes the population change at its next tick and starts
        any death_cooldown_seconds clock from that observation
        (decision #5: observation, not callback).
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

        # Award XP split among allies on the killer's side
        if killer:
            from combat.combat_utils import get_sides
            allies, _ = get_sides(killer)
            recipients = [
                a for a in allies
                if hasattr(a, "at_gain_experience_points")
            ]
            if not recipients:
                # Fallback if handler already cleaned up
                recipients = [killer] if hasattr(killer, "at_gain_experience_points") else []
            if recipients:
                total_xp = self.xp_award if self.xp_award is not None else self.level * 10
                xp_each = max(1, total_xp // len(recipients))
                for ally in recipients:
                    ally.at_gain_experience_points(xp_each)
                    ally.msg(f"|gYou gain {xp_each} experience.|n")

            # Apply alignment influence to all allies
            influence = self.alignment_influence
            if influence:
                for ally in recipients:
                    if hasattr(ally, "shift_alignment"):
                        ally.shift_alignment(influence)

        # Create corpse with any carried items
        if room:
            self._create_corpse(room, cause)

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

        # Transfer loot to corpse; delete mob equipment.
        # MobItem instances (weapons, armour, consumables) are mob-only
        # and never enter the player economy — deleted on death.
        # Everything else (NFT loot from spawn system, fungibles) transfers.
        from typeclasses.items.mob_items.mob_item import MobItem

        for obj in list(self.contents):
            if isinstance(obj, MobItem):
                obj.delete()
            else:
                obj.move_to(corpse, quiet=True, move_type="teleport")

        # Transfer gold and resources to the corpse
        gold = self.get_gold()
        if gold > 0:
            self.transfer_gold_to(corpse, gold)

        for rid, amt in list(self.get_all_resources().items()):
            if amt > 0:
                self.transfer_resource_to(corpse, rid, amt)

        corpse.start_mob_timers(self.corpse_despawn_delay)

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


class LLMCombatMob(LLMMixin, CombatMob):
    """
    CombatMob with LLM-powered dialogue.

    For mobs that can both fight and talk — townspeople, fightable
    guards, named bosses, or any entity that needs combat + AI wandering
    + LLM conversation.

    LLMMixin is first in MRO so its ``_get_context_variables()`` and
    prompt-building methods take priority. CombatMob provides combat,
    state machine AI, and respawn.

    LLM init is handled by BaseActor's auto-init pattern
    (``at_llm_init`` in the init method list).
    """

    llm_prompt_file = AttributeProperty("roleplay_npc.md")
