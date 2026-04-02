"""
FollowableMixin — adds the group/follow system to any actor.

Provides:
  - following: who this object is following
  - nofollow: whether others can follow this object
  - get_group_leader(): walk the follow chain to the root
  - get_followers(): find all direct/indirect followers
  - at_followable_init(): tag for efficient DB queries

Used by FCMCharacter (via direct composition) and combat mobs
(via MobFollowableMixin which adds auto-reacquire logic).
"""

from evennia import ObjectDB
from evennia.typeclasses.attributes import AttributeProperty


class FollowableMixin:
    """Mixin that makes an actor a valid target for CmdFollow."""

    following = AttributeProperty(None)
    nofollow = AttributeProperty(False)

    def at_followable_init(self):
        """Tag this actor as followable for efficient DB queries."""
        if not self.tags.has("followable", category="system"):
            self.tags.add("followable", category="system")

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
        Get all actors directly or indirectly following this object.

        Args:
            same_room: If True, only return followers in the same room
                       (uses room contents scan — fast, no DB query).
                       If False, queries all followable actors globally.
        """
        results = []
        if same_room and self.location:
            # Room scan — finds any actor type (characters + mobs)
            direct = [
                obj for obj in self.location.contents
                if getattr(obj, "following", None) == self and obj != self
            ]
        else:
            # Global query — uses followable tag for efficient filtering
            direct = [
                obj for obj in ObjectDB.objects.filter(
                    db_tags__db_key="followable",
                    db_tags__db_category="system",
                )
                if obj.following == self
            ]
        for f in direct:
            if same_room and f.location != self.location:
                continue
            results.append(f)
            results.extend(f.get_followers(same_room=same_room))
        return results
