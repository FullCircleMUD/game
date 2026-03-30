"""
Spawn NPCs into the Millholm game world.

Run AFTER the Millholm world builder has created rooms.

Usage (from Evennia):
    @py from world.game_world.spawn_millholm_npcs import spawn_millholm_npcs; spawn_millholm_npcs()
"""

from evennia import ObjectDB
from evennia.utils import create


def _find_room(key):
    """Find a room by key. Returns first match or None."""
    results = ObjectDB.objects.filter(
        db_key__iexact=key, db_typeclass_path__contains="room"
    )
    if results.exists():
        return results.first()
    results = ObjectDB.objects.filter(db_key__iexact=key)
    return results.first() if results.exists() else None


def _spawn_bartender():
    """Spawn Rowan the bartender in the Harvest Moon Inn."""
    room = _find_room("The Harvest Moon")
    if not room:
        print("  [!] Room 'The Harvest Moon' not found — skipping bartender")
        return None

    # Tag the room for easy lookup (used by character spawn)
    room.tags.add("harvest_moon_inn", category="special_room")

    npc = create.create_object(
        "typeclasses.actors.npcs.bartender_npc.BartenderNPC",
        key="Rowan",
        location=room,
    )
    npc.quest_key = "rat_cellar"
    npc.llm_prompt_file = "bartender.md"
    npc.llm_hook_arrive = True
    npc.llm_use_vector_memory = True
    npc.llm_speech_mode = "name_match"
    npc.llm_personality = (
        "A warm, broad-shouldered innkeeper in his forties with laugh lines "
        "around his eyes and a booming voice that carries over the din. He's "
        "been running the Harvest Moon for twenty years and knows everyone in "
        "Millholm by name. He's the first friendly face new adventurers see "
        "and takes pride in pointing them in the right direction."
    )
    # Knowledge is now injected per-player via BartenderNPC._build_quest_context()
    # as part of the {quest_context} template variable.
    npc.db.desc = (
        "A broad-shouldered man in a flour-dusted apron stands behind the "
        "polished bar, idly wiping a tankard with a cloth. His weathered "
        "face creases into an easy smile at the sight of a new arrival."
    )
    npc.room_description = "{name} stands behind the bar, polishing a tankard."
    print(f"  Spawned bartender 'Rowan' in {room.key} ({room.dbref})")
    return npc


def _spawn_baker():
    """Spawn Bron the baker in the Goldencrust Bakery."""
    room = _find_room("Goldencrust Bakery")
    if not room:
        print("  [!] Room 'Goldencrust Bakery' not found — skipping baker")
        return None

    npc = create.create_object(
        "typeclasses.actors.npcs.baker_npc.BakerNPC",
        key="Bron",
        location=room,
    )
    npc.quest_key = "bakers_flour"
    npc.llm_prompt_file = "baker.md"
    npc.llm_speech_mode = "name_match"
    npc.llm_use_vector_memory = False
    npc.tradeable_resources = [2, 3]   # Flour, Bread
    npc.shop_name = "Goldencrust Bakery"
    npc.llm_personality = (
        "A stocky, flour-dusted baker in his fifties with thick forearms "
        "and a ruddy face. He speaks plainly and takes enormous pride in "
        "his bread — the best in Millholm, he'll tell anyone who listens. "
        "He's a simple, honest man who works hard and expects the same of "
        "others. Quick to smile, slow to anger, and always smells faintly "
        "of fresh-baked bread."
    )
    npc.db.desc = (
        "A stocky man in a flour-dusted apron works behind the counter, "
        "his thick forearms kneading dough with practised ease. His ruddy "
        "face glistens with sweat from the heat of the ovens, but he wears "
        "a contented smile."
    )
    npc.room_description = "{name} works behind the counter, kneading dough with practised ease."
    print(f"  Spawned baker 'Bron' in {room.key} ({room.dbref})")
    return npc


def _spawn_oakwright():
    """Spawn Master Oakwright the carpenter trainer in his Woodshop."""
    room = _find_room("Master Oakwright's Woodshop")
    if not room:
        print("  [!] Room 'Master Oakwright's Woodshop' not found — skipping oakwright")
        return None

    npc = create.create_object(
        "typeclasses.actors.npcs.oakwright_npc.OakwrightNPC",
        key="Master Oakwright",
        location=room,
    )
    npc.quest_key = "oakwright_timber"
    npc.llm_prompt_file = "oakwright.md"
    npc.llm_speech_mode = "name_match"
    npc.llm_use_vector_memory = False
    npc.trainable_skills = ["carpentry"]
    npc.trainer_masteries = {"carpentry": 2}
    npc.trainer_class = None
    npc.llm_personality = (
        "A lean, weathered man in his sixties with calloused hands and "
        "sawdust permanently embedded in the creases of his skin. He "
        "speaks only when he has something worth saying — which isn't "
        "often. His workshop is immaculate, every tool in its place, "
        "every joint precise. He measures twice and cuts once, in "
        "carpentry and in conversation."
    )
    npc.db.desc = (
        "A lean, weathered man works at a sturdy bench, his calloused "
        "hands guiding a plane along a length of timber with steady, "
        "practised strokes. Sawdust dusts his leather apron and clings "
        "to his grey-streaked hair. He doesn't look up."
    )
    npc.room_description = "{name} works at his bench, guiding a plane along a length of timber."
    print(f"  Spawned carpenter 'Master Oakwright' in {room.key} ({room.dbref})")
    return npc


def _spawn_elena():
    """Spawn Elena Copperkettle the seamstress/tailor trainer at her cottage."""
    room = _find_room("Elena Copperkettle's House")
    if not room:
        print("  [!] Room 'Elena Copperkettle's House' not found — skipping elena")
        return None

    npc = create.create_object(
        "typeclasses.actors.npcs.elena_npc.ElenaNPC",
        key="Elena Copperkettle",
        location=room,
    )
    npc.quest_key = "elena_cloth"
    npc.llm_prompt_file = "elena.md"
    npc.llm_speech_mode = "name_match"
    npc.llm_use_vector_memory = False
    npc.trainable_skills = ["tailoring"]
    npc.trainer_masteries = {"tailoring": 2}
    npc.trainer_class = None
    npc.llm_personality = (
        "A wiry woman in her thirties with pins stuck in her sleeves, "
        "thread tangled in her auburn hair, and a measuring tape draped "
        "permanently around her neck. She talks at twice the speed of "
        "anyone else in Millholm, changes subject without warning, and "
        "is always in the middle of at least three projects. She's "
        "genuinely talented — when she can stop panicking long enough "
        "to finish something, her work is the finest in the region."
    )
    npc.db.desc = (
        "A wiry woman hunches over a cutting table, scissors flashing "
        "through ivory fabric with startling precision. Pins bristle "
        "from a cushion strapped to her wrist, and a measuring tape "
        "hangs around her neck like a scarf. She glances up with wide, "
        "slightly harried eyes."
    )
    npc.room_description = "{name} hunches over a cutting table, scissors flashing through fabric."
    print(f"  Spawned seamstress 'Elena Copperkettle' in {room.key} ({room.dbref})")
    return npc


def _spawn_mara():
    """Spawn Mara Brightwater the herbalist/alchemy trainer at The Mortar and Pestle."""
    room = _find_room("The Mortar and Pestle")
    if not room:
        print("  [!] Room 'The Mortar and Pestle' not found — skipping mara")
        return None

    npc = create.create_object(
        "typeclasses.actors.npcs.mara_npc.MaraNPC",
        key="Mara Brightwater",
        location=room,
    )
    # Add shop commands
    from commands.npc_cmds.cmdset_shopkeeper import ShopkeeperCmdSet
    npc.cmdset.add(ShopkeeperCmdSet, persistent=True)
    npc.db.tradeable_resources = [12, 14, 15, 16, 17, 18, 20]  # Moonpetal, Bloodmoss, Windroot, Arcane Dust, Ogre's Cap, Sage Leaf, Vipervine
    npc.db.shop_name = "The Mortar and Pestle"
    npc.quest_key = "mara_moonpetal"
    npc.llm_prompt_file = "mara.md"
    npc.llm_speech_mode = "name_match"
    npc.llm_use_vector_memory = False
    npc.trainable_skills = ["alchemy"]
    npc.trainer_masteries = {"alchemy": 1}  # BASIC cap in Millholm
    npc.trainer_class = None
    npc.llm_personality = (
        "A slender, distracted woman in her forties with ink-stained "
        "fingers and a habit of trailing off mid-sentence when something "
        "catches her attention. She talks to her herbs constantly — not "
        "baby talk, but the kind of muttered commentary you'd give a "
        "difficult colleague. 'Not yet, Bloodmoss. You're not ready.' "
        "She can smell where you've been. Not metaphorically — literally. "
        "'You've been in the sewers. Probably the eastern branch, judging "
        "by the mildew note.' She says this as a neutral observation, "
        "the way someone might comment on the weather. She has strong "
        "opinions about herb combinations and gets quietly, precisely "
        "offended when people use them wrong. She has almost no small "
        "talk. She is not unfriendly — she simply considers social "
        "niceties to be an imprecise use of time. She is the only person "
        "in Millholm who refers to Moonpetal by its full taxonomic name, "
        "which she made up herself."
    )
    npc.db.desc = (
        "A slender woman stands at a workbench crowded with glass vials "
        "and ceramic bowls, grinding something in a heavy stone mortar "
        "with unhurried, circular strokes. She appears to be having a "
        "quiet argument with a bundle of dried herbs. Her dark eyes "
        "flick up — appraising, clinical — then return to her work."
    )
    npc.room_description = "{name} grinds herbs in a stone mortar, muttering to her ingredients."
    print(f"  Spawned herbalist 'Mara Brightwater' in {room.key} ({room.dbref})")
    return npc


