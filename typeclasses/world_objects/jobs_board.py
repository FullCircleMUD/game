"""
JobsBoard — a world fixture displaying NPC job postings for new players.

A weathered notice board outside the Harvest Moon Inn where town NPCs
post requests for help. Players look at the board to see available jobs.

Eventually, completed quests will be hidden per-character so each player
sees only jobs they haven't finished yet.

Usage (build script):
    board = create_object(JobsBoard, key="a weathered jobs board",
                          location=room)
"""

from evennia import AttributeProperty

from typeclasses.world_objects.base_fixture import WorldFixture


class JobsBoard(WorldFixture):
    """
    A jobs board showing NPC requests for help.

    Each posting is a dict with keys: npc, title, description.
    Stored as a list in the ``postings`` attribute.
    """

    postings = AttributeProperty(list)

    def return_appearance(self, looker, **kwargs):
        """Render the board with all current postings."""
        name = self.get_display_name(looker)
        desc = self.db.desc or ""

        lines = [f"|w{name}|n", desc, ""]

        entries = self.postings or []
        if not entries:
            lines.append("  The board is empty.")
        else:
            for i, posting in enumerate(entries, 1):
                npc = posting.get("npc", "Unknown")
                title = posting.get("title", "Untitled")
                description = posting.get("description", "")
                lines.append(f"  |w[{i}]|n |c{title}|n")
                lines.append(f"      Posted by: |w{npc}|n")
                if description:
                    lines.append(f"      {description}")
                lines.append("")

        return "\n".join(lines)
