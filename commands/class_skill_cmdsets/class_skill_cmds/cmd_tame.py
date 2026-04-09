"""
CmdTame — tame a wild animal into a pet NFT.

Usage:
    tame <animal>

Requires ANIMAL_HANDLING skill at the mastery level required by
the target animal. On success, the wild mob is consumed and a
pet NFT is created that follows the tamer.
"""

import random

from enums.mastery_level import MasteryLevel
from enums.skills_enum import skills

from .cmd_skill_base import CmdSkillBase


# Mastery level required string → MasteryLevel int value
_MASTERY_REQUIRED = {
    "basic": MasteryLevel.BASIC.value,
    "skilled": MasteryLevel.SKILLED.value,
    "expert": MasteryLevel.EXPERT.value,
    "master": MasteryLevel.MASTER.value,
    "grandmaster": MasteryLevel.GRANDMASTER.value,
}


class CmdTame(CmdSkillBase):
    """
    Tame a wild animal.

    Usage:
        tame <animal>

    Attempt to tame a wild animal in the room. Requires ANIMAL_HANDLING
    skill at the mastery level required by the animal. Success is a
    contested roll: d20 + CHA modifier + mastery bonus vs the animal's
    tame DC. On success, the wild animal is consumed and a pet is
    created that follows you.
    """

    key = "tame"
    skill = skills.ANIMAL_HANDLING.value
    help_category = "Nature"

    def unskilled_func(self):
        self.caller.msg(
            "You don't know the first thing about taming animals. "
            "Find a trainer to learn Animal Handling."
        )

    def basic_func(self):
        self._do_tame(MasteryLevel.BASIC)

    def skilled_func(self):
        self._do_tame(MasteryLevel.SKILLED)

    def expert_func(self):
        self._do_tame(MasteryLevel.EXPERT)

    def master_func(self):
        self._do_tame(MasteryLevel.MASTER)

    def grandmaster_func(self):
        self._do_tame(MasteryLevel.GRANDMASTER)

    def _do_tame(self, mastery):
        """Shared taming logic for all mastery levels."""
        caller = self.caller

        # ── Must not be in combat ──
        if caller.scripts.get("combat_handler"):
            caller.msg("You can't tame an animal while fighting!")
            return

        # ── Find target ──
        if not self.args or not self.args.strip():
            caller.msg("Tame what? Usage: tame <animal>")
            return

        target = caller.search(self.args.strip(), location=caller.location)
        if not target:
            return  # search() already sent "Could not find" message

        # ── Validate tameable ──
        if not getattr(target.db, "tameable", False):
            caller.msg(f"{target.key} cannot be tamed.")
            return

        # ── Check mastery requirement ──
        required = _MASTERY_REQUIRED.get(
            getattr(target.db, "tame_mastery_required", "basic"), 0
        )
        if mastery.value < required:
            required_name = MasteryLevel(required).name
            caller.msg(
                f"{target.key} requires {required_name} mastery in "
                f"Animal Handling to tame."
            )
            return

        # ── Contested roll: d20 + CHA mod + mastery bonus vs tame_dc ──
        tame_dc = getattr(target.db, "tame_dc", 15)
        roll = random.randint(1, 20)
        cha_mod = caller.get_attribute_bonus(caller.charisma)
        total = roll + cha_mod + mastery.bonus

        pet_type = getattr(target.db, "tame_pet_type", None)

        if total >= tame_dc:
            self._tame_success(caller, target, pet_type, roll, cha_mod,
                               mastery, total, tame_dc)
        else:
            self._tame_failure(caller, target, roll, cha_mod, mastery,
                               total, tame_dc)

    def _tame_success(self, caller, target, pet_type, roll, cha_mod,
                      mastery, total, tame_dc):
        """Handle successful taming."""
        from blockchain.xrpl.services.nft import NFTService
        from typeclasses.mixins.nft_pet_mirror import NFTPetMirrorMixin

        if not pet_type:
            caller.msg("Error: animal has no pet type configured.")
            return

        # Assign a blank NFT token as this pet type
        try:
            token_id = NFTService.assign_item_type(pet_type, None, None)
        except Exception as err:
            caller.msg(f"Taming failed (system error): {err}")
            return

        # Announce success
        caller.msg(
            f"|gYou carefully approach {target.key}... it calms under "
            f"your hand. You have tamed it!|n "
            f"(Tame: {roll} + {cha_mod + mastery.bonus} = {total} "
            f"vs DC {tame_dc})"
        )
        if caller.location:
            caller.location.msg_contents(
                f"|y{caller.key} tames {target.key}!|n",
                exclude=[caller],
            )

        # Remove the wild mob
        target.delete()

        # Spawn the pet
        pet = NFTPetMirrorMixin.spawn_pet(
            token_id, caller.location, caller.key,
        )
        if pet:
            pet.start_following(caller)

    def _tame_failure(self, caller, target, roll, cha_mod, mastery,
                      total, tame_dc):
        """Handle failed taming attempt."""
        caller.msg(
            f"|y{target.key} shies away from your outstretched hand.|n "
            f"(Tame: {roll} + {cha_mod + mastery.bonus} = {total} "
            f"vs DC {tame_dc})"
        )
        if caller.location:
            caller.location.msg_contents(
                f"|y{caller.key} tries to tame {target.key}, but it "
                f"backs away nervously.|n",
                exclude=[caller],
            )
