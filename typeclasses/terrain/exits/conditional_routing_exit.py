"""
ConditionalRoutingExit — an exit that routes to different destinations
based on player state.

The exit is always visible. When the condition is met, the player traverses
to the exit's normal ``destination``. When the condition is NOT met, the
player is routed to ``alternate_destination_id`` instead.

Extends ExitVerticalAware for direction system + vertical checks.
Has zero dungeon knowledge — pure routing logic.

Supported condition types:
    "quest_active"   — player has the quest and it's not completed
    "quest_complete" — player has completed the quest
    "has_tag"        — player has a specific tag (category="player_flag")

See design/EXIT_ARCHITECTURE.md.
"""

from evennia import AttributeProperty

from typeclasses.terrain.exits.exit_vertical_aware import ExitVerticalAware


class ConditionalRoutingExit(ExitVerticalAware):
    """
    Exit that routes between two destinations based on a condition.

    Builder usage:
        exit = create_object(
            ConditionalRoutingExit,
            key="a dark passage",
            location=room_a,
            destination=room_b,  # condition met → go here
        )
        exit.set_direction("south")
        exit.condition_type = "quest_active"
        exit.condition_key = "rat_cellar"
        exit.alternate_destination_id = room_c.id  # condition NOT met → go here
    """

    condition_type = AttributeProperty(None)
    condition_key = AttributeProperty(None)
    alternate_destination_id = AttributeProperty(None)

    def at_traverse(self, traversing_object, target_location, **kwargs):
        """
        Check condition and route to the appropriate destination.

        Condition met → traverse to normal destination (target_location).
        Condition NOT met → traverse to alternate destination.
        No alternate set → block with message.
        """
        if self._check_condition(traversing_object):
            # Condition met — normal traversal
            super().at_traverse(traversing_object, target_location, **kwargs)
        else:
            # Condition not met — route to alternate
            alt_dest = self._get_alternate_destination()
            if alt_dest:
                super().at_traverse(traversing_object, alt_dest, **kwargs)
            else:
                traversing_object.msg("The way is blocked.")

    def _check_condition(self, traversing_object):
        """
        Evaluate the routing condition for this character.

        Returns True if the condition is met (use primary destination).
        Returns True if no condition is configured (always primary).
        """
        if not self.condition_type or not self.condition_key:
            return True  # no condition → always primary

        if self.condition_type == "quest_active":
            if hasattr(traversing_object, "quests"):
                return (
                    traversing_object.quests.has(self.condition_key)
                    and not traversing_object.quests.is_completed(
                        self.condition_key
                    )
                )
            return False

        if self.condition_type == "quest_complete":
            if hasattr(traversing_object, "quests"):
                return traversing_object.quests.is_completed(
                    self.condition_key
                )
            return False

        if self.condition_type == "has_tag":
            return bool(
                traversing_object.tags.get(
                    self.condition_key, category="player_flag"
                )
            )

        # Unknown condition type — default to primary
        return True

    def _get_alternate_destination(self):
        """Look up the alternate destination room by ID."""
        from evennia import ObjectDB

        if not self.alternate_destination_id:
            return None
        try:
            return ObjectDB.objects.get(id=self.alternate_destination_id)
        except ObjectDB.DoesNotExist:
            return None
