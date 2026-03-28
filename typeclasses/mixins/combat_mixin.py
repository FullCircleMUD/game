"""
CombatMixin — composable combat capability for any actor.

Provides combat handler access, combat entry/exit, and health helpers.
Composed into both FCMCharacter and CombatMob (and any future hybrid NPC
that needs to fight).

Non-PC actors automatically receive CmdSetMobCombat (attack, dodge, flee)
at creation. PCs keep their existing command pipeline via CmdSetCharacterCustom.
"""


class CombatMixin:
    """
    Mixin providing combat handler access and combat initiation.

    Compose into any actor that should participate in combat.
    PCs get commands from CmdSetCharacterCustom; non-PCs get CmdSetMobCombat
    injected at creation.
    """

    # ── Combat handler accessors ──

    def get_combat_handler(self):
        """Return the active CombatHandler script, or None."""
        handlers = self.scripts.get("combat_handler")
        return handlers[0] if handlers else None

    @property
    def is_in_combat(self):
        """True if this actor has an active combat handler."""
        return bool(self.scripts.get("combat_handler"))

    # ── Health helpers ──

    @property
    def hp_fraction(self):
        """Current HP as a fraction of max HP (0.0 to 1.0)."""
        max_hp = self.effective_hp_max
        if max_hp <= 0:
            return 0
        return self.hp / max_hp

    @property
    def is_low_health(self):
        """True if below aggro_hp_threshold (default 50%)."""
        threshold = getattr(self, "aggro_hp_threshold", 0.5)
        return self.hp_fraction < threshold

    # ── Combat entry/exit ──

    def enter_combat(self, target):
        """Enter combat with target. Creates combat handlers on both sides."""
        from combat.combat_utils import enter_combat
        return enter_combat(self, target)

    def exit_combat(self):
        """Stop combat handler cleanly if present."""
        handler = self.get_combat_handler()
        if handler:
            handler.stop_combat()

    def initiate_attack(self, target):
        """
        Programmatic attack entry — used by AI, LLM, or any code that
        needs to trigger an attack.

        Uses execute_cmd() so the attack goes through CmdAttack →
        enter_combat() → CombatHandler. If already actively attacking,
        this is a no-op (let the handler drive).
        """
        if not getattr(self, "is_alive", True) or not self.location:
            return
        if not target or not getattr(target, "hp", None) or target.hp <= 0:
            return

        # Already actively attacking? Let the handler drive.
        handler = self.get_combat_handler()
        if handler:
            action = handler.action_dict
            if action.get("key") == "attack":
                return  # already auto-attacking

        self.execute_cmd(f"attack {target.key}")

    # ── CmdSet injection for non-PCs ──

    def at_object_creation(self):
        super().at_object_creation()
        if not getattr(self, "is_pc", False):
            # Override call:true() from BaseNPC — mob commands shouldn't
            # merge into nearby players' command pools.
            self.locks.add("call:false()")
            from commands.npc_cmds.cmdset_mob_combat import CmdSetMobCombat
            self.cmdset.add(CmdSetMobCombat, persistent=True)
