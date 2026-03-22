...# FullCircleMUD.enums.skills.py

from enum import Enum

from enums.mastery_level import _MASTERY_REVERSE_LOOKUP


class skills(Enum):
    """

    """
    # Production / Economic skills
    BLACKSMITH = 'blacksmith' # converts ingots to weapons and armor etc in ore, ingot, <metal_products> line
    JEWELLER = 'jeweller'   # converts silver ingots & gems (ruby, sapphire, emerald) to jewelry in gem, jewelry line
    CARPENTER = 'carpenter' # converts timber to weapons, furniture and other wood products in wood, timber, <wood_products> line
    ALCHEMIST = 'alchemist' # converts herb & ingredients (mandrake, nightshade, wolfsbane, bats wings) to potions in herb, potion line
    TAILOR = 'tailor' # converts cloth to clothing and other cloth products in wool, cloth, <cloth_products> line
    LEATHERWORKER = 'leatherworker' # converts leather to armor and other leather products in hide, leather, <leather_products> line
    
    #general skills - combat
    BATTLESKILLS = 'battleskills' # combines dodge and help command
    ALERTNESS = "alertness" # initiative & bonus to perception checks

    # general skills - exploration / world
    CARTOGRAPHY = "cartography" # map-making, NFT maps, area memory wipe on creation
    SHIPWRIGHT = "shipwright" # build and repair ships
    SEAMANSHIP = "seamanship" # sailing, rigging, weather reading, ship handling
    ANIMAL_HANDLING = "animal_handling" # tame, train, and command animals

    # class skills - skills only avaoiable through one or more classes

    # WARRIOR LIKE CLASS SKILLS
    BASH = 'bash' # heavy armor, blunt weapons, shield bash, etc
    PUMMEL = 'pummel' # light armor, unarmed combat, quick strikes, etc
    PROTECT = 'protect' # defensive skill that allows the character to take damage for an ally, requires high strength and/or constitution
    FRENZY = 'frenzy' # allows the character to enter a berserk state, increasing damage output but reducing defense, requires high strength and/or constitution
    STRATEGY = "strategy" # group leadership: offence/defence stances, retreat

    # THIEF LIKE CLASS SKILLS
    STEALTH = 'stealth' # sneaking, hiding
    SUBTERFUGE = 'subterfuge' # lockpicking, pickpocketing, trap disarming
    STAB = 'stab' # analogous to 5e sneak attack
    ASSASSINATE = 'assassinate' # instant kill attack from stealth, requires stealth to be effective
    MAGICAL_SECRETS = "magical secrets" # can cast spells from scrolls... and maybe get 1 or 2 spells??

    # BARD LIKE CLASS SKILLS
    PERFORMANCE   = "performance"    # music, poetry, storytelling; social leverage, crowd control
    INSPIRATION   = "inspiration"    # ally buffs, temp HP, morale, advantage
    DEBILITATION  = "debilitation"   # mock, shame, psychic damage, disadvantage
    MANIPULATION  = "manipulation"   # charm, compel, suggestion, redirect aggro
    MISDIRECTION  = "misdirection"       # glamours, invisibility, sensory tricks
    LORE          = "lore"           # identify magic, recall history, counter-magic via knowledge

    # DRUID / RANGER LIKE CLASS SKILLS
    SURVIVALIST = 'survivalist' # allows the foraging of food AND tracking mobs AND danger sense
    ANIMAL_COMPANION = "animal_companion"
    SHAPE_SHIFTING = "shape shifting" # wolf, bear, falcon, dophin, dragon??
    NATURE_MAGIC = "nature_magic" # entangling plants, barkskin, speak with animals, call lightning, light, 

    # MAGE LIKE CLASS SKILLS

    # HAVE CAST AND TRANSCRIBE COPMMANDS BUT THEIR SUCCESS IS DETERMINED BY SKILL IN THE 
    # SCHOL OF MAGIC OF THE SPELL BEING CAST OR TRANSCRIBED
    # ?? POSSIBLY ALSO HAS PREPARE & FORGET COMMANDS THAT ALLOW MANAGEMENT OF SPELLS PRPEARED??

    EVOCATION = 'evocation' # offensive magic - fireball, lightning bolt, etc
    CONJURATION = 'conjuration' # summoning magic - summon elemental, summon familiar, etc
    DIVINATION = 'divination' # utility magic - detect magic, identify, etc
    ABJURATION = 'abjuration' # defensive magic - shield, counterspell, etc
    NECROMANCY = 'necromancy' # dark magic - raise dead, life drain, etc
    ILLUSION = 'illusion' # illusion magic - invisibility, mirror image, etc

    # mage only crafting skill
    ENCHANTING = 'enchanting' # enchanting magic - enchant weapon, armor, etc

    #CLERIC LIKE CLASS SKILLS

    # HAVE CAST COMMAND BUT SUCCESS IS DETERMINED BY SKILL IN THE 
    # SCHOL OF MAGIC OF THE SPELL BEING CAST OR TRANSCRIBED
    # ?? POSSIBLY ALSO HAS PREPARE & FORGET COMMANDS THAT ALLOW MANAGEMENT OF SPELLS PRPEARED??

    DIVINE_HEALING      = "divine_healing"      # party healer - restore HP, cure, revive,dispel, exorcise, remove curse/undead
    DIVINE_PROTECTION   = "divine_protection"   # party buffer - wards, buffs, sanctify areas
    DIVINE_JUDGEMENT    = "divine_judgement"    # war cleric damage dealer - smite, radiant damage, divine wrath
    DIVINE_REVELATION   = "divine_revelation"   # knows stuff (like divination) - detect, prophecy, true sight, commune
    DIVINE_DOMINION     = "divine_dominion"     # party controller - command, compel, oath/bond magic
    TURN_UNDEAD         = "turn_undead"

    @property
    def classes_available_to(self) -> str:
        """Get the classes that can learn this skill."""
        return _CLASS_MAPPINGS_LOOKUP[self]

    @property
    def description(self) -> str:
        """Get a short description of what this skill does."""
        return _SKILL_DESCRIPTIONS.get(self, "No description available.")

