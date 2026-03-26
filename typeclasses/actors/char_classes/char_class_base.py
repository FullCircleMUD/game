"""
CharClassBase — frozen dataclass defining a playable character class.

Each class is a single instance of CharClassBase with its data. The registry
in __init__.py auto-collects all instances for lookup.

Class data is applied to a character via at_char_first_gaining_class() during
character creation. Level-up progression is handled by
at_gain_subsequent_level_in_class(). Both methods modify character stats
additively (race sets the foundation, class adds on top).

Level progression tables map level number (1-40) to per-level gains:
    {
        1: {"weapon_skill_pts": 4, "class_skill_pts": 3, "general_skill_pts": 2,
            "hp_gain": 20, "mana_gain": 2, "move_gain": 5},
        2: { ... },
        ...
    }
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Type

from evennia import CmdSet

from enums.abilities_enum import Ability
from enums.alignment import Alignment


@dataclass(frozen=True)
class CharClassBase:
    key: str = ""
    display_name: str = ""
    description: str = ""

    # Primary ability score for this class (used for XP bonus, display)
    prime_attribute: Optional[Ability] = None

    # Level 1-40 progression — dict of level number to gains dict
    # Each entry: {"weapon_skill_pts", "class_skill_pts", "general_skill_pts",
    #              "hp_gain", "mana_gain", "move_gain"}
    level_progression: Dict[int, Dict] = field(default_factory=dict)

    # Ability score requirements to multiclass INTO this class
    # e.g. {Ability.STR: 14, Ability.CON: 12}
    multi_class_requirements: Dict[Ability, int] = field(default_factory=dict)

    # Minimum remorts required to select this class
    min_remort: int = 0

    # Alignment restrictions — used by chargen to filter available alignments
    required_alignments: List[Alignment] = field(default_factory=list)
    excluded_alignments: List[Alignment] = field(default_factory=list)

    # Race restrictions — race key strings (e.g. ["dwarf", "elf"])
    # Compared against character.race (a string key from the race registry)
    required_races: List[str] = field(default_factory=list)
    excluded_races: List[str] = field(default_factory=list)

    # Optional class-specific command set (the class itself, not an instance)
    class_cmdset: Optional[Type[CmdSet]] = None

    # Whether this class grants spells (temporary, lost on remort) vs
    # learns them (permanent, persist through remort). True for cleric, druid, etc.
    grants_spells: bool = False

    def char_can_take_class(self, character) -> bool:
        """
        Check if a character meets the requirements to take this class.

        Validates race, alignment, and remort requirements. Used during
        character creation and multiclassing.
        """
        # Race check — required whitelist takes precedence over excluded blacklist
        if self.required_races:
            race_ok = character.race in self.required_races
        elif self.excluded_races:
            race_ok = character.race not in self.excluded_races
        else:
            race_ok = True

        # Alignment check — same logic
        if self.required_alignments:
            alignment_ok = character.alignment in self.required_alignments
        elif self.excluded_alignments:
            alignment_ok = character.alignment not in self.excluded_alignments
        else:
            alignment_ok = True

        # Remort check
        remort_ok = character.num_remorts >= self.min_remort

        return race_ok and alignment_ok and remort_ok

    def at_char_first_gaining_class(self, character):
        """
        Apply level 1 class data to a character.

        Called during character creation or when multiclassing into this class
        for the first time. Adds the class cmdset, applies level 1 HP/mana/move
        gains, and grants starting skill points.

        Stats are ADDITIVE — race sets the foundation, class adds on top.
        """
        # Add the class command set (persistent survives server restarts)
        if self.class_cmdset:
            character.cmdset.add(self.class_cmdset, persistent=True)

        level1data = self.level_progression[1]

        # Skill points — added to existing totals (may already have points
        # from racial bonuses or a previous class if multiclassing)
        character.general_skill_pts_available += level1data["general_skill_pts"]
        character.weapon_skill_pts_available += level1data["weapon_skill_pts"]

        # Initialize the classes tracking dict if needed
        if not character.db.classes:
            character.db.classes = {}

        # Track this class — level 1, class-specific skill points
        character.db.classes[self.key] = {
            "level": 1,
            "skill_pts_available": level1data["class_skill_pts"],
        }

        # HP, mana, move — additive on top of racial base
        # Remort per-level bonuses are included in the gain
        hp_gain = level1data["hp_gain"] + getattr(character, "bonus_hp_per_level", 0)
        mana_gain = level1data["mana_gain"] + getattr(character, "bonus_mana_per_level", 0)
        move_gain = level1data["move_gain"] + getattr(character, "bonus_move_per_level", 0)

        character.hp += hp_gain
        character.base_hp_max += hp_gain
        character.hp_max += hp_gain

        character.mana += mana_gain
        character.base_mana_max += mana_gain
        character.mana_max += mana_gain

        character.move += move_gain
        character.base_move_max += move_gain
        character.move_max += move_gain

    def at_gain_subsequent_level_in_class(self, character):
        """
        Apply the next level's progression data to a character.

        Called when a character spends a pending level on this class.
        Validates the character has the class and has levels to spend,
        then applies the progression data for the next level.
        """
        if self.key not in (character.db.classes or {}):
            character.msg(
                f"You are not a {self.display_name}. Find a guild or sponsor "
                f"to become a level 1 {self.display_name}."
            )
            return

        if not character.levels_to_spend > 0:
            character.msg("You do not have any levels to spend.")
            return

        # Deduct the level to spend
        character.levels_to_spend -= 1

        # Increment class level
        class_data = character.db.classes[self.key]
        class_data["level"] += 1

        # Look up progression data for the new level
        level_data = self.level_progression[class_data["level"]]

        # Skill points
        character.general_skill_pts_available += level_data["general_skill_pts"]
        character.weapon_skill_pts_available += level_data["weapon_skill_pts"]
        class_data["skill_pts_available"] += level_data["class_skill_pts"]

        # HP, mana, move — includes remort per-level bonuses
        hp_gain = level_data["hp_gain"] + getattr(character, "bonus_hp_per_level", 0)
        mana_gain = level_data["mana_gain"] + getattr(character, "bonus_mana_per_level", 0)
        move_gain = level_data["move_gain"] + getattr(character, "bonus_move_per_level", 0)

        character.hp += hp_gain
        character.base_hp_max += hp_gain
        character.hp_max += hp_gain

        character.mana += mana_gain
        character.base_mana_max += mana_gain
        character.mana_max += mana_gain

        character.move += move_gain
        character.base_move_max += move_gain
        character.move_max += move_gain

        # Save updated class data back
        character.db.classes[self.key] = class_data

        character.msg(
            f"CONGRATS! You have progressed to level {class_data['level']} "
            f"as a {self.display_name}!"
        )

    def get_valid_alignments(self):
        """
        Return list of valid Alignment enum members for this class.

        If required_alignments is non-empty, only those are valid.
        Otherwise all alignments minus excluded_alignments are valid.
        """
        all_alignments = list(Alignment)
        if self.required_alignments:
            return [a for a in all_alignments if a in self.required_alignments]
        return [a for a in all_alignments if a not in self.excluded_alignments]
