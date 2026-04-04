"""
Raise Lich — necromancy spell, available from MASTER mastery.

The elite version of Raise Dead. Instead of raising a simple undead
minion, transforms a single corpse into a lich — an intelligent undead
spellcaster that fights alongside the necromancer.

The lich retains some of the original creature's abilities and gains
necromantic spellcasting of its own (Drain Life, basic offensive magic).
This is the necromancer's "lieutenant" — a powerful single minion versus
Raise Dead's horde of weaker ones.

Scaling:
    MASTER(4): 1 lich, 10 minutes duration, mana 50
    GM(5):     1 lich, 30 minutes duration, mana 70

The lich is significantly more powerful than a raised dead:
    - Retains original creature's stats (not reduced)
    - Can cast Drain Life (heals itself, sustains in combat)
    - Cold-immune, poison-immune, fire-vulnerable
    - Intelligent AI — targets weakest enemies, uses abilities tactically

Same corpse protection rules as Raise Dead:
    - Player corpses with equipment CANNOT be raised
    - Looted player corpses and NPC corpses are fair game

Only one lich at a time. Casting again while a lich is active
replaces the previous lich (it crumbles).

Cooldown: 2 rounds (default MASTER).

DEPENDENCY: Needs pet/retainer system, corpse objects, NPC AI with
spellcasting capability, and the Drain Life spell for lich to use.
"""

from enums.mastery_level import MasteryLevel
from enums.skills_enum import skills
from world.spells.base_spell import Spell
from world.spells.registry import register_spell


@register_spell
class RaiseLich(Spell):
    key = "raise_lich"
    aliases = ["rl"]
    name = "Raise Lich"
    school = skills.NECROMANCY
    min_mastery = MasteryLevel.MASTER
    mana_cost = {4: 50, 5: 70}
    target_type = "none"
    description = "Transforms a corpse into a lich — an intelligent undead spellcaster."
    mechanics = (
        "Requires a corpse in the room. Consumes the corpse on success.\n"
        "Player corpses with equipment CANNOT be raised.\n"
        "Creates a powerful lich minion that can cast Drain Life.\n"
        "Duration: 10min (Master), 30min (Grandmaster).\n"
        "Only one lich at a time — recasting replaces the previous.\n"
        "Lich retains original creature stats, gains necromantic abilities.\n"
        "Cold-immune, poison-immune, fire-vulnerable.\n"
        "2 round cooldown."
    )

    # Duration in minutes per tier
    _DURATION = {4: 10, 5: 30}

    def _execute(self, caster, target):
        # SCAFFOLD: Implementation pending.
        #
        # When implemented:
        #   1. Search room for corpse objects (same rules as Raise Dead)
        #      → Player corpses with equipment: skip
        #      → Looted player corpses and NPC corpses: allow
        #   2. If caster already has an active lich:
        #      → Destroy the existing lich (crumbles to dust)
        #   3. Consume the corpse
        #   4. Spawn lich NPC:
        #      - Based on original creature's stats (not reduced)
        #      - Add spellcasting AI: Drain Life on enemies
        #      - Set resistances: cold immune, poison immune, fire vulnerable
        #      - Set owner to caster
        #   5. Start timer script for duration — on expiry, lich crumbles
        #   6. Lich joins combat on caster's side if in combat
        #   7. Return success messages
        #
        # Needs:
        #   - Pet/retainer system with spellcasting NPC AI
        #   - Corpse objects from mob death system
        #   - Corpse equipment check
        #   - Lich NPC template with Drain Life AI
        raise NotImplementedError(
            "Raise Lich implementation pending — needs pet/retainer system "
            "with spellcasting NPC AI and corpse objects."
        )
