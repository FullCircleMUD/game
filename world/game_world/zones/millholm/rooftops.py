"""
Millholm Rooftops — the secret district above the craft quarter.

A 3x3 grid of rooftop rooms accessible via a hidden drainpipe in a
back alley, a fly-up point from Artisan's Way, or a hidden wardrobe
passage from Gareth Stonefield's bedroom.

Dark at night, weather-exposed, no lampposts. A thief's paradise.

Cross-district connections (drainpipe, fly exits, Gareth's wardrobe)
are created in soft_deploy.py after both town and rooftops are built.

Usage:
    from world.game_world.zones.millholm.rooftops import build_millholm_rooftops
    build_millholm_rooftops()
"""

from evennia import create_object

from enums.terrain_type import TerrainType
from typeclasses.terrain.rooms.room_base import RoomBase
from typeclasses.terrain.exits.exit_vertical_aware import ExitVerticalAware
from utils.exit_helpers import connect


# ── Zone / district constants ─────────────────────────────────────────
ZONE = "millholm"
DISTRICT = "millholm_rooftops"


def build_millholm_rooftops():
    """Build the Millholm Rooftops district and return a dict of rooms."""
    rooms = {}

    print("  Building rooftop rooms...")

    # ══════════════════════════════════════════════════════════════════
    # SOUTH ROW — Artisan's Way roofline
    # ══════════════════════════════════════════════════════════════════

    rooms["rooftops_w3"] = create_object(
        RoomBase,
        key="Cottage Rooftop",
        attributes=[
            ("desc",
             "A small, homely rooftop above what must be a private "
             "dwelling. The tiles are patched but tidy, and a thin "
             "wisp of hearth smoke curls from a modest chimney. A "
             "clothes line is strung between the chimney and a wooden "
             "post, a few forgotten pegs still clinging to the rope. "
             "A window box of dead herbs sits on a ledge — someone "
             "tried to grow something up here once. The rooftop of the "
             "smithy is visible to the east, its chimney belching "
             "smoke. Westward the roofline drops away toward the edge "
             "of town."),
            ("details", {
                "chimney": (
                    "A modest stone chimney, well-mortared and drawing "
                    "cleanly. The faint smell of wood smoke and pipe "
                    "tobacco drifts from the flue."
                ),
                "clothes line": (
                    "A length of hemp rope strung between the chimney "
                    "and a wooden post. A few wooden pegs are still "
                    "attached, weathered grey. Whatever was hung here "
                    "has long since been taken in."
                ),
                "herbs": (
                    "A wooden window box on the roof ledge, filled with "
                    "dry soil and the brown stalks of dead herbs. Looks "
                    "like rosemary and thyme, once upon a time."
                ),
            }),
        ],
    )

    rooms["rooftops_w2"] = create_object(
        RoomBase,
        key="Smithy Rooftop",
        attributes=[
            ("desc",
             "The broad, solid roof of Hendricks' smithy. Heat radiates "
             "up through the tiles from the forge below, keeping the "
             "slate warm even in the rain. A stout brick chimney belches "
             "grey smoke in steady puffs, and the ring of hammer on "
             "anvil drifts up through the flue. The roof is well "
             "maintained — tiles neatly aligned, gutters clear, mortar "
             "freshly pointed. Hendricks clearly takes as much pride in "
             "his building as his craft. Soot stains fan out from the "
             "chimney in the direction of the prevailing wind."),
            ("details", {
                "chimney": (
                    "A solid brick chimney, wide enough to fit a man "
                    "inside — not that you'd want to. Waves of heat "
                    "pour from the top, and the acrid smell of hot metal "
                    "and coal smoke hangs thick around it."
                ),
                "tiles": (
                    "Well-laid slate tiles, warm to the touch from the "
                    "forge heat below. Not a single one cracked or "
                    "missing. Old Hendricks runs a tight ship."
                ),
                "soot": (
                    "A fan of dark soot stains spreads across the tiles "
                    "downwind of the chimney. Years of forge smoke have "
                    "left their mark."
                ),
                "gutters": (
                    "Iron gutters, recently cleared. A few bent nails "
                    "and a scrap of leather have collected in the corner "
                    "where the downpipe meets the gutter — debris from "
                    "the workshops below."
                ),
            }),
        ],
    )

    rooms["rooftops_w1"] = create_object(
        RoomBase,
        key="Sagging Rooftop",
        attributes=[
            ("desc",
             "The roof of an abandoned workshop, its ridge sagging in "
             "the middle where the timbers have started to give way. "
             "Slate tiles are missing in patches, exposing tar-blackened "
             "felt beneath. A cold chimney stack leans at an angle, its "
             "flue choked with old birds' nests. The remnants of a "
             "ventilation cowl — the kind used to draw fumes from a "
             "forge or tannery — rusts quietly near the eaves. From "
             "here the rooftops of the craft quarter stretch away in "
             "every direction, a jumble of ridgelines, gutters, and "
             "chimney pots. A drainpipe leads back down to the alley "
             "below."),
            ("details", {
                "chimney": (
                    "A squat chimney stack, leaning a few degrees off "
                    "true. The flue is stuffed with twigs and straw — "
                    "jackdaws have been nesting in it for years. No "
                    "smoke has come from this chimney in a long time."
                ),
                "tiles": (
                    "Grey slate tiles, many cracked or missing entirely. "
                    "Where they've gone you can see the tarred felt "
                    "beneath, soft and treacherous underfoot. Step "
                    "carefully."
                ),
                "cowl": (
                    "A rusted metal ventilation cowl, the rotating kind "
                    "once used to draw smoke and fumes out of a workshop "
                    "below. It's seized solid with rust now, but you can "
                    "still see the soot stains around its base."
                ),
                "ridge": (
                    "The roof ridge sags visibly in the middle. The "
                    "timbers beneath must be rotting. It holds your "
                    "weight, but only just."
                ),
            }),
        ],
    )

    # ══════════════════════════════════════════════════════════════════
    # MIDDLE ROW — between Artisan's Way and Old Trade Way rooflines
    # ══════════════════════════════════════════════════════════════════

    rooms["rooftops_ridge"] = create_object(
        RoomBase,
        key="Narrow Ridge",
        attributes=[
            ("desc",
             "A spine of ridge tiles runs along the peak of a "
             "steeply pitched roof, offering a narrow but traversable "
             "path. The tiles on either side drop away at a sharp "
             "angle — a slip here would send you sliding to the "
             "gutters, or worse. The ridge is worn smooth by weather "
             "and by feet — someone walks this route regularly. Rope "
             "has been tied between two chimney pots at either end, "
             "strung low as a makeshift handrail."),
            ("details", {
                "rope": (
                    "A length of tarred rope strung between chimney "
                    "pots at waist height. It's taut and recently "
                    "replaced — the knots are neat and the tar is "
                    "still tacky. Someone maintains this."
                ),
                "tiles": (
                    "Ridge tiles, semi-circular and moss-covered, "
                    "forming a narrow walkway along the roof peak. "
                    "The mortar between them is crumbling in places. "
                    "Every few steps one shifts slightly underfoot."
                ),
                "view": (
                    "From the ridge you can see across the whole "
                    "craft quarter — chimney smoke, washing lines, "
                    "the glint of the smithy's forge light, and "
                    "beyond the rooftops, the dark line of the "
                    "woods to the east."
                ),
            }),
        ],
    )

    rooms["rooftops_chimney"] = create_object(
        RoomBase,
        key="Chimney Forest",
        attributes=[
            ("desc",
             "A cluster of chimney stacks rises from the junction of "
             "three rooflines, creating a forest of brick columns. "
             "Smoke curls from most of them — the workshops below are "
             "busy. The warmth radiating from the bricks makes this "
             "a sheltered spot, and someone has taken advantage: a "
             "bedroll is tucked behind the largest chimney, along "
             "with an empty bottle and a heel of stale bread. The "
             "flat area between the chimneys is large enough to sit "
             "comfortably, hidden from view on all sides."),
            ("details", {
                "bedroll": (
                    "A threadbare bedroll, patched and re-patched, "
                    "tucked into the warmest spot between two chimney "
                    "stacks. Someone has been sleeping up here "
                    "regularly — the blanket is worn smooth in the "
                    "shape of a body."
                ),
                "bottle": (
                    "An empty green glass bottle, the cheap kind "
                    "used for rough cider. The label has been "
                    "scratched off."
                ),
                "bread": (
                    "A heel of bread, hard as a rock and spotted "
                    "with mould. The pigeons haven't even touched it."
                ),
                "chimneys": (
                    "A dozen chimney stacks of varying heights and "
                    "states of repair. Some are warm to the touch, "
                    "others cold and disused. Soot stains streak "
                    "down the brickwork in dark fans."
                ),
            }),
        ],
    )

    rooms["rooftops_gutter"] = create_object(
        RoomBase,
        key="Rain Gutter Walkway",
        attributes=[
            ("desc",
             "A narrow lead-lined gutter runs between two steeply "
             "pitched roofs, forming a precarious walkway barely wide "
             "enough for one person. Rainwater pools in the sagging "
             "sections, and pigeon droppings coat every surface. The "
             "walls of the buildings rise sharply on either side, "
             "blocking the wind but funnelling sound — you can hear "
             "conversations from the rooms below, muffled but "
             "distinct. A plank has been laid across a gap where the "
             "gutter has rusted through."),
            ("details", {
                "plank": (
                    "A rough wooden plank, maybe three feet long, "
                    "bridging a gap in the gutter where the lead has "
                    "rusted away entirely. It bows slightly under "
                    "pressure. Someone has nailed a cleat to each end "
                    "to stop it sliding."
                ),
                "gutter": (
                    "A wide lead-lined gutter, green with verdigris "
                    "and clogged with dead leaves, pigeon feathers, "
                    "and unidentifiable muck. Water pools in the low "
                    "spots. It creaks underfoot."
                ),
                "pigeons": (
                    "Fat grey pigeons roost in every available nook, "
                    "cooing and shuffling. They seem completely "
                    "unbothered by your presence."
                ),
            }),
        ],
    )

    # ══════════════════════════════════════════════════════════════════
    # NORTH ROW — Old Trade Way roofline
    # ══════════════════════════════════════════════════════════════════

    rooms["rooftops_flat"] = create_object(
        RoomBase,
        key="Flat Roof",
        attributes=[
            ("desc",
             "A broad, flat section of roof behind a low parapet wall, "
             "once used for drying laundry or curing hides. The surface "
             "is tarred canvas stretched over planking, soft and giving "
             "underfoot. Empty wooden frames that once held drying racks "
             "stand at angles, and a few rusted iron hooks are driven "
             "into the parapet. Someone has scratched a crude map into "
             "the tar with a knife point — rooftop routes marked with "
             "arrows and X's."),
            ("details", {
                "map": (
                    "A crude map scratched into the tarred surface "
                    "with a knife. It shows a rough layout of the "
                    "rooftops — squares for flat areas, zigzag lines "
                    "for ridges, and arrows marking routes between "
                    "them. Several spots are marked with an X. One "
                    "X is labelled 'stash' in a childish hand."
                ),
                "parapet": (
                    "A low brick wall running around the edge of the "
                    "flat roof, barely knee-height. It would stop you "
                    "rolling off in your sleep but not much else. "
                    "Pigeons perch along the top."
                ),
                "hooks": (
                    "Rusted iron hooks driven into the mortar of the "
                    "parapet. They once held ropes for drying racks "
                    "or washing lines. A few still have scraps of "
                    "cord tied to them."
                ),
            }),
        ],
    )

    rooms["rooftops_gareth"] = create_object(
        RoomBase,
        key="Merchant's Rooftop",
        attributes=[
            ("max_height", 0),
            ("desc",
             "The highest rooftop in the craft quarter — a steeply "
             "pitched roof of expensive clay tiles, dark red and neatly "
             "laid. A decorative iron weathervane in the shape of a "
             "ship turns lazily at the apex. The mortar is fresh, the "
             "gutters are copper, and the chimney is capped with an "
             "ornate terracotta pot. Whoever lives below has money and "
             "isn't afraid to show it. From this vantage point the "
             "entire roofscape is visible — the sagging workshop to "
             "the southeast, the smithy's smoking chimney to the south, "
             "and the flat roofs of the trade road buildings to the "
             "west. A small dormer window is set into the tiles below "
             "the ridge, its shutters latched from the inside."),
            ("details", {
                "weathervane": (
                    "An iron weathervane wrought in the shape of a "
                    "merchant ship under full sail. The metalwork is "
                    "fine — this wasn't cheap. It creaks softly as it "
                    "turns in the wind."
                ),
                "tiles": (
                    "Dark red clay tiles, uniform and professionally "
                    "laid. Not a single one cracked or missing. The "
                    "contrast with the surrounding rooftops — patched "
                    "slate, tarred felt, missing tiles — is stark."
                ),
                "window": (
                    "A small dormer window set into the roof slope, "
                    "its glass panes clean and its shutters painted. "
                    "The shutters are latched from the inside. You "
                    "can't see in, but faint lamplight glows around "
                    "the edges."
                ),
                "gutters": (
                    "Copper gutters, green with patina but clear of "
                    "debris. Downpipes run neatly to the ground. "
                    "Everything about this roof says 'money well spent.'"
                ),
            }),
        ],
    )

    rooms["rooftops_store"] = create_object(
        RoomBase,
        key="General Store Rooftop",
        attributes=[
            ("desc",
             "A broad, flat-topped roof above the general store, its "
             "surface a patchwork of tarred felt and weighted-down "
             "planks. Crates and empty sacks have been left up here, "
             "along with a few broken broom handles and a coil of "
             "fraying rope. The flat roof makes for easy footing "
             "compared to the pitched tiles of the neighbouring "
             "buildings. A hatch in the roof has been nailed shut from "
             "above — the shopkeeper below has no idea anyone comes up "
             "here. The rooftops of the craft quarter stretch away to "
             "the south."),
            ("details", {
                "hatch": (
                    "A wooden roof hatch, nailed shut with heavy iron "
                    "nails driven in from above. The shopkeeper below "
                    "probably thinks it's permanently sealed. Someone "
                    "up here wanted to make sure of that."
                ),
                "crates": (
                    "Empty wooden crates, stamped with the marks of "
                    "various merchants. Someone has been storing things "
                    "up here — or at least using the crates as seats."
                ),
                "rope": (
                    "A coil of fraying hemp rope, the kind used to "
                    "bundle cargo. It looks like it's been cut rather "
                    "than untied."
                ),
            }),
        ],
    )

    print(f"  Created {len(rooms)} rooftop rooms.")

    # ══════════════════════════════════════════════════════════════════
    # EXITS — internal rooftop grid connections
    # ══════════════════════════════════════════════════════════════════

    exit_count = 0

    # South row
    connect(rooms["rooftops_w3"], rooms["rooftops_w2"], "east")
    connect(rooms["rooftops_w2"], rooms["rooftops_w1"], "east")
    # Middle row
    connect(rooms["rooftops_ridge"], rooms["rooftops_chimney"], "east")
    connect(rooms["rooftops_chimney"], rooms["rooftops_gutter"], "east")
    # North row
    # Gareth's roof is higher — need height 1 to reach it from flat roof
    exit_flat_gareth = create_object(
        ExitVerticalAware,
        key="Merchant's Rooftop",
        location=rooms["rooftops_flat"],
        destination=rooms["rooftops_gareth"],
    )
    exit_flat_gareth.set_direction("east")
    exit_flat_gareth.required_min_height = 1
    exit_flat_gareth.required_max_height = 1
    exit_flat_gareth.arrival_heights = {1: 0}

    exit_gareth_flat = create_object(
        ExitVerticalAware,
        key="Flat Roof",
        location=rooms["rooftops_gareth"],
        destination=rooms["rooftops_flat"],
    )
    exit_gareth_flat.set_direction("west")
    exit_gareth_flat.arrival_heights = {0: 1}
    # Gareth's roof is one level higher — height-routed from store
    exit_store_gareth = create_object(
        ExitVerticalAware,
        key="Merchant's Rooftop",
        location=rooms["rooftops_store"],
        destination=rooms["rooftops_gareth"],
    )
    exit_store_gareth.set_direction("west")
    exit_store_gareth.required_min_height = 1
    exit_store_gareth.required_max_height = 1
    exit_store_gareth.arrival_heights = {1: 0}

    exit_gareth_store = create_object(
        ExitVerticalAware,
        key="General Store Rooftop",
        location=rooms["rooftops_gareth"],
        destination=rooms["rooftops_store"],
    )
    exit_gareth_store.set_direction("east")
    exit_gareth_store.arrival_heights = {0: 1}
    # North-south connections
    connect(rooms["rooftops_w3"], rooms["rooftops_ridge"], "north")
    connect(rooms["rooftops_w2"], rooms["rooftops_chimney"], "north")
    connect(rooms["rooftops_w1"], rooms["rooftops_gutter"], "north")
    connect(rooms["rooftops_ridge"], rooms["rooftops_flat"], "north")
    # Gareth's roof is higher — need height 1 to reach it from chimney
    exit_chimney_gareth = create_object(
        ExitVerticalAware,
        key="Merchant's Rooftop",
        location=rooms["rooftops_chimney"],
        destination=rooms["rooftops_gareth"],
    )
    exit_chimney_gareth.set_direction("north")
    exit_chimney_gareth.required_min_height = 1
    exit_chimney_gareth.required_max_height = 1
    exit_chimney_gareth.arrival_heights = {1: 0}

    exit_gareth_chimney = create_object(
        ExitVerticalAware,
        key="Chimney Forest",
        location=rooms["rooftops_gareth"],
        destination=rooms["rooftops_chimney"],
    )
    exit_gareth_chimney.set_direction("south")
    exit_gareth_chimney.arrival_heights = {0: 1}
    connect(rooms["rooftops_gutter"], rooms["rooftops_store"], "north")
    exit_count += 24

    print(f"  Created {exit_count} rooftop exits.")

    # ══════════════════════════════════════════════════════════════════
    # TAGS — zone, district, terrain, properties
    # ══════════════════════════════════════════════════════════════════

    for room in rooms.values():
        room.tags.add(ZONE, category="zone")
        room.tags.add(DISTRICT, category="district")
        room.set_terrain(TerrainType.URBAN.value)
        room.sheltered = False  # weather-exposed
        # Dark at night — no always_lit, no lampposts

    print("  Tagged all rooftop rooms (zone, district, terrain, weather).")
    print("  Millholm Rooftops complete.\n")

    return rooms
