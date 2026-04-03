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
    # ── Production (all classes) ──
    skills.BLACKSMITH: (
        "Forge weapons and armor from metal ingots at a smithy. Higher mastery "
        "unlocks more powerful recipes and improves item quality."
    ),
    skills.JEWELLER: (
        "Cut gems and craft rings, amulets, and other jewelry from silver "
        "ingots and precious stones. Higher mastery unlocks rarer settings."
    ),
    skills.CARPENTER: (
        "Shape timber into weapons, shields, furniture, and other wooden items "
        "at a woodshop. Higher mastery unlocks stronger wood types and designs."
    ),
    skills.ALCHEMIST: (
        "Brew potions, salves, and elixirs from herbs and reagents. Higher "
        "mastery unlocks more potent recipes with stronger or longer effects."
    ),
    skills.TAILOR: (
        "Sew cloth into clothing, robes, cloaks, and enchantable fabric items. "
        "Higher mastery unlocks finer materials and magical weaves."
    ),
    skills.LEATHERWORKER: (
        "Tan hides into leather armor, boots, gloves, and other equipment. "
        "Higher mastery unlocks hardened and reinforced designs."
    ),
    # ── General combat (all classes) ──
    skills.BATTLESKILLS: (
        "Two combat commands available to all classes. Dodge: sacrifice your "
        "next attack to impose disadvantage on all incoming attacks for one "
        "round. Assist: sacrifice your next attack to grant an ally advantage "
        "on their attacks. Outside combat, assist gives advantage on a "
        "companion's next skill check."
    ),
    skills.ALERTNESS: (
        "Passive bonuses that scale with mastery — no active command. "
        "Increases perception (spot hidden doors, detect traps, see through "
        "stealth) and improves initiative rolls in combat. Essential for "
        "avoiding ambushes and acting first."
    ),
    # ── General exploration / world (all classes) ──
    skills.CARTOGRAPHY: (
        "Create maps of explored areas as you travel. Maps are tradeable NFT "
        "items — sell your discoveries to other players or collect a complete "
        "atlas. Higher mastery reveals more detail and covers larger regions."
    ),
    skills.SHIPWRIGHT: (
        "Build and repair ships at a dockyard — from small fishing dinghies "
        "to ocean-going warships. Higher mastery unlocks larger hull designs "
        "and better materials."
    ),
    skills.SEAMANSHIP: (
        "Sail ships between ports, navigate open waters, and explore uncharted "
        "seas. Required to captain any vessel. Higher mastery unlocks faster "
        "routes, longer voyages, and the ability to discover hidden ports."
    ),
    skills.ANIMAL_HANDLING: (
        "Tame wild animals encountered in the world and train them to follow "
        "basic commands. Distinct from the druid/ranger Animal Companion class "
        "skill — this is a general skill available to any class."
    ),
    # ── Warrior ──
    skills.BASH: (
        "Slam into an enemy with brute force. Contested STR roll — on "
        "success, the target is knocked prone (loses their next turn and all "
        "attackers gain advantage). On failure, you may fall prone yourself. "
        "Cooldown shortens with mastery (7 rounds at BASIC, 3 at GM)."
    ),
    skills.PUMMEL: (
        "Batter an enemy with rapid strikes. Contested STR vs target DEX — "
        "on success, the target is stunned (loses their next turn). Lower "
        "risk than bash (no self-prone on failure) but no advantage bonus for "
        "allies. Cooldown shortens with mastery (8 rounds at BASIC, 4 at GM)."
    ),
    skills.PROTECT: (
        "Tank for your group. Protect: designate an ally to guard — you have "
        "a chance to intercept attacks aimed at them (40% at BASIC, 80% at "
        "GM), taking the damage yourself. Taunt: provoke an enemy into "
        "attacking you instead of your allies. Contested CHA vs target WIS."
    ),
    skills.FRENZY: (
        "Enter a berserk rage that boosts damage output at the cost of "
        "reduced defence. Duration and intensity scale with mastery. While "
        "frenzied, you hit harder but are easier to hit."
    ),
    skills.STRATEGY: (
        "Lead your group in combat with three commands. Offence: set an "
        "aggressive stance for your party (bonus to hit and damage, penalty "
        "to AC). Defence: set a defensive stance (bonus AC, penalty to hit). "
        "Retreat: attempt to withdraw your entire group from combat — "
        "contested INT + CHA roll, failure gives enemies a free round."
    ),
    # ── Thief ──
    skills.STEALTH: (
        "Slip into the shadows unseen. Hide: contested stealth vs the best "
        "perceiver in the room. While hidden, you can move between rooms "
        "(re-checked on entry) and set up sneak attacks. Stash: conceal an "
        "object or ally, setting a discovery DC based on your stealth roll."
    ),
    skills.SUBTERFUGE: (
        "The rogue's core toolkit — four commands. Picklock: defeat locks on "
        "doors and chests (DEX + mastery vs lock DC). Case: study a target "
        "to reveal what they're carrying. Pickpocket: steal gold, resources, "
        "or items (contested DEX vs perception, advantage if hidden). Disarm: "
        "safely disable traps on chests, doors, and rooms."
    ),
    skills.STAB: (
        "Backstab — a devastating sneak attack. Strike from stealth or when "
        "you have advantage for massive bonus damage. Requires a finesse "
        "weapon (dagger, shortsword, ninjato). Bonus dice scale from +2d6 at "
        "BASIC to +10d6 at GM. Crits double the bonus. Cooldown shortens "
        "with mastery."
    ),
    skills.ASSASSINATE: (
        "A lethal strike from concealment — chance to instantly kill the "
        "target outright. Must be hidden. Success chance depends on mastery "
        "vs target level. The ultimate high-risk, high-reward ability."
    ),
    skills.MAGICAL_SECRETS: (
        "Recite spell scrolls without being a spellcaster. Mastery "
        "determines the maximum spell level you can use — higher mastery "
        "unlocks more powerful scrolls. Distinct from the mage cast command."
    ),
    # ── Bard ──
    skills.PERFORMANCE: (
        "Music, poetry, and storytelling — entertain crowds to earn coin and "
        "influence NPC opinion. Can also create distractions that aid allies "
        "attempting pickpocket or stealth."
    ),
    skills.INSPIRATION: (
        "Rally your allies in combat with rousing words and song. Grants "
        "temporary HP, AC bonuses, hit bonuses, and damage bonuses to your "
        "group. Effects scale with mastery — GM grants +20 temp HP, +2 AC, "
        "+2 hit, and +2 damage to every ally."
    ),
    skills.DEBILITATION: (
        "Weaponise wit and mockery. Mock: deal psychic damage and attempt to "
        "stun the target through sheer humiliation. Contested CHA + mastery "
        "vs target WIS. Stun duration scales with mastery."
    ),
    skills.MANIPULATION: (
        "Bend others to your will through force of personality. Charm: "
        "contested CHA vs WIS, a charmed mob becomes a temporary follower. "
        "Divert: redirect an enemy's aggression to a different target. "
        "Both scale with mastery for duration and success chance."
    ),
    skills.MISDIRECTION: (
        "Glamours and sensory tricks. Disguise: change your appearance so "
        "NPCs and mobs don't recognise you. Conceal: a magical glamour that "
        "grants invisibility at higher mastery — distinct from physical "
        "stealth (hide)."
    ),
    skills.LORE: (
        "Identify items and creatures by examining them. Reveals stats, "
        "resistances, and weaknesses. Higher mastery identifies more powerful "
        "targets — each tier unlocks identification of creatures up to 10 "
        "levels higher. No mana cost, purely knowledge-based."
    ),
    # ── Druid / Ranger ──
    skills.SURVIVALIST: (
        "Live off the land. Forage: restore hunger in wilderness terrain "
        "(forests, mountains, swamps, etc.) without needing food items. "
        "Higher mastery restores more hunger and lets you share foraged food "
        "with your party. Track: follow creature trails through the "
        "wilderness."
    ),
    skills.ANIMAL_COMPANION: (
        "Bond with a loyal animal companion that fights alongside you and "
        "persists between sessions. If your companion falls, it retreats to "
        "recover and can be re-summoned later. Companion power scales with "
        "mastery — from a small animal at BASIC to formidable beasts at GM."
    ),
    skills.SHAPE_SHIFTING: (
        "Transform into animal forms, each with unique combat abilities and "
        "movement modes. Available forms grow more powerful with mastery — "
        "wolf, bear, falcon, and more. While shifted, your equipment is "
        "absorbed and you use the form's natural attacks."
    ),
    skills.NATURE_MAGIC: (
        "Druid spellcasting — command natural forces through a dedicated "
        "spell school. Includes entangling vines, barkskin, call lightning, "
        "and other nature-themed spells. Mastery unlocks higher-level nature "
        "spells."
    ),
    # ── Mage ──
    skills.EVOCATION: (
        "Offensive spellcasting — hurl raw destructive energy at your foes. "
        "Includes fireball, lightning bolt, cone of cold, and other damage "
        "spells. The primary damage school for mages. Higher mastery unlocks "
        "more devastating spells."
    ),
    skills.CONJURATION: (
        "Summon creatures and objects from other planes. Call elementals, "
        "familiars, and planar beings to fight for you or perform tasks. "
        "Higher mastery summons more powerful and longer-lasting allies."
    ),
    skills.DIVINATION: (
        "Utility and information magic — detect magic, identify items, scry "
        "distant locations, and peer through illusions. The knowledge school "
        "for mages. Higher mastery reveals deeper secrets."
    ),
    skills.ENCHANTING: (
        "Imbue weapons and armor with magical properties at an enchanting "
        "workbench. Add stat bonuses, elemental damage, or special effects "
        "to equipment. Higher mastery unlocks more powerful enchantments. "
        "Recipes are auto-granted as you advance in mastery."
    ),
    skills.ABJURATION: (
        "Defensive and protective magic — shields, counterspells, wards, and "
        "dispelling. Protect yourself and allies from harm, negate enemy "
        "spells, and banish summoned creatures. Higher mastery unlocks "
        "stronger barriers."
    ),
    skills.NECROMANCY: (
        "Dark magic over life and death — drain life force, raise undead "
        "servants, curse the living, and manipulate the boundary between "
        "life and death. Higher mastery unlocks more powerful undead and "
        "darker curses."
    ),
    skills.ILLUSION: (
        "Deceive the senses — invisibility, mirror images, phantasmal "
        "terrors, and sensory manipulation. Trick enemies into attacking "
        "illusions while you act unseen. Higher mastery creates more "
        "convincing and longer-lasting illusions."
    ),
    # ── Cleric ──
    skills.DIVINE_HEALING: (
        "Channel divine power to restore HP, cure diseases and poisons, "
        "remove curses, and revive fallen allies. The primary healing school. "
        "Higher mastery unlocks more powerful restoration and group heals."
    ),
    skills.DIVINE_PROTECTION: (
        "Holy wards and blessings that shield allies from harm. Includes "
        "sanctuary (prevent attacks), bless (bonus to hit and saves), and "
        "protective auras. Higher mastery extends duration and strength."
    ),
    skills.DIVINE_JUDGEMENT: (
        "Channel holy wrath against your enemies. Smite foes with radiant "
        "damage, call down divine strikes, and punish the wicked. The "
        "offensive school for clerics. Higher mastery unlocks more powerful "
        "judgements."
    ),
    skills.DIVINE_REVELATION: (
        "Divine sight and prophecy — detect evil, see through lies, reveal "
        "hidden truths, and commune with the divine for guidance. Higher "
        "mastery grants true sight and deeper communion."
    ),
    skills.DIVINE_DOMINION: (
        "Command through holy authority — compel obedience, bind with sacred "
        "oaths, and exert divine will over the weak-minded. Includes the "
        "Command spell which forces a target to drop their weapon, flee, or "
        "halt. Higher mastery affects more powerful targets."
    ),
    skills.TURN_UNDEAD: (
        "Channel divine energy to repel the undead. Lower-level undead are "
        "stunned and flee; at higher mastery, weaker undead are destroyed "
        "outright. Affects more and tougher undead as mastery increases."
    ),
}

