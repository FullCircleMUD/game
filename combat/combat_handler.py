"""
CombatHandler — per-combatant Evennia Script for real-time combat.

Each combatant in combat gets their own CombatHandler script. The handler
manages action queuing, ticker-driven execution, advantage/disadvantage
tracking, and combat lifecycle hooks.

"In combat" = has a combat_handler script. No script = bystander.
"""

from evennia import TICKER_HANDLER
from evennia.scripts.scripts import DefaultScript
from evennia.typeclasses.attributes import AttributeProperty


class CombatHandler(DefaultScript):
    """
    Per-combatant combat handler.

    Stored as a script on the combatant object. Manages:
        - Action queue (attack, hold, flee)
        - Ticker for action execution
        - Advantage/disadvantage tracking per-target
        - Combat start/end lifecycle hooks on weapons
    """

    # Persisted state
    action_dict = AttributeProperty({"key": "hold", "dt": 0})
    advantage_against = AttributeProperty(dict)       # {target_id: int} rounds remaining
    disadvantage_against = AttributeProperty(dict)     # {target_id: int} rounds remaining
    skip_next_action = AttributeProperty(False)        # single-round skip (dodge)
    # Stun/prone/shield now managed by EffectsManagerMixin named effects
    parries_remaining = AttributeProperty(0)
    parry_advantage = AttributeProperty(False)         # grandmaster: advantage on parry rolls
    stun_checks_remaining = AttributeProperty(0)       # unarmed/nunchaku stun attempts left this round
    disarm_checks_remaining = AttributeProperty(0)      # sai disarm attempts left this round
    executioner_used = AttributeProperty(False)         # GM greatsword: 1 free attack on kill/round
    stab_used = AttributeProperty(False)               # thief stab: once per round
    bash_cooldown = AttributeProperty(0)                # rounds until bash can be used again
    pummel_cooldown = AttributeProperty(0)              # rounds until pummel can be used again
    taunt_cooldown = AttributeProperty(0)               # rounds until taunt can be used again
    protecting = AttributeProperty(None)                 # dbref (int) of character being protected
    reach_counters_remaining = AttributeProperty(0)       # spear: reach counter-attacks left this round
    bonus_attack_dice = AttributeProperty("")           # e.g. "6d6" — consumed on next attack
    _advantage_used = AttributeProperty(dict)          # {target_id: True} consumed by attack this tick
    _disadvantage_used = AttributeProperty(dict)       # {target_id: True} consumed by attack this tick

    def at_script_creation(self):
        self.key = "combat_handler"
        self.persistent = True

    # ================================================================== #
    #  Combat Lifecycle
    # ================================================================== #

    def start_combat(self):
        """Fire at_combat_start on wielded weapon and set fighting position."""
        from combat.combat_utils import get_weapon
        weapon = get_weapon(self.obj)
        if weapon:
            weapon.at_combat_start(self.obj)
        self.obj.position = "fighting"
        self.obj.msg("|rYou enter combat!|n")

    def auto_attack_first_enemy(self):
        """Auto-queue repeating attack on the first enemy from get_sides().
        Called after all combat handlers are created so sides are populated."""
        if self.action_dict and self.action_dict.get("key") == "attack":
            return  # already has an attack queued
        from combat.combat_utils import get_weapon, get_sides
        _, enemies = get_sides(self.obj)
        if enemies:
            weapon = get_weapon(self.obj)
            speed = getattr(weapon, "speed", 1.0) if weapon else 1.0
            dt = max(2, int(4 / speed))
            self.queue_action({
                "key": "attack",
                "target": enemies[0],
                "dt": dt,
                "repeat": True,
            })

    def stop_combat(self):
        """Fire at_combat_end, clean up combat effects, stop ticker, delete handler."""
        from combat.combat_utils import get_weapon
        weapon = get_weapon(self.obj)
        if weapon:
            weapon.at_combat_end(self.obj)
        # Clean up all combat-round-based effects (stun, prone, shield, slowed, etc.)
        if hasattr(self.obj, "clear_combat_effects"):
            self.obj.clear_combat_effects()
        self._stop_ticker()
        self.obj.position = "standing"
        self.obj.ndb.combat_target = None
        self.obj.msg("|gCombat has ended.|n")
        self.delete()

    # ================================================================== #
    #  Action Queue
    # ================================================================== #

    def queue_action(self, action_dict):
        """
        Queue a new action. Cancels current ticker, starts new one.

        Args:
            action_dict: dict with keys:
                key (str): "attack", "hold", "flee"
                target (obj): target for attack actions
                dt (int): seconds between action executions
                repeat (bool): if True, action repeats until replaced
        """
        self.action_dict = action_dict
        # Track current target for room display ("is here, fighting X!")
        target = action_dict.get("target")
        if target:
            self.obj.ndb.combat_target = target
        dt = action_dict.get("dt", 0)
        self._stop_ticker()
        if dt > 0:
            self._start_ticker(dt)

    def execute_next_action(self):
        """Called each tick. Resolves the queued action."""
        from combat.combat_utils import execute_attack

        # Reset per-round flags
        self.executioner_used = False
        self.stab_used = False

        # Decrement multi-round ability cooldowns
        if self.bash_cooldown > 0:
            self.bash_cooldown -= 1
        if self.pummel_cooldown > 0:
            self.pummel_cooldown -= 1
        if self.taunt_cooldown > 0:
            self.taunt_cooldown -= 1

        # Reset parries for this round based on wielded weapon
        from combat.combat_utils import get_weapon
        weapon = get_weapon(self.obj)
        if weapon and hasattr(weapon, "get_parries_per_round"):
            self.parries_remaining = weapon.get_parries_per_round(self.obj)
            self.parry_advantage = weapon.get_parry_advantage(self.obj)
        else:
            self.parries_remaining = 0
            self.parry_advantage = False

        # Reset reach counters for this round (spear)
        if weapon and hasattr(weapon, "get_reach_counters_per_round"):
            self.reach_counters_remaining = weapon.get_reach_counters_per_round(self.obj)

        # Reset lance prone flag for this round (stored on character ndb)
        self.obj.ndb.lance_prone_used = False

        # Reset stun checks for this round (unarmed, nunchaku)
        if weapon and hasattr(weapon, "get_stun_checks_per_round"):
            self.stun_checks_remaining = weapon.get_stun_checks_per_round(self.obj)
        else:
            self.stun_checks_remaining = 0

        # Reset disarm checks for this round (sai)
        if weapon and hasattr(weapon, "get_disarm_checks_per_round"):
            self.disarm_checks_remaining = weapon.get_disarm_checks_per_round(self.obj)
        else:
            self.disarm_checks_remaining = 0

        # Let the combatant make a decision before the action resolves.
        # Mobs use this to sometimes dodge, flee, etc. instead of attacking.
        if hasattr(self.obj, "at_combat_tick"):
            self.obj.at_combat_tick(self)

        # Multi-round skip (stun/prone/paralysis/entangle) — managed by EffectsManagerMixin named effects
        if (self.obj.has_effect("stunned") or self.obj.has_effect("prone")
                or self.obj.has_effect("paralysed") or self.obj.has_effect("entangled")):
            self.bonus_attack_dice = ""  # clear pending stab bonus
        # Single-round skip (dodge)
        elif self.skip_next_action:
            self.skip_next_action = False
            self.bonus_attack_dice = ""  # clear pending stab bonus
        else:
            action = self.action_dict
            if action and action["key"] == "attack":
                target = action.get("target")
                if target and getattr(target, "hp", 0) > 0 and target.location == self.obj.location:
                    # --- SLOWED check: cap to 1 attack, no off-hand ---
                    is_slowed = self.obj.has_effect("slowed")
                    if is_slowed:
                        self.obj.msg(
                            "|B*SLOWED* Your movements are sluggish...|n"
                        )
                        if self.obj.location:
                            self.obj.location.msg_contents(
                                f"|B{self.obj.key} moves sluggishly, "
                                f"slowed by magic.|n",
                                exclude=[self.obj],
                            )

                    # --- Main hand attacks ---
                    attacks = self.obj.effective_attacks_per_round
                    if is_slowed:
                        attacks = 1
                    for _ in range(attacks):
                        if getattr(target, "hp", 0) <= 0:
                            break
                        execute_attack(self.obj, target)

                    # --- Off-hand attacks (dual-wield) ---
                    # Main weapon mastery determines off-hand attack count + penalty
                    # SLOWED blocks off-hand entirely
                    if weapon and getattr(target, "hp", 0) > 0 and not is_slowed:
                        from combat.combat_utils import get_offhand_weapon
                        offhand_count = weapon.get_offhand_attacks(self.obj)
                        if offhand_count > 0:
                            offhand_weapon = get_offhand_weapon(self.obj)
                            if offhand_weapon:
                                offhand_penalty = weapon.get_offhand_hit_modifier(self.obj)
                                for _ in range(offhand_count):
                                    if getattr(target, "hp", 0) <= 0:
                                        break
                                    execute_attack(
                                        self.obj, target,
                                        weapon_override=offhand_weapon,
                                        hit_modifier=offhand_penalty,
                                    )
                else:
                    # Target gone or dead — auto-retarget next enemy
                    from combat.combat_utils import get_sides
                    _, remaining_enemies = get_sides(self.obj)
                    if remaining_enemies:
                        new_target = remaining_enemies[0]
                        self.obj.msg(
                            f"|yYou turn to attack "
                            f"{new_target.get_display_name(self.obj)}!|n"
                        )
                        action["target"] = new_target
                        self.obj.ndb.combat_target = new_target
                    else:
                        # No enemies left — _check_stop_combat() will clean up
                        self.queue_action({"key": "hold", "dt": 0})

                if not action.get("repeat", False):
                    self.queue_action({"key": "hold", "dt": 0})

        # Tick all combat-round-based named effects (shield, stun, prone, slowed, etc.)
        if hasattr(self.obj, "tick_combat_round"):
            self.obj.tick_combat_round()

        # Tick poison DoT (if any — hybrid timing, combat handler drives in-combat ticks)
        poison_scripts = self.obj.scripts.get("poison_dot")
        if poison_scripts:
            poison_scripts[0].tick_poison()

        # Tick acid DoT (if any — combat-round only, from Acid Arrow spell)
        acid_scripts = self.obj.scripts.get("acid_dot")
        if acid_scripts:
            acid_scripts[0].tick_acid()

        # Tick blur (if any — sets disadvantage on enemies each round)
        blur_scripts = self.obj.scripts.get("blur_effect")
        if blur_scripts:
            blur_scripts[0].tick_blur()

        # Always decrement advantage/disadvantage counts and check combat end
        self.decrement_advantages()
        self._check_stop_combat()

    # ================================================================== #
    #  Advantage / Disadvantage (count-based)
    #
    #  Each entry is {target_id: int} where the int is rounds remaining.
    #  Consumed 1 per attack against that target. At end of each tick,
    #  any targets NOT consumed by an attack are decremented by 1
    #  (minimum 1 per round). Entries at 0 are pruned.
    # ================================================================== #

    def has_advantage(self, target):
        return (self.advantage_against or {}).get(target.id, 0) > 0

    def has_disadvantage(self, target):
        return (self.disadvantage_against or {}).get(target.id, 0) > 0

    def set_advantage(self, target, rounds=1):
        """Set advantage rounds against target. Takes max of existing and new.
        Pass rounds=0 to remove."""
        adv = dict(self.advantage_against or {})
        if rounds > 0:
            adv[target.id] = max(adv.get(target.id, 0), rounds)
        else:
            adv.pop(target.id, None)
        self.advantage_against = adv

    def set_disadvantage(self, target, rounds=1):
        """Set disadvantage rounds against target. Takes max of existing and new.
        Pass rounds=0 to remove."""
        dis = dict(self.disadvantage_against or {})
        if rounds > 0:
            dis[target.id] = max(dis.get(target.id, 0), rounds)
        else:
            dis.pop(target.id, None)
        self.disadvantage_against = dis

    def consume_advantage(self, target):
        """Consume 1 round of advantage against target (called on attack)."""
        adv = dict(self.advantage_against or {})
        count = adv.get(target.id, 0)
        if count > 0:
            adv[target.id] = count - 1
            if adv[target.id] <= 0:
                adv.pop(target.id)
            self.advantage_against = adv
            used = dict(self._advantage_used or {})
            used[target.id] = True
            self._advantage_used = used

    def consume_disadvantage(self, target):
        """Consume 1 round of disadvantage against target (called on attack)."""
        dis = dict(self.disadvantage_against or {})
        count = dis.get(target.id, 0)
        if count > 0:
            dis[target.id] = count - 1
            if dis[target.id] <= 0:
                dis.pop(target.id)
            self.disadvantage_against = dis
            used = dict(self._disadvantage_used or {})
            used[target.id] = True
            self._disadvantage_used = used

    def decrement_advantages(self):
        """End-of-tick: decrement any advantage/disadvantage not consumed by
        an attack this tick (minimum 1 per round rule). Then reset tracking."""
        used_adv = self._advantage_used or {}
        adv = dict(self.advantage_against or {})
        for tid in list(adv.keys()):
            if tid not in used_adv:
                adv[tid] -= 1
                if adv[tid] <= 0:
                    del adv[tid]
        self.advantage_against = adv

        used_dis = self._disadvantage_used or {}
        dis = dict(self.disadvantage_against or {})
        for tid in list(dis.keys()):
            if tid not in used_dis:
                dis[tid] -= 1
                if dis[tid] <= 0:
                    del dis[tid]
        self.disadvantage_against = dis

        self._advantage_used = {}
        self._disadvantage_used = {}

    # ================================================================== #
    #  Combat End Detection
    # ================================================================== #

    def _check_stop_combat(self):
        """End combat if one side has no living combatants in room."""
        from combat.combat_utils import get_sides

        allies, enemies = get_sides(self.obj)
        if not enemies:
            # No enemies left — end combat for all allies
            for ally in allies:
                handlers = ally.scripts.get("combat_handler")
                if handlers:
                    handlers[0].stop_combat()

    # ================================================================== #
    #  Ticker Management
    # ================================================================== #

    def _start_ticker(self, dt):
        TICKER_HANDLER.add(
            interval=dt,
            callback=self._on_tick,
            idstring=f"combat_{self.obj.id}",
        )

    def _stop_ticker(self):
        try:
            TICKER_HANDLER.remove(
                interval=self.action_dict.get("dt", 0),
                callback=self._on_tick,
                idstring=f"combat_{self.obj.id}",
            )
        except KeyError:
            pass

    def _on_tick(self, *args, **kwargs):
        """Ticker callback — executes the queued action."""
        if getattr(self.obj, "hp", 0) <= 0:
            self.stop_combat()
            return
        self.execute_next_action()
