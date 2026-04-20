"""
HiddenObjectMixin — adds discovery-based hidden state to world objects.

Hidden objects are invisible to everyone until discovered via the `search`
command. Once ANY character discovers a hidden object, it becomes visible
to everyone currently in the room. The `discovered_by` set tracks which
characters have previously found the object, so it auto-reveals on re-entry.

This is SEPARATE from character HIDDEN condition (which uses reference-counted
conditions via ConditionsMixin). Object hidden state is intrinsic (boolean
attribute), not a stacking condition.

Usage:
    class WorldChest(HiddenObjectMixin, WorldFixture):
        def at_object_creation(self):
            super().at_object_creation()
            self.at_hidden_init()
"""

from evennia.typeclasses.attributes import AttributeProperty

from typeclasses.mixins.character_key import CharacterKeyMixin


class HiddenObjectMixin(CharacterKeyMixin):
    """
    Mixin that tracks hidden state and discovery for world objects.

    Child classes MUST:
        1. Call at_hidden_init() from at_object_creation()
    """

    is_hidden = AttributeProperty(False)
    find_dc = AttributeProperty(15)          # perception check difficulty
    discovered_by = AttributeProperty(default=set)  # set of character keys

    def at_hidden_init(self):
        """
        Initialize hidden object state. Call from at_object_creation().
        Safe to call multiple times.
        """
        pass  # defaults set via AttributeProperty

    def discover(self, finder):
        """
        Mark this object as discovered by finder. Broadcasts to room.

        Args:
            finder: The character who found this object.
        """
        # Add finder to discovered_by set
        char_key = self._get_character_key(finder)
        if char_key:
            discovered = set(self.discovered_by)
            discovered.add(char_key)
            self.discovered_by = discovered

        # Object is no longer hidden (everyone can see it now)
        self.is_hidden = False

        # Broadcast discovery to room
        if self.location:
            self.location.msg_contents(
                f"|y{finder.key} discovers {self.key} hidden nearby!|n"
            )

    def is_hidden_visible_to(self, character):
        """
        Check hidden-state visibility for a character.

        Visible if:
            - Not hidden at all, OR
            - Character has previously discovered it, OR
            - Character has the true_sight effect active (granted by either
              the True Sight or Holy Sight spell — both apply the same effect).
        """
        if not self.is_hidden:
            return True

        char_key = self._get_character_key(character)
        if char_key and char_key in self.discovered_by:
            return True

        if hasattr(character, "has_effect") and character.has_effect("true_sight"):
            return True

        return False
