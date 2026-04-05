"""
ItemRestrictionMixin — data-driven usage restrictions for NFT items.

Mixed into BaseNFTItem so every item has these fields. Default is
unrestricted — items only become restricted when a prototype sets
restriction fields.

Usage restrictions are checked via can_use(character) which returns
(bool, str). The wear() validation chain calls this before equipping.

Restriction logic:
    required_classes   — OR:  character has ANY listed class → pass
    excluded_classes   — NOT: character has ANY listed class → fail
    min_class_levels   — ALL: each class must be at >= level
    required_races     — OR:  character's race is in list → pass
    excluded_races     — NOT: character's race is in list → fail
    min_alignment_score — character.alignment_score >= value
    max_alignment_score — character.alignment_score <= value
    min_total_level    — character.total_level >= value
    min_remorts        — character.num_remorts >= value
    min_attributes     — ALL: each ability score must be >= value
    min_mastery        — ALL: each skill must be at >= mastery level
"""

from evennia.typeclasses.attributes import AttributeProperty


class ItemRestrictionMixin:
    """Data-driven item usage restrictions. Default: unrestricted."""

    # ── Class restrictions (multiclass-aware) ──
    required_classes = AttributeProperty(default=list)
    excluded_classes = AttributeProperty(default=list)
    min_class_levels = AttributeProperty(default=dict)

    # ── Race restrictions ──
    required_races = AttributeProperty(default=list)
    excluded_races = AttributeProperty(default=list)

    # ── Alignment restrictions (score-based) ──
    min_alignment_score = AttributeProperty(None)  # e.g. 300 = Good+ only
    max_alignment_score = AttributeProperty(None)  # e.g. -300 = Evil+ only

    # ── Level / remort gates ──
    min_total_level = AttributeProperty(0)
    min_remorts = AttributeProperty(0)

    # ── Ability score minimums ──
    min_attributes = AttributeProperty(default=dict)

    # ── Skill mastery minimums ──
    min_mastery = AttributeProperty(default=dict)

    @property
    def is_restricted(self):
        """True if any restriction field is set to a non-default value."""
        return bool(
            self.required_classes or self.excluded_classes
            or self.min_class_levels
            or self.required_races or self.excluded_races
            or self.min_alignment_score is not None
            or self.max_alignment_score is not None
            or self.min_total_level or self.min_remorts
            or self.min_attributes or self.min_mastery
        )

    def can_use(self, character):
        """
        Check if a character meets all item restrictions.

        Args:
            character: the character attempting to use this item

        Returns:
            (bool, str) — (allowed, reason_message)
        """
        if not self.is_restricted:
            return (True, "")

        item_name = self.key

        # ── Class checks ──
        char_classes = dict(character.db.classes or {})

        required_classes = [str(c) for c in (self.required_classes or [])]
        excluded_classes = [str(c) for c in (self.excluded_classes or [])]

        if required_classes:
            if not any(c in char_classes for c in required_classes):
                names = ", ".join(
                    c.capitalize() for c in required_classes
                )
                return (False, f"You must be a {names} to use {item_name}.")

        if excluded_classes:
            blocked = [
                c for c in excluded_classes if c in char_classes
            ]
            if blocked:
                names = ", ".join(c.capitalize() for c in blocked)
                return (
                    False,
                    f"A {names} cannot use {item_name}.",
                )

        min_class_levels = dict(self.min_class_levels or {})
        if min_class_levels:
            for cls, req_level in min_class_levels.items():
                if cls not in char_classes:
                    return (
                        False,
                        f"You need to be a level {req_level} "
                        f"{cls.capitalize()} to use {item_name}.",
                    )
                char_level = char_classes[cls].get("level", 0)
                if char_level < req_level:
                    return (
                        False,
                        f"You need to be a level {req_level} "
                        f"{cls.capitalize()} to use {item_name} "
                        f"(currently level {char_level}).",
                    )

        # ── Race checks ──
        required_races = [str(r) for r in (self.required_races or [])]
        if required_races:
            if character.race not in required_races:
                names = ", ".join(str(r) for r in required_races)
                return (
                    False,
                    f"Only {names} can use {item_name}.",
                )

        excluded_races = [str(r) for r in (self.excluded_races or [])]
        if excluded_races:
            if character.race in excluded_races:
                return (
                    False,
                    f"Your race cannot use {item_name}.",
                )

        # ── Alignment checks (score-based) ──
        score = getattr(character, "alignment_score", 0)
        if self.min_alignment_score is not None and score < self.min_alignment_score:
            return (
                False,
                f"Your alignment prevents you from using {item_name}.",
            )
        if self.max_alignment_score is not None and score > self.max_alignment_score:
            return (
                False,
                f"Your alignment prevents you from using {item_name}.",
            )

        # ── Level check ──
        if self.min_total_level:
            if character.total_level < self.min_total_level:
                return (
                    False,
                    f"You must be level {self.min_total_level} to use "
                    f"{item_name} (currently level {character.total_level}).",
                )

        # ── Remort check ──
        if self.min_remorts:
            if character.num_remorts < self.min_remorts:
                return (
                    False,
                    f"You need {self.min_remorts} remort(s) to use "
                    f"{item_name}.",
                )

        # ── Ability score checks ──
        min_attributes = dict(self.min_attributes or {})
        if min_attributes:
            for attr, req_val in min_attributes.items():
                current = getattr(character, attr, 0)
                if current < req_val:
                    return (
                        False,
                        f"You need {req_val} {attr} to use {item_name} "
                        f"(currently {current}).",
                    )

        # ── Skill mastery checks ──
        min_mastery = dict(self.min_mastery or {})
        if min_mastery:
            for skill_key, req_level in min_mastery.items():
                current = self._get_mastery_level(character, skill_key)
                if current < req_level:
                    return (
                        False,
                        f"You need higher mastery in {skill_key} to use "
                        f"{item_name}.",
                    )

        return (True, "")

    @staticmethod
    def _get_mastery_level(character, skill_key):
        """Look up a skill's mastery level across all three skill dicts."""
        for attr in (
            "general_skill_mastery_levels",
            "class_skill_mastery_levels",
            "weapon_skill_mastery_levels",
        ):
            levels = getattr(character.db, attr, None) or {}
            if skill_key in levels:
                return levels[skill_key]
        return 0