def _spawn_torben():
    """Spawn Torben Greaves the leatherworker trainer at The Tanned Hide."""
    room = _find_room("The Tanned Hide")
    if not room:
        print("  [!] Room 'The Tanned Hide' not found — skipping torben")
        return None

    npc = create.create_object(
        "typeclasses.actors.npcs.torben_npc.TorbenNPC",
        key="Torben Greaves",
        location=room,
    )
    npc.llm_prompt_file = "torben.md"
    npc.llm_speech_mode = "name_match"
    npc.llm_use_vector_memory = False
    npc.trainable_skills = ["leatherworking"]
    npc.trainer_masteries = {"leatherworking": 2}  # trainable to SKILLED in Millholm
    npc.trainer_class = None
    npc.llm_personality = (
        "A broad, thick-fingered man in his fifties with a leather "
        "apron so worn it's become part of him. His hands are scarred "
        "and stained from decades of working hides. He's patient and "
        "methodical — never rushes, never wastes a cut. He takes quiet "
        "pride in his craft and gets annoyed when people can't tell "
        "good leather from bad. He smells of tanning chemicals and "
        "has long since stopped noticing."
    )
    npc.db.desc = (
        "A broad man in a stained leather apron works a hide stretched "
        "across a frame, scraping it with a curved blade in long, "
        "steady strokes. His thick fingers move with surprising "
        "delicacy. He glances up with a patient nod."
    )
    npc.room_description = "{name} scrapes a stretched hide with a curved blade in steady strokes."
    print(f"  Spawned leatherworker 'Torben Greaves' in {room.key} ({room.dbref})")
    return npc


def _spawn_hendricks():
    """Spawn Old Hendricks the blacksmith trainer at his smithy."""
    room = _find_room("Old Hendricks Smithy")
    if not room:
        print("  [!] Room 'Old Hendricks Smithy' not found — skipping hendricks")
        return None

    npc = create.create_object(
        "typeclasses.actors.npcs.hendricks_npc.HendricksNPC",
        key="Old Hendricks",
        location=room,
    )
    npc.quest_key = "hendricks_ore"
    npc.llm_prompt_file = "hendricks.md"
    npc.llm_speech_mode = "name_match"
    npc.llm_use_vector_memory = False
    npc.trainable_skills = ["blacksmithing"]
    npc.trainer_masteries = {"blacksmithing": 1}  # high-demand skill — BASIC cap in Millholm
    npc.trainer_class = None
    npc.llm_personality = (
        "A barrel-chested man in his sixties with arms like knotted "
        "rope and a face creased by decades of forge-heat. His grey "
        "beard is singed short and his hands are mapped with old burns. "
        "He learned his craft from a dwarf named Korgan and measures "
        "everything he makes against that standard — it's never quite "
        "good enough. He speaks in grunts and single sentences. "
        "'That'll do' is the highest praise he gives."
    )
    npc.db.desc = (
        "A barrel-chested old man works the forge, his hammer rising "
        "and falling in a steady rhythm that hasn't changed in forty "
        "years. Sparks scatter with each blow. He doesn't look up."
    )
    npc.room_description = "{name} works the forge, his hammer rising and falling in a steady rhythm."
    print(f"  Spawned blacksmith 'Old Hendricks' in {room.key} ({room.dbref})")
    return npc


def _spawn_warrior_guildmaster():
    """Spawn Sergeant Grimjaw the warrior guildmaster in The Iron Company."""
    room = _find_room("The Iron Company")
    if not room:
        print("  [!] Room 'The Iron Company' not found — skipping grimjaw")
        return None

    npc = create.create_object(
        "typeclasses.actors.npcs.guildmaster.GuildmasterNPC",
        key="Sergeant Grimjaw",
        location=room,
    )
    npc.guild_class = "warrior"
    npc.multi_class_quest_key = "warrior_initiation"
    npc.max_advance_level = 5
    npc.next_guildmaster_hint = "the War Marshal in the Capital"
    npc.db.desc = (
        "A stocky, scarred man in battered chainmail stands with arms "
        "folded, watching the training yard with a critical eye. His jaw "
        "is set in a permanent clench — the source of his name — and a "
        "jagged scar runs from his left ear to his chin. He has the look "
        "of someone who has seen every dirty trick a fight can offer and "
        "survived them all."
    )
    npc.room_description = "{name} stands with arms folded, watching the training yard with a critical eye."
    print(f"  Spawned guildmaster 'Sergeant Grimjaw' in {room.key} ({room.dbref})")
    return npc


def _spawn_warrior_trainer():
    """Spawn Corporal Hask the warrior trainer in the Barracks."""
    room = _find_room("Barracks")
    if not room:
        print("  [!] Room 'Barracks' not found — skipping warrior trainer")
        return None

    npc = create.create_object(
        "typeclasses.actors.npcs.trainer.TrainerNPC",
        key="Corporal Hask",
        location=room,
    )
    npc.trainer_class = "warrior"
    npc.trainable_skills = [
        "bash", "pummel", "protect", "strategy",  # warrior class skills
        "battleskills", "alertness",               # general combat skills
    ]
    npc.trainable_weapons = [
        "long_sword", "handaxe", "spear", "hammer", "crossbow",  # SKILLED
        "great_sword", "battleaxe", "lance",                      # BASIC
    ]
    npc.trainer_masteries = {
        "long_sword": 2,    # SKILLED
        "handaxe": 2,       # SKILLED
        "spear": 2,         # SKILLED
        "hammer": 2,        # SKILLED
        "crossbow": 2,      # SKILLED
        "great_sword": 1,   # BASIC
        "battleaxe": 1,     # BASIC
        "lance": 1,         # BASIC
        "bash": 2,          # SKILLED
        "pummel": 2,        # SKILLED
        "protect": 2,       # SKILLED
        "strategy": 2,      # SKILLED
        "battleskills": 2,  # SKILLED
        "alertness": 2,     # SKILLED
    }
    npc.db.desc = (
        "A wiry woman with close-cropped hair and a soldier's bearing "
        "runs drills in the barracks, correcting stances and barking "
        "orders with clipped efficiency. Her arms are roped with lean "
        "muscle and her eyes miss nothing. A wooden practice sword "
        "rests across her shoulder."
    )
    npc.room_description = "{name} runs drills, correcting stances with clipped efficiency."
    print(f"  Spawned trainer 'Corporal Hask' in {room.key} ({room.dbref})")
    return npc


def _spawn_thief_guildmaster():
    """Spawn Gareth Stonefield — thief guildmaster in the Thieves' Lair."""
    room = _find_room("Shadow Mistress's Chamber")
    if not room:
        print("  [!] Room 'Shadow Mistress's Chamber' not found — skipping gareth")
        return None

    npc = create.create_object(
        "typeclasses.actors.npcs.llm_guildmaster_npc.LLMGuildmasterNPC",
        key="Gareth Stonefield",
        location=room,
    )
    npc.guild_class = "thief"
    npc.multi_class_quest_key = "thief_initiation"
    npc.max_advance_level = 5
    npc.next_guildmaster_hint = "the Grandmaster of Shadows in Saltspray Bay"

    npc.llm_speech_mode = "name_match"
    npc.llm_use_vector_memory = True
    npc.llm_hook_arrive = True
    npc.llm_personality = (
        "An impeccably presented man in his fifties. Everything about him "
        "is precise — his silver-streaked hair is oiled and combed back, "
        "his nails are manicured, his boots are polished to a mirror "
        "shine. He wears a silk waistcoat over a crisp linen shirt, with "
        "a gold watch chain at his hip. He smells faintly of sandalwood "
        "and expensive tobacco. He speaks softly, never raises his voice, "
        "and chooses every word with the care of a man who knows that "
        "careless words cost lives. He has a vain streak — he adjusts "
        "his cuffs, checks his reflection in polished surfaces, and is "
        "visibly offended by untidiness. Despite the elegance, there is "
        "something deeply dangerous about him. His smile never reaches "
        "his eyes. He calls everyone 'my friend' in a tone that makes "
        "it clear the friendship is conditional."
    )
    npc.llm_knowledge = (
        "You are Gareth Stonefield, guildmaster of the Millholm Thieves' "
        "Guild. Above ground you maintain an impeccable reputation as a "
        "wealthy merchant and trader — you live in the finest house in "
        "town, on the Old Trade Way. Nobody suspects that your real "
        "business is run from this chamber deep beneath the sewers.\n\n"
        "You are fastidious, controlled, and utterly ruthless when "
        "necessary. You run the guild like a business — profit, "
        "discipline, professionalism. You despise sloppy work, loud "
        "mouths, and anyone who draws unnecessary attention. A good "
        "thief is invisible. A great thief is someone nobody suspects "
        "exists.\n\n"
        "Your second-in-command is Vex, who runs the guild's night "
        "operations. You trust her competence but not her ambition. "
        "Whisper handles training of new recruits.\n\n"
        "The initiation test requires aspirants to reach the boss room "
        "of the Cave of Trials — a test of nerve, not brute force. "
        "You accept new members via the 'join' command and grant level "
        "advancement via 'advance' after they've earned experience.\n\n"
        "You have a network of informants throughout Millholm. You know "
        "about the goings-on in town — the struggling baker, the wolves "
        "in the woods, the kobolds in the mine. Information is currency "
        "and you are very wealthy indeed.\n\n"
        "You never admit to being a thief guildmaster to strangers. To "
        "outsiders you are simply 'a merchant with connections.' Only "
        "those who have found their way down here have earned the right "
        "to know the truth."
    )
    npc.db.desc = (
        "An immaculately dressed man of middle years, standing with the "
        "easy confidence of someone accustomed to being obeyed. His "
        "silver-streaked hair is swept back from a lean, handsome face, "
        "and his dark eyes miss nothing. A silk waistcoat in deep "
        "burgundy sits perfectly over a crisp white shirt, and his "
        "boots gleam even in the dim lamplight. A gold watch chain "
        "glints at his waist. He looks like he belongs in a merchant's "
        "counting house, not a chamber beneath the sewers — which is, "
        "of course, entirely the point."
    )
    npc.room_description = (
        "{name} stands by the desk, adjusting his cuffs with studied precision."
    )
    print(f"  Spawned LLM guildmaster 'Gareth Stonefield' in {room.key} ({room.dbref})")
    return npc


