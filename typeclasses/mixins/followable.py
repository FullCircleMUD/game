"""
FollowableMixin — adds the group/follow system to any actor.

Provides:
  - following: who this object is following
  - nofollow: whether others can follow this object
  - get_group_leader(): walk the follow chain to the root
  - get_followers(): find all direct/indirect followers

Used by FCMCharacter and any NPC that should be followable
(e.g. tutorial companion).
"""

from evennia import ObjectDB
from evennia.typeclasses.attributes import AttributeProperty


class FollowableMixin:
    """Mixin that makes an actor a valid target for CmdFollow."""

    following = AttributeProperty(None)
    nofollow = AttributeProperty(False)

    def get_group_leader(self):
        """Walk the follow chain to the root (the leader)."""
        visited = {self}
        current = self
        while current.following and current.following not in visited:
            visited.add(current.following)
            current = current.following
        return current

    def get_followers(self, same_room=False):
        """
        Get all characters directly or indirectly following this object.

        Args:
            same_room: If True, only return followers in the same room.
        """
        results = []
        direct = [
            obj for obj in ObjectDB.objects.filter(
                db_typeclass_path__contains="character"
            )
            if obj.following == self
        ]
        for f in direct:
            if same_room and f.location != self.location:
                continue
            results.append(f)
            results.extend(f.get_followers(same_room=same_room))
        return results
