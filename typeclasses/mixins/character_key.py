"""
CharacterKeyMixin — canonical ``_get_character_key`` shared by all mixins.

Resolves the three-way signature conflict between HiddenObjectMixin,
FungibleInventoryMixin, and NFTMirrorMixin by providing a single
definition that handles both use cases:

    self._get_character_key()          -> key for *self*
    self._get_character_key(target)    -> key for another character
"""


class CharacterKeyMixin:
    """
    Provides ``_get_character_key()`` to any object in the mixin hierarchy.

    Returns the character's ``.key`` (name string) if the target is an
    FCMCharacter, else ``None``.
    """

    _SELF = object()  # sentinel distinguishing "no arg" from explicit None

    def _get_character_key(self, target=_SELF):
        """
        Get the character_key for service calls.

        Args:
            target: The object to get the key for.  Defaults to ``self``.
                    Passing ``None`` explicitly raises TypeError.

        Returns:
            str or None: The character's key if it is an FCMCharacter,
            else None.

        Raises:
            TypeError: If ``None`` is passed explicitly as target.
        """
        if target is self._SELF:
            target = self
        elif target is None:
            raise TypeError(
                "_get_character_key() received None — pass a valid "
                "game object or omit the argument to use self."
            )
        from typeclasses.actors.character import FCMCharacter

        if isinstance(target, FCMCharacter):
            return target.key
        return None
