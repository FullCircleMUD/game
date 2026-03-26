
import math

from evennia import DefaultCharacter
from evennia.typeclasses.attributes import AttributeProperty

from enums.condition import Condition
from enums.mastery_level import MasteryLevel
from enums.skills_enum import skills
from typeclasses.mixins.effects_manager import EffectsManagerMixin
from typeclasses.mixins.damage_resistance import DamageResistanceMixin


class BaseActor(EffectsManagerMixin, DamageResistanceMixin, DefaultCharacter):

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

    hp = AttributeProperty(1)           # Current hit points
    hp_max = AttributeProperty(2)       # Maximum hit points (race + class + equipment/spell bonuses)

    mana = AttributeProperty(0)
    mana_max = AttributeProperty(1)

    move = AttributeProperty(2)
    move_max = AttributeProperty(3)

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

    total_damage_bonus = AttributeProperty(0)  # total of ALL bonuses to add to add to dam rolls e.g. sword +1

    attacks_per_round = AttributeProperty(1)  # current number of attacks per round, including all modifiers from class, buffs, etc

    stealth_bonus = AttributeProperty(0)  # total of ALL bonuses to stealth rolls from items, buffs, etc
    perception_bonus = AttributeProperty(0)  # total of ALL bonuses to perception checks from items, buffs, etc

    # weapon-type-specific bonuses — keyed by WeaponType.value string (e.g. "unarmed", "long_sword")
    hit_bonuses = AttributeProperty({})     # {weapon_type_value: int} — to-hit bonus per weapon type
    damage_bonuses = AttributeProperty({})  # {weapon_type_value: int} — damage bonus per weapon type

    # damage_resistances — provided by DamageResistanceMixin
    # conditions, apply_effect, remove_effect, named effects — provided by EffectsManagerMixin

    # whether actor is on the ground (0) or flying > 0 or swimming < 0
    # and how many levels high or low they are flying or swimming
    room_vertical_position = AttributeProperty(0)

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
            if pos == "standing":
                return base
            # Append position for non-standing with custom desc
            suffix = {
                "sitting": "is sitting here.",
                "resting": "is resting here.",
                "sleeping": "is sleeping here.",
                "fighting": f"is here, fighting {self._get_fight_target()}!",
            }
            return f"{self.key} {suffix.get(pos, 'stands here.')}"

        template = self._POSITION_TEMPLATES.get(pos, self._POSITION_TEMPLATES["standing"])
        target = self._get_fight_target() if pos == "fighting" else ""
        return template.format(name=self.key, target=target)

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

        # 2. Reset bonus stats to zero/defaults
        self.armor_class = self.base_armor_class
        self.total_hit_bonus = 0
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

        # 4. Post-recalculate checks
        self._check_encumbrance_consequences()

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

        # Ability score: finesse = max(STR, DEX), missile = DEX, melee = STR
        if weapon and getattr(weapon, "is_finesse", False):
            attr_score = max(self.strength, self.dexterity)
        elif weapon and getattr(weapon, "weapon_type", "melee") == "missile":
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

        # Ability score: finesse = max(STR, DEX), missile = DEX, melee = STR
        if weapon and getattr(weapon, "is_finesse", False):
            attr_score = max(self.strength, self.dexterity)
        elif weapon and getattr(weapon, "weapon_type", "melee") == "missile":
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

    def _check_fall(self):
        """If airborne, fall to ground and take flat damage per height level."""
        height = self.room_vertical_position
        if height <= 0:
            return

        self.room_vertical_position = 0
        raw_damage = height * self.FALL_DAMAGE_PER_LEVEL
        damage = self.take_damage(raw_damage, cause="fall", ignore_resistance=True)

        self.msg(
            f"|rYou plummet to the ground! "
            f"You take |w{damage}|r damage from the fall.|n"
        )
        if self.location:
            self.location.msg_contents(
                f"{self.key} plummets from the sky and crashes to the ground!",
                exclude=[self],
                from_obj=self,
            )

    # ================================================================== #
    #  Damage Pipeline
    # ================================================================== #

    def take_damage(self, raw_damage, damage_type=None, cause="combat",
                    ignore_resistance=False, killer=None):
        """
        Central damage application method — ALL damage sources should use this.

        Handles resistance/vulnerability calculation, enforces minimum damage,
        subtracts HP, and triggers death when HP reaches 0.

        Args:
            raw_damage (int): Pre-resistance damage amount.
            damage_type (str|None): Damage type string for resistance lookup
                (e.g. "fire", "piercing"). None or omitted skips resistance.
            cause (str): Death cause passed to die() if HP reaches 0.
                Common values: "combat", "spell", "fall", "drowning".
            ignore_resistance (bool): If True, skip resistance entirely.
                Use for environmental damage (fall, drowning) that bypasses
                all resistances.

        Returns:
            int: Actual damage dealt after resistance/vulnerability.

        Resistance/Vulnerability Rules:
            - Positive resistance (e.g. 50% fire res) reduces damage.
              Even 1% resistance always saves at least 1 HP.
            - Negative resistance = vulnerability (e.g. -25% = 25% vuln).
              Even -1% vulnerability always adds at least 1 HP extra.
            - Final damage is always at least 1 HP (you always feel it).
            - get_resistance() clamps raw values to [-75, 75].

        Usage:
            # Combat damage (resistance applies):
            dealt = target.take_damage(10, damage_type="fire", cause="combat")

            # Environmental damage (no resistance):
            dealt = self.take_damage(20, cause="fall", ignore_resistance=True)

            # Spell damage (prefer apply_spell_damage() wrapper):
            dealt = target.take_damage(15, damage_type="cold", cause="spell")
        """
        damage = raw_damage

        if not ignore_resistance and damage_type and hasattr(self, "get_resistance"):
            resistance = self.get_resistance(damage_type)
            if resistance > 0:
                # Resistance: always saves at least 1 HP
                reduction = max(1, int(damage * resistance / 100))
                damage = damage - reduction
            elif resistance < 0:
                # Vulnerability: always adds at least 1 HP
                extra = max(1, int(damage * abs(resistance) / 100))
                damage = damage + extra

        # Minimum 1 HP damage always dealt
        damage = max(1, damage)
        self.hp = max(0, self.hp - damage)

        # Wimpy auto-flee (characters only — mobs don't have _wimpy_flee)
        if self.hp > 0 and hasattr(self, "_wimpy_flee"):
            self._wimpy_flee()

        if self.hp <= 0:
            # Mobs guard with is_alive, characters with _dying — check both
            already_dead = (
                not getattr(self, "is_alive", True)
            ) or getattr(self, "_dying", False)
            if not already_dead:
                self.die(cause, killer=killer)

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