# Mastery level stat bonuses
_CLASS_MAPPINGS_LOOKUP = {
    skills.BLACKSMITH: {"all"}, # forge, repair
    skills.JEWELLER: {"all"}, #
    skills.CARPENTER: {"all"}, # craft, repair
    skills.ALCHEMIST: {"all"}, # brew
    skills.TAILOR: {"all"}, # sew
    skills.LEATHERWORKER: {"all"}, # tan???

    skills.BATTLESKILLS: {"all"},  # combines dodge and help command
    skills.ALERTNESS: {"all"}, # initiative & perception checks

    skills.CARTOGRAPHY: {"all"}, # map-making
    skills.SHIPWRIGHT: {"all"}, # build & repair ships
    skills.SEAMANSHIP: {"all"}, # sailing & ship handling
    skills.ANIMAL_HANDLING: {"all"}, # tame & train animals

    skills.BASH: {"warrior"}, #bash
    skills.PROTECT: {"warrior", "paladin"}, # protect
    skills.PUMMEL: {"paladin", "warrior"}, #pummel
    skills.FRENZY: {"berserker"}, #fenzy
    skills.STRATEGY: {"paladin", "warrior"},

    skills.STEALTH: {"thief","ninja", "bard"}, # hide, sneak
    skills.SUBTERFUGE: {"thief", "ninja", "bard"}, # pick, steal, disarm
    skills.STAB: {"ninja", "thief"}, #stab
    skills.ASSASSINATE: {"ninja"}, #assassinate
    skills.MAGICAL_SECRETS: {"thief", "ninja"}, # cast from scrolls

    skills.PERFORMANCE: {"bard"},  # mesmerise (distract crowd), entertain(+cha / opinion of char)
    skills.INSPIRATION: {"bard"},  # bolster(+temp HP), inspire(advantage), vigilance(+initiative), focus( + hit rolls), etc
    skills.DEBILITATION: {"bard"}, # mock(psychic damage), shame??(loss of turn), heedless(- initiative), slow???
    skills.MANIPULATION: {"bard"}, # suggest(like cleric command), divert(change who mob aggro is aggo to)
    skills.MISDIRECTION: {"bard"}, # disguise, conceal(invisibility), distract(minor illusion)
    skills.LORE: {"bard"}, # idenitfy, learn 1 mage school of magic (maybe limit list)

    skills.SURVIVALIST: {"druid", "ranger"}, # forage, track, navigate
    skills.ANIMAL_COMPANION: {"druid", "ranger"}, # animal companion
    skills.SHAPE_SHIFTING: {"druid"}, # wolf, bear, falcon, dolphin, dragon??
    skills.NATURE_MAGIC: {"druid", "ranger"}, # entangling plants, barkskin, etc

    skills.EVOCATION: {"mage"},   # cast, transcribe, memorise, forget
    skills.CONJURATION: {"mage"}, # cast, transcribe, memorise, forget
    skills.DIVINATION: {"mage"},  # cast, transcribe, memorise, forget
    skills.ABJURATION: {"mage"},  # cast, transcribe, memorise, forget
    skills.NECROMANCY: {"mage"},  # cast, transcribe, memorise, forget
    skills.ILLUSION: {"mage"},    # cast, transcribe, memorise, forget

    # enchanting is a recipe based skill available only to mages
    skills.ENCHANTING: {"mage"},  # cast, transcribe, memorise, forget

    skills.DIVINE_HEALING: {"cleric", "paladin"}, # cast, memorise, forget
    skills.DIVINE_PROTECTION: {"cleric", "paladin"}, # cast, memorise, forget
    skills.DIVINE_JUDGEMENT: {"cleric", "paladin"}, # cast, memorise, forget
    skills.DIVINE_REVELATION: {"cleric", "paladin"}, # cast, memorise, forget
    skills.DIVINE_DOMINION: {"cleric", "paladin"}, # cast, memorise, forget
    skills.TURN_UNDEAD: {"cleric", "paladin"}, # cast, memorise, forget
}

