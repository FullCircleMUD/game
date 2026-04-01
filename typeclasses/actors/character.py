
from evennia.utils.create import create_object
from evennia.utils.utils import delay

from enums.condition import Condition
from enums.death_cause import DeathCause
from enums.hunger_level import HungerLevel
from enums.alignment import Alignment
from typeclasses.actors.races import Race
from typeclasses.actors.base_actor import BaseActor
from typeclasses.mixins.carrying_capacity import CarryingCapacityMixin
from typeclasses.mixins.fungible_inventory import FungibleInventoryMixin
from evennia.typeclasses.attributes import AttributeProperty

from enums.mastery_level import MasteryLevel

from typeclasses.mixins.followable import FollowableMixin
from typeclasses.mixins.player_preferences import PlayerPreferencesMixin
from typeclasses.mixins.recipe_book import RecipeBookMixin
from typeclasses.mixins.remort import RemortMixin
from typeclasses.mixins.spellbook import SpellbookMixin
from typeclasses.mixins.wearslots.humanoid_wearslots import HumanoidWearslotsMixin
from typeclasses.mixins.combat_mixin import CombatMixin

from evennia.utils.utils import lazy_property

# THE COMMANDS IN HERE WERE ADDED INTO THE GAMES DEFAULT CHARACTER COMMAND SET DIRECTLY
#from commands.all_char_cmds.cmdset_all_chars import CmdSetAllChars

from utils.experience_table import EXPERIENCE_TABLE, get_xp_for_next_level, get_xp_gap

