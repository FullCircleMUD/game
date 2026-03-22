"""
Spawn combat test items into the arena rooms.

Run AFTER test_area_arena() has created the 3x3 arena grid.
Places weapons in key rooms and scatters gold across corners
so players can pick up gear and fight.

Usage (from Evennia):
    @py from world.test_world.test_area_combat import test_area_combat; test_area_combat()
"""

from evennia import ObjectDB, create_object

from typeclasses.world_objects.xp_button import XPButton
from world.test_world.spawn_test_items import spawn_nft_item, _find_room


def test_area_combat():
    """Spawn weapons and gold into the arena for combat testing."""

    print("\n=== Spawning Arena Combat Items ===\n")

    # --- Big Red Button in the Centre room (XP test tool) ---
    centre = _find_room("The Arena (Centre)")
    if centre:
        existing = [o for o in centre.contents if o.key == "Big Red Button"]
        if not existing:
            create_object(XPButton, key="Big Red Button", location=centre)
            print("  Placed Big Red Button in Arena Centre")
        else:
            print("  Big Red Button already exists in Arena Centre")

        # --- Weapons in the Centre room (main fighting pit) ---
        spawn_nft_item("Training Longsword", centre)
        spawn_nft_item("Training Dagger", centre)
    else:
        print("  ! Arena Centre not found")

    # --- Weapons on the weapon racks (West room) ---
    west = _find_room("The Arena (West)")
    if west:
        spawn_nft_item("Training Shortsword", west)
        spawn_nft_item("Training Bow", west)
    else:
        print("  ! Arena West not found")

    # --- A spear by the beast cages (Northeast) ---
    ne = _find_room("The Arena (Northeast)")
    if ne:
        spawn_nft_item("Spear", ne)
    else:
        print("  ! Arena Northeast not found")

    # --- Gold scattered in corners ---
    print("\n--- Arena Gold ---\n")

    for room_key, amount in [
        ("The Arena (Northwest)", 15),
        ("The Arena (Southeast)", 15),
        ("The Arena (Southwest)", 10),
    ]:
        room = _find_room(room_key)
        if room:
            room.receive_gold_from_reserve(amount)
            print(f"  Added {amount} gold to {room.key}")
        else:
            print(f"  ! {room_key} not found")

    print("\n=== Arena Combat Items Done ===\n")
