"""
Bobbin Goode — leader of the merry bandits camped south of Millholm.

A theatrical Robin Hood pastiche (with a strong dose of Mel Brooks's
*Men in Tights*). Bobbin lives at the Common Fire and performs a
scripted song-and-introduction routine the first time a player walks
into the room (within a 10-minute cooldown window). After the routine,
normal LLM-driven conversation takes over via ``LLMMixin``.
"""

import time

from evennia.typeclasses.attributes import AttributeProperty
from evennia.utils.utils import delay

from enums.damage_type import DamageType
from enums.mastery_level import MasteryLevel
from typeclasses.actors.mobs.bandit_base import BobbinBandit
from typeclasses.items.mob_items.mob_item import MobItem


class BobbinGoode(BobbinBandit):
    """The frontman. Charismatic, theatrical, occasionally improvising lyrics."""

    room_description = AttributeProperty(
        "lounges by the common fire in green-and-gold striped tights, "
        "watching the camp with a performer's quick eye."
    )

    # ── LLM ──
    llm_prompt_file = AttributeProperty("bobbin_goode.md")
    llm_personality = AttributeProperty(
        "Theatrical, quick-witted, and just earnest enough to be loveable. "
        "Speaks in performer's cadences. Drops into improvised verses without "
        "warning. Vain about the tights, the hair, and the manifesto. "
        "Genuinely committed to the 'rob the deserving, share with the rest' "
        "code, even when the others quietly sand the corners off it."
    )

    # ── Stats — charismatic L5 swordsman ──
    base_strength = AttributeProperty(12)
    strength = AttributeProperty(12)
    base_dexterity = AttributeProperty(14)
    dexterity = AttributeProperty(14)
    base_constitution = AttributeProperty(12)
    constitution = AttributeProperty(12)
    base_intelligence = AttributeProperty(13)
    intelligence = AttributeProperty(13)
    base_wisdom = AttributeProperty(11)
    wisdom = AttributeProperty(11)
    base_charisma = AttributeProperty(18)
    charisma = AttributeProperty(18)
    base_armor_class = AttributeProperty(13)
    armor_class = AttributeProperty(13)
    base_hp_max = AttributeProperty(40)
    hp_max = AttributeProperty(40)
    hp = AttributeProperty(40)
    level = AttributeProperty(5)
    initiative_speed = AttributeProperty(3)

    damage_dice = AttributeProperty("1d6")
    attack_message = AttributeProperty("flourishes a blade and slashes at")
    loot_gold_max = AttributeProperty(8)

    default_weapon_masteries = {"shortsword": MasteryLevel.SKILLED.value}

    # ── Performance routine ──
    PERFORMANCE_COOLDOWN_SECONDS = 600  # 10 min between full song-and-intros

    def at_object_creation(self):
        super().at_object_creation()
        weapon = MobItem.spawn_mob_item("bronze_shortsword", location=self)
        if weapon:
            self.wear(weapon)

    # ==================================================================
    #  Entry song-and-introduction routine
    # ==================================================================

    def at_new_arrival(self, arriving_obj):
        """Player entered the Common Fire — kick off the song chain."""
        if not getattr(arriving_obj, "is_pc", False):
            return
        if not self._performance_can_start():
            return

        # Don't restart for back-to-back arrivals
        last = self.db.last_performance_at or 0.0
        now = time.time()
        if now - last < self.PERFORMANCE_COOLDOWN_SECONDS:
            return
        self.db.last_performance_at = now

        delay(0.5, self._song_setup)

    def _performance_can_start(self):
        return (
            self.is_alive
            and self.location is not None
            and not self.scripts.get("combat_handler")
        )

    def _song_continues(self):
        """Re-checked at every step; aborts cleanly if Bobbin is killed,
        moved, or dragged into combat mid-verse."""
        return self._performance_can_start()

    def _song_setup(self):
        if not self._song_continues():
            return
        self.location.msg_contents(
            f"|c{self.key}|n stands by the fire with eyes shut and one hand "
            f"on his heart, plainly mid-performance — he has not yet noticed "
            f"your arrival."
        )
        delay(2, self._song_line_1)

    def _song_line_1(self):
        if not self._song_continues():
            return
        self.location.msg_contents(
            f'|c{self.key}|n sings, |y"♪ We\'re men! We\'re |Mmen|y in '
            f'|Mtights|y! ♪"|n'
        )
        delay(3, self._song_line_2)

    def _song_line_2(self):
        if not self._song_continues():
            return
        self.location.msg_contents(
            f'|c{self.key}|n sings, |y"♪ We roam around the forest looking '
            f'for— uh— |MFIGHTS|y! ♪"|n'
        )
        delay(4, self._song_line_3)

    def _song_line_3(self):
        if not self._song_continues():
            return
        self.location.msg_contents(
            f'|c{self.key}|n sings, |y"♪ We rob from the rich, and we— well, '
            f'we mostly *keep* it actually — NO WAIT — give to the |MPOOR|y, '
            f'that\'s |Mright|y! ♪"|n'
        )
        delay(4, self._song_line_4)

    def _song_line_4(self):
        if not self._song_continues():
            return
        self.location.msg_contents(
            f'|c{self.key}|n sings, |y"♪ We may look like sissies but— "|n '
            f'|x...the verse trails off.|n'
        )
        delay(2, self._notice_player)

    def _notice_player(self):
        if not self._song_continues():
            return
        self.location.msg_contents(
            f"|c{self.key}|n opens his eyes mid-pose, sees he has an audience, "
            f"and his face flushes a deep, betrayed pink. He drops the heroic "
            f"stance, clears his throat, and adjusts his cap."
        )
        delay(1, self._introduce)

    def _introduce(self):
        if not self._song_continues():
            return
        self.location.msg_contents(
            f'|c{self.key}|n says, "Ah — friend! I, ah — I didn\'t see you '
            f'come in. Bobbin Goode, at your service. Welcome to the camp."'
        )