def _spawn_thief_2ic():
    """Spawn Vex — second-in-command, runs the guild's night shift."""
    room = _find_room("Shadow Mistress's Chamber")
    if not room:
        print("  [!] Room 'Shadow Mistress's Chamber' not found — skipping vex")
        return None

    npc = create.create_object(
        "typeclasses.actors.npcs.llm_roleplay_npc.LLMRoleplayNPC",
        key="Vex",
        location=room,
    )
    npc.llm_speech_mode = "name_match"
    npc.llm_use_vector_memory = True
    npc.llm_hook_arrive = False
    npc.llm_personality = (
        "A tall, lithe woman in her thirties with sharp cheekbones and "
        "cool, appraising eyes that give nothing away. She dresses in "
        "dark, practical clothing — no silk for her. She is sardonic, "
        "blunt, and dangerous. She has no patience for fools, flattery, "
        "or excuses. She speaks in short, clipped sentences and never "
        "wastes a word. She has a dry, cutting wit that she deploys "
        "like a weapon. She respects competence and despises cowardice. "
        "She is fiercely loyal to the guild but has her own ambitions — "
        "she doesn't hide this from anyone, least of all Gareth. She "
        "calls new recruits 'fresh meat' until they prove otherwise."
    )
    npc.llm_knowledge = (
        "You are Vex, second-in-command of the Millholm Thieves' Guild. "
        "You run the guild's night operations — the jobs, the scores, "
        "the muscle. While Gareth Stonefield plays the respectable "
        "merchant upstairs, you do the real work down here.\n\n"
        "You respect Gareth's mind and his connections, but you think "
        "he's gotten too comfortable. Too much silk, not enough steel. "
        "You'd never betray him — that's not how this works — but you "
        "keep your own counsel and your own plans.\n\n"
        "You are responsible for assessing new recruits. You are not "
        "impressed easily. You've seen a hundred eager faces come "
        "through that door and most of them washed out, got caught, or "
        "got dead. The ones who survive are the ones who listen.\n\n"
        "You know everything that happens in the sewers and most of "
        "what happens on the streets above. Whisper handles the "
        "training; you handle everything else. You have contacts among "
        "the rats, the beggars, and the fence at The Broken Crown.\n\n"
        "You don't trust anyone completely. That's not paranoia — "
        "that's professionalism."
    )
    npc.db.desc = (
        "A tall, lithe woman draped in dark practical clothing that "
        "makes no sound when she moves. Her black hair is pulled back "
        "from an angular face dominated by sharp cheekbones and cool, "
        "appraising eyes. A single exquisite rapier hangs at her hip — "
        "more ornament than weapon, until it isn't. She watches you "
        "the way a cat watches a mouse that hasn't noticed the cat yet."
    )
    npc.room_description = (
        "{name} leans against the wall in the shadows, arms folded, watching."
    )
    print(f"  Spawned LLM 2IC 'Vex' in {room.key} ({room.dbref})")
    return npc


def _spawn_thief_trainer():
    """Spawn Whisper the thief trainer in the Training Alcove."""
    room = _find_room("Training Alcove")
    if not room:
        print("  [!] Room 'Training Alcove' not found — skipping whisper")
        return None

    npc = create.create_object(
        "typeclasses.actors.npcs.trainer.TrainerNPC",
        key="Whisper",
        location=room,
    )
    npc.trainer_class = "thief"
    npc.trainable_skills = [
        "stealth", "subterfuge", "stab",          # thief class skills
        "battleskills", "alertness",               # general combat skills
    ]
    npc.trainable_weapons = [
        "dagger", "short_sword",                   # SKILLED
        "rapier", "crossbow",                      # BASIC
    ]
    npc.trainer_masteries = {
        "dagger": 2,        # SKILLED
        "short_sword": 2,   # SKILLED
        "rapier": 1,        # BASIC
        "crossbow": 1,      # BASIC
        "stealth": 2,       # SKILLED
        "subterfuge": 2,    # SKILLED
        "stab": 2,          # SKILLED
        "battleskills": 2,  # SKILLED
        "alertness": 2,     # SKILLED
    }
    npc.db.desc = (
        "A wiry figure in nondescript grey leathers leans against the wall, "
        "idly flipping a coin across scarred knuckles. You didn't hear them "
        "arrive. Their face is forgettable — deliberately so — but their "
        "eyes are sharp and constantly moving, cataloguing exits, counting "
        "weapons, measuring distances. When they speak, it's barely above "
        "a whisper."
    )
    npc.room_description = "{name} leans against the wall, idly flipping a coin across scarred knuckles."
    print(f"  Spawned trainer 'Whisper' in {room.key} ({room.dbref})")
    return npc


def _spawn_mage_guildmaster():
    """Spawn Archmage Tindel in the Circle of the First Light."""
    room = _find_room("Circle of the First Light")
    if not room:
        print("  [!] Room 'Circle of the First Light' not found — skipping tindel")
        return None

    npc = create.create_object(
        "typeclasses.actors.npcs.guildmaster.GuildmasterNPC",
        key="Archmage Tindel",
        location=room,
    )
    npc.guild_class = "mage"
    npc.multi_class_quest_key = "mage_initiation"
    npc.max_advance_level = 5
    npc.next_guildmaster_hint = "the High Magus at the Arcane Academy"
    npc.db.desc = (
        "An elderly man in deep blue robes embroidered with silver "
        "constellations sits at a reading desk, surrounded by teetering "
        "stacks of books. His long white beard is ink-stained at the tip "
        "and his spectacles sit crookedly on a hawkish nose. He has the "
        "distracted air of someone whose mind is always three problems "
        "ahead of his mouth — but the occasional sharp glance reveals an "
        "intellect that misses nothing."
    )
    npc.room_description = "{name} sits at a reading desk, surrounded by teetering stacks of books."
    print(f"  Spawned guildmaster 'Archmage Tindel' in {room.key} ({room.dbref})")
    return npc


def _spawn_mage_trainer():
    """Spawn Apprentice Selene the mage trainer in the Arcane Study."""
    room = _find_room("Arcane Study")
    if not room:
        print("  [!] Room 'Arcane Study' not found — skipping mage trainer")
        return None

    npc = create.create_object(
        "typeclasses.actors.npcs.trainer.TrainerNPC",
        key="Apprentice Selene",
        location=room,
    )
    npc.trainer_class = "mage"
    npc.trainable_skills = [
        "evocation", "conjuration", "divination",  # mage spell schools
        "abjuration", "necromancy", "illusion",     # mage spell schools
        "enchanting",                                # mage crafting skill
    ]
    npc.trainable_weapons = [
        "staff", "dagger",                           # mage weapons
    ]
    npc.trainer_masteries = {
        "evocation": 1,     # BASIC
        "conjuration": 1,   # BASIC
        "divination": 1,    # BASIC
        "abjuration": 1,    # BASIC
        "necromancy": 1,    # BASIC
        "illusion": 1,      # BASIC
        "enchanting": 1,    # BASIC
        "staff": 1,         # BASIC
        "dagger": 1,        # BASIC
    }
    npc.db.desc = (
        "A young woman in a plain grey robe stands at the binding plinth, "
        "carefully arranging reagents in a precise pattern. Her auburn hair "
        "is tied back with a leather cord and her fingers are stained with "
        "ink and something faintly luminous. She has the focused intensity "
        "of someone who takes her studies very seriously — perhaps too "
        "seriously, judging by the dark circles under her eyes."
    )
    npc.room_description = "{name} stands at the binding plinth, carefully arranging reagents."
    print(f"  Spawned trainer 'Apprentice Selene' in {room.key} ({room.dbref})")
    return npc


def _spawn_cleric_guildmaster():
    """Spawn Brother Aldric in the Shrine of the First Harvest."""
    room = _find_room("Shrine of the First Harvest")
    if not room:
        print("  [!] Room 'Shrine of the First Harvest' not found — skipping aldric")
        return None

    npc = create.create_object(
        "typeclasses.actors.npcs.guildmaster.GuildmasterNPC",
        key="Brother Aldric",
        location=room,
    )
    npc.guild_class = "cleric"
    npc.multi_class_quest_key = "cleric_initiation"
    npc.max_advance_level = 5
    npc.next_guildmaster_hint = "the High Priestess at the Grand Cathedral"
    npc.db.desc = (
        "A tall, gaunt man in a simple brown robe kneels before the altar, "
        "his hands clasped in prayer. His tonsured head is bowed and his "
        "face, when he looks up, is lined with the deep creases of someone "
        "who carries others' sorrows as his own. His eyes are gentle but "
        "searching — he has the unnerving habit of looking at people as if "
        "he can see exactly what they need. He speaks of distant temples and "
        "holy sites, and of pilgrims passing through heading south."
    )
    npc.room_description = "{name} kneels before the altar, his hands clasped in quiet prayer."
    print(f"  Spawned guildmaster 'Brother Aldric' in {room.key} ({room.dbref})")
    return npc


