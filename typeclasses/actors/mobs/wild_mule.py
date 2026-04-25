"""
WildMule — passive tameable animal mob.

A wild mule that can be tamed by a character with ANIMAL_HANDLING skill
(BASIC mastery or higher). On successful tame, the wild mob is consumed
and a pet Mule NFT is created.

Non-aggressive, non-combatant. Just stands around chewing thistles.
"""

from evennia.typeclasses.attributes import AttributeProperty

from typeclasses.actors.mob import CombatMob


class WildMule(CombatMob):
    """A wild mule that can be tamed into a pet."""

    # ── Taming ──
    tameable = AttributeProperty(True)
    tame_dc = AttributeProperty(10)
    tame_pet_type = AttributeProperty("Mule")
    tame_mastery_required = AttributeProperty("basic")

    # ── Stats — hardy but passive ──
    level = AttributeProperty(1)
    hp = AttributeProperty(20)
    base_hp_max = AttributeProperty(20)
    hp_max = AttributeProperty(20)
    base_strength = AttributeProperty(14)
    strength = AttributeProperty(14)
    base_constitution = AttributeProperty(14)
    constitution = AttributeProperty(14)
    base_dexterity = AttributeProperty(10)
    dexterity = AttributeProperty(10)
    base_armor_class = AttributeProperty(10)
    armor_class = AttributeProperty(10)

    # ── Behaviour — passive ──
    is_aggressive = AttributeProperty(False)

    # ── Gold loot ──
    loot_gold_max = AttributeProperty(0)

    def at_object_creation(self):
        super().at_object_creation()
        self.db.desc = (
            "A stocky wild mule with a dusty brown coat and long ears. "
            "It watches you warily but doesn't seem inclined to run."
        )

    def get_room_description(self):
        return "A wild mule stands here, chewing on some thistles."

    def at_new_arrival(self, arriving_obj):
        """Don't react to arrivals — passive animal."""
        pass
