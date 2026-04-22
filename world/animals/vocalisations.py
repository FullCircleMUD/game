"""
Species-default vocalisations and spoken lines for animals.

Two parallel tables, both keyed by species:

    VOCALISATIONS — third-person action lines shown to listeners who do NOT
        understand the animal language. The animal "barks excitedly" or
        "whinnies and stamps a hoof" — flavour, not dialogue. Critical to the
        no-tell principle: a casual observer can't distinguish a quest-giver
        animal from a flavour animal without speaking the animal language.

    SPOKEN_LINES — first-person dialogue shown to listeners who DO understand
        the animal language (i.e. have Condition.SPEAK_WITH_ANIMALS active).

Each table is keyed by species, then by hook (a string identifying the
trigger context: "stay", "follow", "feed", "mount", "dismount", "name",
"dismiss", "ambient"). The "_default" species provides fallbacks for any
species without an explicit entry, and any hook missing from a species
table also falls back to "_default".

Per-instance overrides on the AnimalSpeakerMixin (vocalisation_overrides /
spoken_overrides) take precedence over the table — drop a dict on a quest
animal to give it bespoke lines without changing the table.
"""

import random


# ================================================================== #
#  Non-speaker view — third-person action lines
# ================================================================== #

VOCALISATIONS = {
    "dog": {
        "stay": [
            "sits down and whines softly.",
            "sits but watches you with pleading eyes.",
            "drops to its haunches and lets out a small whuff.",
        ],
        "follow": [
            "wags its tail and trots to your side.",
            "barks once and falls into step beside you.",
            "bounds to your heel, tongue lolling.",
        ],
        "feed": [
            "wolfs down the food gratefully.",
            "buries its muzzle in the food and eats noisily.",
            "tail thumps the ground as it eats.",
        ],
        "mount": [
            "bristles uncertainly as you climb onto its back.",
        ],
        "dismount": [
            "shakes itself out as you climb down.",
        ],
        "name": [
            "tilts its head, ears pricked at the new sound.",
        ],
        "dismiss": [
            "barks once and trots away.",
        ],
        "ambient": [
            "sniffs the air and lets out a low woof.",
            "scratches behind one ear with a hind leg.",
            "barks at a passing shadow.",
        ],
    },
    "horse": {
        "stay": [
            "snorts and stamps a hoof, but stays put.",
            "lowers its head and stands quietly.",
        ],
        "follow": [
            "tosses its mane and falls in beside you.",
            "whinnies softly and trots after you.",
        ],
        "feed": [
            "munches the food noisily, ears flicking.",
            "snuffles at the food, then eats with relish.",
        ],
        "mount": [
            "stands steady as you settle into the saddle.",
        ],
        "dismount": [
            "shakes its mane as you swing down.",
        ],
        "name": [
            "swivels an ear at the sound of its new name.",
        ],
        "dismiss": [
            "whinnies and trots away.",
        ],
        "ambient": [
            "stamps a hoof and snorts.",
            "shakes its mane, tail swishing.",
            "whinnies softly.",
        ],
    },
    "mule": {
        "stay": [
            "plants its hooves and refuses to move, ears flat.",
            "snorts and stays exactly where it is.",
        ],
        "follow": [
            "plods after you with stoic resignation.",
            "flicks its long ears and ambles along behind you.",
        ],
        "feed": [
            "munches the food with patient, steady chewing.",
        ],
        "mount": [
            "stands stoically as you climb on.",
        ],
        "dismount": [
            "twitches an ear as you climb down.",
        ],
        "name": [
            "flicks an ear, unimpressed.",
        ],
        "dismiss": [
            "trundles off without a backward glance.",
        ],
        "ambient": [
            "flicks its long ears.",
            "snorts and stamps a hoof.",
        ],
    },
    "cat": {
        "stay": [
            "settles down and begins grooming a paw.",
            "curls up where it is, tail twitching.",
        ],
        "follow": [
            "weaves around your ankles, then pads silently after you.",
            "trots after you with its tail held high.",
        ],
        "feed": [
            "delicately picks at the food, purring.",
            "eats with quick, fastidious bites.",
        ],
        "mount": [
            "leaps lightly onto your shoulder.",
        ],
        "dismount": [
            "leaps gracefully to the ground.",
        ],
        "name": [
            "stares at you, unblinking, at the sound of the new name.",
        ],
        "dismiss": [
            "flicks its tail and slinks away into the shadows.",
        ],
        "ambient": [
            "yawns, showing tiny sharp teeth.",
            "purrs softly.",
            "watches a far corner intently, then loses interest.",
        ],
    },
    "rat": {
        "stay": [
            "crouches motionless, whiskers twitching.",
        ],
        "follow": [
            "scurries along at your heels.",
        ],
        "feed": [
            "nibbles the food rapidly, holding it in tiny paws.",
        ],
        "name": [
            "twitches its whiskers at the new sound.",
        ],
        "dismiss": [
            "scurries away into the shadows.",
        ],
        "ambient": [
            "twitches its whiskers and looks about.",
            "scratches at the floor with tiny claws.",
        ],
    },
    "owl": {
        "stay": [
            "ruffles its feathers and settles where it is.",
        ],
        "follow": [
            "takes wing in a near-silent rush, gliding after you.",
        ],
        "feed": [
            "tears the food apart with sharp pulls of its beak.",
        ],
        "name": [
            "swivels its head and stares at you with huge amber eyes.",
        ],
        "dismiss": [
            "spreads its wings and flies off into the dark.",
        ],
        "ambient": [
            "swivels its head almost completely around.",
            "hoots softly, the sound oddly resonant.",
        ],
    },
    "hawk": {
        "stay": [
            "perches motionless, eyes scanning the horizon.",
        ],
        "follow": [
            "takes off in a powerful beat of wings and circles overhead.",
        ],
        "feed": [
            "tears into the food with hooked beak and talon.",
        ],
        "name": [
            "screams once, a piercing cry, at its new name.",
        ],
        "dismiss": [
            "shrieks once and arrows away into the sky.",
        ],
        "ambient": [
            "flexes its talons against its perch.",
            "lets out a piercing shriek.",
        ],
    },
    "imp": {
        "stay": [
            "hovers in place, flickering with arcane sparks.",
        ],
        "follow": [
            "buzzes after you on bat-like wings.",
        ],
        "feed": [
            "incinerates the food with a small jet of flame and laughs.",
        ],
        "name": [
            "cackles at the sound of its new name.",
        ],
        "dismiss": [
            "vanishes in a puff of sulphurous smoke.",
        ],
        "ambient": [
            "flickers with tiny arcane flames.",
            "snickers quietly to itself.",
        ],
    },

    # Fallback used for any species not listed above and any hook missing
    # from a listed species' table.
    "_default": {
        "stay": [
            "stays where it is.",
        ],
        "follow": [
            "follows along.",
        ],
        "feed": [
            "eats contentedly.",
        ],
        "mount": [
            "stands patiently as you climb on.",
        ],
        "dismount": [
            "shifts as you climb down.",
        ],
        "name": [
            "looks at you blankly.",
        ],
        "dismiss": [
            "wanders off.",
        ],
        "ambient": [
            "shifts its weight.",
        ],
    },
}


