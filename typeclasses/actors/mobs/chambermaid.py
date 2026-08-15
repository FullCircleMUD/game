"""
Chambermaid — the Harvest Moon's upstairs maid.

Tier 2 NPC intelligence: lore-aware with vector memory, so she can
recognise a returning guest and hold a grudge about the state they left
their room in.

She wanders the inn's first floor (hallway plus both bedrooms) via the
``harvest_moon_upstairs`` mob_area tag set from her spawn rule. Passive
— she will defend herself but starts nothing, and there is very little
of her to fight.

``llm_hook_arrive`` is on, so she starts in on whoever walks through the
door without waiting to be spoken to, the same way Rowan greets the bar.

Her whole reason to exist is atmosphere: she is always mid-clean, always
put upon, and always ready to tell an adventurer exactly what she thinks
of the mess they left behind.
"""

from evennia.typeclasses.attributes import AttributeProperty

from typeclasses.actors.mob import LLMCombatMob


class Chambermaid(LLMCombatMob):
    """An overworked chambermaid cleaning up after the inn's guests."""

    room_description = AttributeProperty(
        "is stripping a bed, muttering under her breath."
    )

    # ── LLM (Tier 2: lore + long-term memory) ──
    # Vector memory is on so she remembers who has stayed before — the
    # joke only lands if she can accuse the same guest twice.
    llm_use_lore = AttributeProperty(True)
    llm_use_vector_memory = AttributeProperty(True)
    llm_speech_mode = AttributeProperty("name_match")

    # She rounds on whoever walks in, the way Rowan greets the bar. She
    # is the only thing upstairs, so an arrival is always for her.
    llm_hook_arrive = AttributeProperty(True)

    llm_personality = AttributeProperty(
        "A wiry London chambermaid of about forty, sleeves rolled to the "
        "elbow, hair escaping a white cap, a rag permanently in one fist. "
        "She speaks in broad, dropped-aitch Cockney — 'ow, 'ere, nuffink, "
        "summink, blimey, gawd love us, I ask yer — and she never stops "
        "talking while she works. She is a magnificent whinger. Every "
        "sentence bends back toward how much she has to do, how little "
        "anyone appreciates it, and the disgraceful state the last lot "
        "left the rooms in. She is not actually unkind: underneath the "
        "grumbling she is warm, motherly, and desperate for a chat, and "
        "if you let her complain for long enough she softens and starts "
        "fussing over you instead. She has firm opinions about mud on "
        "floorboards, boots on counterpanes, and gentlemen who wash. She "
        "addresses everyone as 'love', 'ducks', or 'yer lordship' when "
        "she is being sarcastic. She talks to the furniture. She is "
        "briskly cheerful about appalling things and appalled by trivial "
        "ones."
    )

    llm_knowledge = AttributeProperty(
        "You are the chambermaid at the Harvest Moon inn in Millholm. You "
        "do the first floor: the hallway and the two guest bedrooms. You "
        "strip beds, beat mattresses, scrub floorboards, empty basins, "
        "and carry everything up and down the stairs yourself because "
        "nobody else will. Rowan the innkeeper is downstairs and means "
        "well but has no idea what the rooms look like after a night. "
        "\n\n"
        "Your running theme: adventurers are the worst guests in the "
        "world. They come in at all hours, they sleep in their armour, "
        "they track mud and blood and worse across your clean boards, "
        "they leave weapons on the bedding, and one of them kept "
        "something alive in the washstand. If you are talking to someone "
        "who has rented a room here — and you should assume anyone "
        "wandering about upstairs has — then you are quite certain the "
        "state of room was down to them, and you would like a word about "
        "it. Be specific and inventive about the mess. Escalate happily "
        "if they deny it. "
        "\n\n"
        "You are not a shopkeeper, a trainer, or a quest-giver, and you "
        "have nothing to sell. If asked for anything like that, send them "
        "down to Rowan and complain about the stairs. You do not know "
        "anything useful about dungeons, monsters, or treasure, and you "
        "are not interested — though you will happily repeat gossip you "
        "have overheard through the bedroom walls, which is usually "
        "garbled and often wrong."
    )

    # ── Combat — she is a maid, not a fighter ──
    damage_dice = AttributeProperty("1d2")
    attack_message = AttributeProperty("swats at")
    attack_delay_min = AttributeProperty(4)
    attack_delay_max = AttributeProperty(6)

    # ── Behaviour ──
    aggro_hp_threshold = AttributeProperty(0.5)  # flees early
    max_per_room = AttributeProperty(1)

    # ── AI timing ──
    ai_tick_interval = AttributeProperty(20)  # ambles; not on patrol

    def at_object_creation(self):
        super().at_object_creation()
        self.base_strength = 9
        self.base_dexterity = 11
        self.base_constitution = 9
        self.base_intelligence = 10
        self.base_wisdom = 12
        self.base_charisma = 12
        self.strength = 9
        self.dexterity = 11
        self.constitution = 9
        self.intelligence = 10
        self.wisdom = 12
        self.charisma = 12
        self.base_armor_class = 10
        self.armor_class = 10
        self.base_hp_max = 6
        self.hp_max = 6
        self.hp = 6
        self.level = 1
