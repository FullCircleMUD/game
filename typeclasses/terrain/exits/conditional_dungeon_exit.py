"""
ConditionalDungeonExit — quest-gated dungeon entry with fallback room.

When the condition is met (e.g. quest active), enters a procedural dungeon.
When the condition is NOT met, routes to an alternate destination (normal
room traversal with vertical checks).

Composes ProceduralDungeonMixin with ConditionalRoutingExit.

See design/EXIT_ARCHITECTURE.md and design/PROCEDURAL_DUNGEONS.md.
"""

from typeclasses.mixins.procedural_dungeon import ProceduralDungeonMixin
from typeclasses.terrain.exits.conditional_routing_exit import (
    ConditionalRoutingExit,
)


class ConditionalDungeonExit(ProceduralDungeonMixin, ConditionalRoutingExit):
    """
    Exit that enters a dungeon when a condition is met, or routes to a
    fallback room when it is not.

    Builder usage:
        trigger = create_object(
            ConditionalDungeonExit,
            key="a dark passage",
            location=cellar,
            destination=cellar,  # self-referential (dungeon path)
        )
        trigger.set_direction("south")
        trigger.dungeon_template_id = "rat_cellar"
        trigger.condition_type = "quest_active"
        trigger.condition_key = "rat_cellar"
        trigger.alternate_destination_id = empty_cellar.id
    """

    def at_traverse(self, traversing_object, target_location, **kwargs):
        """
        Check condition → dungeon or fallback.

        Condition met → enter_dungeon() (procedural instance).
        Condition NOT met → ConditionalRoutingExit routes to alternate.
        """
        if self._check_condition(traversing_object):
            self.enter_dungeon(traversing_object)
        else:
            # Route to alternate destination via normal exit traversal
            alt_dest = self._get_alternate_destination()
            if alt_dest:
                # Use ExitVerticalAware's at_traverse for proper checks
                from typeclasses.terrain.exits.exit_vertical_aware import (
                    ExitVerticalAware,
                )
                ExitVerticalAware.at_traverse(
                    self, traversing_object, alt_dest, **kwargs
                )
            else:
                traversing_object.msg("The way is blocked.")
