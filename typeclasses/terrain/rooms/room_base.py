
from collections import defaultdict
from django.utils.translation import gettext as _
from evennia.utils.utils import (
    compress_whitespace,
    iter_to_str,
    make_iter,
)
from evennia import (
    DefaultRoom,
    AttributeProperty
)
from enums.condition import Condition
from enums.terrain_type import TerrainType
from typeclasses.mixins.fungible_inventory import FungibleInventoryMixin
from typeclasses.mixins.quest_tag import QuestTagMixin


def _can_see_hidden(entity):
    """Check if entity can see HIDDEN actors/objects.

    True Sight: HIDDEN at all tiers (SKILLED+).
    Holy Sight: HIDDEN at MASTER+ (tier 4) only.
    """
    if not hasattr(entity, "has_effect"):
        return False
    if entity.has_effect("true_sight"):
        return True
    if (
        entity.has_effect("holy_sight")
        and (getattr(entity.db, "holy_sight_tier", 0) or 0) >= 4
    ):
        return True
    return False


class RoomBase(QuestTagMixin, FungibleInventoryMixin, DefaultRoom):

    allow_combat = AttributeProperty(True, autocreate=False)
    allow_pvp = AttributeProperty(False, autocreate=False)
    allow_death = AttributeProperty(True, autocreate=False)
    defeat_destination = AttributeProperty(None, autocreate=False)

    # this room allows one level of flying
    max_height = AttributeProperty(1)
    # this room does not go underwater (must be negative)
    max_depth = AttributeProperty(0)

    # Lightweight examinable descriptions: {"keyword": "description", ...}
    details = AttributeProperty(default=dict)

    # Day/Night lighting — None means "derive from terrain type"
    natural_light = AttributeProperty(None, autocreate=False)

    # Permanently lit — room is never dark regardless of time/light sources
    always_lit = AttributeProperty(False, autocreate=False)

    # Weather shelter — None means "derive from terrain type"
    # True = sheltered (indoor building), False = exposed (outdoor)
    sheltered = AttributeProperty(None, autocreate=False)

    # Terrain types that are naturally dark (no sunlight)
    _DARK_TERRAIN = {TerrainType.UNDERGROUND.value, TerrainType.DUNGEON.value}

    # Terrain types that are subterranean (no weather at all)
    _SUBTERRANEAN_TERRAIN = {TerrainType.UNDERGROUND.value, TerrainType.DUNGEON.value}


    vert_descriptions = AttributeProperty(None, autocreate=False)
    """Per-height room descriptions. Dict {height_int: description_str}.
    None = use standard db.desc for all heights (default).

    When set, characters at a matching height see the height-specific
    description instead of db.desc. Heights without a mapping fall back
    to db.desc with the standard flying/underwater prefix.

    Example:
        room.vert_descriptions = {
            0: "A cobblestone courtyard surrounded by high walls...",
            1: "From above, the courtyard spreads out below you...",
            -1: "The water is waist deep here...",
        }
    """

    def at_object_creation(self):
        super().at_object_creation()
        self.at_fungible_init()

    # --- Zone / District helpers ---

    def set_zone(self, zone_name):
        """Set this room's zone tag (replaces any existing)."""
        self.tags.clear(category="zone")
        self.tags.add(zone_name, category="zone")

    def get_zone(self):
        """Return this room's zone name, or None."""
        return self.tags.get(category="zone")

    def set_district(self, district_name):
        """Set this room's district tag (replaces any existing)."""
        self.tags.clear(category="district")
        self.tags.add(district_name, category="district")

    def get_district(self):
        """Return this room's district name, or None."""
        return self.tags.get(category="district")

    def set_terrain(self, terrain_name):
        """Set this room's terrain tag (replaces any existing)."""
        self.tags.clear(category="terrain")
        self.tags.add(terrain_name, category="terrain")

    def get_terrain(self):
        """Return this room's terrain type, or None."""
        return self.tags.get(category="terrain")

    # --- Lighting helpers ---

    @property
    def has_natural_light(self):
        """
        Whether this room receives natural sunlight.

        If natural_light is explicitly set (True/False), use that.
        Otherwise derive from terrain type: underground/dungeon = False,
        everything else = True.
        """
        explicit = self.natural_light
        if explicit is not None:
            return bool(explicit)
        terrain = self.get_terrain()
        if terrain and terrain in self._DARK_TERRAIN:
            return False
        return True

    # --- Weather exposure helpers ---

    @property
    def is_subterranean(self):
        """True for underground/dungeon rooms — no weather at all."""
        terrain = self.get_terrain()
        return terrain is not None and terrain in self._SUBTERRANEAN_TERRAIN

    @property
    def is_sheltered(self):
        """
        True for indoor/building rooms — hear muffled weather, no effects.

        If sheltered is explicitly set (True/False), use that.
        Otherwise derive from terrain type: urban = sheltered,
        everything else = not sheltered.
        """
        explicit = self.sheltered
        if explicit is not None:
            return bool(explicit)
        terrain = self.get_terrain()
        return terrain == TerrainType.URBAN.value

    @property
    def is_weather_exposed(self):
        """True for outdoor rooms that get full weather descriptions + effects."""
        return not self.is_subterranean and not self.is_sheltered

    def _has_light_source_in_room(self):
        """Check if any lit light source exists in the room contents."""
        for obj in self.contents:
            if getattr(obj, "is_light_source", False) and getattr(obj, "is_lit", False):
                return True
            # Light spell on a character illuminates the room for everyone
            if hasattr(obj, "has_effect") and obj.has_effect("light_spell"):
                return True
        return False

    def _looker_has_light(self, looker):
        """Check if the looker carries or wears a lit light source."""
        if not hasattr(looker, "contents"):
            return False
        for obj in looker.contents:
            if getattr(obj, "is_light_source", False) and getattr(obj, "is_lit", False):
                return True
        return False

    def is_dark(self, looker=None):
        """
        Return True if this room is currently dark for the given looker.

        A room is NOT dark if any of:
            - It is permanently lit (always_lit)
            - It has natural light and the current phase is a light phase
            - A lit light source exists in the room (lamp post, dropped torch)
            - The looker carries a lit light source
            - The looker has DARKVISION
        """
        # Permanently lit rooms are never dark
        if self.always_lit:
            return False

        from typeclasses.scripts.day_night_service import get_time_of_day

        # Natural light rooms are lit during light phases
        if self.has_natural_light and get_time_of_day().is_light:
            return False

        # Any lit fixture or dropped light source in the room
        if self._has_light_source_in_room():
            return False

        # Looker-specific checks
        if looker:
            if self._looker_has_light(looker):
                return False
            if (
                hasattr(looker, "has_condition")
                and looker.has_condition(Condition.DARKVISION)
            ):
                return False

        return True

    def at_object_receive(self, moved_obj, source_location, **kwargs):
        """Fire quest events and notify mobs when something enters."""
        super().at_object_receive(moved_obj, source_location, **kwargs)
        if self.quest_tags and hasattr(moved_obj, "quests"):
            self.fire_quest_event(moved_obj, "enter_room")

        # Notify mobs in this room about the new arrival
        for obj in self.contents:
            if obj != moved_obj and hasattr(obj, "at_new_arrival"):
                obj.at_new_arrival(moved_obj)

    def msg_contents(self, text=None, exclude=None, from_obj=None, mapping=None,
                     raise_funcparse_errors=False, **kwargs):
        """
        Override to filter room messages based on actor visibility.

        - HIDDEN actor: only recipients with true_sight see the message.
        - INVISIBLE actor: only recipients with DETECT_INVIS see the message.

        All 34+ existing callers pass from_obj=caller, so this works
        automatically with zero caller changes.
        """
        if from_obj and hasattr(from_obj, "has_condition"):
            if from_obj.has_condition(Condition.HIDDEN):
                # Only sight-capable recipients see messages from hidden actors
                exclude = list(make_iter(exclude)) if exclude else []
                for obj in self.contents:
                    if obj not in exclude and not _can_see_hidden(obj):
                        exclude.append(obj)
            elif from_obj.has_condition(Condition.INVISIBLE):
                exclude = list(make_iter(exclude)) if exclude else []
                for obj in self.contents:
                    if obj not in exclude and not (
                        hasattr(obj, "has_condition")
                        and obj.has_condition(Condition.DETECT_INVIS)
                    ):
                        exclude.append(obj)

        # Sleeping characters get a muffled message instead of the real content.
        # Collect sleepers, exclude them from the normal broadcast, then send
        # the muffled version directly.
        sleepers = []
        for obj in self.contents:
            if (getattr(obj, "position", None) == "sleeping"
                    and obj != from_obj
                    and (not exclude or obj not in exclude)):
                sleepers.append(obj)

        if sleepers:
            exclude = list(make_iter(exclude)) if exclude else []
            exclude.extend(sleepers)
            for sleeper in sleepers:
                sleeper.msg("|xYou hear muffled sounds nearby...|n")

        super().msg_contents(
            text, exclude=exclude, from_obj=from_obj, mapping=mapping,
            raise_funcparse_errors=raise_funcparse_errors, **kwargs
        )

    def msg_contents_with_invis_alt(self, normal_msg, invis_msg, from_obj, exclude=None):
        """
        Send room message with alternate text for invisible actors.

        - HIDDEN from_obj: only true_sight recipients see normal_msg.
        - INVISIBLE from_obj: DETECT_INVIS recipients see normal_msg,
          others see invis_msg. from_obj is always excluded.
        - Normal: standard msg_contents with from_obj.
        """
        exclude = list(make_iter(exclude)) if exclude else []
        if from_obj and from_obj not in exclude:
            exclude.append(from_obj)

        if from_obj and hasattr(from_obj, "has_condition"):
            if from_obj.has_condition(Condition.HIDDEN):
                # Only sight-capable recipients see messages from hidden actors
                for obj in self.contents:
                    if obj in exclude:
                        continue
                    if _can_see_hidden(obj):
                        obj.msg(normal_msg)
                return
            if from_obj.has_condition(Condition.INVISIBLE):
                for obj in self.contents:
                    if obj in exclude:
                        continue
                    if (
                        hasattr(obj, "has_condition")
                        and obj.has_condition(Condition.DETECT_INVIS)
                    ):
                        obj.msg(normal_msg)
                    else:
                        obj.msg(invis_msg)
                return

        super().msg_contents(normal_msg, exclude=exclude, from_obj=from_obj)

    def return_appearance(self, looker, **kwargs):
        """
        Main callback used by 'look' for the object to describe itself.

        Assembles the room display procedurally (CircleMUD-style):
          1. Header (subclass hook)
          2. Room name — cyan, with vertical-position suffix
          3. Room description — skipped when brief mode is active on movement
          4. Auto-exits — cyan, compact line (only if looker has auto_exits pref)
          5. Things/objects — green
          6. Characters — yellow
          7. Footer (subclass hook)

        Empty sections are suppressed entirely — no "None" lines.

        Args:
            looker (DefaultObject): Object doing the looking.
            **kwargs: Passed into all helper methods.
                ignore_brief (bool): If True, always show description even
                    when the looker has brief_mode enabled. The ``look``
                    command passes True; room-entry passes nothing (False).

        Returns:
            str: The formatted room description.
        """
        if not looker:
            return ""

        ignore_brief = kwargs.get("ignore_brief", False)

        # ── Dark room shortcut ─────────────────────────────────────
        if self.is_dark(looker):
            parts = []
            header = self.get_display_header(looker, **kwargs)
            if header:
                parts.append(header)
            parts.append("|cUnknown|n")
            parts.append(self.get_display_desc(looker, **kwargs))
            footer = self.get_display_footer(looker, **kwargs)
            if footer:
                parts.append(footer)
            return f"\n{self.format_appearance(chr(10).join(parts), looker, **kwargs)}"

        # ── Room name (cyan) with vertical position suffix ─────────
        char_height = looker.room_vertical_position
        base_name = self.get_display_name(looker, **kwargs)
        extra = self.get_extra_display_name_info(looker, **kwargs)
        if extra:
            base_name = f"{base_name} {extra}"

        if char_height == 0 and self.max_depth < 0:
            formatted_name = f"{base_name}   (Swimming)"
        elif char_height < 0:
            formatted_name = f"{base_name}   (Underwater)"
        elif char_height > 0:
            formatted_name = f"{base_name}   (Flying)"
        else:
            formatted_name = base_name

        parts = []
        header = self.get_display_header(looker, **kwargs)
        if header:
            parts.append(header)
        parts.append(f"|c{formatted_name}|n")

        # ── Description (default color) — respect brief mode ────────
        show_desc = ignore_brief or not getattr(looker, "brief_mode", False)
        if show_desc:
            desc = self.get_display_desc(looker, **kwargs)
            # Add height prefix only when vert_descriptions didn't provide
            # a height-specific description (those already describe the
            # scene from the correct perspective).
            has_vert_desc = (
                self.vert_descriptions
                and (char_height in self.vert_descriptions
                     or str(char_height) in self.vert_descriptions)
            )
            if not has_vert_desc:
                if char_height < 0:
                    desc = f"Swimming underwater you can dimly perceive above you:\n{desc}"
                elif char_height > 0:
                    desc = f"Flying you can see below you:\n{desc}"
            if desc:
                parts.append(f"|n{desc}")

        # ── Auto-exits (cyan, compact) ─────────────────────────────
        if getattr(looker, "auto_exits", True):
            exits_str = self.get_display_exits(looker, **kwargs)
            if exits_str:
                parts.append(f"|c{exits_str}|n")

        # ── Things/objects (green) ─────────────────────────────────
        things_str = self.get_display_things(looker, **kwargs)
        if things_str:
            parts.append(f"|g{things_str}|n")

        # ── Characters (yellow) ───────────────────────────────────
        chars_str = self.get_display_characters(looker, **kwargs)
        if chars_str:
            parts.append(f"|y{chars_str}|n")

        footer = self.get_display_footer(looker, **kwargs)
        if footer:
            parts.append(footer)

        return f"\n{self.format_appearance(chr(10).join(parts), looker, **kwargs)}"

    def get_display_header(self, looker, **kwargs):
        """
        Get the 'header' component of the object description. Called by `return_appearance`.

        Args:
            looker (DefaultObject): Object doing the looking.
            **kwargs: Arbitrary data for use when overriding.
        Returns:
            str: The header display string.

        """
        return ""

    def get_extra_display_name_info(self, looker=None, **kwargs):
        """
        Adds any extra display information to the object's name. By default this is is the
        object's dbref in parentheses, if the looker has permission to see it.

        Args:
            looker (DefaultObject): The object looking at this object.

        Returns:
            str: The dbref of this object, if the looker has permission to see it. Otherwise, an
            empty string is returned.

        Notes:
            By default, this becomes a string (#dbref) attached to the object's name.

        """
        if looker and self.locks.check_lockstring(looker, "perm(Builder)"):
            return f"(#{self.id})"
        return ""

    def get_display_desc(self, looker, **kwargs):
        """
        Get the 'desc' component of the object description. Called by `return_appearance`.

        If ``vert_descriptions`` is set and contains a key matching the
        looker's ``room_vertical_position``, that description is used
        instead of ``db.desc``. Otherwise falls back to the standard
        description with flying/underwater prefixes.

        Args:
            looker (DefaultObject): Object doing the looking.
            **kwargs: Arbitrary data for use when overriding.
        Returns:
            str: The desc display string.
        """
        if self.is_dark(looker):
            return "|xIt is pitch black. You can't see a thing.|n"

        # Check for height-specific description override
        # Note: Evennia may serialize dict keys as strings, so check both
        desc = None
        if self.vert_descriptions:
            height = getattr(looker, "room_vertical_position", 0)
            if height in self.vert_descriptions:
                desc = self.vert_descriptions[height]
            elif str(height) in self.vert_descriptions:
                desc = self.vert_descriptions[str(height)]

        if desc is None:
            desc = self.db.desc or self.default_description

        # Suppress weather when underwater — you can't see the sky
        char_height = getattr(looker, "room_vertical_position", 0)
        if char_height >= 0:
            weather_line = self._get_weather_desc_line()
            if weather_line:
                desc = f"{desc}\n{weather_line}"
        return desc

    def _get_weather_desc_line(self):
        """
        Return a weather description line for the current room, or "".

        Subterranean rooms get nothing. Sheltered rooms get muffled
        indoor sounds for audible weather. Exposed rooms get full
        weather descriptions.
        """
        if self.is_subterranean:
            return ""

        from typeclasses.scripts.weather_service import get_weather
        from utils.weather_descs import EXPOSED_WEATHER_DESCS, SHELTERED_WEATHER_DESCS

        zone = self.get_zone()
        weather = get_weather(zone)

        if self.is_sheltered:
            return SHELTERED_WEATHER_DESCS.get(weather, "")
        return EXPOSED_WEATHER_DESCS.get(weather, "")

    # Direction → compact abbreviation for auto-exit line
    _DIR_ABBREVS = {
        "north": "n", "south": "s", "east": "e", "west": "w",
        "northeast": "ne", "northwest": "nw",
        "southeast": "se", "southwest": "sw",
        "up": "u", "down": "d", "in": "in", "out": "out",
    }

    # Canonical display order for cardinal/vertical directions
    _DIR_ORDER = [
        "north", "east", "south", "west",
        "northeast", "northwest", "southeast", "southwest",
        "up", "down", "in", "out",
    ]

    def get_display_exits(self, looker, **kwargs):
        """
        Compact CircleMUD-style auto-exit line.

        Returns a string like ``[ Exits: n e s w ]`` using direction
        abbreviations for cardinal exits. Non-directional exits (portals,
        named passages) use their full key. Closed doors are hidden.

        Returns:
            str: The compact exits string, or "" if no visible exits.
        """
        exits = self.filter_visible(
            self.contents_get(content_type="exit"), looker, **kwargs
        )

        # Filter hidden/invisible exits and closed doors
        exits = [
            ex for ex in exits
            if (not hasattr(ex, "is_visible_to") or ex.is_visible_to(looker))
            and (not hasattr(ex, "is_open") or ex.is_open)
        ]

        # Filter height-gated exits based on looker's vertical position.
        # Exits with required_min/max_height or arrival_heights set are
        # only shown when the looker is at an accessible height.
        char_height = getattr(looker, "room_vertical_position", 0)
        exits = [
            ex for ex in exits
            if not hasattr(ex, "is_height_accessible")
            or ex.is_height_accessible(char_height)
        ]

        if not exits:
            return ""

        # Build list of abbreviations, sorted by canonical direction order
        dir_order = {d: i for i, d in enumerate(self._DIR_ORDER)}
        labels = []
        for ex in exits:
            direction = getattr(ex, "direction", None)
            if direction and direction in self._DIR_ABBREVS:
                labels.append((dir_order.get(direction, 99), self._DIR_ABBREVS[direction]))
            else:
                # Non-directional exit — use its key
                labels.append((100, ex.key))

        labels.sort(key=lambda pair: pair[0])
        exit_names = " ".join(label for _, label in labels)
        return f"[ Exits: {exit_names} ]"

    def get_display_characters(self, looker, **kwargs):
        """
        Get the 'characters' component of the object description. Called by `return_appearance`.

        Filters out HIDDEN and INVISIBLE characters based on looker's conditions.
        Returns empty string in dark rooms or when no visible characters.
        """
        if self.is_dark(looker):
            return ""

        characters = self.filter_visible(
            self.contents_get(content_type="character"), looker, **kwargs
        )

        # Filter hidden/invisible characters
        visible = []
        looker_has_detect = (
            hasattr(looker, "has_condition")
            and looker.has_condition(Condition.DETECT_INVIS)
        )
        for char in characters:
            if not hasattr(char, "has_condition"):
                visible.append(char)
                continue
            if char.has_condition(Condition.HIDDEN):
                if not _can_see_hidden(looker):
                    continue
            if char.has_condition(Condition.INVISIBLE) and not looker_has_detect:
                continue
            visible.append(char)

        # Filter by height-gated visibility
        visible = [
            char for char in visible
            if not hasattr(char, "is_height_visible_to")
            or char.is_height_visible_to(looker)
        ]

        if not visible:
            return ""

        lines = []
        for char in visible:
            # Use room_description if available, otherwise fall back to name
            if hasattr(char, "get_room_description"):
                line = char.get_room_description()
            else:
                line = char.get_display_name(looker, **kwargs)
            # Append visibility tags
            if hasattr(char, "has_condition"):
                if char.has_condition(Condition.INVISIBLE):
                    line += " (invisible)"
                if char.has_condition(Condition.HIDDEN):
                    line += " (hidden)"
            lines.append(line)
        return "\n".join(lines)

    def get_display_things(self, looker, **kwargs):
        """
        Get the 'things' component of the object description. Called by `return_appearance`.

        Filters out hidden/invisible objects based on looker's discovery
        state and conditions. Returns empty string in dark rooms or when
        no visible objects.
        """
        if self.is_dark(looker):
            return ""

        # sort and handle same-named things
        things = self.filter_visible(self.contents_get(content_type="object"), looker, **kwargs)

        # Filter hidden/invisible objects
        things = [
            thing for thing in things
            if not hasattr(thing, "is_visible_to") or thing.is_visible_to(looker)
        ]

        # Filter by height-gated visibility
        things = [
            thing for thing in things
            if not hasattr(thing, "is_height_visible_to")
            or thing.is_height_visible_to(looker)
        ]

        # Separate items with ground descriptions (full sentences) from
        # bare-name items (grouped and comma-separated).
        ground_sentences = []
        bare_things = []
        for thing in things:
            gdesc = getattr(thing, "ground_description", "")
            if gdesc:
                ground_sentences.append(gdesc)
            else:
                bare_things.append(thing)

        grouped_things = defaultdict(list)
        for thing in bare_things:
            grouped_things[thing.get_display_name(looker, **kwargs)].append(thing)

        thing_names = []
        for thingname, thinglist in sorted(grouped_things.items()):
            nthings = len(thinglist)
            thing = thinglist[0]
            singular, plural = thing.get_numbered_name(nthings, looker, key=thingname)
            thing_names.append(singular if nthings == 1 else plural)
        thing_names = iter_to_str(thing_names, endsep=_(", and"))

        # Append any fungibles (gold, resources) visible in the room
        fungible_display = self.get_room_fungible_display()

        parts = []
        if ground_sentences:
            parts.append("\n".join(ground_sentences))
        if thing_names:
            parts.append(thing_names)
        if fungible_display:
            parts.append(fungible_display)
        return "\n".join(parts) if parts else ""

    def get_display_footer(self, looker, **kwargs):
        """
        Get the 'footer' component of the object description. Called by `return_appearance`.

        Args:
            looker (DefaultObject): Object doing the looking.
            **kwargs: Arbitrary data for use when overriding.
        Returns:
            str: The footer display string.

        """
        return ""
