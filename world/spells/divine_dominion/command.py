"""
Command — divine dominion spell, available from BASIC mastery.

Issues a one-word divine command that compels a target to obey.
Contested WIS check — caster d20 + WIS + mastery vs target d20 + WIS.

Command words:
    halt   — STUNNED (action denial, no advantage to enemies)
    grovel — PRONE (action denial + advantage to all enemies)
    drop   — force-drops wielded weapon (mobs: to floor, players: to inventory)
    flee   — forces target to execute the flee command

Halt/Grovel duration scaling:
    BASIC(1):   halt 1 / grovel 1
    SKILLED(2): halt 2 / grovel 1
    EXPERT(3):  halt 2 / grovel 2
    MASTER(4):  halt 3 / grovel 2
    GM(5):      halt 3 / grovel 3

Drop and Flee are instant — no duration scaling.

Mana: 5 / 8 / 10 / 14 / 16
Cooldown: 0 (spammable).
Combat-only. HUGE+ immune.
"""

from enums.size import Size
from enums.mastery_level import MasteryLevel
from enums.skills_enum import skills
from combat.combat_utils import force_drop_weapon, get_actor_size
from utils.dice_roller import dice
from world.spells.base_spell import Spell
from world.spells.registry import register_spell

_VALID_COMMANDS = {"halt", "grovel", "drop", "flee"}
_IMMUNE_SIZES = {Size.HUGE, Size.GARGANTUAN}

# Duration scaling: tier → rounds
_HALT_ROUNDS = {1: 1, 2: 2, 3: 2, 4: 3, 5: 3}
_GROVEL_ROUNDS = {1: 1, 2: 1, 3: 2, 4: 2, 5: 3}


