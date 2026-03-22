"""
Antimagic Field — abjuration spell, available from EXPERT mastery.

The "Fireball of abjuration" — affects EVERYTHING in the room,
including the caster's own party. Suppresses all magic:
    1. No spellcasting allowed while field is active
    2. DISPELS all active spell effects on everyone in the room
    3. DISPELS all active potion effects on everyone in the room
    4. Permanent item effects (enchantments, innate properties) remain

This is the anti-caster nuke. Forces spell-heavy bosses into melee
where warriors can dominate. But it also strips YOUR party's buffs —
your mage's Mage Armor, your cleric's Sanctuary, everyone's potions.

Duration scales with mastery (the only scaling dimension):
    EXPERT(3):  1 round,  mana 28
    MASTER(4):  2 rounds, mana 39
    GM(5):      3 rounds, mana 49

Mana costs match Fireball — you're paying nuke-level mana for a
nuke-level effect, just defensive instead of offensive.

Cooldown: uses default tier-based (EXPERT=1, MASTER=2, GM=3).

Counter-play considerations:
    - Antimagic + Fireball is a legit combo: strip enemy buffs, then nuke
    - Necro drain tanks HATE this (strips Vampiric Touch bonus HP)
    - Abjurer vs Abjurer: whoever drops antimagic first wins
    - Smart bosses might have antimagic too — turns the tables on caster parties

DEPENDENCY: Needs dispel mechanics (iterate active spell/potion scripts,
remove effects), room-level casting suppression, and combat round timer.
"""

from enums.condition import Condition
from enums.mastery_level import MasteryLevel
from enums.skills_enum import skills
from world.spells.base_spell import Spell
from world.spells.registry import register_spell


@register_spell
class AntimagicField(Spell):
    key = "antimagic_field"
    aliases = ["amf", "antimagic"]
    name = "Antimagic Field"
    school = skills.ABJURATION
    min_mastery = MasteryLevel.EXPERT
    mana_cost = {3: 28, 4: 39, 5: 49}
    target_type = "none"
    description = "Erupts a field that suppresses all magic, dispelling active effects."
    mechanics = (
        "Unsafe — affects EVERYTHING in the room including you and allies.\n"
        "Immediately DISPELS all active spell and potion effects on everyone.\n"
        "No spellcasting allowed while the field is active.\n"
        "Permanent item enchantments are NOT affected.\n"
        "Duration: 1 round (Expert), 2 rounds (Master), 3 rounds (Grandmaster).\n"
        "Mana cost matches Fireball tier-for-tier."
    )

    # Duration in combat rounds per tier
    _DURATION = {3: 1, 4: 2, 5: 3}

    def _execute(self, caster, target):
        # SCAFFOLD: Implementation pending.
        #
        # When implemented:
        #   1. Get all living entities in the room (get_room_all)
        #   2. For each entity:
        #      a. Iterate active scripts — find spell buff scripts and potion
        #         buff scripts (PotionBuffScript, any SpellTimerScript)
        #      b. For each script: call remove_effect/cleanup, then stop script
        #      c. Remove spell-granted conditions (SHIELDED, MAGE_ARMORED,
        #         HASTED, BLESSED, VAMPIRIC, etc.)
        #      d. Do NOT remove innate conditions (DARKVISION, racial abilities)
        #      e. Do NOT remove permanent item enchantment effects
        #      f. Send dispel message to each affected entity
        #   3. Apply ANTIMAGIC condition to the ROOM (or all entities)
        #      → combat system / cmd_cast checks for this condition
        #      → if present, casting fails: "The antimagic field prevents casting!"
        #   4. Start AntimagicTimerScript on the room:
        #      - Duration from _DURATION table
        #      - On expiry: remove ANTIMAGIC condition, send "field collapses" message
        #   5. Return success messages
        #
        # Needs:
        #   - Dispel mechanic (iterate + remove active buff scripts)
        #   - Room-level condition or casting suppression check
        #   - Combat round timer script
        #   - Distinction between dispellable vs permanent effects
        raise NotImplementedError(
            "Antimagic Field implementation pending — needs dispel mechanics, "
            "room-level casting suppression, and combat round timer."
        )
