"""
CmdFlee — attempt to escape combat by fleeing through a random exit.

In combat: DEX check (d20 + DEX mod vs DC 10). On success, flee through
a random open exit and leave combat. On failure, lose the action and all
enemies get 1 round of advantage.

Height advantage: if no enemy has a melee weapon at the same height,
flee auto-succeeds (no DEX check needed).

Out of combat: comic panic run through a random exit (auto-success).
"""

import random

from evennia import Command

from commands.command import FCMCommandMixin
from utils.dice_roller import dice
from utils.movement_messages import FLEE_MESSAGES


FLEE_DC = 10


def _direction_of(exit_obj):
    """
    The direction to tell the fleeing character they went.

    Exits are keyed by their destination's name, so the key is no use here —
    "You flee Old Trade Way West!" reads as nonsense. Fall back to it only
    when an exit carries no direction at all.
    """
    return getattr(exit_obj, "direction", None) or exit_obj.key


def _get_open_exits(caller):
    """Return exits the caller can traverse (filters closed/locked doors)."""
    room = caller.location
    if not room:
        return []
    return [
        ex for ex in room.exits
        if ex.destination and ex.access(caller, "traverse")
    ]


class CmdFlee(FCMCommandMixin, Command):
    """
    Flee from combat through a random exit.

    Usage:
        flee

    In combat, roll a DEX check to escape. On success you flee
    through a random open exit. On failure you lose your action
    and enemies gain advantage against you.

    Out of combat, you panic and run in a random direction.
    """

    key = "flee"
    aliases = []
    help_category = "Combat"

    def func(self):
        caller = self.caller
        handler = caller.scripts.get("combat_handler")

        if handler:
            self._flee_in_combat(caller, handler[0])
        else:
            self._flee_out_of_combat(caller)

    def _flee_in_combat(self, caller, handler):
        """Attempt to flee from combat (DEX check)."""
        from combat.combat_utils import get_sides, get_weapon
        from combat.height_utils import can_reach_target

        # Held in place? Refuse before any side effects (broadcast, stop_combat, move).
        _, block_msg = caller.get_movement_blocking_effect()
        if block_msg:
            caller.msg(f"|rYou try to flee — {block_msg}|n")
            return

        exits = _get_open_exits(caller)
        if not exits:
            caller.msg("|rYou try to flee but there's nowhere to go!|n")
            return

        # Capture enemies before any movement changes rooms
        _, enemies = get_sides(caller)

        # Height advantage: if no enemy can melee us, flee auto-succeeds.
        # An enemy threatens melee if they're at the same height with a
        # melee weapon (or unarmed).
        any_melee_threat = False
        for enemy in enemies:
            if enemy.location != caller.location:
                continue
            e_weapon = get_weapon(enemy)
            e_type = getattr(e_weapon, "weapon_type", "melee") if e_weapon else "melee"
            if e_type == "melee" and can_reach_target(enemy, caller, e_weapon):
                any_melee_threat = True
                break

        # DEX check: d20 + DEX modifier vs DC (skipped if no melee threat)
        dex_mod = caller.get_attribute_bonus(caller.dexterity)
        roll = dice.roll("1d20") + dex_mod

        if not any_melee_threat or roll >= FLEE_DC:
            # Success — flee through random exit
            chosen = random.choice(exits)
            direction = _direction_of(chosen)

            caller.msg(f"|rYou flee {direction}!|n")

            # Stop combat before moving so weapon hooks fire in the right room
            handler.stop_combat()

            # Pull following pets out of combat and flee with owner. They move
            # quietly — the owner's own announce covers the group.
            source_room = caller.location
            for f in caller.get_followers(same_room=True):
                if getattr(f, "is_pet", False) and f.location == source_room:
                    if hasattr(f, "exit_combat"):
                        f.exit_combat()
                    f.move_to(chosen.destination, move_type="flee", quiet=True)

            # The room hears about this through the seam, not from here, so a
            # quiet caller can silence it and blind onlookers get "Someone".
            caller.move_to(
                chosen.destination,
                move_type="flee",
                exit_obj=chosen,
                **FLEE_MESSAGES,
            )

            # Check if remaining combatants should end combat
            for enemy in enemies:
                enemy_handlers = enemy.scripts.get("combat_handler")
                if enemy_handlers:
                    enemy_handlers[0]._check_stop_combat()
        else:
            # Failure — lose this action, enemies get advantage
            for enemy in enemies:
                enemy_handler = enemy.scripts.get("combat_handler")
                if enemy_handler:
                    enemy_handler[0].set_advantage(caller, rounds=1)

            caller.msg("|rYou try to flee but can't escape!|n")
            if caller.location:
                caller.location.msg_contents(
                    "$You() $conj(try) to run but cannot escape!",
                    from_obj=caller,
                    exclude=[caller],
                )

    def _flee_out_of_combat(self, caller):
        """Comic panic run — auto-success, random exit."""
        exits = _get_open_exits(caller)
        if not exits:
            caller.msg("|yYou panic but there's nowhere to run!|n")
            if caller.location:
                caller.location.msg_contents(
                    "$You() $conj(look) around in a panic but "
                    "there's nowhere to run!",
                    from_obj=caller,
                    exclude=[caller],
                )
            return

        chosen = random.choice(exits)
        direction = _direction_of(chosen)

        caller.msg(f"|yYou panic and flee {direction}!|n")

        # One-off wording, so it is passed rather than given a flag of its own.
        caller.move_to(
            chosen.destination,
            move_type="flee",
            exit_obj=chosen,
            msg_from="{name} panics and flees {direction} for no apparent reason!",
            msg_to="{name} arrives {direction}, in a blind panic.",
        )
