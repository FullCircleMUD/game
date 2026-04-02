"""
MobFollowableMixin — FollowableMixin with auto-reacquire for mobs.

Extends FollowableMixin with AI-driven leader reacquisition. On each
AI idle tick, if not following anyone, scans the room for the
configured squad_leader_typeclass and follows them.

Handles all group reformation cases:
- Staggered respawn (guards spawn before or after sergeant)
- Partial kills (some guards survive, new ones join the group)
- Sergeant death and respawn (guards find the new sergeant)

Usage::

    class MeleeGuard(MobFollowableMixin, HumanoidWearslotsMixin, AggressiveMob):
        squad_leader_typeclass = GuardSergeant
"""

from typeclasses.mixins.followable import FollowableMixin


class MobFollowableMixin(FollowableMixin):
    """
    FollowableMixin with auto-reacquire for mobs.

    Set ``squad_leader_typeclass`` on the subclass to the typeclass
    of the leader mob. On each AI idle tick, if not following anyone,
    scans the room for an instance of that typeclass and follows them.

    The leader mob doesn't need this mixin — it gets base
    ``FollowableMixin`` from ``CombatMob`` and just exists as the
    follow target.
    """

    squad_leader_typeclass = None

    def ai_idle(self):
        """If not following anyone, look for the squad leader."""
        if not self.following and self.squad_leader_typeclass and self.location:
            for obj in self.location.contents:
                if (isinstance(obj, self.squad_leader_typeclass)
                        and obj != self
                        and getattr(obj, "is_alive", False)):
                    self.following = obj
                    break
        super().ai_idle()
