
import math

from evennia import DefaultCharacter
from evennia.typeclasses.attributes import AttributeProperty

from enums.condition import Condition
from enums.size import Size
from enums.mastery_level import MasteryLevel
from enums.skills_enum import skills
from typeclasses.mixins.effects_manager import EffectsManagerMixin
from typeclasses.mixins.damage_resistance import DamageResistanceMixin
from typeclasses.mixins.height_aware_mixin import HeightAwareMixin
from typeclasses.mixins.unseen_name import UnseenNameMixin


class BaseActor(
    UnseenNameMixin,
    HeightAwareMixin,
    EffectsManagerMixin,
    DamageResistanceMixin,
    DefaultCharacter,
):

    #: Actors are people until a typeclass or spawn rule says otherwise.
    #: CombatMob sets "something" — most mobs are animals.
    unseen_name = AttributeProperty("Someone")

    # ── Size — unified across all actors ──
    # Stored as string for Evennia serialization (dbserialize can't handle
    # str enums). PCs get base_size set from race.size in at_taking_race();
    # mobs/pets override via their own AttributeProperty.
    # size is the active value, rebuilt from base_size by _recalculate_stats().
    base_size = AttributeProperty(Size.MEDIUM.value)
    size = AttributeProperty(Size.MEDIUM.value)

    # ── Movement messages ──
    # The single seam for inter-room movement text. Everything lives here
    # rather than in exit hooks because move_to() gates these two methods on
    # quiet= — a message emitted from at_traverse()/at_post_traverse() is
    # unconditional and cannot be silenced. See docs/movement-messages.md.

    def _movement_subject(self, party):
        """The actor, or their party when others are moving with them."""
        return "{name}'s party" if party else "{name}"

    def _announce_movement(self, room, text, move_type, direction=None, extra=None):
        """
        Emit a movement line to a room, with the mover excluded.

        ``text`` is a template, never a finished string. ``{name}`` is bound to
        the mover as an object, so Evennia resolves it through
        get_display_name() once per recipient — that is what redacts it to
        "Someone" for anyone who cannot see. A caller that formats a name in
        itself has already lost that.

        ``extra`` lets a caller add placeholders of its own. It is merged
        first, so the seam's own keys always win and ``{name}`` cannot be
        rebound to something that skips the per-recipient resolution.
        """
        mapping = dict(extra or {})
        mapping.update({"name": self, "direction": direction or ""})
        room.msg_contents(
            (text, {"type": move_type}),
            exclude=(self,),
            from_obj=self,
            mapping=mapping,
        )

    def announce_move_from(
        self, destination, msg=None, mapping=None, move_type="move", **kwargs
    ):
        """
        Tell the room being left that this actor is going, and which way.

        A caller may supply its own wording as ``msg_from``, and extra
        placeholders as ``msg_mapping``. Templates get ``{name}`` and
        ``{direction}`` — here the bare direction travelled, e.g. "north".
        """
        from utils.movement_messages import followers_in, resolve_rule

        location = self.location
        if not location:
            return
        if msg:
            return super().announce_move_from(
                destination, msg=msg, mapping=mapping, move_type=move_type, **kwargs
            )

        exit_obj = kwargs.get("exit_obj")
        direction = getattr(exit_obj, "direction", None)
        extra = kwargs.get("msg_mapping")

        # A caller that knows something the seam cannot see says so directly.
        override = kwargs.get("msg_from")
        if override:
            self._announce_movement(location, override, move_type, direction, extra)
            return

        # A group is one event, so the party moves under the leader's verb —
        # a mixed walking/flying party still reads as a single line.
        rule = resolve_rule(self, location)
        subject = self._movement_subject(followers_in(self, location))

        if direction:
            text = f"{subject} {rule.departure} {{direction}}{rule.end}"
        else:
            text = f"{subject} {rule.departure}{rule.end}"
        self._announce_movement(location, text, move_type, direction, extra)

    def announce_move_to(
        self, source_location, msg=None, mapping=None, move_type="move", **kwargs
    ):
        """
        Tell the room being entered that this actor has arrived, and from where.

        A caller may supply its own wording as ``msg_to``, and extra
        placeholders as ``msg_mapping``. Templates get ``{name}`` and
        ``{direction}`` — here the whole arrival phrase, e.g. "from the south"
        or "from below", since that is what reads naturally on this side.
        """
        from utils.exit_helpers import OPPOSITES
        from utils.movement_messages import arrival_phrase, followers_in, resolve_rule

        destination = self.location
        if msg or not source_location or not destination:
            # No source means this wasn't a move through the world (creation,
            # or straight into an inventory) — vanilla handles those.
            return super().announce_move_to(
                source_location,
                msg=msg,
                mapping=mapping,
                move_type=move_type,
                **kwargs,
            )

        # The exit leading back the way they came names the direction they
        # arrived from. Two rooms can be joined more than once — a staircase
        # and a passage, say — so prefer the way back that pairs with the exit
        # actually used, or arriving by the stairs reports the corridor.
        # Failing that take any way back (links need not be symmetrical), and
        # failing that invert the exit traversed, which is all a one-way exit
        # leaves us.
        travelled = getattr(kwargs.get("exit_obj"), "direction", None)
        opposite = OPPOSITES.get(travelled) if travelled else None

        ways_back = [
            obj
            for obj in destination.contents
            if obj.location is destination and obj.destination is source_location
        ]
        paired = next(
            (obj for obj in ways_back if getattr(obj, "direction", None) == opposite),
            None,
        )
        reciprocal = paired or (ways_back[0] if ways_back else None)
        direction = getattr(reciprocal, "direction", None) or opposite

        phrase = arrival_phrase(direction) if direction else ""
        extra = kwargs.get("msg_mapping")

        override = kwargs.get("msg_to")
        if override:
            self._announce_movement(destination, override, move_type, phrase, extra)
            return

        # Followers have not cascaded yet — they are still in the source room.
        rule = resolve_rule(self, destination)
        subject = self._movement_subject(followers_in(self, source_location))

        if phrase:
            text = f"{subject} {rule.arrival} {{direction}}{rule.end}"
        else:
            text = f"{subject} {rule.arrival}{rule.end}"
        self._announce_movement(destination, text, move_type, phrase, extra)

    def at_object_creation(self):
        super().at_object_creation()
        # Auto-init composed mixins if present. Defensive pattern —
        # avoids subclasses forgetting to call init when composing mixins.
        # All init methods are idempotent (guard against double-init).
        for init_method in (
            "at_fungible_init",
            "at_wearslots_init",
            "at_followable_init",
            "at_carrying_capacity_init",
            "at_recipe_book_init",
            "at_spellbook_init",
            "at_llm_init",
        ):
            if hasattr(self, init_method):
                getattr(self, init_method)()

    def at_pre_move(self, destination, move_type="move", **kwargs):
        """Block physical movement if held by a movement-blocking effect.

        Catches every movement path (walk, follow, flee, AI wander,
        forced-flee) for any actor — not just players. Teleport is
        exempt: magical relocation bypasses physical restraint.
        """
        if move_type in ("move", "follow", "flee", "traverse"):
            _, block_msg = self.get_movement_blocking_effect()
            if block_msg:
                self.msg(block_msg)
                return False
        return super().at_pre_move(destination, move_type=move_type, **kwargs)

    #########################################################
    # Ability Scores (point buy system)
    #########################################################
    #
    # UNIVERSAL PATTERN — ability score modifiers are NEVER cached:
    #
    # The "current" ability scores below are modified by equipment/spell
    # effects via apply_effect/remove_effect. But the MODIFIER derived
    # from an ability score (floor((score-10)/2)) is ALWAYS computed at
    # check time — never baked into other cached stats.
    #
    # This applies universally to ALL stats: AC, hit/dam, initiative,
    # carrying capacity, poison resistance, perception, etc. No exceptions.
    #
    # Why: ability modifiers often depend on context (finesse weapons use
    # dex not str, monks may use wis, different weapons grant different
    # mastery bonuses). Caching them would require cascading recalculation.
    #
    # See apply_effect() below for the full pattern description.
    #
    #########################################################

    # the actors base natural values without any magic, equipment, buffs etc

    base_strength = AttributeProperty(8)
    base_dexterity = AttributeProperty(8)
    base_constitution = AttributeProperty(8)
    base_intelligence = AttributeProperty(8)
    base_wisdom = AttributeProperty(8)
    base_charisma = AttributeProperty(8)

    # the current active values of the actors ability scores
    # these get updated by condition effects, buffs, equipment etc
    # the MODIFIER (floor((score-10)/2)) is computed at check time, not stored

    strength = AttributeProperty(8)
    dexterity = AttributeProperty(8)
    constitution = AttributeProperty(8)
    intelligence = AttributeProperty(8)
    wisdom = AttributeProperty(8)
    charisma = AttributeProperty(8)

    #########################################################
    # Core Stats
    #########################################################

    hp = AttributeProperty(5)           # Current hit points
    base_hp_max = AttributeProperty(5)  # Natural max HP (race + class levels, no equipment/spells)
    hp_max = AttributeProperty(5)       # Effective max HP (base + equipment/spell bonuses)

    mana = AttributeProperty(5)
    base_mana_max = AttributeProperty(5)  # Natural max mana (race + class levels)
    mana_max = AttributeProperty(5)

    move = AttributeProperty(80)
    base_move_max = AttributeProperty(80)  # Natural max move (race + class levels)
    move_max = AttributeProperty(80)

    # what the actors base AC is
    # WITHOUT DEXTERITY or other modifiers armour, spells, or anything else
    # will be 10 for nearly all characters unless they have a racial or other
    # ability that raises thier base AC (e.g. a turtle character with a shell)
    base_armor_class = AttributeProperty(10)             # Base armor class

    # the actor's current AC, including all modifiers from dex, armour, spells, etc
    # this is what is used for combat etc
    armor_class = AttributeProperty(10)             # Current armor class

    # base crit threshold for the actor
    base_crit_threshold = AttributeProperty(20)   # Default crit on natural 20 only

    #########################################################
    # caches of variable stats prevent constant recalculation
    #########################################################
    # update as needed whenever condtion effects are added or removed
    # running totals of bonuses from items, buffs, etc

    initiative_bonus = AttributeProperty(0) # total of ALL bonuses to add to initiative rolls

    total_hit_bonus = AttributeProperty(0)  # total of ALL bonuses to add to hit rolls e.g. sword +1
    save_bonus = AttributeProperty(0)  # bonus to save-each-round rolls (Bless, etc.)

    total_damage_bonus = AttributeProperty(0)  # total of ALL bonuses to add to add to dam rolls e.g. sword +1

    attacks_per_round = AttributeProperty(1)  # current number of attacks per round, including all modifiers from class, buffs, etc

    stealth_bonus = AttributeProperty(0)  # total of ALL bonuses to stealth rolls from items, buffs, etc
    perception_bonus = AttributeProperty(0)  # total of ALL bonuses to perception checks from items, buffs, etc

    # weapon-type-specific bonuses — keyed by WeaponType.value string (e.g. "unarmed", "long_sword")
    hit_bonuses = AttributeProperty({})     # {weapon_type_value: int} — to-hit bonus per weapon type
    damage_bonuses = AttributeProperty({})  # {weapon_type_value: int} — damage bonus per weapon type

    # damage_resistances — provided by DamageResistanceMixin
    # conditions, apply_effect, remove_effect, named effects — provided by EffectsManagerMixin

    # room_vertical_position — provided by HeightAwareMixin

    # Short sentence displayed in room character list (CircleMUD-style).
    # None = use default template. Players can override via ``roomdesc``.
    room_description = AttributeProperty(None, autocreate=False)

    # Position/posture — affects room display, regen rate, and movement.
    # Valid values: "standing", "sitting", "resting", "sleeping", "fighting"
    position = AttributeProperty("standing", autocreate=False)

    # Position display templates (used when no custom room_description is set)
    _POSITION_TEMPLATES = {
        "standing": "{name}, a thoroughly unremarkable fellow, stands here.",
        "sitting": "{name} is sitting here.",
        "resting": "{name} is resting here.",
        "sleeping": "{name} is sleeping here.",
        "fighting": "{name} is here, fighting {target}!",
    }

    # Regen multipliers by position
    REGEN_MULTIPLIERS = {
        "standing": 1,
        "sitting": 1,
        "resting": 2,
        "sleeping": 3,
        "fighting": 0,
    }

    def get_room_description(self):
        """
        Return the room description for this actor.

        Priority:
        1. Custom room_description (player-set via ``roomdesc``) — used as-is
           for standing, with position suffix appended for other positions.
        2. Position-based default template from _POSITION_TEMPLATES.
        """
        pos = self.position or "standing"

        if self.room_description:
            if "{name}" in self.room_description:
                base = self.room_description.replace("{name}", self.key)
            else:
                desc = self.room_description.lstrip()
                if desc.startswith((",", "'", "'")):
                    base = f"{self.key}{desc}"
                else:
                    base = f"{self.key} {desc}"
            afk_tag = " |w(AFK)|n" if getattr(self, "afk", False) else ""
            if pos == "standing":
                return base + afk_tag
            # Append position for non-standing with custom desc
            suffix = {
                "sitting": "is sitting here.",
                "resting": "is resting here.",
                "sleeping": "is sleeping here.",
                "fighting": f"is here, fighting {self._get_fight_target()}!",
            }
            return f"{self.key} {suffix.get(pos, 'stands here.')}" + afk_tag

        template = self._POSITION_TEMPLATES.get(pos, self._POSITION_TEMPLATES["standing"])
        target = self._get_fight_target() if pos == "fighting" else ""
        desc = template.format(name=self.key, target=target)
        if getattr(self, "afk", False):
            desc += " |w(AFK)|n"
        return desc

    def _get_fight_target(self):
        """Return the name of who this actor is fighting, or 'someone'."""
        target = getattr(self, "ndb", None) and getattr(self.ndb, "combat_target", None)
        if target:
            return target.key
        return "someone"

    # ================================================================== #
    #  Level — subclasses override get_level() for their progression
    # ================================================================== #

    def get_level(self):
        """
        Return this actor's combat level for stat calculations.

        BaseActor returns 1. FCMCharacter overrides to return total_level.
        NPCs set a level attribute directly and override this.
        """
        return 1

    # ================================================================== #
    #  Effect System — see EffectsManagerMixin
    # ================================================================== #
    #
    # UNIVERSAL PATTERN — NO EXCEPTIONS:
    #
    # Every cached stat on the actor stores ONLY bonuses from equipment
    # and spell/potion effects. Nothing else. apply_effect/remove_effect
    # (on EffectsManagerMixin) increment/decrement these when items are
    # worn/removed or buffs start/expire.
    #
    # Ability score modifiers and skill mastery bonuses are NEVER cached.
    # They are ALWAYS computed at check time — when the roll, capacity
    # check, or combat calculation actually happens. This applies to ALL
    # stats universally: AC, hit bonus, damage, initiative, carrying
    # capacity, poison resistance, perception, and any future stats.
    #
    # For timed/tracked effects, use apply_named_effect() instead.
    # See EffectsManagerMixin and CLAUDE.md "Effect System Framework".
    #

    def get_attribute_bonus(self, score):
        return math.floor((score - 10) / 2)

    # ================================================================== #
    #  Nuclear Recalculate — rebuild Tier 2 stats from all effect sources
    # ================================================================== #

    def _recalculate_stats(self):
        """
        Rebuild all Tier 2 numeric stats from scratch.

        Called whenever an effect source changes (equip/unequip, buff
        apply/expire). Guarantees stat consistency by computing from
        all sources rather than incremental add/subtract.

        Sources (in application order):
            1. Racial effects (damage resistances)
            2. Worn equipment wear_effects
            3. Active named effects (spells, potions, combat buffs)

        Conditions are NOT rebuilt here — they use ref-counting and are
        managed incrementally via add_condition/remove_condition.
        """
        # 1. Reset ability scores to base
        self.strength = self.base_strength
        self.dexterity = self.base_dexterity
        self.constitution = self.base_constitution
        self.intelligence = self.base_intelligence
        self.wisdom = self.base_wisdom
        self.charisma = self.base_charisma

        # 2. Reset pool maxes to base (race + class levels, no equipment)
        self.hp_max = self.base_hp_max
        self.mana_max = self.base_mana_max
        self.move_max = self.base_move_max

        # 3. Reset size to base
        self.size = self.base_size

        # 4. Reset bonus stats to zero/defaults
        self.armor_class = self.base_armor_class
        self.total_hit_bonus = 0
        self.save_bonus = 0
        self.total_damage_bonus = 0
        self.initiative_bonus = 0
        self.stealth_bonus = 0
        self.perception_bonus = 0
        self.attacks_per_round = 1
        self.hit_bonuses = {}
        self.damage_bonuses = {}
        self.damage_resistances = {}

        # Track which conditions' companion effects have been counted
        # to prevent double-applying when multiple sources grant the
        # same condition (e.g. two "haste" rings).
        self._accumulated_companions = set()

        # 3a. Racial effects (conditions already handled at creation)
        from typeclasses.actors.races import get_race
        race = get_race(self.race) if hasattr(self, 'race') and self.race else None
        if race:
            for effect in race.racial_effects:
                self._accumulate_effect(effect)

        # 3b. Worn equipment
        if hasattr(self, 'get_all_worn'):
            for item in self.get_all_worn().values():
                for effect in (item.wear_effects or []):
                    self._accumulate_effect(effect)

        # 3c. Active named effects (spells, potions, combat buffs)
        for record in (self.active_effects or {}).values():
            for effect in record.get("effects", []):
                self._accumulate_effect(effect)

        del self._accumulated_companions

        # 4. Clamp current pools to new maxes (e.g. after equipment removal)
        eff_hp = self.effective_hp_max
        if self.hp > eff_hp:
            self.hp = eff_hp
        if self.mana > self.mana_max:
            self.mana = self.mana_max
        if self.move > self.move_max:
            self.move = self.move_max

        # 5. Post-recalculate checks
        self._check_encumbrance_consequences()
        if hasattr(self, '_check_equipment_restrictions'):
            self._check_equipment_restrictions()

    def _accumulate_effect(self, effect):
        """
        Apply one effect dict's numeric contribution during recalculate.

        Handles stat_bonus, damage_resistance, hit_bonus, damage_bonus.
        Condition flag handling is skipped (managed separately via
        ref-counting), but companion stat effects on active conditions
        are included.
        """
        effect_type = effect.get("type")
        if effect_type == "stat_bonus":
            stat = effect["stat"]
            value = effect["value"]
            current = getattr(self, stat, None)
            if current is not None:
                setattr(self, stat, current + value)
        elif effect_type == "damage_resistance":
            self.apply_resistance_effect(effect)
        elif effect_type == "hit_bonus":
            wt = effect["weapon_type"]
            value = effect["value"]
            bonuses = dict(self.hit_bonuses)
            bonuses[wt] = bonuses.get(wt, 0) + value
            self.hit_bonuses = bonuses
        elif effect_type == "damage_bonus":
            wt = effect["weapon_type"]
            value = effect["value"]
            bonuses = dict(self.damage_bonuses)
            bonuses[wt] = bonuses.get(wt, 0) + value
            self.damage_bonuses = bonuses
        elif effect_type == "condition":
            # Condition flags are NOT rebuilt by recalculate.
            # But companion stat effects on active conditions are included,
            # only ONCE per condition (not per source that grants it).
            cond_key = effect.get("condition")
            if (effect.get("effects")
                    and self.has_condition(cond_key)
                    and cond_key not in self._accumulated_companions):
                self._accumulated_companions.add(cond_key)
                for sub in effect["effects"]:
                    self._accumulate_effect(sub)

    # ================================================================== #
    #  Effective stats — combine cached base with ability modifiers
    # ================================================================== #

    @property
    def effective_ac(self):
        """AC including DEX modifier. armor_class stores equipment/spell bonuses only."""
        return self.armor_class + self.get_attribute_bonus(self.dexterity)

    @property
    def effective_initiative(self):
        """Initiative including DEX modifier."""
        return self.initiative_bonus + self.get_attribute_bonus(self.dexterity)

    @property
    def effective_hp_max(self):
        """Max HP including CON modifier (per level)."""
        return self.hp_max + (self.get_attribute_bonus(self.constitution) * self.get_level())

    def get_skill_mastery(self, skill_key):
        """Look up a skill's mastery level from any mastery dict.
        Returns the MasteryLevel int value (0=UNSKILLED if not found).
        """
        # General skills (flat: {skill: int})
        general = getattr(self.db, "general_skill_mastery_levels", None) or {}
        if skill_key in general:
            return general[skill_key]
        # Class skills (nested: {skill: {"mastery": int, "classes": [...]}})
        class_m = getattr(self.db, "class_skill_mastery_levels", None) or {}
        entry = class_m.get(skill_key)
        if entry:
            return entry.get("mastery", 0) if hasattr(entry, "get") else entry
        # Weapon skills (flat: {weapon: int})
        weapon = getattr(self.db, "weapon_skill_mastery_levels", None) or {}
        if skill_key in weapon:
            return weapon[skill_key]
        return MasteryLevel.UNSKILLED.value

    @property
    def effective_stealth_bonus(self):
        """Stealth bonus: equipment/spells + DEX modifier + STEALTH mastery bonus."""
        mastery_int = self.get_skill_mastery(skills.STEALTH.value)
        mastery_bonus = MasteryLevel(mastery_int).bonus
        return self.stealth_bonus + self.get_attribute_bonus(self.dexterity) + mastery_bonus

    @property
    def effective_perception_bonus(self):
        """Perception bonus: equipment/spells + WIS modifier + ALERTNESS mastery bonus."""
        mastery_int = self.get_skill_mastery(skills.ALERTNESS.value)
        mastery_bonus = MasteryLevel(mastery_int).bonus if mastery_int > 0 else MasteryLevel.UNSKILLED.bonus
        return self.perception_bonus + self.get_attribute_bonus(self.wisdom) + mastery_bonus

    @property
    def effective_hit_bonus(self):
        """
        Self-contained total hit bonus. Inspects wielded weapon for context.

        Combines: cached equipment bonuses + ability modifier + weapon-type
        bonus + weapon mastery bonus. Combat system just calls
        attacker.effective_hit_bonus — no args needed.
        """
        from combat.combat_utils import get_weapon
        weapon = get_weapon(self)

        # Ability score: finesse = max(STR, DEX), ranged = DEX, melee = STR
        if weapon and getattr(weapon, "is_finesse", False):
            attr_score = max(self.strength, self.dexterity)
        elif weapon and getattr(weapon, "weapon_type", "melee") == "ranged":
            attr_score = self.dexterity
        else:
            attr_score = self.strength

        total = self.total_hit_bonus + self.get_attribute_bonus(attr_score)

        if weapon:
            wt_key = getattr(weapon, "weapon_type_key", None)
            if wt_key:
                total += self.hit_bonuses.get(wt_key, 0)
            total += weapon.get_mastery_hit_bonus(self)

        return total

    @property
    def effective_attacks_per_round(self):
        """
        Total attacks per round: cached attacks_per_round (base + condition
        effects like HASTED) + weapon mastery extra attacks.
        """
        total = self.attacks_per_round
        from combat.combat_utils import get_weapon
        weapon = get_weapon(self)
        if weapon and hasattr(weapon, "get_extra_attacks"):
            total += weapon.get_extra_attacks(self)
        return total

    @property
    def effective_damage_bonus(self):
        """
        Self-contained total damage bonus. Inspects wielded weapon for context.

        Combines: cached equipment bonuses + ability modifier + weapon-type
        bonus + weapon mastery bonus. Combat system just calls
        attacker.effective_damage_bonus — no args needed.
        """
        from combat.combat_utils import get_weapon
        weapon = get_weapon(self)

        # Ability score: finesse = max(STR, DEX), ranged = DEX, melee = STR
        if weapon and getattr(weapon, "is_finesse", False):
            attr_score = max(self.strength, self.dexterity)
        elif weapon and getattr(weapon, "weapon_type", "melee") == "ranged":
            attr_score = self.dexterity
        else:
            attr_score = self.strength

        total = self.total_damage_bonus + self.get_attribute_bonus(attr_score)

        if weapon:
            wt_key = getattr(weapon, "weapon_type_key", None)
            if wt_key:
                total += self.damage_bonuses.get(wt_key, 0)
            total += weapon.get_mastery_damage_bonus(self)

        return total

    @property
    def effective_crit_threshold(self):
        """base_crit_threshold + weapon mastery crit modifier."""
        from combat.combat_utils import get_weapon
        weapon = get_weapon(self)
        total = self.base_crit_threshold
        if weapon:
            total += weapon.get_mastery_crit_threshold_modifier(self)
        return total

    # ================================================================== #
    #  Condition overrides — automatic messaging on gain/loss
    # ================================================================== #

    def _resolve_condition_enum(self, condition):
        """Convert a string or Condition enum to a Condition enum (or None if invalid)."""
        if isinstance(condition, Condition):
            return condition
        try:
            return Condition(condition)
        except ValueError:
            return None

    def add_condition(self, condition):
        """
        Override to send start messages when a condition is newly gained.

        Timing: snapshot visibility state BEFORE incrementing so that
        gaining INVISIBLE/HIDDEN itself doesn't filter its own announcement.
        """
        was_hidden = self.has_condition(Condition.HIDDEN)
        was_invisible = self.has_condition(Condition.INVISIBLE)

        newly_gained = super().add_condition(condition)

        if newly_gained and self.location:
            cond_enum = self._resolve_condition_enum(condition)
            if cond_enum:
                self.msg(cond_enum.get_start_message())
                if not was_hidden:
                    self.location.msg_contents(
                        cond_enum.get_start_message_third_person(self.key),
                        exclude=[self],
                        from_obj=self if was_invisible else None,
                    )

                # --- Condition-specific side effects ---
                if cond_enum == Condition.WATER_BREATHING:
                    self.stop_breath_timer()

        return newly_gained

    def remove_condition(self, condition):
        """
        Override to send end messages when a condition is fully removed.

        Timing: check visibility state AFTER decrementing so that
        losing INVISIBLE/HIDDEN itself doesn't filter its own announcement.
        """
        fully_removed = super().remove_condition(condition)

        if fully_removed and self.location:
            cond_enum = self._resolve_condition_enum(condition)
            if cond_enum:
                self.msg(cond_enum.get_end_message())
                if not self.has_condition(Condition.HIDDEN):
                    self.location.msg_contents(
                        cond_enum.get_end_message_third_person(self.key),
                        exclude=[self],
                        from_obj=self if self.has_condition(Condition.INVISIBLE) else None,
                    )

                # --- Condition-specific side effects ---
                if cond_enum == Condition.FLY:
                    self._check_fall()
                elif cond_enum == Condition.WATER_BREATHING:
                    if self.room_vertical_position < 0:
                        self.start_breath_timer()

        return fully_removed

    # ── Fall damage when FLY condition is lost while airborne ──

    FALL_DAMAGE_PER_LEVEL = 10
    WATER_FALL_ABSORB = 20

    def _check_fall(self):
        """If airborne, fall to ground and take flat damage per height level.

        Water (rooms with max_depth < 0) absorbs the first WATER_FALL_ABSORB
        HP of fall damage — a short dock jump is harmless, but a cliff dive
        still hurts.
        """
        height = self.room_vertical_position
        if height <= 0:
            return

        room = self.location

        # Climbable fixture safety — if something supports this height,
        # the character grabs on and slides down instead of falling.
        if room:
            for obj in room.contents:
                climbable = getattr(obj, "climbable_heights", None)
                if climbable and height in climbable:
                    self.room_vertical_position = 0
                    self.msg(
                        f"|yYou grab onto {obj.key} and slide "
                        f"safely to the ground.|n"
                    )
                    room.msg_contents(
                        f"{self.key} grabs onto {obj.key} and "
                        f"slides to the ground.",
                        exclude=[self],
                        from_obj=self,
                    )
                    return

        # Feather Fall — float gently to the ground, no damage
        if hasattr(self, "has_effect") and self.has_effect("feather_fall"):
            self.room_vertical_position = 0
            self.msg("|yYou float gently to the ground, light as a feather.|n")
            if room:
                room.msg_contents(
                    f"{self.key} floats gently to the ground.",
                    exclude=[self],
                    from_obj=self,
                )
            return

        self.room_vertical_position = 0
        raw_damage = height * self.FALL_DAMAGE_PER_LEVEL

        # Water cushions the fall
        lands_in_water = room and getattr(room, "max_depth", 0) < 0
        if lands_in_water:
            raw_damage = max(0, raw_damage - self.WATER_FALL_ABSORB)

        if raw_damage <= 0 and lands_in_water:
            self.msg("|yYou splash into the water!|n")
            if room:
                room.msg_contents(
                    f"{self.key} does the most magnificent belly-flop "
                    f"into the water!",
                    exclude=[self],
                    from_obj=self,
                )
            return

        if lands_in_water:
            damage = self.take_damage(
                raw_damage, cause="fall", ignore_resistance=True
            )
            self.msg(
                f"|rYou plummet into the water from a great height! "
                f"You take |w{damage}|r damage from the impact.|n"
            )
            if room:
                room.msg_contents(
                    f"{self.key} plummets from the sky and crashes "
                    f"into the water!",
                    exclude=[self],
                    from_obj=self,
                )
        else:
            damage = self.take_damage(
                raw_damage, cause="fall", ignore_resistance=True
            )
            self.msg(
                f"|rYou plummet to the ground! "
                f"You take |w{damage}|r damage from the fall.|n"
            )
            if room:
                room.msg_contents(
                    f"{self.key} plummets from the sky and crashes "
                    f"to the ground!",
                    exclude=[self],
                    from_obj=self,
                )

    # ================================================================== #
    #  Damage Pipeline
    # ================================================================== #

    def calculate_damage(self, raw_damage, damage_type=None,
                         ignore_resistance=False):
        """
        Calculate final damage after resistance/vulnerability. Does NOT apply.

        Use this when you need to know the damage amount before applying it
        (e.g. to broadcast a hit message before triggering death).

        Args:
            raw_damage (int): Pre-resistance damage amount.
            damage_type (str|None): Damage type string for resistance lookup.
            ignore_resistance (bool): If True, skip resistance entirely.

        Returns:
            int: Final damage after resistance/vulnerability (minimum 1).
        """
        damage = raw_damage

        if not ignore_resistance and damage_type and hasattr(self, "get_resistance"):
            resistance = self.get_resistance(damage_type)
            if resistance > 0:
                reduction = max(1, int(damage * resistance / 100))
                damage = damage - reduction
            elif resistance < 0:
                extra = max(1, int(damage * abs(resistance) / 100))
                damage = damage + extra

        return max(1, damage)

    def apply_damage(self, damage, cause="combat", killer=None):
        """
        Apply pre-calculated damage. Subtracts HP, triggers wimpy and death.

        Use after calculate_damage() when you need to control message
        ordering (e.g. broadcast hit message before death message).

        Args:
            damage (int): Final damage amount to apply.
            cause (str): Death cause passed to die() if HP reaches 0.
            killer: The entity that dealt the killing blow, if any.

        Returns:
            int: The damage amount (pass-through for convenience).
        """
        self.hp = max(0, self.hp - damage)

        if self.hp > 0 and hasattr(self, "_wimpy_flee"):
            self._wimpy_flee()

        if self.hp <= 0:
            already_dead = (
                not getattr(self, "is_alive", True)
            ) or getattr(self, "_dying", False)
            if not already_dead:
                self.die(cause, killer=killer)

        return damage

    def take_damage(self, raw_damage, damage_type=None, cause="combat",
                    ignore_resistance=False, killer=None):
        """
        Central damage method — calculate resistance and apply in one call.

        Convenience wrapper around calculate_damage() + apply_damage().
        Most callers should use this. Use the split methods only when you
        need to insert logic (like broadcasting a hit message) between
        damage calculation and application.

        Args:
            raw_damage (int): Pre-resistance damage amount.
            damage_type (str|None): Damage type string for resistance lookup
                (e.g. "fire", "piercing"). None or omitted skips resistance.
            cause (str): Death cause passed to die() if HP reaches 0.
                Common values: "combat", "spell", "fall", "drowning".
            ignore_resistance (bool): If True, skip resistance entirely.
                Use for environmental damage (fall, drowning) that bypasses
                all resistances.
            killer: The entity that dealt the killing blow, if any.

        Returns:
            int: Actual damage dealt after resistance/vulnerability.
        """
        damage = self.calculate_damage(raw_damage, damage_type, ignore_resistance)
        self.apply_damage(damage, cause, killer)
        return damage

    # ── Breath timer helpers ──

    def start_breath_timer(self):
        """Start the underwater breath timer if not already running."""
        if self.scripts.get("breath_timer"):
            return
        from typeclasses.scripts.breath_timer import BreathTimerScript
        BreathTimerScript.create("breath_timer", obj=self)

    def stop_breath_timer(self):
        """Stop and remove the underwater breath timer if running."""
        timers = self.scripts.get("breath_timer")
        if timers:
            for timer in timers:
                timer.delete()

    # ── Death ──

    def _death_cry(self):
        """Broadcast a death cry to adjacent rooms."""
        room = self.location
        if not room:
            return
        for exit_obj in room.exits:
            dest = exit_obj.destination
            if dest and dest != room:
                dest.msg_contents(
                    "|rYour blood freezes as you hear someone's death cry.|n"
                )

    def die(self, cause="unknown", killer=None):
        """
        Basic death stub. Sets HP to 0 and announces death.

        FCMCharacter overrides with corpse/purgatory/XP penalty.
        CombatMob will override with loot drop/respawn.

        Args:
            cause: Death cause string (e.g. "combat", "starvation").
            killer: The entity that dealt the killing blow, if any.
        """
        self.hp = 0
        self.msg("|rYou have died!|n")
        if self.location:
            self.location.msg_contents(
                f"{self.key} has died!",
                exclude=[self],
                from_obj=self,
            )