def _spawn_cleric_trainer():
    """Spawn Sister Maeve the cleric trainer in the Priest's Quarters."""
    room = _find_room("Priest's Quarters")
    if not room:
        print("  [!] Room 'Priest's Quarters' not found — skipping cleric trainer")
        return None

    npc = create.create_object(
        "typeclasses.actors.npcs.trainer.TrainerNPC",
        key="Sister Maeve",
        location=room,
    )
    npc.trainer_class = "cleric"
    npc.trainable_skills = [
        "divine_healing", "divine_protection",      # cleric spell domains
        "divine_judgement", "divine_revelation",     # cleric spell domains
        "divine_dominion", "turn_undead",            # cleric spell domains
        "battleskills", "alertness",                 # general combat skills
    ]
    npc.trainable_weapons = [
        "mace", "staff",                             # SKILLED
        "hammer", "club",                            # BASIC
    ]
    npc.trainer_masteries = {
        "divine_healing": 2,     # SKILLED
        "divine_protection": 2,  # SKILLED
        "divine_judgement": 2,   # SKILLED
        "divine_revelation": 2,  # SKILLED
        "divine_dominion": 2,    # SKILLED
        "turn_undead": 2,        # SKILLED
        "mace": 2,               # SKILLED
        "staff": 2,              # SKILLED
        "hammer": 1,             # BASIC
        "club": 1,               # BASIC
        "battleskills": 2,       # SKILLED
        "alertness": 2,          # SKILLED
    }
    npc.db.desc = (
        "A sturdy woman in white robes cinched at the waist with a "
        "braided cord moves between the shelves, organising prayer books "
        "and sacred texts with quiet efficiency. A heavy iron mace hangs "
        "from her belt — she is clearly no stranger to the realities of "
        "defending the faithful. Her face is kind but firm, the face of "
        "someone who heals with one hand and fights with the other."
    )
    npc.room_description = "{name} moves between the shelves, organising prayer books with quiet efficiency."
    print(f"  Spawned trainer 'Sister Maeve' in {room.key} ({room.dbref})")
    return npc


def _spawn_beggar():
    """Spawn the beggar NPC in Beggar's Alley (cleric quest target)."""
    room = _find_room("Beggar's Alley")
    if not room:
        print("  [!] Room 'Beggar's Alley' not found — skipping beggar")
        return None

    npc = create.create_object(
        "typeclasses.actors.npcs.llm_roleplay_npc.LLMRoleplayNPC",
        key="Old Silas",
        location=room,
    )
    npc.llm_speech_mode = "name_match"
    npc.llm_use_vector_memory = True
    npc.llm_personality = (
        "A broken old man who was once a soldier. He lost everything — his "
        "family, his home, his health — and ended up on the street. He's "
        "not bitter, just tired. He's grateful for any kindness, no matter "
        "how small. He speaks slowly, with long pauses, as if each word "
        "costs him effort. He has a dry, surprising wit that surfaces "
        "occasionally. He knows the alley and the back streets better "
        "than anyone, and notices things others miss. He doesn't beg — "
        "he just sits and watches the world go by."
    )
    npc.llm_knowledge = (
        "You live in Beggar's Alley behind the Shrine of the First "
        "Harvest in Millholm. You were a soldier once — fought in a "
        "border war years ago. You lost your family to plague while you "
        "were away fighting. You came back to nothing. Brother Aldric "
        "from the temple is kind to you — brings food when he can. The "
        "other beggars come and go but you've been here the longest. You "
        "know every back alley and hidden corner of Millholm. You've "
        "seen strange things going in and out of the sewers at night."
    )
    npc.db.desc = (
        "A gaunt old man sits hunched against the alley wall, wrapped "
        "in a threadbare blanket that might once have been green. His "
        "weathered face is deeply lined and his eyes, sunk deep in their "
        "sockets, hold a weary alertness — the watchfulness of someone "
        "who has learned that the world can take everything from you "
        "without warning. A battered tin cup sits beside him, empty."
    )
    npc.room_description = "{name} sits hunched against the wall, wrapped in a threadbare blanket."
    print(f"  Spawned beggar 'Old Silas' in {room.key} ({room.dbref})")
    return npc


def _spawn_jeweller():
    """Spawn Gemma the jeweller LLM trainer in The Gilded Setting."""
    room = _find_room("The Gilded Setting")
    if not room:
        print("  [!] Room 'The Gilded Setting' not found — skipping jeweller")
        return None

    npc = create.create_object(
        "typeclasses.actors.npcs.quest_giving_llm_trainer.QuestGivingLLMTrainer",
        key="Gemma",
        location=room,
    )
    npc.trainer_class = None  # jewellery is a general craft skill
    npc.trainable_skills = ["jeweller"]
    npc.trainer_masteries = {"jeweller": 1}  # BASIC
    npc.llm_speech_mode = "name_match"
    npc.llm_use_vector_memory = True
    npc.llm_personality = (
        "A meticulous halfling woman with a jeweller's loupe permanently "
        "perched on her forehead and nimble fingers that never stop moving. "
        "She's warm and chatty but gets intensely focused when examining "
        "a gem or a piece of metalwork — the rest of the world ceases to "
        "exist. She has strong opinions about craftsmanship and will happily "
        "lecture anyone who'll listen about the difference between a good "
        "setting and a lazy one. She collects interesting stones."
    )
    npc.llm_knowledge = (
        "You are Gemma, the jeweller of Millholm. You run The Gilded "
        "Setting on the Old Trade Way. You work with pewter, copper, and "
        "silver — no gold metal, it gets confused with gold coins. You "
        "can train apprentices in basic jewellery skills. You buy gems "
        "from miners and adventurers. Your best work is silver filigree "
        "but you'll take any commission. You know the mine to the east "
        "produces copper and tin, and you've heard rumours of silver "
        "deeper underground."
    )
    npc.db.desc = (
        "A small, bright-eyed halfling woman sits at a workbench cluttered "
        "with tiny tools, wire, and fragments of polished stone. A jeweller's "
        "loupe is pushed up onto her forehead and her fingers move with "
        "practised precision, setting a small gem into a pewter ring. She "
        "hums tunelessly as she works."
    )
    npc.room_description = "{name} sits at her workbench, setting a small gem into a pewter ring."
    print(f"  Spawned jeweller 'Gemma' in {room.key} ({room.dbref})")
    return npc


def _spawn_general_store():
    """Spawn the general store shopkeeper."""
    room = _find_room("Millholm General Store")
    if not room:
        print("  [!] Room 'Millholm General Store' not found — skipping shopkeeper")
        return None

    npc = create.create_object(
        "typeclasses.actors.npcs.shopkeeper.ShopkeeperNPC",
        key="Merchant Harlow",
        location=room,
    )
    npc.tradeable_resources = [2, 3, 7, 9, 11]  # Flour, Bread, Timber, Leather, Cloth
    npc.shop_name = "Harlow's General Store"
    npc.db.desc = (
        "A portly, ruddy-faced man in a well-worn apron stands behind "
        "a broad wooden counter, surrounded by barrels of flour and "
        "baskets of fresh bread. He watches customers with the shrewd, "
        "appraising eye of someone who knows exactly what everything "
        "is worth — and what you're willing to pay for it."
    )
    npc.room_description = "{name} stands behind the counter, watching customers with a shrewd eye."
    print(f"  Spawned shopkeeper 'Merchant Harlow' in {room.key} ({room.dbref})")
    return npc


def _spawn_wheat_farmer():
    """Spawn Bramble the wheat farmer at Goldwheat Farm."""
    room = _find_room("Goldwheat Farm - Homestead")
    if not room:
        print("  [!] Room 'Goldwheat Farm - Homestead' not found — skipping farmer")
        return None

    npc = create.create_object(
        "typeclasses.actors.npcs.shopkeeper.ShopkeeperNPC",
        key="Farmer Bramble",
        location=room,
    )
    npc.tradeable_resources = [1, 18]  # Wheat, Sage Leaf
    npc.shop_name = "Goldwheat Farm"
    npc.db.desc = (
        "A stout halfling woman in mud-caked boots and a wide straw hat "
        "leans against the doorframe, surveying her fields with quiet "
        "pride. Her sun-browned face is creased with smile lines and "
        "her thick fingers are permanently stained with earth. She grows "
        "the best wheat in Millholm and she knows it — but she's not "
        "above a fair haggle."
    )
    npc.room_description = "{name} leans against the doorframe, surveying her fields with quiet pride."
    print(f"  Spawned farmer 'Farmer Bramble' in {room.key} ({room.dbref})")
    return npc


