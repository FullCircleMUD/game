"""
FCMQuest — base class for all quests.

Inspired by EvAdventure's quest system. Class-based (not data-driven) so quest
logic can be as simple or complex as needed. Each quest step is a method named
``step_<stepname>`` that checks conditions and advances the quest.

Subclass patterns:
    Single-step:   Override one step method (template quests do this).
    Multi-step:    Multiple step_A, step_B, etc. — each sets current_step.
    Branching:     Step methods set different next steps based on conditions.
    Timed:         on_accept() starts a timer; step methods check deadline.
    Repeatable:    repeatable = True — can be re-accepted after completion.
    Chained:       prerequisites = ["quest_a"] — must complete others first.
    Custom:        Override progress() entirely for non-standard logic.
"""


class FCMQuest:
    """
    Base quest class. Subclass to define specific quests.

    Class attributes (override in subclass):
        key:            Unique registry key.
        name:           Display name.
        desc:           Description shown to the player.
        quest_type:     Category string — "guild", "main", "side", "repeatable".
        start_step:     Which step to begin on (default "start").
        reward_xp:      XP awarded on completion (0 = none).
        reward_gold:    Gold awarded on completion (0 = none).
        prerequisites:  List of quest keys that must be completed first.
        repeatable:     If True, can be re-accepted after completion.
    """

    key = "base_quest"
    name = "Base Quest"
    desc = "A quest."
    quest_type = "side"
    start_step = "start"
    reward_xp = 0
    reward_gold = 0
    reward_bread = 0   # Bread (resource ID 3) awarded on completion
    prerequisites = []
    repeatable = False
    # Account-level cap: max completions per account across all characters/remorts.
    # None = uncapped. Set to an integer (e.g. 10) on starter quests to prevent
    # create-delete farming. Checked silently — capped players see no offer.
    account_cap = None

    # Default help strings (can be overridden per step)
    help_start = "Begin your quest."
    help_completed = "You have completed this quest."
    help_abandoned = "You have abandoned this quest."
    help_failed = "You have failed this quest."

    def __init__(self, quester, handler=None):
        self.quester = quester
        self._handler = handler
        self.data = self.handler.load_quest_data(self.key)
        self._current_step = self.get_data("current_step") or self.start_step

    # ── Handler access ──

    @property
    def handler(self):
        return self._handler if self._handler else self.quester.quests

    # ── Step tracking ──

    @property
    def current_step(self):
        return self._current_step

    @current_step.setter
    def current_step(self, step_name):
        self._current_step = step_name
        self.add_data("current_step", step_name)

    # ── Status ──

    @property
    def status(self):
        return self.get_data("status", "started")

    @status.setter
    def status(self, value):
        self.add_data("status", value)

    @property
    def is_completed(self):
        return self.status == "completed"

    @property
    def is_abandoned(self):
        return self.status == "abandoned"

    @property
    def is_failed(self):
        return self.status == "failed"

    # ── Data persistence ──

    def add_data(self, key, value):
        """Store persistent quest data."""
        self.data[key] = value
        self.handler.save_quest_data(self.key)

    def get_data(self, key, default=None):
        """Retrieve persistent quest data."""
        return self.data.get(key, default)

    def remove_data(self, key):
        """Remove persistent quest data."""
        self.data.pop(key, None)
        self.handler.save_quest_data(self.key)

    # ── Acceptance ──

    @classmethod
    def can_accept(cls, character):
        """Check if a character can accept this quest.

        Returns:
            (bool, str): (can_accept, reason_if_not)
            A False with an empty reason string means silently suppressed
            (account cap reached) — the caller should show no message.
        """
        # Account-level cap check — silent suppression (no error shown to player)
        if cls.account_cap is not None:
            account = getattr(character, "account", None)
            if account:
                counts = account.attributes.get(
                    "quest_completion_counts", default={}
                ) or {}
                if counts.get(cls.key, 0) >= cls.account_cap:
                    return (False, "")

        for prereq_key in cls.prerequisites:
            if not character.quests.is_completed(prereq_key):
                from world.quests import get_quest

                prereq = get_quest(prereq_key)
                prereq_name = prereq.name if prereq else prereq_key
                return (False, f"You must complete '{prereq_name}' first.")

        if character.quests.has(cls.key):
            quest = character.quests.get(cls.key)
            if quest.is_completed and not cls.repeatable:
                return (False, "You have already completed this quest.")
            if not quest.is_completed and not quest.is_abandoned and not quest.is_failed:
                return (False, "You are already on this quest.")

        return (True, "")

    def on_accept(self):
        """Called when quest is first accepted. Override for setup logic."""
        pass

    # ── Progress ──

    def progress(self, *args, **kwargs):
        """Check current step. Called by quest handler on relevant events."""
        if self.is_completed or self.is_abandoned or self.is_failed:
            return
        step_method = getattr(self, f"step_{self.current_step}", None)
        if step_method:
            step_method(*args, **kwargs)

    # ── Completion ──

    def complete(self):
        """Mark quest complete and apply rewards."""
        self.status = "completed"
        self.on_complete()
        if self.reward_xp and hasattr(self.quester, "at_gain_experience_points"):
            self.quester.at_gain_experience_points(self.reward_xp)
        if self.reward_gold and hasattr(self.quester, "receive_gold_from_reserve"):
            self.quester.receive_gold_from_reserve(self.reward_gold)
            self._register_quest_debt("gold", "gold", self.reward_gold)
        if self.reward_bread and hasattr(self.quester, "receive_resource_from_reserve"):
            self.quester.receive_resource_from_reserve(3, self.reward_bread)
            self.quester.msg(
                f"|gYou receive {self.reward_bread} "
                f"{'Bread' if self.reward_bread == 1 else 'Breads'}.|n"
            )
            self._register_quest_debt("resources", "3", self.reward_bread)
        # Increment account-level completion counter (for starter quest caps)
        if self.__class__.account_cap is not None:
            account = getattr(self.quester, "account", None)
            if account:
                counts = account.attributes.get(
                    "quest_completion_counts", default={}
                ) or {}
                counts[self.key] = counts.get(self.key, 0) + 1
                account.attributes.add("quest_completion_counts", counts)

    @staticmethod
    def _register_quest_debt(category, key, amount):
        """Register quest reward debt with the spawn system.

        Graceful no-op if the spawn service isn't running yet (e.g. in tests).
        """
        from blockchain.xrpl.services.spawn.service import get_spawn_service

        service = get_spawn_service()
        if service:
            service.allocate_quest_reward(category, key, amount)

    def on_complete(self):
        """Called on completion. Override for custom logic."""
        pass

    def abandon(self):
        """Abandon the quest."""
        self.status = "abandoned"
        self.cleanup()

    def fail(self):
        """Fail the quest."""
        self.status = "failed"
        self.cleanup()

    def cleanup(self):
        """Called on completion or abandonment for cleanup."""
        pass

    # ── Help ──

    def help(self, *args, **kwargs):
        """Get help text for the current step or status."""
        if self.status in ("completed", "abandoned", "failed"):
            help_resource = getattr(
                self, f"help_{self.status}", f"You have {self.status} this quest."
            )
        else:
            help_resource = getattr(
                self, f"help_{self.current_step}", "No help available."
            )

        if callable(help_resource):
            return help_resource(*args, **kwargs)
        return str(help_resource)

    # ── Default step ──

    def step_start(self, *args, **kwargs):
        """Default start step — completes immediately. Override in subclass."""
        self.complete()
