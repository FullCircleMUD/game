"""
Shared HP → descriptive string helper.

Used by the `diagnose` command and the prompt `%s`/`%c` tokens to
produce a colour-coded English description of a character's health
("in excellent condition", "has some small wounds", etc.).
"""


def health_description(current, maximum):
    """Return a descriptive string for an HP ratio, colour-wrapped."""
    if maximum <= 0:
        return "|xin an unknown state|n"
    if current <= 0:
        return "|Rincapacitated|n"
    ratio = current / maximum
    if ratio >= 1.0:
        return "|gin excellent condition|n"
    elif ratio >= 0.9:
        return "|ghas a few scratches|n"
    elif ratio >= 0.75:
        return "|ghas some small wounds and bruises|n"
    elif ratio >= 0.50:
        return "|yhas quite a few wounds|n"
    elif ratio >= 0.30:
        return "|yhas some big nasty wounds and scratches|n"
    elif ratio >= 0.15:
        return "|rlooks pretty hurt|n"
    else:
        return "|ris in awful condition|n"