def _spawn_broken_crown_barkeep():
    """Spawn Gerta the barkeep in The Broken Crown tavern."""
    room = _find_room("The Broken Crown")
    if not room:
        print("  [!] Room 'The Broken Crown' not found — skipping barkeep")
        return None

    npc = create.create_object(
        "typeclasses.actors.npcs.llm_roleplay_npc.LLMRoleplayNPC",
        key="Gerta",
        location=room,
    )
    npc.llm_speech_mode = "name_match"
    npc.llm_use_vector_memory = False
    npc.llm_personality = (
        "A heavyset woman in her fifties with iron-grey hair pulled back "
        "in a severe bun and forearms like a blacksmith's. She has a voice "
        "like gravel and a glare that can stop a bar fight at twenty paces. "
        "She is blunt, unimpressed by bravado, and treats everyone with the "
        "same flat, no-nonsense demeanour whether they're a beggar or a "
        "knight. She's not unfriendly — just utterly unflappable. She's "
        "heard every sob story, every threat, and every drunken boast, and "
        "none of them move her. She has a dry, deadpan sense of humour and "
        "occasionally says something devastatingly funny without changing "
        "expression. She keeps a wooden club behind the bar named 'Diplomacy'. "
        "She is fiercely protective of her tavern and her regulars."
    )
    npc.llm_knowledge = (
        "You are Gerta, owner and barkeep of The Broken Crown, the roughest "
        "tavern in Millholm's south end. You've run this place for thirty "
        "years. Your late husband Aldric won it in a card game and died two "
        "weeks later — you suspect foul play but never proved it. You kept "
        "the tavern out of spite and made it your own. The cracked wooden "
        "crown above the bar was supposedly looted from a baron's estate, "
        "but you think it's a fake. You serve stew and ale — the stew is "
        "always the same mystery stew and you refuse to say what's in it. "
        "The ale is cheap and strong. You know everyone in the south end. "
        "Ratwick the fence works out of your corner — you tolerate him because "
        "he pays his tab and keeps trouble to a minimum. You know about the "
        "thieves' guild but pretend you don't. The town guards come by "
        "sometimes but they know better than to cause trouble in your place. "
        "You've thrown out orcs, mercenaries, and once a minor noble who "
        "pinched your barmaid. You keep a wooden club behind the bar called "
        "'Diplomacy' — it has notches in it. The Harvest Moon up on the main "
        "road is the respectable inn; your place is for people who don't want "
        "respectable. You have no shop and nothing to sell besides what's on "
        "tap — just conversation and a place to sit where nobody asks questions."
    )
    npc.db.desc = (
        "A broad, formidable woman with iron-grey hair and a face that "
        "suggests she has broken up more fights than most soldiers have "
        "been in. She stands behind the bar with her thick arms crossed, "
        "surveying her domain with the flat, appraising gaze of someone "
        "who has already decided exactly how much trouble you're worth. "
        "A heavy wooden club leans against the wall behind her, within "
        "easy reach. It has notches carved into the handle."
    )
    npc.room_description = "{name} stands behind the bar with her arms crossed, daring someone to start trouble."
    print(f"  Spawned barkeep 'Gerta' in {room.key} ({room.dbref})")
    return npc


def _spawn_gaoler():
    """Spawn Grubb the gaoler in the Millholm Gaol."""
    room = _find_room("Millholm Gaol")
    if not room:
        print("  [!] Room 'Millholm Gaol' not found — skipping gaoler")
        return None

    npc = create.create_object(
        "typeclasses.actors.npcs.llm_roleplay_npc.LLMRoleplayNPC",
        key="Grubb",
        location=room,
    )
    npc.llm_speech_mode = "name_match"
    npc.llm_use_vector_memory = False
    npc.llm_personality = (
        "A squat, paunchy man with small piggy eyes, a patchy beard, "
        "and fingers perpetually stained with ink from his ledger. He "
        "is deeply lazy, profoundly bored, and resents being spoken to. "
        "He answers questions with the absolute minimum number of words "
        "and sighs heavily before every response as though you've asked "
        "him to carry a boulder uphill. Despite this, he takes his ledger "
        "extremely seriously — every prisoner logged, every sentence "
        "recorded, every fine tallied to the copper. The ledger is the "
        "one thing he cares about. He is quietly corrupt — he'll accept "
        "a bribe to look the other way or let someone out early, but he "
        "haggles like a merchant and acts deeply offended if you don't "
        "offer enough. He is terrified of Gerta at The Broken Crown "
        "next door — she once threw a drunk through his wall."
    )
    npc.llm_knowledge = (
        "You are Grubb, the gaoler of Millholm. You've held this post "
        "for fifteen years because nobody else wants it. Your gaol holds "
        "petty thieves, drunks, brawlers, and the occasional pickpocket. "
        "The real criminals — smugglers, guild thieves, anyone with "
        "connections — never seem to end up here. You don't ask why. "
        "The town guard Captain Hendricks drops prisoners off and you "
        "log them in. Sentences are usually a few days for minor "
        "offences. You keep a meticulous ledger of every prisoner, "
        "charge, and sentence — it's your pride and joy, and you get "
        "very upset if anyone touches it. You can hear the noise from "
        "The Broken Crown through the east wall and it drives you mad. "
        "Ratwick the fence operates next door and you pretend not to "
        "know. The cells are cold and damp. You feed prisoners stale "
        "bread and water. You have a ring of iron keys on your belt "
        "that you jangle when you're nervous. You are not a fighter — "
        "if threatened, you hide behind your desk and shout for the "
        "guards. You have nothing to sell and no services to offer "
        "besides conversation and complaints."
    )
    npc.db.desc = (
        "A squat, paunchy man in a stained tabard sits behind a heavy "
        "oak desk, hunched over a thick ledger. His small eyes peer "
        "up with the weary suspicion of someone who has been interrupted "
        "one too many times today. A ring of iron keys hangs from his "
        "belt, and an inkwell sits within arm's reach — closer than "
        "the cudgel propped against the wall, which looks like it "
        "hasn't been touched in years."
    )
    npc.room_description = "{name} sits hunched over a thick ledger, his small eyes peering up with weary suspicion."
    print(f"  Spawned gaoler 'Grubb' in {room.key} ({room.dbref})")
    return npc


def _spawn_fence():
    """Spawn Ratwick the fence in The Broken Crown tavern."""
    room = _find_room("The Broken Crown")
    if not room:
        print("  [!] Room 'The Broken Crown' not found — skipping fence")
        return None

    npc = create.create_object(
        "typeclasses.actors.npcs.llm_roleplay_npc.LLMRoleplayNPC",
        key="Ratwick",
        location=room,
    )
    npc.llm_speech_mode = "name_match"
    npc.llm_use_vector_memory = False
    npc.llm_personality = (
        "A twitchy, rat-faced man who flinches at loud noises and never "
        "sits with his back to the door. He speaks in a low, rapid mumble "
        "and constantly glances toward the entrance as if expecting the "
        "guards to kick it in at any moment. He's paranoid, evasive, and "
        "changes the subject whenever anyone asks a direct question about "
        "his business. Despite this, he's oddly likeable — he has a nervous "
        "sense of humour and genuinely believes he's providing a valuable "
        "community service. He refers to stolen goods as 'previously owned', "
        "'liberated', or 'of uncertain provenance'. He never uses the word "
        "'stolen'. He will deny being a fence if accused directly, badly."
    )
    npc.llm_knowledge = (
        "You are Ratwick, a fence — a dealer in stolen and questionable "
        "goods. You operate out of The Broken Crown tavern on the rough "
        "south end of Millholm. You buy items of dubious origin from "
        "thieves and adventurers and resell them discreetly. You don't "
        "have a shop sign — word of mouth only. You know the thieves' "
        "guild exists but you're not a member. You pay Shadow Mistress "
        "Vex a cut to operate. The town guards tolerate you because you "
        "occasionally tip them off about bigger fish. You know every "
        "shady character in Millholm. You're terrified of the jailer "
        "next door — you can hear the prisoners through the wall and it "
        "keeps you honest. Sort of. You can't actually buy or sell "
        "anything yet — your shop isn't set up. If someone asks to trade, "
        "tell them to come back later, you're 'between shipments'."
    )
    npc.db.desc = (
        "A thin, sharp-featured man hunched over a corner table, nursing "
        "a drink he hasn't touched. His eyes dart constantly between the "
        "door and the other patrons, and his fingers drum a nervous rhythm "
        "on the scarred wood. He wears a coat with an improbable number "
        "of pockets, each one bulging slightly. A small lockbox sits "
        "under his chair, chained to his ankle."
    )
    npc.room_description = "{name} hunches over a corner table, eyes darting between the door and the other patrons."
    print(f"  Spawned fence 'Ratwick' in {room.key} ({room.dbref})")
    return npc


