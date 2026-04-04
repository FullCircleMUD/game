"""
CmdQuests — global character command for viewing quest log.

Usage:
    quests              — list all active and completed quests
    quests <questname>  — show details for a specific quest
"""

from evennia import Command

from commands.command import FCMCommandMixin


class CmdQuests(FCMCommandMixin, Command):
    """
    View your quest log.

    Usage:
        quests              — list all active and completed quests
        quests <questname>  — show details for a specific quest

    Shows all quests you have accepted, their current status,
    and any progress information.
    """

    key = "quests"
    aliases = ["quest log", "questlog"]
    locks = "cmd:all()"
    help_category = "Character"
    allow_while_sleeping = True

    def func(self):
        caller = self.caller
        args = self.args.strip()

        if args:
            # Show details for a specific quest
            quest = caller.quests.get(args)
            if not quest:
                # Try partial match
                for q in caller.quests.all():
                    if args.lower() in q.key.lower() or args.lower() in q.name.lower():
                        quest = q
                        break
            if not quest:
                caller.msg(f"No quest found matching '{args}'.")
                return
            lines = [f"|w{quest.name}|n — {quest.status}"]
            lines.append(quest.help())
            # For collect quests, show resource progress
            if hasattr(quest, "required_resources"):
                for rid, needed in quest.required_resources.items():
                    has = caller.get_resource(rid)
                    color = "|g" if has >= needed else "|r"
                    from blockchain.xrpl.currency_cache import get_resource_type
                    rt = get_resource_type(rid)
                    rname = rt["name"] if rt else f"Resource {rid}"
                    lines.append(f"  {color}{rname}: {has}/{needed}|n")
            caller.msg("\n".join(lines))
            return

        active = caller.quests.active()
        completed = caller.quests.completed()

        if not active and not completed:
            caller.msg("You have no quests.")
            return

        lines = []
        if active:
            lines.append("|w=== Active Quests ===|n")
            for q in active:
                lines.append(f"  {q.name} ({q.quest_type}) — {q.help()}")
        if completed:
            lines.append("|w=== Completed Quests ===|n")
            for q in completed:
                lines.append(f"  |x{q.name}|n ({q.quest_type})")

        caller.msg("\n".join(lines))
