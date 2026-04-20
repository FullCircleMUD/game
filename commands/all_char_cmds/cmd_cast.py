"""
Cast command — cast a memorised spell.

Usage:
    cast '<spell>' [target]

Spell names must be enclosed in single quotes (the Magic Symbols).
For hostile spells, a target is required. For friendly spells
(healing), no target defaults to self. Mana is deducted on cast.
The spell stays memorised after casting.
"""

from evennia import Command

from commands.command import FCMCommandMixin
from enums.condition import Condition
from utils.targeting.helpers import resolve_target
from utils.targeting.predicates import check_range, p_can_see
from world.spells.registry import SPELL_REGISTRY


class CmdCast(FCMCommandMixin, Command):
    """
    Cast a memorised spell.

    Usage:
        cast '<spell>'
        cast '<spell>' <target>

    Examples:
        cast 'magic missile' goblin
        cast 'cure wounds'
        cast 'cure wounds' bob
    """

    key = "cast"
    aliases = []
    locks = "cmd:all()"
    help_category = "Magic"

    def func(self):
        caller = self.caller

        if not self.args:
            caller.msg("Cast what? Usage: cast '<spell>' [target]")
            return

        args = self.args.strip()

        # Spell name must be enclosed in single quotes
        if "'" not in args:
            caller.msg(
                "Spell names must be enclosed in the Magic Symbols: '\n"
                "Usage: cast '<spell>' [target]"
            )
            return

        first_quote = args.index("'")
        rest = args[first_quote + 1:]
        if "'" not in rest:
            caller.msg(
                "Spell names must be enclosed in the Magic Symbols: '\n"
                "Usage: cast '<spell>' [target]"
            )
            return

        second_quote = rest.index("'")
        spell_name = rest[:second_quote].strip()
        target_str = rest[second_quote + 1:].strip()

        if not spell_name:
            caller.msg("Cast what? Usage: cast '<spell>' [target]")
            return

        # Look up spell by name or key (underscores as spaces)
        spell_match = None
        spell_name_lower = spell_name.lower()
        for spell_key, spell_obj in SPELL_REGISTRY.items():
            if spell_obj.name.lower() == spell_name_lower:
                spell_match = spell_obj
                break
            if spell_key.replace("_", " ") == spell_name_lower:
                spell_match = spell_obj
                break

        if not spell_match:
            caller.msg("You don't know a spell by that name.")
            return

        # Extract spell argument if the spell requires one
        spell_arg = None
        if spell_match.has_spell_arg:
            parts = target_str.split(None, 1)
            if parts:
                spell_arg = parts[0].lower()
                target_str = parts[1] if len(parts) > 1 else ""
            # If no parts, spell_arg stays None — spell handles the error

        # Check if spell is memorised
        if not caller.is_memorised(spell_match.key):
            caller.msg(
                f"You haven't memorised {spell_match.name}. "
                f"Use |wmemorise {spell_match.name.lower()}|n first."
            )
            return

        # Resolve target — requires_sight controls whether p_can_see
        # is passed as an extra predicate. Actor types also get it
        # so hidden/height-barrier-gated targets are filtered.
        extra = (p_can_see,) if spell_match.requires_sight else ()
        target, secondaries = resolve_target(
            caller, target_str, spell_match.target_type,
            aoe=spell_match.aoe,
            extra_predicates=extra,
        )
        if target is None and spell_match.target_type != "none":
            return

        # Range/height check — universal, uses spell's overridable messages
        if target and target is not caller:
            if not check_range(caller, target, spell_match.range, source=spell_match):
                return

        # Self-targeting rejection for hostile/any_actor spells
        if spell_match.target_type in ("actor_hostile", "actor_any") and target is caller:
            caller.msg("You can't target yourself with that spell.")
            return

        # Cast the spell
        success, result = spell_match.cast(
            caller, target, spell_arg=spell_arg, secondaries=secondaries,
        )

        # Break invisibility on offensive cast (no advantage — spells only)
        if success and spell_match.target_type == "actor_hostile":
            if (hasattr(caller, "break_invisibility")
                    and caller.has_condition(Condition.INVISIBLE)):
                caller.break_invisibility()
                caller.msg("|yYour invisibility fades as you cast.|n")

        # Break sanctuary on offensive cast
        if success and spell_match.target_type == "actor_hostile":
            if (hasattr(caller, "break_sanctuary")
                    and caller.has_condition(Condition.SANCTUARY)):
                caller.break_sanctuary()
                caller.msg("|WYour sanctuary fades as you cast an offensive spell!|n")

        if isinstance(result, str):
            # Validation failure — single string to caster only
            caller.msg(result)
        else:
            # Spell executed — multi-perspective message dict
            caller.msg(result["first"])
            if target and target != caller and result.get("second"):
                target.msg(result["second"])
            if caller.location and result.get("third"):
                exclude = [caller]
                if target and target != caller:
                    exclude.append(target)
                caller.location.msg_contents(result["third"], exclude=exclude)