_SKILL_DESCRIPTIONS = {
    # Production
    skills.BLACKSMITH: "Craft weapons and armor from metal ingots at a smithy.",
    skills.JEWELLER: "Craft jewelry from silver ingots and gems.",
    skills.CARPENTER: "Craft weapons, furniture and shields from timber at a woodshop.",
    skills.ALCHEMIST: "Brew potions from herbs and reagents.",
    skills.TAILOR: "Craft clothing and cloth items from cloth.",
    skills.LEATHERWORKER: "Craft leather armor and equipment from leather.",
    # General combat
    skills.BATTLESKILLS: "Dodge: give incoming attacks disadvantage, costs your next attack. Assist: give an ally advantage, costs your next attack.",
    skills.ALERTNESS: "Bonus to perception checks — spot hidden doors, traps, and stealthed foes. Bonus to initiative rolls, determining turn order in combat.",
    # General — exploration / world
    skills.CARTOGRAPHY: "Create maps of explored areas. Maps are NFT items that can be traded or displayed.",
    skills.SHIPWRIGHT: "Build and repair ships — from small dinghies to ocean-going vessels.",
    skills.SEAMANSHIP: "Sail ships, read the weather, handle rigging, and navigate open waters.",
    skills.ANIMAL_HANDLING: "Tame wild animals, train them, and command them in and out of combat.",
    # Warrior
    skills.BASH: "Knock an enemy prone with a powerful strike. Contested STR roll — target loses a turn and enemies gain advantage.",
    skills.PUMMEL: "Stun an enemy with rapid strikes. Contested STR vs target DEX — target loses a turn on success.",
    skills.PROTECT: "Tanking — protect intercepts attacks on an ally; taunt provokes enemies to attack you instead.",
    skills.FRENZY: "Enter a berserk rage — increased damage but reduced defence.",
    skills.STRATEGY: "Group leadership — offence and defence set group combat stances; retreat withdraws the group from a fight.",
    # Thief
    skills.STEALTH: "Hide in shadows and stash objects or allies out of sight. Foundation for rogue abilities.",
    skills.SUBTERFUGE: "Pick locks, case marks, pickpocket valuables, and disarm traps — the core rogue toolkit.",
    skills.STAB: "Sneak attack — deal bonus damage dice when you have advantage. Scales from +2d6 to +10d6 with mastery.",
    skills.ASSASSINATE: "Lethal strike from stealth — chance to instantly kill the target.",
    skills.MAGICAL_SECRETS: "Cast spells from scrolls even without formal magical training.",
    # Bard
    skills.PERFORMANCE: "Music, poetry and storytelling — entertain crowds and influence NPCs.",
    skills.INSPIRATION: "Bolster allies with temporary HP, advantage, and morale boosts.",
    skills.DEBILITATION: "Taunt and shame enemies — psychic damage, lost turns, disadvantage.",
    skills.MANIPULATION: "Charm, suggest, and redirect enemy attention through force of personality.",
    skills.MISDIRECTION: "Glamours and sensory tricks — disguise, conceal, create distractions.",
    skills.LORE: "Identify items and creatures through knowledge. Higher mastery reveals more powerful targets.",
    # Druid/Ranger
    skills.SURVIVALIST: "Forage to restore hunger in the wilderness. Higher mastery restores more and unlocks party sharing.",
    skills.ANIMAL_COMPANION: "Bond with a wild animal that fights alongside you.",
    skills.SHAPE_SHIFTING: "Transform into animal forms — wolf, bear, falcon, and more.",
    skills.NATURE_MAGIC: "Command natural forces — entangling vines, barkskin, call lightning.",
    # Mage
    skills.EVOCATION: "Offensive magic — fireball, lightning bolt, and other destructive spells.",
    skills.CONJURATION: "Summoning magic — call elementals, familiars, and planar beings.",
    skills.DIVINATION: "Utility magic — detect magic, identify items, scry distant locations.",
    skills.ENCHANTING: "Imbue weapons and armor with magical properties at a workbench.",
    skills.ABJURATION: "Defensive magic — shields, counterspells, wards, and dispelling.",
    skills.NECROMANCY: "Dark magic — raise undead, drain life force, curse the living.",
    skills.ILLUSION: "Illusion magic — invisibility, mirror images, and phantasmal tricks.",
    # Cleric
    skills.DIVINE_HEALING: "Restore HP, cure ailments, revive the fallen, and dispel undead.",
    skills.DIVINE_PROTECTION: "Wards, blessings, and sanctified areas that shield allies.",
    skills.DIVINE_JUDGEMENT: "Holy wrath — smite foes with radiant damage and divine strikes.",
    skills.DIVINE_REVELATION: "Divine sight — detect evil, prophecy, true sight, commune with the divine.",
    skills.DIVINE_DOMINION: "Command and compel — holy authority, oath magic, and binding vows.",
    skills.TURN_UNDEAD: "Stun undead mobs based on their hit dice. At higher mastery, destroy them outright.",
}

