"""
UnseenNameMixin — what a thing is called when the looker can't make it out.

Naming something a looker cannot see leaks it, whether the cause is the
thing being concealed or the looker being unable to see at all. This
mixin gives every root typeclass one answer to that, and lets the *word*
be content rather than code.

Usage — compose it first, and declare the placeholder::

    class WorldItem(UnseenNameMixin, HeightAwareMixin, DefaultObject):
        unseen_name = AttributeProperty("something")

``unseen_name`` is an AttributeProperty, so a spawn rule can set it per
instance in YAML. A wolf is "something"; a gnoll carrying a spear is
"Someone"; neither needs a new typeclass to say so.

This is what lets funcparser actor-stance strings anonymise for free.
``$You()`` resolves through ``get_display_name``, so
``"$You() $conj(slap) {target}."`` renders as "Someone slaps Fred" for an
observer who can't see the actor — correct grammar, no separately
authored text.
"""

from evennia.typeclasses.attributes import AttributeProperty

from utils.targeting.predicates import p_can_see


class UnseenNameMixin:
    """Render as ``unseen_name`` when the looker cannot see this object."""

    #: What this reads as to a looker who cannot make it out. Overridden
    #: per typeclass, and per instance from a spawn rule.
    unseen_name = AttributeProperty("something")

    def get_display_name(self, looker=None, **kwargs):
        """Return the placeholder when ``looker`` cannot see this."""
        if looker is not None and looker is not self:
            # p_can_see is concealment *and* sight: the thing may be
            # hidden, invisible or behind a height barrier, or the looker
            # may be blind or standing in the dark. All of them mean the
            # same thing here — do not name it.
            if not p_can_see(self, looker):
                return self.unseen_name
        # Self is exempt: you always know your own name, however concealed.
        #
        # super() walks the MRO from *after* this mixin, not up to a parent
        # class, and a class appears in an MRO only once — so there is no
        # recursion here. Nothing between this mixin and Evennia sits in
        # that path today, so it resolves to DefaultObject.get_display_name
        # and returns the real name.
        #
        # Compose this mixin FIRST in the bases so it answers before
        # anything else and only delegates onward when the looker can see.
        # A subclass that overrides get_display_name sits *before* it and
        # runs first — its super() call lands here, and it then decorates
        # whichever answer it gets. TorchNFTItem appending "(lit)" will
        # therefore append to the placeholder as readily as to the name.
        return super().get_display_name(looker, **kwargs)