@register_spell
class Command(Spell):
    key = "command"
    aliases = ["cmd"]
    name = "Command"
    school = skills.DIVINE_DOMINION
    min_mastery = MasteryLevel.BASIC
    mana_cost = {1: 5, 2: 8, 3: 10, 4: 14, 5: 16}
    target_type = "actor_hostile"
    has_spell_arg = True
    cooldown = 0
    description = "Issues a divine command that compels the target to obey."
    mechanics = (
        "Usage: cast command <halt|grovel|drop|flee> <target>\n"
        "Contested WIS check. On failure, target obeys the command.\n"
        "Halt = stun, Grovel = prone, Drop = disarm, Flee = forced flee.\n"
        "Combat-only. HUGE+ immune."
    )

    def _execute(self, caster, target, **kwargs):
        tier = self.get_caster_tier(caster)

        # --- Validate command word ---
        command_word = kwargs.get("spell_arg")
        if not command_word or command_word not in _VALID_COMMANDS:
            caster.mana += self.mana_cost.get(tier, 0)
            valid = ", ".join(sorted(_VALID_COMMANDS))
            return (False, {
                "first": (
                    f"|rCommand what? "
                    f"Usage: |wcast command <{valid}> <target>|n"
                ),
                "second": None,
                "third": None,
            })

        # --- Combat-only gate ---
        if not target.scripts.get("combat_handler"):
            caster.mana += self.mana_cost.get(tier, 0)
            return (False, {
                "first": "|rCommand only works in combat.|n",
                "second": None,
                "third": None,
            })

        # --- Size gate ---
        target_size = get_actor_size(target)
        if target_size in _IMMUNE_SIZES:
            return (True, {
                "first": (
                    f"|Y{target.key} is too massive to be commanded!|n"
                ),
                "second": (
                    f"|Y{caster.key} tries to command you, but your "
                    f"will is unshakeable!|n"
                ),
                "third": (
                    f"|Y{caster.key} tries to command {target.key}, "
                    f"but the creature is too massive to be compelled!|n"
                ),
            })

        # --- Contested WIS vs WIS check ---
        caster_roll = dice.roll("1d20")
        caster_wis = caster.get_attribute_bonus(caster.wisdom)
        mastery_bonus = MasteryLevel(tier).bonus
        caster_total = caster_roll + caster_wis + mastery_bonus

        target_roll = dice.roll("1d20")
        target_wis = target.get_attribute_bonus(target.wisdom)
        target_total = target_roll + target_wis

        # --- Contested check failed ---
        if caster_total <= target_total:
            return (True, {
                "first": (
                    f"|YYou command {target.key} to {command_word}, "
                    f"but they resist your divine authority!|n"
                ),
                "second": (
                    f"|Y{caster.key} commands you to {command_word}, "
                    f"but you shake off the compulsion!|n"
                ),
                "third": (
                    f"|Y{caster.key} commands {target.key} to "
                    f"{command_word}, but they resist!|n"
                ),
            })

        # --- Apply command effect ---
        effect_msg = self._apply_command(
            caster, target, command_word, tier,
        )

        return (True, effect_msg)

    def _apply_command(self, caster, target, word, tier):
        """Dispatch to the correct mechanic for the command word."""
        if word == "halt":
            return self._cmd_halt(caster, target, tier)
        elif word == "grovel":
            return self._cmd_grovel(caster, target, tier)
        elif word == "drop":
            return self._cmd_drop(caster, target)
        elif word == "flee":
            return self._cmd_flee(caster, target)

    def _cmd_halt(self, caster, target, tier):
        """HALT — apply STUNNED (action denial)."""
        rounds = _HALT_ROUNDS.get(tier, 1)
        applied = target.apply_stunned(rounds, source=caster)
        s = "s" if rounds != 1 else ""

        if applied:
            first = (
                f"|Y*COMMAND: HALT* You speak with divine authority and "
                f"{target.key} freezes in place!\n"
                f"*STUNNED* ({rounds} round{s})|n"
            )
        else:
            first = (
                f"|YYou command {target.key} to halt, but they are "
                f"already stunned!|n"
            )

        return {
            "first": first,
            "second": (
                f"|Y{caster.key} speaks with divine authority — "
                f"\"HALT!\" — and your body freezes!|n"
            ),
            "third": (
                f"|Y{caster.key} commands {target.key} — \"HALT!\" — "
                f"and they freeze in place!|n"
            ),
        }

    def _cmd_grovel(self, caster, target, tier):
        """GROVEL — apply PRONE (action denial + advantage to enemies)."""
        rounds = _GROVEL_ROUNDS.get(tier, 1)
        applied = target.apply_prone(rounds, source=caster)
        s = "s" if rounds != 1 else ""

        if applied:
            first = (
                f"|Y*COMMAND: GROVEL* You speak with divine authority and "
                f"{target.key} collapses to the ground!\n"
                f"*PRONE* ({rounds} round{s})|n"
            )
        else:
            first = (
                f"|YYou command {target.key} to grovel, but they are "
                f"already on the ground!|n"
            )

        return {
            "first": first,
            "second": (
                f"|Y{caster.key} speaks with divine authority — "
                f"\"GROVEL!\" — and you collapse to the ground!|n"
            ),
            "third": (
                f"|Y{caster.key} commands {target.key} — \"GROVEL!\" — "
                f"and they collapse to the ground!|n"
            ),
        }

    def _cmd_drop(self, caster, target):
        """DROP — force-drop wielded weapon."""
        dropped, weapon_name = force_drop_weapon(target)

        if dropped:
            first = (
                f"|Y*COMMAND: DROP* You speak with divine authority and "
                f"{target.key} drops their {weapon_name}!|n"
            )
            second = (
                f"|Y{caster.key} speaks with divine authority — "
                f"\"DROP!\" — and your fingers release your "
                f"{weapon_name} against your will!|n"
            )
            third = (
                f"|Y{caster.key} commands {target.key} — \"DROP!\" — "
                f"and their {weapon_name} clatters from their grip!|n"
            )
        else:
            first = (
                f"|YYou command {target.key} to drop their weapon, "
                f"but they have nothing to drop!|n"
            )
            second = (
                f"|Y{caster.key} speaks with divine authority — "
                f"\"DROP!\" — but you have nothing to drop.|n"
            )
            third = (
                f"|Y{caster.key} commands {target.key} — \"DROP!\" — "
                f"but they have nothing to drop.|n"
            )

        return {"first": first, "second": second, "third": third}

    def _cmd_flee(self, caster, target):
        """FLEE — force target to execute the flee command."""
        target.execute_cmd("flee")

        return {
            "first": (
                f"|Y*COMMAND: FLEE* You speak with divine authority and "
                f"{target.key} turns and runs!|n"
            ),
            "second": (
                f"|Y{caster.key} speaks with divine authority — "
                f"\"FLEE!\" — and your legs carry you away!|n"
            ),
            "third": (
                f"|Y{caster.key} commands {target.key} — \"FLEE!\" — "
                f"and they turn and run!|n"
            ),
        }
