"""
Base exit typeclass — auto-generates a description from the destination
room when no custom ``db.desc`` is set.
"""

from evennia import DefaultExit


class ExitBase(DefaultExit):

    def return_appearance(self, looker, **kwargs):
        """
        Auto-generate a description from the destination room when
        no custom db.desc is set, so exits never show Evennia's
        default "This is an exit."
        """
        if self.db.desc:
            return super().return_appearance(looker, **kwargs)

        dest = self.destination
        if dest:
            dest_name = dest.get_display_name(looker)
            dest_desc = dest.db.desc
            lines = [f"|c{dest_name}|n"]
            if dest_desc:
                # First sentence of the destination room description
                preview = dest_desc.split(".")[0].strip()
                if preview:
                    lines.append(preview + ".")
            return "\n".join(lines)

        return super().return_appearance(looker, **kwargs)
