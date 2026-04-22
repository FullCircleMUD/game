"""
Create zone spawn scripts for the Millholm game world.

Run AFTER the Millholm world builder has created rooms with mob_area tags.
Each zone gets a ZoneSpawnScript that reads its JSON config and maintains
mob populations automatically — bosses included.

Usage (from Evennia):
    @py from world.game_world.spawn_millholm_mobs import spawn_millholm_mobs; spawn_millholm_mobs()
"""

from typeclasses.scripts.zone_spawn_script import ZoneSpawnScript


def spawn_millholm_mobs():
    """Create zone spawn scripts for all Millholm zones."""
    print("--- Creating Millholm Spawn Scripts ---")

    script = ZoneSpawnScript.create_for_zone("millholm_farms")
    if script:
        print(f"  Created {script.key} ({len(script.db.spawn_table)} rules)")
    else:
        print("  [!] Failed to create millholm_farms spawn script")

    script = ZoneSpawnScript.create_for_zone("millholm_woods")
    if script:
        print(f"  Created {script.key} ({len(script.db.spawn_table)} rules)")
    else:
        print("  [!] Failed to create millholm_woods spawn script")

    script = ZoneSpawnScript.create_for_zone("millholm_sewers")
    if script:
        print(f"  Created {script.key} ({len(script.db.spawn_table)} rules)")
    else:
        print("  [!] Failed to create millholm_sewers spawn script")

    script = ZoneSpawnScript.create_for_zone("millholm_mine")
    if script:
        print(f"  Created {script.key} ({len(script.db.spawn_table)} rules)")
    else:
        print("  [!] Failed to create millholm_mine spawn script")

    script = ZoneSpawnScript.create_for_zone("millholm_southern")
    if script:
        print(f"  Created {script.key} ({len(script.db.spawn_table)} rules)")
    else:
        print("  [!] Failed to create millholm_southern spawn script")

    script = ZoneSpawnScript.create_for_zone("millholm_cemetery")
    if script:
        print(f"  Created {script.key} ({len(script.db.spawn_table)} rules)")
    else:
        print("  [!] Failed to create millholm_cemetery spawn script")

    script = ZoneSpawnScript.create_for_zone("millholm_lake")
    if script:
        print(f"  Created {script.key} ({len(script.db.spawn_table)} rules)")
    else:
        print("  [!] Failed to create millholm_lake spawn script")

    script = ZoneSpawnScript.create_for_zone("millholm_town")
    if script:
        print(f"  Created {script.key} ({len(script.db.spawn_table)} rules)")
    else:
        print("  [!] Failed to create millholm_town spawn script")

    script = ZoneSpawnScript.create_for_zone("millholm_rooftops")
    if script:
        print(f"  Created {script.key} ({len(script.db.spawn_table)} rules)")
    else:
        print("  [!] Failed to create millholm_rooftops spawn script")

    print("--- Millholm spawn script creation complete ---")
