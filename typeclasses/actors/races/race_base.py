"""
RaceBase — frozen dataclass defining a playable race.

Each race is a single instance of RaceBase with its data. The registry
in __init__.py auto-collects all instances for lookup.

Race data is applied to a character via at_taking_race() during character
creation (or remort). Racial ability score bonuses are permanent and modify
both base_<stat> and <stat>. Racial effects (conditions, resistances) are
applied via the standard apply_effect system.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Type

from evennia import CmdSet

from enums.abilities_enum import Ability
from enums.actor_size import ActorSize
from enums.alignment import Alignment
from enums.mastery_level import MasteryLevel
from enums.weapon_type import WeaponType


@dataclass(frozen=True)
class RaceBase:
    key: str = ""
    display_name: str = ""
    description: str = ""
    size: ActorSize = ActorSize.MEDIUM

    # Starting stats — race sets the foundation, class adds on top
    base_hp: int = 10
    base_mana: int = 10
    base_move: int = 50
    base_armor_class: int = 10

    # Ability score bonuses — Ability enum keys for typo prevention
    # e.g. {Ability.CON: 2, Ability.DEX: -1}
    # Applied to BOTH base_<stat> and <stat> (permanent, not equipment)
    # Uses ability.value (e.g. "constitution") for setattr lookups
    ability_score_bonuses: Dict[Ability, int] = field(default_factory=dict)

    # Effects applied via character.apply_effect() — same format as wear_effects
    # e.g. [{"type": "condition", "condition": "darkvision"},
    #        {"type": "damage_resistance", "damage_type": "poison", "value": 30}]
    racial_effects: List[Dict] = field(default_factory=list)

    # Languages granted free at creation (in addition to Common)
    racial_languages: List[str] = field(default_factory=list)

    # Alignment restrictions — used by chargen to filter available alignments
    required_alignments: List[Alignment] = field(default_factory=list)
    excluded_alignments: List[Alignment] = field(default_factory=list)

    # Racial weapon proficiencies — WeaponType enums granted at BASIC mastery
    # e.g. [WeaponType.BATTLEAXE, WeaponType.HAMMER]
    racial_weapon_proficiencies: List[WeaponType] = field(default_factory=list)

    # Minimum remorts required to select this race
    min_remort: int = 0

    # Optional race-specific command set
    racial_cmdset: Optional[Type[CmdSet]] = None

    def at_taking_race(self, character):
        """
        Apply all racial data to a character.

        Called during character creation or remort. Sets starting stats,
        applies ability score bonuses (permanent), conditions, resistances,
        and languages.
        """
        # Race identifier
        character.race = self.key

        # Starting stats
        character.hp = self.base_hp
        character.base_hp_max = self.base_hp
        character.hp_max = self.base_hp

        character.mana = self.base_mana
        character.base_mana_max = self.base_mana
        character.mana_max = self.base_mana

        character.move = self.base_move
        character.base_move_max = self.base_move
        character.move_max = self.base_move

        character.base_armor_class = self.base_armor_class
        character.armor_class = self.base_armor_class

        # Ability score bonuses — permanent, modify both base and current
        # ability.value gives the string name (e.g. "constitution") for setattr
        for ability, bonus in self.ability_score_bonuses.items():
            base_attr = f"base_{ability.value}"
            setattr(character, base_attr, getattr(character, base_attr) + bonus)
            setattr(character, ability.value, getattr(character, ability.value) + bonus)

        # Racial effects (conditions, resistances) via standard effect system
        for effect in self.racial_effects:
            character.apply_effect(effect)

        # Languages — always includes Common
        langs = set(character.db.languages or set())
        langs.add("common")
        for lang in self.racial_languages:
            langs.add(lang)
        character.db.languages = langs

        # Racial weapon proficiencies — grant BASIC mastery
        if self.racial_weapon_proficiencies:
            weapon_skills = dict(character.db.weapon_skill_mastery_levels or {})
            for weapon in self.racial_weapon_proficiencies:
                weapon_skills[weapon.value] = MasteryLevel.BASIC.value
            character.db.weapon_skill_mastery_levels = weapon_skills

        # Racial command set (persistent survives server restarts)
        if self.racial_cmdset:
            character.cmdset.add(self.racial_cmdset, persistent=True)

    def get_valid_alignments(self):
        """
        Return list of valid Alignment enum members for this race.

        If required_alignments is non-empty, only those are valid.
        Otherwise all alignments minus excluded_alignments are valid.
        """
        all_alignments = list(Alignment)
        if self.required_alignments:
            return [a for a in all_alignments if a in self.required_alignments]
        return [a for a in all_alignments if a not in self.excluded_alignments]
