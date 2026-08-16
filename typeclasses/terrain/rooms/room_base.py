
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
from typeclasses.mixins.unseen_name import UnseenNameMixin
from utils.targeting.predicates import (
    p_actor_visible_to,
    p_can_perceive,
    p_living,
    p_object_visible_to,
)
from utils.visibility import looker_is_blind


class RoomBase(UnseenNameMixin, QuestTagMixin, FungibleInventoryMixin, DefaultRoom):

    #: A room you cannot see is not nowhere — it is somewhere unidentified.
    unseen_name = AttributeProperty("Somewhere")

    allow_combat = AttributeProperty(True, autocreate=False)
    allow_pvp = AttributeProperty(False, autocreate=False)
    allow_death = AttributeProperty(True, autocreate=False)
    defeat_destination = AttributeProperty(None, autocreate=False)

    # this room allows one level of flying
    max_height = AttributeProperty(1)
    # this room does not go underwater (must be negative)
    max_depth = AttributeProperty(0)

    # Height visibility barriers — tuple of (barrier_height, max_concealed_size)
    # or None. Objects small enough are hidden from observers on the other side.
    # See HeightAwareMixin.is_height_visible_to() for the check algorithm.
    visibility_up_barrier = AttributeProperty(None, autocreate=False)
    visibility_down_barrier = AttributeProperty(None, autocreate=False)

    # Lightweight examinable descriptions: {"keyword": "description", ...}
    details = AttributeProperty(default=dict)

    # Day/Night lighting — None means "derive from terrain type"
    natural_light = AttributeProperty(None, autocreate=False)

    # Permanently lit — room is never dark regardless of time/light sources
    always_lit = AttributeProperty(False, autocreate=False)

    # Weather shelter — None means "derive from terrain type"
    # True = sheltered (indoor building), False = exposed (outdoor)
    sheltered = AttributeProperty(None, autocreate=False)

    # Weather suppression — None means "derive from terrain type"
    # True = no weather at all (extra-planar / artificial sky / void),
    # False = forced weather-eligible regardless of terrain.
    subterranean = AttributeProperty(None, autocreate=False)

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

    # --- Sleep policy helpers ---

    def set_sleep_policy(self, policy):
        """Set sleep policy: 'none' or 'super'. Clear to restore default."""
        self.tags.clear(category="sleep_policy")
        self.tags.add(policy, category="sleep_policy")

    def get_sleep_policy(self):
        """Return sleep policy tag, or None (default = normal sleep)."""
        return self.tags.get(category="sleep_policy")

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
        """
        True for rooms with no weather at all.

        If subterranean is explicitly set (True/False), use that.
        Otherwise derive from terrain type: underground/dungeon = True,
        everything else = False.
        """
        explicit = self.subterranean
        if explicit is not None:
            return bool(explicit)
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

    @staticmethod
    def _is_lit_source(obj):
        """True if obj is a light source that is currently burning."""
        return (getattr(obj, "is_light_source", False)
                and getattr(obj, "is_lit", False))

    def _has_light_source_in_room(self):
        """
        Check whether anything is lighting this room, for everyone in it.

        Light does not care who owns it. A torch on the floor, a torch in
        a hand and the light spell on someone's shoulder all light the
        room for every occupant alike — four in a dungeon with one lantern
        between them can all see.

        The reach into an actor's contents is deliberately one level deep
        and gated on ``p_living``. That excludes chests, sacks and dropped
        packs, so a lantern shut inside one stays dark, and it excludes
        corpses, so the torch on a body you just dropped has to be looted
        before it lights anything. A lantern inside a backpack inside a
        character does not count either, for the same reason as the chest.
        """
        for obj in self.contents:
            if self._is_lit_source(obj):
                return True
            # Light spell on a character illuminates the room for everyone
            if hasattr(obj, "has_effect") and obj.has_effect("light_spell"):
                return True
            if p_living(obj, None) and any(
                    self._is_lit_source(carried) for carried in obj.contents):
                return True
        return False

    def _dark_ignoring_darkvision(self):
        """
        Return True if this room lacks light, for anyone without DARKVISION.

        Same checks as is_dark(), minus the looker's own DARKVISION —
        used both by is_dark() and by seeing_via_darkvision() to tell
        "genuinely lit" apart from "dark, but seen through darkvision".

        Takes no looker: light is a property of the room, and the only
        thing that varies by observer is darkvision, which is is_dark()'s
        business.
        """
        # Permanently lit rooms are never dark
        if self.always_lit:
            return False

        from typeclasses.scripts.day_night_service import get_time_of_day

        # Natural light rooms are lit during light phases
        if self.has_natural_light and get_time_of_day().is_light:
            return False

        # Any light in the room — on the floor, in a hand, or on a
        # shoulder. Carried light is genuine light, not vision, so it
        # answers here rather than per-looker.
        if self._has_light_source_in_room():
            return False

        return True

    def is_dark(self, looker=None):
        """
        Return True if this room is currently dark for the given looker.

        A room is NOT dark if any of:
            - It is permanently lit (always_lit)
            - It has natural light and the current phase is a light phase
            - A lit light source exists in the room — a lamp post, a
              dropped torch, or one carried by anyone standing in it
            - The looker has DARKVISION
        """
        if not self._dark_ignoring_darkvision():
            return False

        if (
            looker
            and hasattr(looker, "has_condition")
            and looker.has_condition(Condition.DARKVISION)
        ):
            return False

        return True

    def seeing_via_darkvision(self, looker=None):
        """
        Return True if the room is dark but the looker sees it via DARKVISION.

        Used to tag the room name (Dark) for darkvision lookers, so they
        experience the darkness mechanic instead of it being invisible to
        them, and can anticipate when non-darkvision companions can't see.
        """
        if not looker or not hasattr(looker, "has_condition"):
            return False
        return (
            looker.has_condition(Condition.DARKVISION)
            and self._dark_ignoring_darkvision()
        )

    # Naming is UnseenNameMixin's job — see unseen_name above.

    def at_object_receive(self, moved_obj, source_location, **kwargs):
        """Fire quest events and tell the room something entered.

        The mob arrival dispatcher. Mobs hear it through
        ``at_new_arrival``.

        The notification is gated on perception, asked once per recipient
        with the arriver as the thing being perceived. This is the push
        side of the same question ``get_targets_in_room`` answers when a
        mob looks around: without it, a mob attacks an invisible player
        it walked past a moment ago without noticing.

        ``p_can_perceive`` rather than ``p_can_see``, deliberately.
        Concealment excludes — a hidden or invisible arrival is not
        announced at all. Darkness does not: someone walking in makes
        noise, so an unlit room still gets the notification. What a
        recipient can work out about an arrival it cannot see is the
        behaviour's problem, not the dispatcher's — which is why the
        sight half lives in ``at_llm_player_arrive``, where an NPC that
        cannot see chooses to challenge rather than greet.

        The counters come with the predicate: a mob holding DETECT_INVIS
        is still told about an invisible arrival, and one under
        true_sight about a hidden one.

        The LLM NPC half of the same event —
        ``at_llm_player_arrive`` — is dispatched from
        ``FCMCharacter.at_post_move`` instead, behind an identical
        ``p_can_perceive`` gate. Evennia calls this hook *before*
        ``at_post_move``, and ``at_post_move`` is where the arriving
        player's ``look`` happens, so a greeting sent from here prints
        above the room the player just walked into. The two hooks are
        the same event and the gate must stay identical in both places
        — change one, change the other.
        """
        super().at_object_receive(moved_obj, source_location, **kwargs)
        if self.quest_tags and hasattr(moved_obj, "quests"):
            self.fire_quest_event(moved_obj, "enter_room")

        for obj in self.contents:
            if obj is moved_obj:
                continue
            if not p_can_perceive(moved_obj, obj):
                continue
            if hasattr(obj, "at_new_arrival"):
                obj.at_new_arrival(moved_obj)

    def msg_contents(self, text=None, exclude=None, from_obj=None, mapping=None,
                     raise_funcparse_errors=False, **kwargs):
        """
        Override to filter room messages by whether ``from_obj`` is
        concealed from each recipient.

        Both concealment axes are asked, because ``from_obj`` may be an
        actor or an object:

        - ``p_actor_visible_to`` — HIDDEN actors need ``true_sight``,
          INVISIBLE actors need ``DETECT_INVIS``.
        - ``p_object_visible_to`` — a door or fixture composing
          ``HiddenObjectMixin`` / ``InvisibleObjectMixin``.

        Each predicate passes anything outside its own domain through
        untouched, so an actor is gated only by the first and a door only
        by the second.

        Operands are in messaging order — ``from_obj`` is the thing being
        seen, the recipient is the observer. Targeting asks the same
        predicates the other way round.
        """
        if from_obj is not None:
            exclude = list(make_iter(exclude)) if exclude else []
            for obj in self.contents:
                if obj in exclude:
                    continue
                if not (p_actor_visible_to(from_obj, obj)
                        and p_object_visible_to(from_obj, obj)):
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

    def msg_contents_with_invis_alt(self, normal_msg, invis_msg, from_obj,
                                    exclude=None, mapping=None):
        """
        Send a room message with alternate text for those who can't see the actor.

        Recipients who can see ``from_obj`` get ``normal_msg``; those who
        cannot get ``invis_msg``. ``from_obj`` is always excluded.

        What an observer receives depends only on **whether** they can see
        the actor, never on **why** they can't — hidden and invisible
        produce the same experience, and a future concealment cause gets
        the same treatment for free. ``p_actor_visible_to`` is the
        single source of that answer.

        Both messages go through ``super().msg_contents``, so each keeps
        its funcparser handling ($You() / $conj()). That matters for the
        alt: ``get_display_name`` already renders the actor as "Someone"
        for anyone who can't see them, so a caller can pass the *same*
        template as both arguments and get correct anonymised grammar
        without authoring a second string.
        """
        exclude = list(make_iter(exclude)) if exclude else []
        if from_obj and from_obj not in exclude:
            exclude.append(from_obj)

        unseeing = []
        if from_obj is not None:
            unseeing = [
                obj for obj in self.contents
                if obj not in exclude
                and not p_actor_visible_to(from_obj, obj)
            ]

        if unseeing:
            seeing = [obj for obj in self.contents if obj not in exclude
                      and obj not in unseeing]
            super().msg_contents(
                invis_msg, exclude=exclude + seeing, from_obj=from_obj,
                mapping=mapping,
            )

        super().msg_contents(
            normal_msg, exclude=exclude + unseeing, from_obj=from_obj,
            mapping=mapping,
        )

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

        parts = []
        header = self.get_display_header(looker, **kwargs)
        if header:
            parts.append(header)

        # Sight is a property of the looker, so it is asked once here and
        # the sections below share the answer.
        sighted = not looker_is_blind(looker)

        # ── Room name (cyan) ───────────────────────────────────────
        # Always shown. get_display_name anonymises it for itself, so an
        # unseen room names itself "Somewhere" — or whatever its own
        # unseen_name says. Only the decorations are sight-only: where
        # you are standing, and the darkvision tag.
        char_height = looker.room_vertical_position
        formatted_name = self.get_display_name(looker, **kwargs)

        if sighted:
            extra = self.get_extra_display_name_info(looker, **kwargs)
            if extra:
                formatted_name = f"{formatted_name} {extra}"

            if char_height == 0 and self.max_depth < 0:
                formatted_name = f"{formatted_name}   (Swimming)"
            elif char_height < 0:
                formatted_name = f"{formatted_name}   (Underwater)"
            elif char_height > 0:
                formatted_name = f"{formatted_name}   (Flying)"

            if self.seeing_via_darkvision(looker):
                formatted_name = f"{formatted_name}   (Dark)"

        parts.append(f"|c{formatted_name}|n")

        # ── Description, exits — sight only ────────────────────────
        # The description names and describes the place, and you cannot
        # pick out a doorway across an unlit room. Things and characters
        # follow below for everyone — each anonymises for itself, so an
        # unlit room reads as shapes you cannot identify, not as empty.
        if sighted:
            # ── Description (default color) — respect brief mode ────
            show_desc = ignore_brief or not getattr(looker, "brief_mode", False)
            if show_desc:
                desc = self.get_display_desc(looker, **kwargs)
                # Add height prefix only when vert_descriptions didn't
                # provide a height-specific description (those already
                # describe the scene from the correct perspective).
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

            # ── Auto-exits (cyan, compact) ─────────────────────────
            # Sight only: you cannot pick out a doorway across an unlit
            # room, even though open_exits still lets you grope your way
            # through one.
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
            if p_object_visible_to(ex, looker)
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
        Returns empty string when no characters can be perceived.

        Lighting is not this method's decision. A looker who cannot see
        still perceives that bodies are present, so every perceived
        character is rendered — each through ``get_display_name``, which
        anonymises to "Someone" when the looker is blind or the room is
        dark for them. What is withheld alongside the name is everything
        else that would identify them: the room description, the
        alignment aura, and the height and concealment tags.
        """
        characters = self.filter_visible(
            self.contents_get(content_type="character"), looker, **kwargs
        )

        # Concealment (HIDDEN / INVISIBLE) and height gating are one
        # question — whether this looker can perceive that character.
        visible = [char for char in characters if p_can_perceive(char, looker)]

        if not visible:
            return ""

        # Sight is a property of the looker, not of any one character, so
        # it is the same answer for everyone here — asked once rather than
        # once per candidate, since is_dark scans the room to answer it.
        sighted = not looker_is_blind(looker)

        # Check if looker can see alignment auras. Sighted, because an
        # aura tells you what someone is — the same identifying detail the
        # anonymised name is withholding.
        looker_detects_alignment = (
            sighted
            and hasattr(looker, "has_effect")
            and looker.has_effect("detect_alignment")
        )

        lines = []
        for char in visible:
            # Three distinct renderings. A looker who cannot see gets the
            # anonymised name and a verb of its own; one who can gets the
            # room description, or the plain name where there is none.
            if not sighted:
                # No "else" — unseen_name is settable, so this has to read
                # for "A mysterious presence" as well as for "Someone".
                name = char.get_display_name(looker, **kwargs)
                line = f"{name} is in the room."
            elif hasattr(char, "get_room_description"):
                line = char.get_room_description()
            else:
                line = char.get_display_name(looker, **kwargs)
            # Prepend alignment tag if looker has Detect Alignment
            if looker_detects_alignment and char != looker:
                alignment = getattr(char, "alignment_score", 0)
                if alignment <= -300:
                    line = f"|r(Evil)|n {line}"
                elif alignment >= 300:
                    line = f"|Y(Good)|n {line}"
                else:
                    line = f"|w(Neutral)|n {line}"
            # Append height tags. Where someone is standing is something
            # you can see, so a looker who cannot gets none of it.
            if sighted:
                char_height = getattr(char, "room_vertical_position", 0)
                if char_height > 0:
                    line += " (Flying)"
                elif char_height < 0:
                    line += " (Underwater)"
                elif self.max_depth < 0:
                    line += " (Swimming)"
            # Append visibility tags. These say how you are managing to
            # perceive someone concealed — meaningless to a looker who is
            # not perceiving them by sight at all.
            if sighted and hasattr(char, "has_condition"):
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
        state and conditions. Returns empty string when nothing can be
        perceived.

        Lighting is not this method's decision — see get_display_characters.
        """
        # sort and handle same-named things
        things = self.filter_visible(self.contents_get(content_type="object"), looker, **kwargs)

        # Concealment (hidden / invisible mixins) and height gating are
        # one question — whether this looker can perceive that object.
        things = [thing for thing in things if p_can_perceive(thing, looker)]

        # Sight is a property of the looker, so it is the same answer for
        # everything here — asked once rather than once per candidate.
        sighted = not looker_is_blind(looker)

        # Separate items with ground descriptions (full sentences) from
        # bare-name items (grouped and comma-separated). A ground
        # description names and describes the item, so a looker who cannot
        # see gets none of them — everything falls through to the
        # anonymising name instead.
        ground_sentences = []
        bare_things = []
        for thing in things:
            gdesc = getattr(thing, "ground_description", "") if sighted else ""
            if gdesc:
                ground_sentences.append(gdesc)
            else:
                bare_things.append(thing)

        if not sighted:
            # Collapsed rather than one line each: item counts vary far
            # more than character counts, and a room of twelve dropped
            # things would otherwise repeat itself twelve times. The
            # singular keeps the item's own word, so a settable
            # unseen_name still reads ("A strange shape is on the ground.").
            if not bare_things:
                thing_names = ""
            elif len(bare_things) == 1:
                # Capitalised here rather than in unseen_name, which stays
                # lowercase so it still reads mid-sentence ("you bump into
                # something"). Any settable word gets the same treatment.
                name = bare_things[0].get_display_name(looker, **kwargs)
                name = name[0].upper() + name[1:] if name else name
                thing_names = f"{name} is on the ground."
            else:
                thing_names = "Several things are on the ground."
        else:
            grouped_things = defaultdict(list)
            for thing in bare_things:
                grouped_things[thing.get_display_name(looker, **kwargs)].append(thing)

            names = []
            for thingname, thinglist in sorted(grouped_things.items()):
                nthings = len(thinglist)
                thing = thinglist[0]
                singular, plural = thing.get_numbered_name(nthings, looker, key=thingname)
                names.append(singular if nthings == 1 else plural)
            thing_names = iter_to_str(names, endsep=_(", and"))

        # Append any fungibles (gold, resources) visible in the room.
        # Sighted only — loose coin on the floor is spotted by eye, and
        # the display names and counts it besides.
        fungible_display = self.get_room_fungible_display() if sighted else ""

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
