"""
Deterministic per-language text garbling.

When a character speaks in a language the listener doesn't know,
the speech is replaced with language-flavoured gibberish. The same
word always produces the same garbled output within a given language
so eavesdroppers see consistent (but meaningless) text.
"""

import hashlib
import re

# Phonetic syllable palettes per language.
_SYLLABLES = {
    "dwarven": [
        "khor", "grim", "dur", "thok", "brak", "mor", "dun", "gor",
        "vak", "thur", "rik", "gron", "mak", "drek", "bor", "krag",
    ],
    "elfish": [
        "ael", "ith", "lora", "ven", "thil", "ara", "iel", "ena",
        "ori", "sha", "lae", "mir", "val", "nia", "elu", "tha",
    ],
    "goblin": [
        "gak", "snit", "mog", "bur", "zik", "gob", "nar", "skag",
        "gur", "muk", "nag", "skrit", "blag", "grik", "zug", "mak",
    ],
    "dragon": [
        "zhar", "voth", "kael", "thur", "drak", "vor", "shael", "rath",
        "gol", "zeth", "kyr", "maar", "vael", "thon", "drex", "zul",
    ],
    "halfling": [
        "pip", "tum", "bur", "wick", "mer", "bil", "rob", "took",
        "bram", "nib", "dell", "lob", "hin", "fer", "gam", "nob",
    ],
    "celestial": [
        "sol", "ira", "thae", "ora", "lum", "cael", "mira", "eos",
        "aur", "sel", "zha", "lia", "thal", "anu", "kir", "eth",
    ],
}


def garble(text: str, language: str) -> str:
    """Replace *text* with language-flavoured gibberish.

    The mapping is deterministic: the same (word, language) pair always
    produces the same garbled word.  Punctuation and spacing are preserved
    so the "shape" of the sentence remains visible.

    Args:
        text: The original speech text.
        language: Language key (e.g. ``"dwarven"``).

    Returns:
        Garbled string, or the original text unchanged if the language
        has no syllable palette (e.g. ``"common"``).
    """
    syllables = _SYLLABLES.get(language)
    if not syllables:
        return text

    def _garble_word(word: str) -> str:
        # Strip leading/trailing punctuation, garble core, re-attach.
        match = re.match(r"^([^a-zA-Z]*)([a-zA-Z]+)([^a-zA-Z]*)$", word)
        if not match:
            return word  # pure punctuation / whitespace
        prefix, core, suffix = match.groups()

        # Deterministic seed from the word + language.
        seed = int(
            hashlib.md5(
                f"{core.lower()}:{language}".encode()
            ).hexdigest(),
            16,
        )

        # Pick syllables to roughly match original word length.
        result = []
        remaining = len(core)
        idx = seed
        while remaining > 0:
            syl = syllables[idx % len(syllables)]
            # Don't overshoot by more than 2 chars.
            if len(syl) > remaining + 2 and result:
                break
            result.append(syl)
            remaining -= len(syl)
            idx = idx * 31 + 17  # simple deterministic step

        garbled = "".join(result)

        # Preserve capitalisation of original.
        if core[0].isupper():
            garbled = garbled[0].upper() + garbled[1:]

        return f"{prefix}{garbled}{suffix}"

    # Split on whitespace, garble each token, rejoin.
    tokens = text.split(" ")
    return " ".join(_garble_word(t) for t in tokens)
