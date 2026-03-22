"""
SpellbookMixin — spell learning, memorisation, and query for characters.

Characters acquire spells in two ways:
    - **Learned** (permanent): consuming SpellScrollNFTItem objects (mages),
      starting knowledge from chargen. Persists through remort.
    - **Granted** (temporary): class abilities (cleric domains), quests,
      racial innates. Lost on remort via revoke_all_granted_spells().

Both types require memorisation before casting. Memorisation is
capped by class level + ability bonus + equipment:

    Mage:   floor(mage_level / 4) + get_attribute_bonus(intelligence) + extra_memory_slots
    Cleric: floor(cleric_level / 4) + get_attribute_bonus(wisdom) + extra_memory_slots

Cap is checked at memorise time only — buffing ability to memorise extra
spells is valid; they stay memorised when the buff drops.

Storage:
    self.db.spellbook = {"magic_missile": True, ...}        — permanently learned
    self.db.granted_spells = {"cure_wounds": True, ...}     — temporarily granted
    self.db.memorised_spells = {"magic_missile": True, ...} — ready to cast

Usage:
    class FCMCharacter(SpellbookMixin, ...):
        def at_object_creation(self):
            ...
            self.at_spellbook_init()
"""

import math

from evennia.typeclasses.attributes import AttributeProperty

from world.spells.registry import get_spell