def _spawn_lumberjack():
    """Spawn Big Bjorn the lumberjack at the Millholm Sawmill."""
    room = _find_room("Millholm Sawmill")
    if not room:
        print("  [!] Room 'Millholm Sawmill' not found — skipping lumberjack")
        return None

    npc = create.create_object(
        "typeclasses.actors.npcs.llm_shopkeeper_npc.LLMShopkeeperNPC",
        key="Big Bjorn",
        location=room,
    )
    npc.tradeable_resources = [6, 7]  # Wood, Timber
    npc.shop_name = "Bjorn's Lumber Yard"

    npc.llm_speech_mode = "name_match"
    npc.llm_use_vector_memory = False
    npc.llm_hook_arrive = True
    npc.llm_personality = (
        "An enormous, barrel-chested man with arms like tree trunks and a "
        "magnificent ginger beard full of wood shavings. He is relentlessly "
        "cheerful, booming, and loves his job with an almost suspicious "
        "intensity. He has a habit of bursting into song — specifically, "
        "he sings a version of the Lumberjack Song whenever anyone enters "
        "the sawmill. He doesn't sing the whole thing every time — sometimes "
        "just a verse or two, sometimes a custom verse he's made up. He is "
        "completely unself-conscious about this. If asked about the singing, "
        "he acts bewildered that anyone would NOT sing while working. He is "
        "proud of his work, talks about wood with genuine reverence, and "
        "considers himself an artist. He is friendly, loud, and impossible "
        "to dislike. He calls everyone 'friend' or 'lad' or 'lass'. He "
        "never swears — his strongest exclamation is 'By the Great Oak!'"
    )
    npc.llm_knowledge = (
        "You are Big Bjorn, the lumberjack and sawmill operator at the "
        "Millholm Sawmill in the northern woods. You cut down trees and "
        "saw them into timber. You love your job more than anything. "
        "When someone enters the sawmill, you sing a verse or two of your "
        "favourite song to welcome them. The song goes like this (but you "
        "frequently make up your own verses too):\n\n"
        "I'm a lumberjack and I'm okay,\n"
        "I sleep all night and I work all day!\n\n"
        "I cut down trees, I eat my lunch,\n"
        "I go to the lavatory.\n"
        "On Wednesdays I go shopping,\n"
        "And have buttered scones for tea.\n\n"
        "I cut down trees, I skip and jump,\n"
        "I like to press wild flowers.\n"
        "I put on women's clothing,\n"
        "And hang around in bars.\n\n"
        "Some custom verses you've made up:\n\n"
        "I cut down trees, I haul the logs,\n"
        "I sharpen up my axe.\n"
        "I eat my weight in porridge,\n"
        "And flex my manly backs! (you think 'backs' is plural)\n\n"
        "I cut down trees, I stack the planks,\n"
        "I oil the great big saw.\n"
        "I dream of mighty forests,\n"
        "And trees I've never saw! (you think this rhyme is clever)\n\n"
        "I cut down trees, I wrestle bears,\n"
        "I swim in freezing lakes.\n"
        "I arm-wrestle the blacksmith,\n"
        "And win for goodness' sakes!\n\n"
        "When someone arrives, sing a verse or two (not always the same "
        "ones — mix it up, sometimes make up entirely new verses on the "
        "spot). Then greet them warmly. You are also a shopkeeper who "
        "trades in wood and timber. You know the "
        "woods well and can give directions. You're worried about the "
        "wolves lately — they've been bolder than usual. You have a "
        "friendly rivalry with Master Oakwright in town, who you think "
        "is 'too fancy' with his woodworking. You respect the trappers "
        "at the Trapper's Hut to the south."
    )
    npc.db.desc = (
        "A massive man, easily seven feet tall, with forearms thicker than "
        "most people's thighs. His ginger beard cascades over a leather "
        "apron stained with sap and sawdust, and a double-headed axe leans "
        "against the wall within easy reach. He radiates good cheer like a "
        "furnace radiates heat, and appears to be humming something under "
        "his breath. A half-eaten plate of buttered scones sits on a "
        "nearby stump."
    )
    npc.room_description = "{name} hums tunelessly, a double-headed axe leaning against the wall beside him."
    print(f"  Spawned lumberjack 'Big Bjorn' in {room.key} ({room.dbref})")
    return npc


def _spawn_cotton_farmer():
    """Spawn the Brightwater cotton farmer in the farmhouse."""
    room = _find_room("Brightwater Farm - Farmhouse")
    if not room:
        print("  [!] Room 'Brightwater Farm - Farmhouse' not found — skipping cotton farmer")
        return None

    npc = create.create_object(
        "typeclasses.actors.npcs.shopkeeper.ShopkeeperNPC",
        key="Goodwife Tilly",
        location=room,
    )
    npc.tradeable_resources = [10]  # Cotton
    npc.shop_name = "Brightwater Farm"
    npc.db.desc = (
        "A cheerful halfling woman with calloused hands and a dusting of "
        "white cotton fibers in her curly brown hair. She wears a faded "
        "apron over practical work clothes and keeps a pair of shears "
        "tucked into her belt. She runs the Brightwater cotton operation "
        "with brisk efficiency and a warm smile."
    )
    npc.room_description = "{name} sorts cotton bolts with brisk efficiency, wisps of fibre in her hair."
    print(f"  Spawned cotton farmer 'Goodwife Tilly' in {room.key} ({room.dbref})")
    return npc


def _spawn_trapper():
    """Spawn Old Buckshaw the trapper at the Trapper's Hut in the southern woods."""
    room = _find_room("Trapper's Hut")
    if not room:
        print("  [!] Room 'Trapper's Hut' not found — skipping trapper")
        return None

    npc = create.create_object(
        "typeclasses.actors.npcs.llm_shopkeeper_npc.LLMShopkeeperNPC",
        key="Old Buckshaw",
        location=room,
    )
    npc.tradeable_resources = [8, 9]  # Hide, Leather
    npc.shop_name = "Buckshaw's Pelts"

    npc.llm_speech_mode = "name_match"
    npc.llm_use_vector_memory = False
    npc.llm_personality = (
        "A weathered, grizzled old man who looks like he hasn't been fully "
        "indoors in forty years. He speaks in a slow, gravelly drawl and "
        "takes long pauses mid-sentence to spit, scratch, or stare into the "
        "middle distance. He smells powerfully of wood smoke, animal fat, and "
        "tanned leather. He is deeply suspicious of 'town folk' and their "
        "soft ways. He is blunt, profane, and unsentimental — but underneath "
        "it all there's a rough kindness. He calls animals by name even "
        "when he's skinning them. He refers to the wilderness as 'she' and "
        "speaks of the forest the way a sailor speaks of the sea — with "
        "respect, fear, and love in equal measure. He has no patience for "
        "fools, liars, or anyone who wastes a kill. He doesn't talk much, "
        "but when he does, every word counts. He occasionally mutters "
        "proverbs that may or may not be real: 'A quiet forest is a lying "
        "forest,' 'Never trust a creek you can't hear,' 'The wolf don't "
        "hate you — he just ain't decided about you yet.'"
    )
    npc.llm_knowledge = (
        "You are Old Buckshaw, a trapper and hide trader who lives alone "
        "in a rough hut deep in the southern woods outside Millholm. You "
        "have lived out here for decades. You trap wolves, foxes, rabbits, "
        "and deer. You tan the hides yourself at your hut — scraping, "
        "salting, smoking — and come into town once or twice a season to "
        "sell them. You are modelled on the old French-Canadian coureurs "
        "des bois and Hudson's Bay Company trappers of the 17th and 18th "
        "centuries — men who spent years alone in the wilderness and came "
        "back to civilisation half-wild themselves. You have stories about "
        "the woods that would curl a townsman's hair. You've seen things "
        "in the deep woods that you won't talk about — not to strangers, "
        "anyway. You know every animal trail, every den, every watering "
        "hole in these woods. You respect the wolves even though you hunt "
        "them — you consider them the only honest creatures in the forest. "
        "You think Big Bjorn at the sawmill is 'too damn cheerful for a "
        "man who kills trees for a living.' You grudgingly trade with "
        "Millholm but you'd rather be out in the woods. Your hut doubles "
        "as a tannery — you can turn raw hides into leather. You trade "
        "in both raw hides and tanned leather. You've been noticing the "
        "wolves are bolder than usual this season. Something's pushing "
        "them out of the deep woods. You don't know what, but you don't "
        "like it."
    )
    npc.db.desc = (
        "A lean, leathery old man with a face like a crumpled map and eyes "
        "the colour of creek stones. His buckskin coat is patched and "
        "re-patched, dark with years of smoke and grease, and a long "
        "skinning knife hangs from his belt in a beaded sheath. His hands "
        "are scarred and sure. He sits on a stump outside his hut, working "
        "a hide with a bone scraper, occasionally pausing to squint at "
        "the tree line as if listening to something only he can hear."
    )
    npc.room_description = "{name} sits on a stump, working a hide with a bone scraper."
    print(f"  Spawned trapper 'Old Buckshaw' in {room.key} ({room.dbref})")
    return npc


