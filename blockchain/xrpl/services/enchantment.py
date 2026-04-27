"""
EnchantmentService — pre-disclosed gem enchantment outcomes.

Replaces runtime d100 rolls at craft time with a persistent slot model
where the next outcome is always pre-disclosed before the player commits
payment. Required by ECONOMY.md to satisfy gambling-law constraints
(no "uncertain future event" at the moment of purchase).

One row per (output_table, mastery_level) in EnchantmentSlot. All
enchanters server-wide compete for the same row — race resolved via
select_for_update() and a slot_number tiebreaker.

Roll happens AFTER consumption, never before purchase.
"""

from django.db import transaction

from blockchain.xrpl.models import EnchantmentSlot
from world.recipes.enchanting.gem_tables import roll_gem_enchantment


def _roll(output_table, mastery_level):
    """Run the existing rolling function and pack into a JSON-friendly dict.

    Outcome shape:
      - wear_effects: list of wear_effect dicts (standard item format)
      - restrictions: dict in ItemRestrictionMixin field format
    """
    wear_effects, restrictions = roll_gem_enchantment(
        output_table, mastery_level,
    )
    return {"wear_effects": wear_effects, "restrictions": restrictions}


class EnchantmentService:
    """Service layer for pre-disclosed gem enchantment slots."""

    @staticmethod
    def preview_slot(output_table, mastery_level):
        """
        Return the next available outcome without modifying state.

        Lazily seeds the row on first query for a given pair, so adding
        new entries to gem_tables.py needs no migration.

        Slots are kept per (output_table, mastery_level) so a BASIC and
        a GM enchanter looking at the same gem type see independent
        pre-disclosed outcomes from separate slot rows.

        Returns a dict: {slot_number, wear_effects (list), restrictions
        (dict in ItemRestrictionMixin field format)}.
        """
        slot, _ = EnchantmentSlot.objects.get_or_create(
            output_table=output_table,
            mastery_level=mastery_level,
            defaults={
                "slot_number": 1,
                "current_outcome": _roll(output_table, mastery_level),
            },
        )
        outcome = slot.current_outcome or {}
        return {
            "slot_number": slot.slot_number,
            "wear_effects": outcome.get("wear_effects", []),
            "restrictions": outcome.get("restrictions", {}),
        }

    @staticmethod
    def consume_slot(output_table, mastery_level, expected_slot_number):
        """
        Atomically consume the slot the player previewed.

        Returns the consumed outcome dict {effects, restrictions} on
        success, or None if another player consumed this slot first
        (race-loss). Caller must check for None and abort cleanly
        without touching the player's materials.

        On success, advances slot_number and rolls the next outcome.
        """
        with transaction.atomic():
            slot = EnchantmentSlot.objects.select_for_update().get(
                output_table=output_table,
                mastery_level=mastery_level,
            )
            if slot.slot_number != expected_slot_number:
                return None

            outcome = slot.current_outcome
            slot.slot_number += 1
            slot.current_outcome = _roll(output_table, mastery_level)
            slot.save(update_fields=[
                "slot_number", "current_outcome", "rolled_at",
            ])
            return outcome