class SpellbookMixin:

    # Equipment bonus to memorisation cap — via stat_bonus effect
    extra_memory_slots = AttributeProperty(0)

    # ================================================================== #
    #  Initialization
    # ================================================================== #

    def at_spellbook_init(self):
        """Initialize spellbook storage. Call from at_object_creation()."""
        if not self.db.spellbook:
            self.db.spellbook = {}
        if not self.db.granted_spells:
            self.db.granted_spells = {}
        if not self.db.memorised_spells:
            self.db.memorised_spells = {}

    # ================================================================== #
    #  Learning (permanent)
    # ================================================================== #

    def learn_spell(self, spell_key):
        """
        Add a spell to this character's spellbook (permanent).

        Validates:
            1. Spell exists in SPELL_REGISTRY
            2. Not already known (learned or granted)
            3. Character has the required school mastery

        Returns:
            (bool, str) — (success, message)
        """
        spell = get_spell(spell_key)
        if not spell:
            return (False, "That spell doesn't exist.")

        if self.knows_spell(spell_key):
            return (False, f"You already know {spell.name}.")

        # Check school mastery in class_skill_mastery_levels
        current_mastery = (self.db.class_skill_mastery_levels or {}).get(
            spell.school_key, 0
        )
        if current_mastery < spell.min_mastery.value:
            return (
                False,
                f"You need at least |w{spell.min_mastery.name}|n mastery in "
                f"|w{spell.school_key}|n to learn this spell.",
            )

        if self.db.spellbook is None:
            self.db.spellbook = {}
        self.db.spellbook[spell_key] = True
        return (True, f"You learn {spell.name}!")

    def knows_spell(self, spell_key):
        """Check if this character knows a spell (learned OR granted)."""
        if (self.db.spellbook or {}).get(spell_key):
            return True
        if (self.db.granted_spells or {}).get(spell_key):
            return True
        return False

    # ================================================================== #
    #  Granting (temporary)
    # ================================================================== #

    def grant_spell(self, spell_key):
        """
        Add a spell to granted spells (class abilities, quests, etc.).

        Granted spells behave identically to learned spells for
        memorise/cast/forget — the only difference is they can be
        revoked (e.g. on remort).

        Returns:
            (bool, str) — (success, message)
        """
        spell = get_spell(spell_key)
        if not spell:
            return (False, "That spell doesn't exist.")

        if self.is_granted(spell_key):
            return (False, f"{spell.name} is already granted.")

        if self.db.granted_spells is None:
            self.db.granted_spells = {}
        self.db.granted_spells[spell_key] = True
        return (True, f"You have been granted {spell.name}.")

    def revoke_spell(self, spell_key):
        """
        Remove a granted spell. Also removes from memorised if memorised.

        Returns:
            (bool, str) — (success, message)
        """
        if not self.is_granted(spell_key):
            return (False, "That spell isn't granted.")

        granted = dict(self.db.granted_spells)
        del granted[spell_key]
        self.db.granted_spells = granted

        # Also remove from memorised if it was memorised and not also learned
        if self.is_memorised(spell_key) and not (self.db.spellbook or {}).get(spell_key):
            memorised = dict(self.db.memorised_spells)
            del memorised[spell_key]
            self.db.memorised_spells = memorised

        spell = get_spell(spell_key)
        name = spell.name if spell else spell_key
        return (True, f"{name} has been revoked.")

    def revoke_all_granted_spells(self):
        """
        Revoke all granted spells — called on remort.

        Also removes any memorised spells that were only granted
        (not also permanently learned).
        """
        granted = self.db.granted_spells or {}
        if not granted:
            return

        memorised = dict(self.db.memorised_spells or {})
        spellbook = self.db.spellbook or {}

        for spell_key in granted:
            if spell_key in memorised and not spellbook.get(spell_key):
                del memorised[spell_key]

        self.db.memorised_spells = memorised
        self.db.granted_spells = {}

    def is_granted(self, spell_key):
        """Check if a spell is currently granted."""
        return bool((self.db.granted_spells or {}).get(spell_key))

    # ================================================================== #
    #  Memorisation
    # ================================================================== #

    def memorise_spell(self, spell_key):
        """
        Add a spell to the memorised set. Checks cap.

        Returns:
            (bool, str) — (success, message)
        """
        if not self.knows_spell(spell_key):
            return (False, "You don't know that spell.")

        if self.is_memorised(spell_key):
            return (False, "That spell is already memorised.")

        cap = self.get_memorisation_cap()
        current_count = len(self.db.memorised_spells or {})
        if current_count >= cap:
            return (
                False,
                f"You can only memorise {cap} spell{'s' if cap != 1 else ''}. "
                f"Forget one first.",
            )

        if self.db.memorised_spells is None:
            self.db.memorised_spells = {}
        self.db.memorised_spells[spell_key] = True
        spell = get_spell(spell_key)
        return (True, f"You memorise {spell.name}.")

    def forget_spell(self, spell_key):
        """
        Remove a spell from the memorised set. Instant.

        Returns:
            (bool, str) — (success, message)
        """
        if not self.is_memorised(spell_key):
            return (False, "That spell isn't memorised.")

        spells = dict(self.db.memorised_spells)
        del spells[spell_key]
        self.db.memorised_spells = spells

        spell = get_spell(spell_key)
        return (True, f"You forget {spell.name}.")

    def is_memorised(self, spell_key):
        """Check if a spell is currently memorised."""
        if not self.db.memorised_spells:
            return False
        return self.db.memorised_spells.get(spell_key, False)

    # ================================================================== #
    #  Memorisation Cap
    # ================================================================== #

    def get_memorisation_cap(self):
        """
        Compute total memory slots.

        Sums across all caster classes:
            Mage:   floor(mage_level / 4) + get_attribute_bonus(intelligence)
            Cleric: floor(cleric_level / 4) + get_attribute_bonus(wisdom)

        Plus equipment bonus (extra_memory_slots).
        Always returns at least 1.
        """
        classes = self.db.classes or {}
        total = 0

        # Mage contribution
        mage_level = classes.get("mage", {}).get("level", 0)
        if mage_level > 0:
            total += (
                math.floor(mage_level / 4)
                + self.get_attribute_bonus(self.intelligence)
            )

        # Cleric contribution
        cleric_level = classes.get("cleric", {}).get("level", 0)
        if cleric_level > 0:
            total += (
                math.floor(cleric_level / 4)
                + self.get_attribute_bonus(self.wisdom)
            )

        # Equipment bonus
        total += self.extra_memory_slots or 0

        return max(1, total)

    # ================================================================== #
    #  Queries
    # ================================================================== #

    def get_known_spells(self, school=None):
        """
        Get known spells (learned + granted), optionally filtered by school.

        Returns:
            dict of {spell_key: Spell instance}
        """
        all_keys = set()
        spellbook = self.db.spellbook
        if spellbook:
            if isinstance(spellbook, dict):
                all_keys.update(spellbook.keys())
            else:
                # Legacy list format: ["magic_missile", ...]
                all_keys.update(spellbook)
        granted = self.db.granted_spells
        if granted:
            if isinstance(granted, dict):
                all_keys.update(granted.keys())
            else:
                all_keys.update(granted)

        if not all_keys:
            return {}

        known = {
            key: get_spell(key)
            for key in all_keys
            if get_spell(key) is not None
        }

        if school is not None:
            from enum import Enum
            school_str = school.value if isinstance(school, Enum) else school
            known = {k: v for k, v in known.items() if v.school_key == school_str}

        return known

    def get_memorised_spells(self):
        """
        Get all memorised spells.

        Returns:
            dict of {spell_key: Spell instance}
        """
        if not self.db.memorised_spells:
            return {}

        return {
            key: get_spell(key)
            for key in self.db.memorised_spells
            if get_spell(key) is not None
        }