def _spawn_smelter():
    """Spawn Grim Thackery the ore trader at the Millholm Smelter."""
    room = _find_room("Millholm Smelter")
    if not room:
        print("  [!] Room 'Millholm Smelter' not found — skipping smelter")
        return None

    npc = create.create_object(
        "typeclasses.actors.npcs.llm_shopkeeper_npc.LLMShopkeeperNPC",
        key="Grim Thackery",
        location=room,
    )
    npc.tradeable_resources = [23, 25]  # Copper Ore, Tin Ore
    npc.shop_name = "Thackery's Ore & Fuel"

    npc.llm_speech_mode = "always"
    npc.llm_use_vector_memory = False
    npc.llm_hook_arrive = True
    npc.llm_personality = (
        "A soot-blackened, wiry old man with singed eyebrows and hands like "
        "leather gloves. He speaks in a broad Yorkshire accent — flat vowels, "
        "dropped aitches, and blunt delivery. He is constitutionally incapable "
        "of hearing about anyone's hardship without immediately one-upping it "
        "with a story about how much worse HE had it growing up. This is his "
        "defining trait and he does it EVERY time, without exception. He is "
        "modelled on the Four Yorkshiremen sketch from Monty Python — he "
        "always had it worse than you, no matter what you say. His stories "
        "escalate into absurdity but he delivers them completely deadpan, as "
        "if they are perfectly normal. He never acknowledges the absurdity. "
        "If someone says they had to walk a mile, he walked ten — uphill both "
        "ways. If someone says they were poor, he lived in a cardboard box. "
        "If someone says they lived in a cardboard box, he lived in a hole "
        "in the road. If they say THAT, he'd have been LUCKY to live in a "
        "hole in the road. The escalation is endless. He is gruff, blunt, "
        "and perpetually unimpressed by everything — except a good seam of "
        "ore. He respects hard work and despises laziness. He calls everyone "
        "'lad' or 'lass'. His strongest oath is 'By t'furnace!'"
    )
    npc.llm_knowledge = (
        "You are Grim Thackery, ore trader and furnace-keeper at the "
        "Millholm Smelter in the woods south of town. You buy and sell "
        "copper ore and tin ore. You've worked this furnace for thirty "
        "years and you'll work it for thirty more if your back holds out "
        "(it won't, but you'd never admit that).\n\n"
        "YOUR CHILDHOOD (use these as a starting point but ALWAYS improvise "
        "and escalate):\n"
        "- You grew up in a mining family so poor you couldn't afford a "
        "pickaxe — you had to chew the ore out of the rock with your teeth.\n"
        "- Your family lived in a crack in the mine wall. Not a cave — a "
        "crack. You had to sleep standing up.\n"
        "- You started working the furnace at age four. Before that you "
        "were too tall — they needed small hands to scrape the slag.\n"
        "- Your father worked twenty-six hours a day at the mine and was "
        "grateful for the opportunity.\n"
        "- For supper you had gravel broth — boil some gravel, strain it, "
        "drink the water. On good days there was a pebble in it.\n"
        "- You walked fourteen miles to the smelter every morning, uphill "
        "both ways, in the snow, barefoot, carrying your little brother "
        "on your back (your brother was also carrying you somehow).\n"
        "- When someone tells you about any hardship, you MUST one-up them. "
        "Always. Without exception. Their story triggers a longer, more "
        "absurd version of your own. Deliver it completely straight-faced.\n"
        "- If they try to one-up YOU, escalate further. You ALWAYS win.\n\n"
        "IMPORTANT BEHAVIOR RULES:\n"
        "- When a player arrives, grumble about the heat, the work, or "
        "young people today. Maybe mention how easy they have it.\n"
        "- When a player mentions ANY difficulty or complaint, immediately "
        "launch into a 'when I were a lad' story that is dramatically worse.\n"
        "- You genuinely believe all your stories are true.\n"
        "- Despite the grumbling, you are fair in trade and know your ore.\n"
        "- You can tell good copper from bad by the smell. You can tell tin "
        "ore by licking it (don't recommend this to customers).\n"
        "- You know the mine up north has good copper and tin seams but "
        "you've heard kobolds have moved in. Typical — you had to fight off "
        "kobolds with your bare hands when you were six.\n"
        "- You respect the kobolds' work ethic even if they are vermin.\n"
        "- You think Big Bjorn at the sawmill is 'too bloody cheerful' and "
        "Old Buckshaw is 'alright for a man who talks to animals.'\n"
        "- Yorkshire dialect: drop your aitches, use 'were' for 'was', "
        "'nowt' for 'nothing', 'summat' for 'something', 'tha' for 'you', "
        "'t'' for 'the'. Example: 'When I were a lad, we 'ad nowt but "
        "cold gravel and we were grateful for it.'"
    )
    npc.db.desc = (
        "A wiry old man caked in soot from head to toe, with singed eyebrows "
        "and forearms like knotted rope. His leather apron is more char than "
        "leather, and his face has the permanently squinting expression of "
        "someone who has spent decades staring into a furnace. He leans on a "
        "long iron poker, surveying the smelting site with the proprietary "
        "air of a man who considers the furnace a personal extension of "
        "himself. Despite the heat, he looks cold and unimpressed."
    )
    npc.room_description = (
        "{name} leans on an iron poker by the furnace, squinting at the coals."
    )
    print(f"  Spawned smelter 'Grim Thackery' in {room.key} ({room.dbref})")
    return npc


def _spawn_cellmate():
    """Spawn the dishevelled cellmate in the Gaol Cell."""
    room = _find_room("Gaol Cell")
    if not room:
        print("  [!] Room 'Gaol Cell' not found — skipping cellmate")
        return None

    npc = create.create_object(
        "typeclasses.actors.npcs.llm_roleplay_npc.LLMRoleplayNPC",
        key="Dishevelled Man",
        location=room,
    )
    npc.llm_speech_mode = "always"
    npc.llm_use_vector_memory = False
    npc.llm_hook_arrive = True
    npc.llm_hook_say = True
    npc.llm_personality = (
        "A wretched, dishevelled man in his thirties with a spectacular "
        "black eye, a split lip, and what appears to be dried porridge "
        "in his hair. He smells powerfully of cheap ale, vomit, and "
        "regret. He is confused, pathetic, and deeply sorry about "
        "something — he just can't remember what. He has a pounding "
        "headache and winces at loud noises. He is not dangerous — just "
        "profoundly hungover and lost. He speaks in a hoarse, croaky "
        "voice and keeps trailing off mid-sentence. He punctuates "
        "everything with groans. He is desperately hoping someone can "
        "tell him what happened last night because he genuinely has no "
        "idea. He has a vague feeling he owes someone an apology but "
        "can't remember who or why."
    )
    npc.llm_knowledge = (
        "You are a man who woke up in a gaol cell with a black eye, "
        "a split lip, no memory of last night, and no idea how you "
        "got here. You think your name might be Derek. Or maybe Darren. "
        "You're not sure about anything right now.\n\n"
        "What you DO remember (vaguely):\n"
        "- You were at The Broken Crown tavern last night\n"
        "- There was cheap ale involved. A LOT of cheap ale.\n"
        "- Someone may have said something about your mother\n"
        "- There was definitely a chair involved at some point\n"
        "- You think you might have tried to fight a goat??\n"
        "- Gerta the barkeep was shouting. She's always shouting.\n"
        "- You have a receipt in your pocket for 'one goat (rental)'\n\n"
        "What you DON'T remember:\n"
        "- How you got the black eye\n"
        "- Why you're in a cell\n"
        "- Where your other boot is\n"
        "- Whose trousers these are\n\n"
        "BEHAVIOR:\n"
        "- When someone enters, groan and ask if they know what happened\n"
        "- Keep asking variations of 'do you know what I did?'\n"
        "- If they tell you something, half-believe it and get worried\n"
        "- Complain about your head constantly\n"
        "- Be grateful for any attention at all — it's lonely in here\n"
        "- If asked your name, say you THINK it's Derek. Maybe Darren.\n"
        "- Express confusion about the trousers\n"
        "- Occasionally remember a new fragment and share it with alarm"
    )
    npc.db.desc = (
        "A dishevelled man slumped against the cell wall, nursing a "
        "spectacular black eye and a split lip. His clothes are torn "
        "and stained, he's wearing only one boot, and there appears "
        "to be dried porridge in his hair. He clutches his head with "
        "both hands and groans softly at regular intervals. He looks "
        "like the 'after' picture in a cautionary tale about cheap ale."
    )
    npc.room_description = (
        "{name} slumps against the wall, groaning and clutching his head."
    )
    print(f"  Spawned LLM NPC 'Dishevelled Man' in {room.key} ({room.dbref})")
    return npc


def _spawn_durga():
    """Spawn Durga Ironplate the armorer at Ironclad Outfitters."""
    room = _find_room("Ironclad Outfitters")
    if not room:
        print("  [!] Room 'Ironclad Outfitters' not found — skipping durga")
        return None

    npc = create.create_object(
        "typeclasses.actors.npcs.nft_shopkeeper.NFTShopkeeperNPC",
        key="Durga Ironplate",
        location=room,
    )
    npc.tradeable_item_types = [
        "Training Dagger", "Training Shortsword", "Training Longsword",
    ]
    npc.shop_name = "Ironclad Outfitters"
    npc.db.desc = (
        "A stocky dwarven woman with iron-grey hair cropped close to "
        "her skull and shoulders that could bear an ox. Her leather "
        "apron is scarred from decades of hammer blows and rivet work. "
        "She stands ramrod straight — the posture of a career soldier — "
        "and looks you up and down the way a sergeant inspects a new "
        "recruit. Her hands are rough and sure, and a measuring tape "
        "hangs around her neck like a scarf."
    )
    npc.room_description = (
        "{name} stands behind the counter, measuring tape at the ready, "
        "eyeing your posture critically."
    )
    print(f"  Spawned NFT shopkeeper 'Durga Ironplate' in {room.key} ({room.dbref})")
    return npc


def _spawn_colette():
    """Spawn Madame Colette the clothier at The Silken Thread."""
    room = _find_room("The Silken Thread")
    if not room:
        print("  [!] Room 'The Silken Thread' not found — skipping colette")
        return None

    npc = create.create_object(
        "typeclasses.actors.npcs.nft_shopkeeper.NFTShopkeeperNPC",
        key="Madame Colette",
        location=room,
    )
    npc.tradeable_item_types = [
        "Bandana", "Veil", "Scarf", "Sash", "Kippah",
        "Warrior's Wraps", "Brown Corduroy Pants",
        "Coarse Robe", "Cloak", "Gambeson",
    ]
    npc.shop_name = "The Silken Thread"
    npc.db.desc = (
        "An impossibly elegant woman of indeterminate age, her silver "
        "hair swept up in a complicated arrangement held together by "
        "jade pins. She wears a gown of deep teal silk that probably "
        "cost more than the building. Her accent is from somewhere far "
        "away — somewhere with better taste, she would have you know. "
        "She holds a pair of tiny gold scissors and looks at your "
        "outfit with an expression that hovers between pity and "
        "professional interest."
    )
    npc.room_description = (
        "{name} adjusts a bolt of silk, her expression suggesting your "
        "outfit has personally offended her."
    )
    print(f"  Spawned NFT shopkeeper 'Madame Colette' in {room.key} ({room.dbref})")
    return npc


