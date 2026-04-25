"""
BasePet — base class for all pets in FCM.

Pets are NFT-backed actors that follow their owner through the game world.
They have HP (can be attacked and killed), respect room size restrictions,
and have a hunger timer.

Composes:
    NFTPetMirrorMixin — pet-specific NFT lifecycle (owner_key based, not location chain)
    FollowableMixin — follow chain, group combat entry
    BaseNPC — HP, level, room display, death, combat infrastructure

States:
    FOLLOWING — actively following owner room to room
    WAITING — stationary in a room, owner walked away or told it to stay
    STABLED — in AccountBank (no Evennia object in world)

Hunger:
    Pets have a fed_until timestamp. After it expires:
    0-8h past: hungry (warnings). 8-16h: starving (reduced stats).
    16h+: death (NFT destroyed).
"""

import time

from evennia.typeclasses.attributes import AttributeProperty

from enums.size import Size
from typeclasses.actors.npc import BaseNPC
from typeclasses.mixins.animal_speaker_mixin import AnimalSpeakerMixin
from typeclasses.mixins.followable import FollowableMixin
from typeclasses.mixins.nft_pet_mirror import NFTPetMirrorMixin


# Hunger thresholds in seconds past fed_until
_HUNGRY_AFTER = 0               # immediately after food runs out
_STARVING_AFTER = 8 * 3600      # 8 hours after food runs out
_DEATH_AFTER = 16 * 3600        # 16 hours after food runs out (24h total from last feed)


class BasePet(NFTPetMirrorMixin, FollowableMixin, AnimalSpeakerMixin, BaseNPC):
    """
    Base class for all pets. Subclass for specific pet types.

    Pets are always in the world (following/waiting) or in an AccountBank
    (stabled). They are NEVER in character.contents — enforced by
    NFTPetMirrorMixin.at_pre_move.
    """

    is_pet = True  # marker for filtering
    pet_type = AttributeProperty("")  # "dog", "horse", "mule" — for dot syntax matching

    # ── Pet state ──
    # owner_key is provided by NFTPetMirrorMixin
    pet_state = AttributeProperty("waiting")  # "following" / "waiting"
    fed_until = AttributeProperty(0)          # timestamp when food runs out

    # ── Room description ──
    room_description = AttributeProperty("stands here.")

    # ── Defaults ──
    is_immortal = AttributeProperty(False)  # pets can die

    def at_object_creation(self):
        super().at_object_creation()
        self.at_followable_init()
        # Start fed — 8 hours of food
        self.fed_until = time.time() + (8 * 3600)
        # Pets natively understand the animal language. Speakers don't need
        # SPEAK_WITH_ANIMALS to be heard by their pet — the pet always hears
        # them; SPEAK_WITH_ANIMALS only governs the *human* side of the link.
        langs = set(self.db.languages or set())
        langs.add("animal")
        self.db.languages = langs

    # ================================================================== #
    #  Room Display
    # ================================================================== #

    def get_room_description(self):
        """Return the pet's room description based on state.

        Returns empty string if mounted (rider's description includes mount).
        """
        if getattr(self, "is_mounted", False):
            return ""

        name = self.key
        state = self.pet_state
        if state == "following":
            return f"|c{name}|n {self.room_description}"
        elif state == "waiting":
            return f"|c{name}|n waits here patiently."
        return f"|c{name}|n is here."

    # ================================================================== #
    #  Follow / Stay
    # ================================================================== #

    def start_following(self, owner):
        """Begin following the owner character."""
        self.following = owner
        self.pet_state = "following"
        self.owner_key = owner.key

    def stop_following(self):
        """Stop following and wait in the current room."""
        self.following = None
        self.pet_state = "waiting"

    # ================================================================== #
    #  Hunger
    # ================================================================== #

    def feed(self, seconds=28800):
        """Feed the pet, resetting the hunger timer.

        Args:
            seconds: how long the food lasts (default 8 hours = 28800s)
        """
        self.fed_until = time.time() + seconds

    def check_hunger(self):
        """Check the pet's hunger state.

        Returns:
            str: "fed", "hungry", "starving", or "dead"
        """
        now = time.time()
        time_past = now - self.fed_until

        if time_past <= 0:
            return "fed"
        elif time_past < _STARVING_AFTER:
            return "hungry"
        elif time_past < _DEATH_AFTER:
            return "starving"
        return "dead"

    def get_hunger_display(self):
        """Return a coloured hunger status string."""
        state = self.check_hunger()
        if state == "fed":
            return "|gFed|n"
        elif state == "hungry":
            return "|yHungry|n"
        elif state == "starving":
            return "|rStarving!|n"
        return "|rDead|n"

    # ================================================================== #
    #  Death
    # ================================================================== #

    def die(self, cause="unknown", killer=None):
        """Handle pet death — clean up combat, notify owner, destroy NFT."""
        if not getattr(self, "is_alive", True):
            return

        self.is_alive = False
        self.following = None

        # Force dismount if being ridden
        if hasattr(self, "force_dismount"):
            self.force_dismount()

        # Clean up combat handler if in combat
        if hasattr(self, "exit_combat"):
            self.exit_combat()

        # Notify the room
        room = self.location
        if room:
            room.msg_contents(
                f"|r{self.key} has been slain!|n",
                from_obj=self,
            )

        # Notify the owner if online
        owner = self._get_owner_character()
        if owner and owner.sessions.count():
            owner.msg(f"|rYour pet {self.key} has died!|n")

        # Delete the object (triggers NFTPetMirrorMixin.at_object_delete → craft_input)
        self.delete()
