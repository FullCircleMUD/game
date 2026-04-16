"""
Cast command — cast a memorised spell.

Usage:
    cast <spell> [target]

For hostile spells, a target is required. For friendly spells
(healing), no target defaults to self. Mana is deducted on cast.
The spell stays memorised after casting.
"""

from evennia import Command

from commands.command import FCMCommandMixin
from enums.condition import Condition
from world.spells.registry import get_spell, SPELL_REGISTRY
from world.spells.spell_utils import resolve_actor_target, resolve_item_target


class CmdCast(FCMCommandMixin, Command):
    """
    Cast a memorised spell.

    Usage:
        cast <spell>
        cast <spell> <target>

    Examples:
        cast magic missile goblin
        cast mm goblin
        cast cure wounds
        cast cure wounds bob
    """

    key = "cast"
    aliases = ["c", "ca"]
    locks = "cmd:all()"
    help_category = "Magic"

    def func(self):
        caller = self.caller

        if not self.args:
            caller.msg("Cast what? Usage: cast <spell> [target]")
            return

        args = self.args.strip()

        # Try to find the spell — match against known spell keys/names/aliases
        # Strategy: try longest prefix match against spell names
        spell_match = None
        target_str = ""
        best_match_len = 0

        for spell_key, spell_obj in SPELL_REGISTRY.items():
            # Check if args starts with the spell name (case insensitive)
            # Require word boundary after match to prevent partial matches
            name_lower = spell_obj.name.lower()
            if args.lower().startswith(name_lower):
                after = args[len(name_lower):]
                if after and not after[0].isspace():
                    pass  # partial word match — skip
                elif len(name_lower) > best_match_len:
                    spell_match = spell_obj
                    target_str = after.strip()
                    best_match_len = len(name_lower)

            # Also check by key with underscores replaced
            key_display = spell_key.replace("_", " ")
            if args.lower().startswith(key_display):
                after = args[len(key_display):]
                if after and not after[0].isspace():
                    pass  # partial word match — skip
                elif len(key_display) > best_match_len:
                    spell_match = spell_obj
                    target_str = after.strip()
                    best_match_len = len(key_display)

            # Check aliases — require word boundary (space or end of string)
            # to prevent short aliases like "ma" matching inside "magic"
            for alias in getattr(spell_obj, "aliases", []):
                alias_lower = alias.lower()
                if args.lower().startswith(alias_lower):
                    after = args[len(alias_lower):]
                    if after and not after[0].isspace():
                        continue  # partial word match — skip
                    remainder = after.strip()
                    if len(alias_lower) > best_match_len:
                        spell_match = spell_obj
                        target_str = remainder
                        best_match_len = len(alias_lower)

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

        # Resolve target — each target_type except "self" and "none"
        # has a helper in world.spells.spell_utils that does its own
        # scoping, validation, and error messaging. On None, the helper
        # has already told the caster what went wrong, so we just return.
        target = None
        if spell_match.target_type == "self":
            target = caller
        elif spell_match.target_type == "none":
            target = None
        elif spell_match.target_type in ("hostile", "friendly", "any_actor"):
            target = resolve_actor_target(
                caller, target_str, spell_match.target_type,
            )
            if not target:
                return
        elif spell_match.target_type in ("inventory_item", "world_item", "any_item"):
            target = resolve_item_target(
                caller, target_str, spell_match.target_type,
            )
            if not target:
                return

        # Cast the spell
        success, result = spell_match.cast(caller, target, spell_arg=spell_arg)

        # Break invisibility on offensive cast (no advantage — spells only)
        if success and spell_match.target_type == "hostile":
            if (hasattr(caller, "break_invisibility")
                    and caller.has_condition(Condition.INVISIBLE)):
                caller.break_invisibility()
                caller.msg("|yYour invisibility fades as you cast.|n")

        # Break sanctuary on offensive cast
        if success and spell_match.target_type == "hostile":
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