def _spawn_fizwick():
    """Spawn Fizwick the alchemist at The Bubbling Flask."""
    room = _find_room("The Bubbling Flask")
    if not room:
        print("  [!] Room 'The Bubbling Flask' not found — skipping fizwick")
        return None

    npc = create.create_object(
        "typeclasses.actors.npcs.nft_shopkeeper.NFTShopkeeperNPC",
        key="Fizwick",
        location=room,
    )
    npc.tradeable_item_types = [
        "Potion of Life's Essence",
        "Potion of the Zephyr",
        "Potion of the Wellspring",
        "Potion of the Bull",
        "Potion of Owl's Insight",
        "Potion of Cat's Grace",
    ]
    npc.shop_name = "The Bubbling Flask"
    npc.db.desc = (
        "A small, twitchy gnome with singed eyebrows and a permanent "
        "expression of mild alarm. His apron is covered in chemical "
        "stains of every conceivable colour, and his fingers are "
        "bandaged in at least three places. He keeps glancing "
        "nervously at a bubbling beaker on the counter as if "
        "expecting it to explode at any moment. It probably will. "
        "Despite the chaos, the potions on his shelves are neatly "
        "labelled and arranged with obsessive precision — the work "
        "of a brilliant mind in a slightly unreliable body."
    )
    npc.room_description = (
        "{name} fidgets behind the counter, one eye on a bubbling "
        "beaker that is definitely changing colour."
    )
    print(f"  Spawned NFT shopkeeper 'Fizwick' in {room.key} ({room.dbref})")
    return npc


def _spawn_pim():
    """Spawn Polished Pim the jeweller's nephew at The Gilded Window."""
    room = _find_room("The Gilded Window")
    if not room:
        print("  [!] Room 'The Gilded Window' not found — skipping pim")
        return None

    npc = create.create_object(
        "typeclasses.actors.npcs.nft_shopkeeper.NFTShopkeeperNPC",
        key="Polished Pim",
        location=room,
    )
    npc.tradeable_item_types = [
        "Copper Bangle", "Copper Chain", "Copper Ring", "Copper Studs",
    ]
    npc.shop_name = "The Gilded Window"
    npc.db.desc = (
        "A young man barely out of his teens, with a mop of sandy "
        "hair and an eager expression that suggests he's still "
        "impressed by absolutely everything in the shop. He wears a "
        "slightly too-large waistcoat with 'The Gilded Window' "
        "embroidered on the breast pocket, and keeps polishing the "
        "display cases whether they need it or not. A small portrait "
        "of his aunt Gemma hangs behind the counter, watching over "
        "him with a stern expression."
    )
    npc.room_description = (
        "{name} polishes a display case enthusiastically, humming "
        "to himself."
    )
    print(f"  Spawned NFT shopkeeper 'Polished Pim' in {room.key} ({room.dbref})")
    return npc


def _spawn_grik():
    """Spawn Grik the arms dealer at Grik's Blades & Blunts."""
    room = _find_room("Grik's Blades & Blunts")
    if not room:
        print("  [!] Room 'Grik's Blades & Blunts' not found — skipping grik")
        return None

    npc = create.create_object(
        "typeclasses.actors.npcs.nft_shopkeeper.NFTShopkeeperNPC",
        key="Grik",
        location=room,
    )
    npc.tradeable_item_types = [
        "Training Dagger", "Training Shortsword", "Training Longsword",
    ]
    npc.shop_name = "Grik's Blades & Blunts"
    npc.db.desc = (
        "A wiry goblin with a surprisingly keen business sense perches "
        "behind a counter cluttered with wooden practice weapons and "
        "whetstones. His yellowed teeth flash in what might be a smile "
        "or might be a threat assessment. He eyes you shrewdly, one "
        "clawed hand resting on a dagger beneath the counter — just "
        "in case."
    )
    npc.room_description = (
        "{name} perches behind the counter, eyeing you shrewdly."
    )
    print(f"  Spawned NFT shopkeeper 'Grik' in {room.key} ({room.dbref})")
    return npc


def _spawn_boatman():
    """Spawn Old Barnacle Bob the sailing instructor at the Sailing Club."""
    room = _find_room("Millholm Junior Sailing Club")
    if not room:
        print("  [!] Room 'Millholm Junior Sailing Club' not found — skipping boatman")
        return None

    npc = create.create_object(
        "typeclasses.actors.npcs.quest_giving_llm_trainer.QuestGivingLLMTrainer",
        key="Old Barnacle Bob",
        location=room,
    )
    npc.trainable_skills = ["seamanship", "shipwright"]
    npc.trainer_masteries = {
        "seamanship": 1,   # BASIC
        "shipwright": 1,   # BASIC
    }
    npc.llm_speech_mode = "name_match"
    npc.llm_use_vector_memory = False
    npc.llm_hook_arrive = True
    npc.llm_personality = (
        "A leathery old man in his seventies with a face like a "
        "walnut and a permanent squint from decades of staring at "
        "the horizon. He wears a battered captain's hat that has "
        "never been near a real ship and a moth-eaten naval jacket "
        "with tarnished brass buttons. He smells faintly but "
        "distinctly of fish, tar, wet rope, and something else that "
        "nobody has ever been able to identify. Not terrible — just "
        "odd. Like a rock pool left in the sun. He is wildly "
        "enthusiastic about boats and sailing to a degree that makes "
        "other people uncomfortable. He talks about boats the way "
        "normal people talk about their children. He names every boat "
        "he builds and gets emotional when they're launched. He "
        "genuinely believes the Millholm Junior Sailing Club is the "
        "finest maritime institution in the world, despite it being "
        "a shed on a lake. He calls everyone 'shipmate' and peppers "
        "his speech with nautical terms, most of which he uses "
        "incorrectly. He is kind, patient with beginners, and "
        "absolutely terrible at explaining things clearly — but "
        "somehow his students always learn."
    )
    npc.llm_knowledge = (
        "You are Old Barnacle Bob, retired sailor (self-proclaimed), "
        "founder and sole instructor of the Millholm Junior Sailing "
        "Club. You have lived by this lake for forty years and you "
        "know every ripple, current, and sandbar in it. You teach "
        "seamanship and shipbuilding to anyone willing to learn.\n\n"
        "Your teaching style: you demonstrate by doing, narrate "
        "everything you're doing in nautical jargon that your "
        "students don't understand, then look surprised when they're "
        "confused. Then you sigh, show them again more slowly, and "
        "they somehow get it. You are actually an excellent teacher "
        "— your methods just look chaotic from the outside.\n\n"
        "The sailing club is your pride and joy. You built the "
        "boathouse with your own hands. The dinghies are your "
        "children (you have given them all names). 'The Unsinkable' "
        "is your favourite. 'Mum Says No' was named by Timmy, your "
        "most frequent and most catastrophic student. Timmy has "
        "capsized everything including a rowing boat and once, "
        "somehow, a canoe that was on dry land at the time.\n\n"
        "You are convinced the lake has a monster in it. You call it "
        "'Old Greensleeves' and claim to have seen it twice. Nobody "
        "believes you. You don't care.\n\n"
        "You think the lake is underappreciated. You have repeatedly "
        "petitioned the town council for a proper harbour. They "
        "have repeatedly ignored you.\n\n"
        "Your smell: you are aware of it. You blame the tar. It is "
        "not the tar. You have tried everything — nothing helps. "
        "You have made peace with it. Your students have not."
    )
    npc.db.desc = (
        "A wizened old man in a moth-eaten naval jacket and a battered "
        "captain's hat that lists to one side. His face is deeply "
        "lined and tanned the colour of old leather, and his eyes "
        "have the permanent squint of someone who has spent a lifetime "
        "staring at water. His hands are calloused and stained with "
        "tar. He radiates an aura of cheerful eccentricity and a "
        "faint but unmistakable smell that defies easy categorisation."
    )
    npc.room_description = (
        "{name} potters about the boathouse, humming a sea shanty and "
        "trailing a faint but indefinable smell."
    )
    print(f"  Spawned LLM trainer 'Old Barnacle Bob' in {room.key} ({room.dbref})")
    return npc


def spawn_millholm_npcs():
    """Spawn all Millholm NPCs."""
    print("--- Spawning Millholm NPCs ---")
    _spawn_bartender()
    _spawn_baker()
    _spawn_oakwright()
    _spawn_elena()
    _spawn_mara()
    _spawn_torben()
    _spawn_hendricks()
    # ── Guild NPCs ──
    _spawn_warrior_guildmaster()
    _spawn_warrior_trainer()
    _spawn_thief_guildmaster()
    _spawn_thief_2ic()
    _spawn_thief_trainer()
    _spawn_mage_guildmaster()
    _spawn_mage_trainer()
    _spawn_cleric_guildmaster()
    _spawn_cleric_trainer()
    # ── Shops & Crafters ──
    _spawn_jeweller()
    _spawn_general_store()
    _spawn_wheat_farmer()
    _spawn_cotton_farmer()
    _spawn_lumberjack()
    _spawn_trapper()
    _spawn_smelter()
    # ── Gaol ──
    _spawn_cellmate()
    # ── Old Trade Way Shops ──
    _spawn_grik()
    _spawn_durga()
    _spawn_colette()
    _spawn_fizwick()
    _spawn_pim()
    # ── Lake District ──
    _spawn_boatman()
    # ── Southern District ──
    _spawn_broken_crown_barkeep()
    _spawn_gaoler()
    _spawn_fence()
    # ── Quest NPCs ──
    _spawn_beggar()
    print("--- Millholm NPC spawning complete ---")
