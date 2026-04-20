"""
Potion quality name helper.

Builds quality-prefixed potion names from the PotionQuality enum.
Effects and scaling data now live directly in per-tier prototype files
and NFTItemType.default_metadata — no scaling tables needed.
"""

from enums.potion_quality import PotionQuality


def get_quality_name(base_name, mastery_int):
    """Return a quality-prefixed potion name for the given mastery level.

    Example: ``get_quality_name("Potion of the Bull", 1)`` → ``"Watery Potion of the Bull"``
    """
    quality = PotionQuality(mastery_int)
    return f"{quality.prefix} {base_name}"
