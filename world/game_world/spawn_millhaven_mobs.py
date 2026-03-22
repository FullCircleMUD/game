"""
Create zone spawn scripts and boss mobs for the Millhaven game world.

Run AFTER the Millhaven world builder has created rooms with mob_area tags.
Each zone gets a ZoneSpawnScript that reads its JSON config and maintains
mob populations automatically. Unique boss mobs are spawned directly
(they manage their own respawn via is_unique=True).

Usage (from Evennia):
    @py from world.game_world.spawn_millhaven_mobs import spawn_millhaven_mobs; spawn_millhaven_mobs()
"""

from evennia import ObjectDB
from evennia.utils import create

from typeclasses.scripts.zone_spawn_script import ZoneSpawnScript


def _find_room(key):
    """Find a room by key. Returns first match or None."""
    results = ObjectDB.objects.filter(
        db_key__iexact=key, db_typeclass_path__contains="room"
    )
    if results.exists():
        return results.first()
    results = ObjectDB.objects.filter(db_key__iexact=key)
    return results.first() if results.exists() else None


def spawn_millhaven_mobs():
    """Create zone spawn scripts and boss mobs for all Millhaven zones."""
    print("--- Creating Millhaven Spawn Scripts ---")

    script = ZoneSpawnScript.create_for_zone("millhaven_farms")
    if script:
        print(f"  Created {script.key} ({len(script.db.spawn_table)} rules)")
    else:
        print("  [!] Failed to create millhaven_farms spawn script")

    script = ZoneSpawnScript.create_for_zone("millhaven_woods")
    if script:
        print(f"  Created {script.key} ({len(script.db.spawn_table)} rules)")
    else:
        print("  [!] Failed to create millhaven_woods spawn script")

    script = ZoneSpawnScript.create_for_zone("millhaven_sewers")
    if script:
        print(f"  Created {script.key} ({len(script.db.spawn_table)} rules)")
    else:
        print("  [!] Failed to create millhaven_sewers spawn script")

    script = ZoneSpawnScript.create_for_zone("millhaven_mine")
    if script:
        print(f"  Created {script.key} ({len(script.db.spawn_table)} rules)")
    else:
        print("  [!] Failed to create millhaven_mine spawn script")

    script = ZoneSpawnScript.create_for_zone("millhaven_southern")
    if script:
        print(f"  Created {script.key} ({len(script.db.spawn_table)} rules)")
    else:
        print("  [!] Failed to create millhaven_southern spawn script")

    # ── Boss Mobs ──
    _spawn_bosses()

    print("--- Millhaven spawn script creation complete ---")


def _spawn_bosses():
    """Spawn unique boss mobs in their fixed locations."""
    print("  --- Spawning Boss Mobs ---")

    # Kobold Chieftain in the Kobold Warren
    room = _find_room("Kobold Warren")
    if room:
        boss = create.create_object(
            "typeclasses.actors.mobs.kobold_chieftain.KoboldChieftain",
            key="the Kobold Chieftain",
            location=room,
        )
        boss.db.desc = (
            "A squat but powerfully built kobold wearing a crude crown of "
            "copper wire and rat bones. Its eyes gleam with cunning malice, "
            "and it grips a notched short sword in one clawed hand. Scars "
            "crisscross its scaled hide — this one has survived where "
            "others fell."
        )
        boss.start_ai()
        print(f"  Spawned 'the Kobold Chieftain' in {room.key} ({room.dbref})")
    else:
        print("  [!] Room 'Kobold Warren' not found — skipping Kobold Chieftain")

    # Gnoll Warlord in the Gnoll Camp
    room = _find_room("Gnoll Camp")
    if room:
        boss = create.create_object(
            "typeclasses.actors.mobs.gnoll_warlord.GnollWarlord",
            key="the Gnoll Warlord",
            location=room,
        )
        boss.db.desc = (
            "A towering gnoll stands head and shoulders above its kin, its "
            "mottled fur streaked with warpaint in red and black. A massive "
            "greataxe rests across its shoulders, its blade stained dark. "
            "The warlord's yellow eyes burn with feral intelligence, and a "
            "necklace of teeth and finger bones rattles at its throat."
        )
        boss.start_ai()
        print(f"  Spawned 'the Gnoll Warlord' in {room.key} ({room.dbref})")
    else:
        print("  [!] Room 'Gnoll Camp' not found — skipping Gnoll Warlord")