class FCMCharacter(
    CombatMixin,
    CarryingCapacityMixin,
    FollowableMixin,
    FungibleInventoryMixin,
    HumanoidWearslotsMixin,
    PlayerPreferencesMixin,
    RecipeBookMixin,
    SpellbookMixin,
    RemortMixin,
    BaseActor  # now includes EffectsManagerMixin + DamageResistanceMixin
    ):

    is_pc = True  # Convention — distinguishes player characters from NPCs/mobs

    # point_buy, num_remorts, and bonus_*_per_level are in RemortMixin

    #########################################################
    # Player-specific attributes
    #########################################################

    alignment = AttributeProperty(Alignment.TRUE_NEUTRAL)  # Character's moral alignment (e.g., "Good", "Evil", "Neutral")

    race = AttributeProperty(Race.HUMAN)

    experience_points = AttributeProperty(0)  # Total experience points accumulated by the character

    # all levels spent on all classes combined
    total_level = AttributeProperty(1)  # Total character level, calculated from class levels
    highest_xp_level_earned = AttributeProperty(1)  # Highest level reached via XP (prevents duplicate rewards)

    # levels achieved but not yet spent on a class
    levels_to_spend = AttributeProperty(0)  # Levels available to spend on leveling up

    # used in hunger system, tracks how hungry characer is.
    hunger_level = AttributeProperty(HungerLevel.FULL)

    # need to see how timers work in evennia to see if hunger free tick pass
    # is actually needed.

    #This is a mechanism to allow that when a character eats to full,
    # they don't drop to satisfied a second later
    # if they have bad luck with timing the cycle processing
    # other wise drop one level per hunger cycle
    # after a character gets set to full, this gets set to true and
    # on the next hunger cycle it gets set to false
    # and from then on all hunger processing is normal
    hunger_free_pass_tick: bool = False

    # need to think through how banks will work
    # bank_contents: Optional[BankContents] = Field(default=None, exclude=True)

    # skill points available to be spent on general or weapon skills
    # class specific skill points are tracked within the class data
    general_skill_pts_available = AttributeProperty(0)
    weapon_skill_pts_available = AttributeProperty(0)

    # holds an instance of NFTPet
    active_pet = AttributeProperty(None)
    #holds an instance of NFTMount
    active_mount = AttributeProperty(None)

    # ── Group / Follow system ──
    # following, nofollow, get_group_leader(), get_followers() from FollowableMixin
    # nofollow also in PlayerPreferencesMixin (player-facing toggle)

    # ── Combat preferences ──
    wimpy_threshold = AttributeProperty(0)  # 0 = disabled, >0 = auto-flee HP

    # ── Prompt ──
    # Tokens: %h=HP, %H=maxHP, %m=Mana, %M=maxMana, %v=Move, %V=maxMove,
    #         %g=Gold, %x=XP, %l=Level
    prompt_format = AttributeProperty("%hH %mM %vV > ")

    # ── Death / respawn ──
    # respawn_location: where the character goes after death (set by cemetery
    #   'bind' command). Default: Millholm Cemetery.
    # home: Evennia built-in. Where the character goes on recall (future).
    #   Default: Harvest Moon Inn. Also used as defeat fallback (non-lethal).
    # Fallback chain on death: respawn_location → home → Limbo.
    respawn_location = AttributeProperty(None)

    # ── Quest handler ──

    @lazy_property
    def quests(self):
        from world.quests.quest_handler import FCMQuestHandler
        return FCMQuestHandler(self)

    def at_pre_move(self, destination, move_type="move", **kwargs):
        """Check movement blockers before moving."""
        if getattr(self, "afk", False) and move_type in ("move", "follow"):
            self.msg("|yReminder: You are currently flagged as AFK.|n")
        if self.ndb.is_processing:
            self.msg("You can't leave in the middle of a job! Wait for it to finish.")
            return False
        pos = getattr(self, "position", "standing")
        if pos not in ("standing", "fighting"):
            self.msg("You need to stand up first!")
            return False
        if self.location and hasattr(self.location, "check_pre_leave"):
            allowed, msg = self.location.check_pre_leave(self, destination)
            if not allowed:
                if msg:
                    self.msg(msg)
                return False
        # Movement point cost — normal moves, follows, and exit traversals
        if move_type in ("move", "follow", "traverse") and self.move < 1:
            self.msg("You are too exhausted to move.")
            return False
        return super().at_pre_move(destination, move_type=move_type, **kwargs)

    def at_post_move(self, source_location, move_type="move", **kwargs):
        """Deduct movement and auto-move followers when this character moves."""
        super().at_post_move(source_location, move_type=move_type, **kwargs)

        # Deduct 1 movement point for normal moves, follows, and exit traversals
        if move_type in ("move", "follow", "traverse"):
            self.move = max(0, self.move - 1)

        # Breath timer — start if we moved into underwater without one
        if self.room_vertical_position < 0:
            if not self.has_condition(Condition.WATER_BREATHING):
                self.start_breath_timer()
        else:
            # Surfaced or on land — stop any running timer
            self.stop_breath_timer()

        # HIDDEN movement check — stealth vs best perceiver on room entry
        if self.has_condition(Condition.HIDDEN) and self.location:
            self._check_hidden_on_entry()

        # Passive trap detection on room entry
        if self.location:
            self._check_traps_on_entry()

        # Notify LLM NPCs of player arrival
        if self.location and getattr(self, "is_pc", False):
            for obj in self.location.contents:
                if obj != self and hasattr(obj, "at_llm_player_arrive"):
                    obj.at_llm_player_arrive(self)

        # District map auto-creation for cartographers
        if self.location and getattr(self, "is_pc", False):
            self._check_map_autocreation()

        # Don't cascade followers on follow moves or teleports.
        # Teleport suppression prevents followers auto-following into
        # dungeons, death respawns, etc. Group dungeon entry explicitly
        # collects and moves followers instead.
        if move_type in ("follow", "teleport"):
            return
        if not source_location:
            return
        # Collect ALL followers in the chain (direct + indirect) who are
        # in the source room, and move them all with move_type="follow"
        # so they don't trigger further cascades.
        all_followers = self.get_followers(same_room=False)
        for f in all_followers:
            if f.location == source_location:
                f.msg(f"You follow {self.get_display_name(f)}.")
                f.move_to(self.location, move_type="follow")

    # ── HIDDEN movement check ──

    def _check_hidden_on_entry(self):
        """
        Roll stealth vs best passive perceiver in the current room.

        Called on room entry while HIDDEN. Success = stay hidden.
        Fail = revealed with appropriate messages.
        """
        room = self.location
        best_dc = 0
        for obj in room.contents:
            if obj == self:
                continue
            if not hasattr(obj, "effective_perception_bonus"):
                continue
            score = 10 + obj.effective_perception_bonus
            if score > best_dc:
                best_dc = score

        if best_dc <= 0:
            # Empty room — auto-succeed
            self.msg("|gYou slip in unnoticed.|n")
            return

        from utils.dice_roller import dice
        has_adv = getattr(self.db, "non_combat_advantage", False)
        has_dis = getattr(self.db, "non_combat_disadvantage", False)
        roll = dice.roll_with_advantage_or_disadvantage(advantage=has_adv, disadvantage=has_dis)
        self.db.non_combat_advantage = False
        self.db.non_combat_disadvantage = False
        stealth = self.effective_stealth_bonus
        total = roll + stealth

        if total >= best_dc:
            self.msg(
                f"|gYou slip in unnoticed.|n "
                f"(Stealth: {roll} + {stealth} = {total} vs DC {best_dc})"
            )
        else:
            self.remove_condition(Condition.HIDDEN)
            self.msg(
                f"|rYou are spotted!|n "
                f"(Stealth: {roll} + {stealth} = {total} vs DC {best_dc})"
            )
            room.msg_contents(
                f"{self.key} slips into the room but is spotted!",
                exclude=[self],
                from_obj=self,
            )

    # ── Passive trap detection ──

    def _check_traps_on_entry(self):
        """
        Passive perception check for traps on room entry.

        Checks all objects, exits, and the room itself for armed,
        undetected traps. If passive perception (10 + bonus) meets
        or exceeds the trap's find_dc, the trap is auto-detected.

        True Sight at EXPERT+ tier auto-detects all traps regardless
        of perception (magical sight pierces all concealment).
        """
        room = self.location
        passive_dc = 10 + self.effective_perception_bonus

        # True Sight EXPERT+ or Holy Sight SKILLED+ auto-detects traps
        true_sight_detects_traps = (
            (self.has_effect("true_sight")
             and (self.db.true_sight_tier or 0) >= 3)  # True Sight EXPERT+
            or (self.has_effect("holy_sight")
                and (self.db.holy_sight_tier or 0) >= 2)  # Holy Sight SKILLED+
        )

        # Check objects and exits in the room
        for obj in list(room.contents) + list(room.exits):
            if (
                hasattr(obj, "is_trapped")
                and obj.is_trapped
                and hasattr(obj, "trap_armed")
                and obj.trap_armed
                and hasattr(obj, "trap_detected")
                and not obj.trap_detected
                and (true_sight_detects_traps or passive_dc >= obj.trap_find_dc)
            ):
                obj.detect_trap(self)

        # Check room itself (pressure plates)
        if (
            hasattr(room, "is_trapped")
            and room.is_trapped
            and hasattr(room, "trap_armed")
            and room.trap_armed
            and hasattr(room, "trap_detected")
            and not room.trap_detected
            and (true_sight_detects_traps or passive_dc >= room.trap_find_dc)
        ):
            room.detect_trap(self)

    # ── District map auto-creation ────────────────────────────────────

    def _check_map_autocreation(self):
        """
        Spawn a blank district map NFT when entering a tagged room
        without that map in inventory.

        Only fires for characters with CARTOGRAPHY BASIC+.
        """
        from enums.mastery_level import MasteryLevel
        from enums.skills_enum import skills
        from world.cartography.map_registry import get_map_keys_for_room

        mastery_levels = self.db.general_skill_mastery_levels or {}
        cart_level = mastery_levels.get(skills.CARTOGRAPHY.value, 0)
        if cart_level < MasteryLevel.BASIC.value:
            return

        for map_key, _point_key in get_map_keys_for_room(self.location):
            if not self._get_map_from_inventory(map_key):
                self._spawn_blank_map(map_key)

    def _spawn_blank_map(self, map_key):
        """Create a blank DistrictMapNFTItem and place it in this character's inventory."""
        from typeclasses.items.base_nft_item import BaseNFTItem
        from world.cartography.map_registry import get_map

        map_def = get_map(map_key)
        display_name = map_def["display_name"] if map_def else map_key

        try:
            token_id = BaseNFTItem.assign_to_blank_token("DistrictMap")
        except Exception:
            return  # No blank tokens available or DistrictMap type missing

        obj = BaseNFTItem.spawn_into(token_id, self)
        if obj is None:
            return

        obj.map_key = map_key
        obj.key = f"map of {display_name}".lower()
        obj.db.surveyed_points = set()
        self.msg(f"|gA blank map of {display_name} materialises in your pack.|n")

    def _get_map_from_inventory(self, map_key):
        """Return the first DistrictMapNFTItem in inventory with matching map_key, or None."""
        from typeclasses.items.maps.district_map_nft_item import DistrictMapNFTItem
        for item in self.contents:
            if isinstance(item, DistrictMapNFTItem) and item.map_key == map_key:
                return item
        return None

    #########################################################
    # Character death
    #########################################################


    #########################################################
    # UI Display settings — see PlayerPreferencesMixin
    #########################################################

    # ================================================================== #
    #  Level override — players use total_level for stat calculations
    # ================================================================== #

    def get_level(self):
        return self.total_level

    def search(self, searchdata, **kwargs):
        """
        Extended search with substring fallback after Evennia's built-in matching.

        Cascade:
        1. Evennia's built-in matching (exact match + word-start prefix)
        2. Substring fallback — matches term anywhere in key or aliases

        Skips substring fallback if exact=True or searchdata is not a string.

        Extra kwargs:
            exclude_worn (bool): If True, worn/equipped items are filtered
                from results. Use for disposal commands (drop, give, deposit)
                so equipped items don't appear in disambiguation lists.
            only_worn (bool): If True, only worn/equipped items are returned.
                Use for the remove command.
        """
        exclude_worn = kwargs.pop("exclude_worn", False)
        only_worn = kwargs.pop("only_worn", False)

        if kwargs.get("exact") or not isinstance(searchdata, str):
            return super().search(searchdata, **kwargs)

        caller_quiet = kwargs.get("quiet", False)

        # Step 1: Evennia's full matching (exact=False)
        results = super().search(
            searchdata, **{**kwargs, "exact": False, "quiet": True}
        )

        if not results:
            # Step 2: Substring fallback on candidates
            candidates = kwargs.get("candidates")
            if candidates is None:
                candidates = self.get_search_candidates(searchdata, **kwargs)
            if candidates:
                term = searchdata.lower()
                results = [
                    obj
                    for obj in candidates
                    if term in obj.key.lower()
                    or any(term in a.lower() for a in obj.aliases.all())
                ]
                if kwargs.get("use_locks", True):
                    results = [
                        x
                        for x in results
                        if x.access(self, "search", default=True)
                    ]

        # Filter out worn/equipped items when requested
        if exclude_worn and results:
            unworn = [obj for obj in results if not self.is_worn(obj)]
            if not unworn:
                # All matches were worn — give a helpful message
                if not caller_quiet:
                    self.msg(f"You must remove {results[0].key} first.")
                    return None
                return []
            results = unworn

        # Filter to only worn/equipped items when requested
        if only_worn and results:
            worn = [obj for obj in results if self.is_worn(obj)]
            if not worn:
                if not caller_quiet:
                    self.msg("You are not wearing that.")
                    return None
                return []
            results = worn

        # Handle stacked results if applicable
        stacked = kwargs.get("stacked", 0)
        if stacked and len(results) > 1:
            is_stacked, results = self.get_stacked_results(results, **kwargs)
            if is_stacked:
                return results

        if caller_quiet:
            return results
        return self.handle_search_results(searchdata, results, **kwargs)

    # ── Encumbrance consequences (buff expiry / item removal) ──

    def _check_encumbrance_consequences(self):
        """If now over-encumbered, apply position-appropriate consequences."""
        if not self.is_encumbered:
            return
        height = self.room_vertical_position
        max_depth = getattr(self.location, "max_depth", 0) if self.location else 0
        if height > 0:
            # Flying — fall
            self.msg("|rYou are too heavy to stay airborne!|n")
            self._check_fall()
        elif max_depth < 0:
            # In water (surface or below) — sink to bottom
            if height > max_depth:
                self.room_vertical_position = max_depth
            self.msg("|rYou are too heavy! You sink to the bottom!|n")
            self.start_breath_timer()
        # On dry ground — no immediate consequence (movement blocked at exit)

    # ── Carry capacity override ──

    def get_max_capacity(self):
        """Carry capacity including STR modifier (5 kg per +1)."""
        base = self.max_carrying_capacity_kg or 0
        return base + self.get_attribute_bonus(self.strength) * 5

    # ── Death system ──

    # Purgatory release timer (seconds)
    PURGATORY_DURATION = 60

    # XP penalty on death (fraction of total)
    DEATH_XP_PENALTY = 0.05

    _ALLOWED_IN_PURGATORY = {"look", "help", "who", "say", "ooc", "release", "quit"}

    @property
    def in_purgatory(self):
        """True if the character is currently in a purgatory room."""
        from typeclasses.terrain.rooms.room_purgatory import RoomPurgatory
        return isinstance(self.location, RoomPurgatory)

    def at_pre_cmd(self, cmd):
        """Block most commands while in purgatory."""
        if self.in_purgatory and cmd.key not in self._ALLOWED_IN_PURGATORY:
            self.msg(
                "You are in purgatory. You will be released automatically "
                "in up to 60 seconds, or type |wrelease|n for early release "
                "(50 gold from your bank)."
            )
            return True

    def _wimpy_flee(self):
        """Auto-flee when HP drops below wimpy threshold during combat."""
        import random
        from combat.combat_utils import get_sides

        if self.wimpy_threshold <= 0 or self.hp <= 0:
            return
        if self.hp >= self.wimpy_threshold:
            return

        handler = self.get_combat_handler()
        if not handler:
            return

        # Find open exits
        room = self.location
        if not room:
            return
        exits = [
            ex for ex in room.exits
            if ex.destination and ex.access(self, "traverse")
        ]
        if not exits:
            self.msg("|rYou try to flee but there's nowhere to go!|n")
            return

        chosen = random.choice(exits)
        direction = chosen.key

        # Capture enemies before stopping combat
        _, enemies = get_sides(self)

        # Stop combat before moving
        handler.stop_combat()

        self.msg(f"|rYour wimpy threshold is reached — you flee {direction}!|n")
        if room:
            room.msg_contents(
                f"$You() $conj(panic) and $conj(flee) {direction}!",
                from_obj=self,
                exclude=[self],
            )

        self.move_to(chosen.destination)

        # Clean up combat for remaining enemies
        for enemy in enemies:
            enemy_handler = (enemy.get_combat_handler()
                             if hasattr(enemy, "get_combat_handler")
                             else None)
            if enemy_handler:
                enemy_handler._check_stop_combat()

    def die(self, cause="unknown", killer=None):
        """
        Handle character death or defeat.

        Guards against double-death: if two damage sources fire in the same
        tick (e.g. poison DoT + combat hit), the second call exits immediately.

        In allow_death=False rooms (arenas, etc.), the character is "defeated"
        instead: an empty corpse spawns for flavour, but the character keeps
        all gear, gold, resources, and XP. They are teleported to the room's
        defeat_destination (or home as fallback) on 1 HP.

        In normal rooms, full death: corpse with all items, XP penalty,
        purgatory.

        Args:
            cause: DeathCause value string (e.g. "combat", "starvation")
            killer: The entity that dealt the killing blow, if any.
        """
        # Guard against double-death (e.g. poison DoT + combat hit same tick)
        if getattr(self, "_dying", False):
            return
        self._dying = True

        room = self.location

        # ── Defeat flow (allow_death=False) ──
        if room and not getattr(room, "allow_death", True):
            self._defeat(room, cause)
            return

        # ── Full death flow ──
        self._real_death(room, cause)

    def _defeat(self, room, cause):
        """Handle defeat in a no-death room — empty corpse, keep gear, teleport out."""
        from typeclasses.world_objects.corpse import Corpse

        # Capture height before effects removal can change it
        actor_height = self.room_vertical_position

        # 1. Stop combat handler if active
        self.exit_combat()

        # 2. Clear all effects to prevent DoTs following player to safe room
        self.clear_all_effects()

        # 3. Remove dungeon_character tag if in a dungeon instance
        dungeon_tag = self.tags.get(category="dungeon_character")
        if dungeon_tag:
            self.tags.remove(dungeon_tag, category="dungeon_character")

        # 4. Empty corpse for flavour (no items, no gold, no resources)
        #    key="corpse" so name searches don't match the corpse (see mob.py)
        corpse = create_object(
            Corpse,
            key="corpse",
            location=room,
        )
        corpse.owner_character_key = self.db.character_key
        corpse.owner_name = self.key
        corpse.cause_of_death = "defeat"

        # Height transfer: flying actor's corpse falls to ground, underwater stays
        if actor_height > 0:
            corpse.room_vertical_position = 0
            if room:
                room.msg_contents(
                    f"The corpse of {self.key} falls to the ground.",
                    from_obj=corpse,
                )
        elif actor_height < 0:
            corpse.room_vertical_position = actor_height

        corpse.start_timers()

        # 5. Reset HP to 1
        self.hp = 1

        # 6. Announce defeat
        room.msg_contents(
            f"{self.key} has been defeated!",
            exclude=[self], from_obj=self,
        )
        self.msg("|yYou have been defeated!|n")

        # 7. Teleport to defeat_destination (or home as fallback)
        destination = getattr(room, "defeat_destination", None)
        if destination is None:
            destination = self.home
        if destination:
            self.move_to(destination, quiet=True, move_type="teleport")
            self.msg(destination.db.desc or "You come to in an unfamiliar place.")
        self._dying = False  # allow future deaths

    def _real_death(self, room, cause):
        """Handle full death — corpse with all items, XP penalty, purgatory.

        Order matches CircleMUD's raw_kill(): strip affects → stop fighting →
        make corpse → transfer items. This ensures no stale buff state leaks
        into purgatory and combat is cleanly exited before item transfer.
        """
        from typeclasses.items.base_nft_item import BaseNFTItem
        from typeclasses.world_objects.corpse import Corpse

        # Capture height before effects/equipment removal can change it.
        # Equipment-granted FLY persists through clear_all_effects() and is
        # only removed at unequip (step 4), which happens after corpse creation.
        actor_height = self.room_vertical_position

        # 1. Stop combat — clean up handler, pending actions, combat effects
        self.exit_combat()

        # 2. Strip ALL effects (seconds-based, combat, permanent)
        #    stop_combat already cleared combat_rounds effects; this catches
        #    seconds-based buffs (mage armor, potions, poison DoT) and
        #    permanent named effects. Silent — no end messages on death.
        self.clear_all_effects()

        # 3. Create Corpse object in current room
        #    key="corpse" so name searches don't match the corpse (see mob.py)
        corpse = create_object(
            Corpse,
            key="corpse",
            location=room,
        )
        corpse.owner_character_key = self.db.character_key
        corpse.owner_name = self.key
        corpse.cause_of_death = cause

        # Height transfer: flying actor's corpse falls to ground, underwater stays
        if actor_height > 0:
            corpse.room_vertical_position = 0
            if room:
                room.msg_contents(
                    f"The corpse of {self.key} falls to the ground.",
                    from_obj=corpse,
                )
        elif actor_height < 0:
            corpse.room_vertical_position = actor_height

        # 4. Unequip all worn/wielded/held items
        #    remove() fires at_remove() hooks which decrement conditions
        for item in list(self.get_all_worn().values()):
            if item is not None:
                self.remove(item)

        # 5. Move all NFT items to corpse
        for obj in list(self.contents):
            if isinstance(obj, BaseNFTItem):
                obj.move_to(corpse, quiet=True, move_type="teleport")

        # 6. Transfer all gold to corpse
        gold = self.get_gold()
        if gold > 0:
            self.transfer_gold_to(corpse, gold)

        # 7. Transfer all resources to corpse
        for rid, amt in list(self.get_all_resources().items()):
            if amt > 0:
                self.transfer_resource_to(corpse, rid, amt)

        # 8. Reset hunger to full with free tick (prevent immediate re-starvation)
        self.hunger_level = HungerLevel.FULL
        self.hunger_free_pass_tick = True

        # 9. XP penalty — lose 5% of total experience (no level loss)
        xp_penalty = int(self.experience_points * self.DEATH_XP_PENALTY)
        if xp_penalty > 0:
            self.experience_points -= xp_penalty

        # 10. Reset HP to 1
        self.hp = 1

        # 11. Announce death + death cry to adjacent rooms
        if room:
            room.msg_contents(
                f"{self.key} has died!", exclude=[self], from_obj=self,
            )
        self.msg("|rYou have died!|n")
        self._death_cry()
        if xp_penalty > 0:
            self.msg(f"You lost {xp_penalty} experience points.")

        # 12. Start corpse timers
        corpse.start_timers()

        # 13. Teleport to purgatory + start release timer
        purgatory = self._find_purgatory()
        if purgatory:
            self.move_to(purgatory, quiet=True, move_type="teleport")
            if purgatory.db.desc:
                self.msg(purgatory.db.desc)
            self.msg(
                f"\n|yYou will be released automatically in "
                f"{self.PURGATORY_DURATION} seconds.|n\n"
                f"Type |wrelease|n for early release (50 gold from your bank)."
            )
            delay(self.PURGATORY_DURATION, self._purgatory_release)
        else:
            # No purgatory room — send directly to respawn location
            destination = self.respawn_location or self.home or self._get_limbo()
            if destination:
                self.move_to(destination, quiet=True, move_type="teleport")
            self.msg("You feel yourself drawn back to the world of the living...")
            # Reset _dying after 1s so same-tick damage can't re-trigger death
            delay(1, self._reset_dying)

    def _purgatory_release(self):
        """Auto-release from purgatory after the timer expires."""
        from evennia import logger

        if not self.in_purgatory:
            return  # already released early via CmdRelease
        destination = self.respawn_location or self.home
        if not destination:
            destination = self._get_limbo()
            logger.log_warn(
                f"Purgatory release: {self.key} has no respawn_location or home, "
                f"falling back to Limbo"
            )
        self.move_to(destination, quiet=True, move_type="teleport")
        self.msg("You feel yourself drawn back to the world of the living...")
        self._dying = False  # allow future deaths

    def _reset_dying(self):
        """Reset the double-death guard so the character can die again."""
        self._dying = False

    def _get_limbo(self):
        """Return Limbo (Evennia default room, id=2), or None if not yet created."""
        from evennia import ObjectDB

        try:
            return ObjectDB.objects.get(id=2)
        except ObjectDB.DoesNotExist:
            return None

    def _find_purgatory(self):
        """Find the purgatory room."""
        from evennia import ObjectDB

        results = ObjectDB.objects.filter(
            db_typeclass_path__contains="room_purgatory"
        )
        if results.exists():
            return results.first()
        return None

    def get_display_things(self, looker, **kwargs):
        """Hide inventory from non-Builder lookers (staff/admin only)."""
        if looker and looker.locks.check_lockstring(looker, "perm(Builder)"):
            return super().get_display_things(looker, **kwargs)
        return ""

    def at_object_creation(self):
        """
        Called once when the object is first created.
        Add the all-character skill CmdSet here.
        """
        super().at_object_creation()
        from evennia.utils.search import search_tag

        # Set default home to Harvest Moon Inn (future recall destination)
        if not self.home:
            inn_rooms = search_tag("harvest_moon_inn", category="special_room")
            if inn_rooms:
                self.home = inn_rooms[0]
            else:
                limbo = self._get_limbo()
                if limbo:
                    self.home = limbo

        # Set default respawn to Millholm Cemetery (death respawn point)
        if not self.respawn_location:
            cemetery_rooms = search_tag("millholm_cemetery", category="special_room")
            if cemetery_rooms:
                self.respawn_location = cemetery_rooms[0]
        self.at_fungible_init()
        self.at_carrying_capacity_init()
        self.at_wearslots_init()
        self.at_recipe_book_init()
        self.at_spellbook_init()

        # Initialize the dict if it doesn't exist

        # general skills and mastery levels
        # e.g "forge": 1    where 1 corresponds to enum MasteryLevel.BASIC.value
        if not self.db.general_skill_mastery_levels:
            self.db.general_skill_mastery_levels = {}

        # class specific skills and mastery levels
        if not self.db.class_skill_mastery_levels:
            self.db.class_skill_mastery_levels = {}

        # weapon skills and mastery levels
        # e.g "longsword": 3    where 1 corresponds to enum MasteryLevel.EXPERT.value
        if not self.db.weapon_skill_mastery_levels:
            self.db.weapon_skill_mastery_levels = {}


        # hold a dict of dicts containing data about character classes (can multiclass)
        # e.g {
        #       "warrior" : {"class_level: 1", "class_skill_points_available: 3"}
        #       "cleric" : {"class_level: 2", "class_skill_points_available: 1"}
        #       }
        if not self.db.classes:
            self.db.classes = {}

        """
        # added for testing data persistence of mastery levels
        # and also processing of commands by different mastery levels
        # kept here as a known working example of how to set mastery levels

        self.db.general_skill_mastery_levels["blacksmith"] = MasteryLevel.BASIC.value
        self.db.general_skill_mastery_levels["survivalist"] = MasteryLevel.GRANDMASTER.value
        self.db.general_skill_mastery_levels["carpenter"] = MasteryLevel.BASIC.value
        """

    def at_post_puppet(self, **kwargs):
        """Called after player connects to this character."""
        super().at_post_puppet(**kwargs)
        # Safety net: clear double-death guard on login
        self._dying = False
        # Telemetry: record session start
        if self.account:
            from blockchain.xrpl.services.telemetry import TelemetryService

            TelemetryService.record_session_start(self.account.id, self.key)
        # Backfill respawn_location and home for characters created before
        # these defaults existed, or created before the world was built.
        if not self.respawn_location:
            from evennia.utils.search import search_tag

            cemetery_rooms = search_tag("millholm_cemetery", category="special_room")
            if cemetery_rooms:
                self.respawn_location = cemetery_rooms[0]
        if not self.home or self.home.id == 2:  # 2 = Limbo
            from evennia.utils.search import search_tag

            inn_rooms = search_tag("harvest_moon_inn", category="special_room")
            if inn_rooms:
                self.home = inn_rooms[0]

        # Safety net: if stuck in purgatory (e.g. server crash lost the timer),
        # reschedule the release so they don't wait forever.
        if self.in_purgatory:
            from evennia.utils.utils import delay

            delay(self.PURGATORY_DURATION, self._purgatory_release)

        # Tutorial recovery — clean up stale tutorial state on puppet.
        # Triggers if: location is gone, instance script is gone, or
        # character is no longer in a tutorial room (e.g. went OOC from hub).
        tutorial_tags = self.tags.get(category="tutorial_character", return_list=True)
        if tutorial_tags:
            from evennia import ScriptDB

            instance_key = tutorial_tags[0]
            script_exists = ScriptDB.objects.filter(db_key=instance_key).exists()
            location_gone = self.location is None or not self.location.pk
            in_tutorial_room = (
                self.location
                and self.location.pk
                and self.location.tags.get("tutorial_room", category="tutorial_room")
            )

            if not script_exists or location_gone or not in_tutorial_room:
                # Collapse instance if it still exists
                if script_exists:
                    for script in ScriptDB.objects.filter(db_key=instance_key):
                        if hasattr(script, "collapse_instance"):
                            script.collapse_instance(give_reward=False)
                # Remove tag in case collapse didn't
                self.tags.remove(instance_key, category="tutorial_character")
                for item in list(self.contents):
                    if getattr(item.db, "tutorial_item", False):
                        item.delete()

                # Return to pre-tutorial location or Harvest Moon
                from evennia import ObjectDB

                target = None
                prev_id = self.db.pre_tutorial_location_id
                if prev_id:
                    try:
                        target = ObjectDB.objects.get(id=prev_id)
                    except ObjectDB.DoesNotExist:
                        pass
                if not target:
                    target = ObjectDB.objects.filter(
                        db_key="The Harvest Moon"
                    ).first()
                if not target:
                    try:
                        target = ObjectDB.objects.get(id=2)  # Limbo
                    except ObjectDB.DoesNotExist:
                        pass
                if target:
                    self.location = target
                    self.db.pre_tutorial_location_id = None

        # Mail notification
        from commands.room_specific_cmds.postoffice.cmd_mail import CmdMail

        unread = CmdMail.get_unread_count(self)
        if unread:
            self.msg(
                f"|yYou have {unread} unread message(s). "
                f"Visit a Post Office to read them.|n"
            )

        # Tutorial offer — first puppet only.
        # Kept minimal; the Harvest Moon bartender (Rowan) greets new
        # arrivals conversationally via llm_hook_arrive.
        if self.account and not getattr(self.account.db, "tutorial_offered", False):
            self.account.db.tutorial_offered = True
            self.msg(
                "\n|c=== Welcome to FullCircleMUD! ===|n\n"
                "Talk to the bartender, or type |wtutorial|n to start "
                "learning the ropes.\n"
            )

        # Spell hint — show once for characters with spellcasting classes.
        if self.account and not getattr(self.account.db, "seen_spell_hint", False):
            has_spells = bool(self.db.spellbook or self.db.granted_spells)
            if has_spells:
                self.account.db.seen_spell_hint = True
                self.msg(
                    "\n|c╔═══════════════════════════════════════════════╗|n"
                    "\n|c║|n  You have spells! Here's how to use them:     |c║|n"
                    "\n|c║|n                                               |c║|n"
                    "\n|c║|n  |wspells|n     — see your available spells       |c║|n"
                    "\n|c║|n  |wmemorise <spell>|n — prepare a spell for use   |c║|n"
                    "\n|c║|n  |wcast <spell>|n     — cast a memorised spell    |c║|n"
                    "\n|c║|n  |wforget <spell>|n   — free a memory slot        |c║|n"
                    "\n|c║|n                                               |c║|n"
                    "\n|c║|n  You must memorise a spell before casting it. |c║|n"
                    "\n|c╚═══════════════════════════════════════════════╝|n"
                )

        # Send initial vitals for the split webclient panel
        self.send_vitals_update()

    # ── Prompt ──────────────────────────────────────────────────────

    _PROMPT_TOKENS = {
        "%h": lambda s: str(s.hp),
        "%H": lambda s: str(s.effective_hp_max),
        "%m": lambda s: str(s.mana),
        "%M": lambda s: str(s.mana_max),
        "%v": lambda s: str(s.move),
        "%V": lambda s: str(s.move_max),
        "%g": lambda s: str(s.get_gold()),
        "%x": lambda s: str(getattr(s.db, "xp", 0) or 0),
        "%l": lambda s: str(s.get_level()),
    }

    def get_prompt(self):
        """Build the text prompt string from the player's format template."""
        fmt = self.prompt_format or "%hH %mM %vV > "
        for token, resolver in self._PROMPT_TOKENS.items():
            if token in fmt:
                fmt = fmt.replace(token, resolver(self))
        return fmt

    # ── OOB Vitals ─────────────────────────────────────────────────

    def send_vitals_update(self):
        """Send structured vitals data via OOB for the split webclient panel."""
        self.msg(
            oob=(
                "vitals_update",
                {
                    "hp": self.hp,
                    "hp_max": self.effective_hp_max,
                    "mana": self.mana,
                    "mana_max": self.mana_max,
                    "move": self.move,
                    "move_max": self.move_max,
                    "level": self.get_level(),
                },
            )
        )

    def at_post_unpuppet(self, account, session=None, **kwargs):
        """Called after player disconnects from this character."""
        super().at_post_unpuppet(account, session=session, **kwargs)
        # Telemetry: record session end
        from blockchain.xrpl.services.telemetry import TelemetryService

        TelemetryService.record_session_end(account.id, self.key)

    def at_gain_experience_points(self, experience_gained):

        self.experience_points += experience_gained

        # Max level cap — prevent infinite recursion at level 40
        if self.total_level >= 40:
            return

        exp_required = get_xp_for_next_level(self.total_level)

        if self.experience_points >= exp_required:
            self.total_level += 1

            # Only grant spendable level for genuinely NEW thresholds
            # (prevents duplicate rewards after death XP penalty + re-earn)
            if self.total_level > self.highest_xp_level_earned:
                self.highest_xp_level_earned = self.total_level
                self.levels_to_spend += 1
                self.msg("\n***********************")
                self.msg(" WOOT!! YOU LEVELED UP ")
                self.msg("***********************\n")

            # Recurse to check for multiple level-ups
            self.at_gain_experience_points(0)

    def at_object_delete(self):
        """
        Hard block: prevent deletion if character holds NFTs or fungibles.
        Returns False to abort deletion.
        """
        from typeclasses.items.base_nft_item import BaseNFTItem

        # Check for NFT items in inventory
        nfts = [obj for obj in self.contents if isinstance(obj, BaseNFTItem)]
        if nfts:
            return False

        # Check for gold or resources
        if self.get_gold() > 0:
            return False
        if any(amt > 0 for amt in (self.db.resources or {}).values()):
            return False

        return True

    def get_class_string(self):

        if not self.db.classes:
            self.db.classes = {}

        classes = self.db.classes

        txt_return = f"Lvl {self.total_level} ("

        for class_key in classes:
            txt_return += f" {class_key.capitalize()} {classes[class_key]["level"]} |"


        txt_return += f" Unused {self.levels_to_spend} )"

        return txt_return