# ================================================================== #
#  Speaker view — first-person dialogue
# ================================================================== #

SPOKEN_LINES = {
    "dog": {
        "stay": [
            "Can't I come with you, please?",
            "I'll wait right here. Hurry back!",
            "Aww, fine. I'll watch the door.",
        ],
        "follow": [
            "Right behind you, friend!",
            "Lead the way!",
            "Adventure! Adventure!",
        ],
        "feed": [
            "Best food ever! Thank you!",
            "Mmm, mine! All mine!",
        ],
        "mount": [
            "Hey, I'm not a horse, you know.",
        ],
        "dismount": [
            "Phew. That was weird.",
        ],
        "name": [
            "That's me! That's my name!",
        ],
        "dismiss": [
            "Bye! See you later, friend!",
        ],
        "ambient": [
            "Smell that? Something's interesting that way.",
            "An itch! Got it.",
            "Did you hear that?",
        ],
    },
    "horse": {
        "stay": [
            "Very well. I'll wait.",
            "Don't be long, friend.",
        ],
        "follow": [
            "Lead on. I am with you.",
            "I am ready to ride.",
        ],
        "feed": [
            "Good oats. My thanks.",
        ],
        "mount": [
            "Steady, friend. Hold the reins gently.",
        ],
        "dismount": [
            "A good ride. Rest now.",
        ],
        "name": [
            "A fine name. I shall answer to it.",
        ],
        "dismiss": [
            "Farewell, rider.",
        ],
        "ambient": [
            "The grass here smells sweet.",
            "Easy now. All is well.",
        ],
    },
    "mule": {
        "stay": [
            "Fine. I'm not moving anyway.",
            "Yeah. Sure. I'll stay.",
        ],
        "follow": [
            "If we must.",
            "Slow down, you long-legged thing.",
        ],
        "feed": [
            "About time. Got any more?",
        ],
        "mount": [
            "Heavy. You're heavy.",
        ],
        "dismount": [
            "Finally.",
        ],
        "name": [
            "Whatever you say, boss.",
        ],
        "dismiss": [
            "Don't call me, I'll call you.",
        ],
        "ambient": [
            "These flies are awful.",
            "I don't like the look of that path.",
        ],
    },
    "cat": {
        "stay": [
            "Of course I'll stay. I was going to anyway.",
            "Fine. Don't expect me to be here when you get back.",
        ],
        "follow": [
            "I have decided to accompany you.",
            "Try to keep up.",
        ],
        "feed": [
            "Acceptable.",
            "More? You may bring more.",
        ],
        "mount": [
            "I am a CAT. We do not carry passengers.",
        ],
        "dismount": [
            "About time you got off.",
        ],
        "name": [
            "If I must answer to something.",
        ],
        "dismiss": [
            "I was leaving anyway.",
        ],
        "ambient": [
            "There is a mouse two rooms over. I can smell it.",
            "Hm.",
            "Something moved. I saw it.",
        ],
    },
    "rat": {
        "stay": [
            "Yes yes, hidden, hidden.",
        ],
        "follow": [
            "Coming, coming!",
        ],
        "feed": [
            "Crumbs! Wonderful crumbs!",
        ],
        "name": [
            "Yes? That me?",
        ],
        "dismiss": [
            "Bye-bye!",
        ],
        "ambient": [
            "Cheese? Anywhere? No?",
            "Sniff sniff sniff.",
        ],
    },
    "owl": {
        "stay": [
            "I shall watch from here.",
        ],
        "follow": [
            "I shall fly above you.",
        ],
        "feed": [
            "A fine offering.",
        ],
        "name": [
            "It is a worthy name.",
        ],
        "dismiss": [
            "Farewell. The night calls.",
        ],
        "ambient": [
            "The night is full of sounds.",
            "I see far, in the dark.",
        ],
    },
    "hawk": {
        "stay": [
            "I shall perch here. Be swift.",
        ],
        "follow": [
            "I shall ride the winds above.",
        ],
        "feed": [
            "Fresh meat is best.",
        ],
        "name": [
            "I accept it.",
        ],
        "dismiss": [
            "The skies await.",
        ],
        "ambient": [
            "I see all from above.",
            "Prey moves below.",
        ],
    },
    "imp": {
        "stay": [
            "Don't be long. I get bored.",
        ],
        "follow": [
            "Let's burn things!",
        ],
        "feed": [
            "Crispy. I prefer it crispy.",
        ],
        "name": [
            "Hee hee. A name. I'll remember.",
        ],
        "dismiss": [
            "Back to the warm dark for me.",
        ],
        "ambient": [
            "It's awfully cold up here, isn't it?",
            "Hee hee hee.",
        ],
    },

    "_default": {
        "stay": [
            "I will stay.",
        ],
        "follow": [
            "I will follow.",
        ],
        "feed": [
            "Thank you.",
        ],
        "mount": [
            "I shall bear you.",
        ],
        "dismount": [
            "We are done.",
        ],
        "name": [
            "I hear you.",
        ],
        "dismiss": [
            "Farewell.",
        ],
        "ambient": [
            "Hm.",
        ],
    },
}


def _lookup(table, species, hook):
    """Return a hook entry from the species table, falling back to _default.

    Returns None if neither species nor _default has the hook.
    """
    species_key = (species or "").lower()
    species_table = table.get(species_key) or {}
    entry = species_table.get(hook)
    if not entry:
        entry = table.get("_default", {}).get(hook)
    return entry


def get_vocalisation(species, hook):
    """Pick a random non-speaker action line for (species, hook), or None."""
    entry = _lookup(VOCALISATIONS, species, hook)
    if not entry:
        return None
    return random.choice(entry)


def get_spoken_line(species, hook):
    """Pick a random speaker dialogue line for (species, hook), or None."""
    entry = _lookup(SPOKEN_LINES, species, hook)
    if not entry:
        return None
    return random.choice(entry)
