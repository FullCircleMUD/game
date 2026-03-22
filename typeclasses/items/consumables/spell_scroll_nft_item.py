"""
SpellScrollNFTItem — an NFT that teaches a spell when transcribed.

When consumed via the `transcribe` command, delegates to
SpellbookMixin.learn_spell() which handles all validation (spell
exists, not already known, school mastery sufficient). On success
the scroll is deleted (token returns to RESERVE).

The spell_key attribute (set by prototype) must match a key in
world.spells.registry.SPELL_REGISTRY.
"""

from evennia.typeclasses.attributes import AttributeProperty

from typeclasses.items.consumables.consumable_nft_item import ConsumableNFTItem


class SpellScrollNFTItem(ConsumableNFTItem):
    """A consumable NFT that teaches a spell when transcribed."""

    spell_key = AttributeProperty("")  # set by prototype, matches SPELL_REGISTRY key

    def at_object_creation(self):
        super().at_object_creation()
        self.tags.add("spell_scroll", category="consumable_type")

    def at_consume(self, consumer):
        """
        Delegate to SpellbookMixin.learn_spell().

        Returns:
            (bool, str) — (success, message)
        """
        if not self.spell_key:
            return (False, "This scroll is blank.")
        return consumer.learn_spell(self.spell_key)
