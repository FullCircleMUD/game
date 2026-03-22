class ItemNameGenerator:
    """LLM-powered name generation for unique crafted items."""

    def generate_inset_name(self, weapon_name, gem_effects, character):
        """
        Generate a unique name for a gem-inset weapon.

        Args:
            weapon_name: Base weapon name (e.g. "Iron Longsword")
            gem_effects: List of effect dicts from the gem
            character: The character performing the insetting

        Returns:
            str: Generated name for the weapon
        """
        # Stub — returns hardcoded name until LLM integration
        return "LLMName"


name_generator = ItemNameGenerator()
