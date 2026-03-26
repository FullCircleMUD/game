"""
Spawn test items into the test world.

Run AFTER build_test_world() has created rooms.
Spawns one of every recipe scroll into its appropriate crafting room and adds
gold to key rooms. Resources are no longer pre-spawned — players
harvest them from RoomHarvesting rooms.

Usage (from Evennia):
    @py from world.test_world.spawn_test_items import spawn_test_items; spawn_test_items()
"""

from evennia import ObjectDB, create_object

from typeclasses.items.base_nft_item import BaseNFTItem
from typeclasses.world_objects.chest import WorldChest
from typeclasses.world_objects.key_item import KeyItem


def _find_room(key):
    """Find a room by key. Returns first match or None."""
    results = ObjectDB.objects.filter(db_key__iexact=key, db_typeclass_path__contains="room")
    if results.exists():
        return results.first()
    # fallback: search all objects
    results = ObjectDB.objects.filter(db_key__iexact=key)
    return results.first() if results.exists() else None


def spawn_nft_item(item_type_name, location):
    """
    Allocate a blank token, assign it an item type, and spawn into location.

    Uses BaseNFTItem factory methods — no direct service/model access.
    Returns the created Evennia object, or None on failure.
    """
    try:
        token_id = BaseNFTItem.assign_to_blank_token(item_type_name)
    except Exception as err:
        print(f"  Failed to assign blank token for '{item_type_name}': {err}")
        return None

    obj = BaseNFTItem.spawn_into(token_id, location)
    if obj:
        print(f"  Spawned '{item_type_name}' (NFT #{token_id}) in {location.key}")
    return obj


def _spawn_recipes(room_key, recipe_names):
    """Spawn a list of recipe scrolls into the given room."""
    room = _find_room(room_key)
    if not room:
        print(f"  ! {room_key} room not found — skipping {len(recipe_names)} recipes")
        return
    for name in recipe_names:
        spawn_nft_item(name, room)


def spawn_test_items():
    """Spawn test items and fungibles into the test world."""

    print("\n=== Spawning Test Items ===\n")

    # --- Carpentry recipes → Woodshop ---
    print("--- Carpentry Recipes ---\n")
    _spawn_recipes("Woodshop", [
        "Training Longsword Recipe",
        "Training Shortsword Recipe",
        "Training Dagger Recipe",
        "Training Bow Recipe",
        "Club Recipe",
        "Wooden Shield Recipe",
        "Shaft Recipe",
        "Haft Recipe",
        "Training Greatsword Recipe",
        "Wooden Torch Recipe",
    ])

    # --- Blacksmithing recipes → Blacksmith ---
    print("\n--- Blacksmithing Recipes ---\n")
    _spawn_recipes("blacksmith", [
        "Iron Longsword Recipe",
        "Iron Shortsword Recipe",
        "Iron Dagger Recipe",
        "Iron Hand Axe Recipe",
        "Spear Recipe",
        "Ironbound Shield Recipe",
        "Bronze Lantern Recipe",
    ])

    # --- Leatherworking recipes → Leathershop ---
    print("\n--- Leatherworking Recipes ---\n")
    _spawn_recipes("Leathershop", [
        "Leather Boots Recipe",
        "Leather Gloves Recipe",
        "Leather Belt Recipe",
        "Leather Cap Recipe",
        "Leather Pants Recipe",
        "Bridle Recipe",
        "Backpack Recipe",
        "Panniers Recipe",
        "Sling Recipe",
        "Leather Straps Recipe",
        "Leather Armor Recipe",
    ])

    # --- Tailoring recipes → Tailor ---
    print("\n--- Tailoring Recipes ---\n")
    _spawn_recipes("Tailor", [
        "Gambeson Recipe",
        "Coarse Robe Recipe",
        "Kippah Recipe",
        "Brown Corduroy Pants Recipe",
        "Bandana Recipe",
        "Cloak Recipe",
        "Veil Recipe",
        "Scarf Recipe",
        "Sash Recipe",
        "Warrior's Wraps Recipe",
    ])

    # --- Jewellery recipes → Jeweller ---
    print("\n--- Jewellery Recipes ---\n")
    _spawn_recipes("Jeweller", [
        "Pewter Ring Recipe",
        "Copper Ring Recipe",
        "Pewter Hoops Recipe",
        "Copper Studs Recipe",
        "Pewter Bracelet Recipe",
        "Copper Bangle Recipe",
        "Pewter Chain Recipe",
        "Copper Chain Recipe",
    ])

    # --- Alchemy recipes → Apothecary ---
    print("\n--- Alchemy Recipes ---\n")
    _spawn_recipes("Apothecary", [
        "Potion of Life's Essence Recipe",
        "Potion of the Zephyr Recipe",
        "Potion of the Wellspring Recipe",
        "Potion of the Bull Recipe",
        "Potion of Cat's Grace Recipe",
        "Potion of the Bear Recipe",
        "Potion of Fox's Cunning Recipe",
        "Potion of Owl's Insight Recipe",
        "Potion of the Silver Tongue Recipe",
    ])

    # --- Gold in key rooms ---
    print("\n--- Gold ---\n")

    #woodshop = _find_room("Woodshop")
    cabin = _find_room("cabin")
    if cabin:
        cabin.receive_gold_from_reserve(200)
        print(f"  Added 200 gold to {cabin.key}")


    # --- Locked chest with hides + key in the Wolves Den ---
    print("\n--- Wolves Den Chest ---\n")

    wolves_den = _find_room("Wolves Den")
    if wolves_den:
        # Create a locked chest
        chest = create_object(WorldChest, key="iron chest", location=wolves_den)
        chest.is_locked = True
        chest.is_open = False
        chest.key_tag = "wolves_den_key"
        chest.db.desc = "A heavy iron chest, scarred with claw marks."
        # Make it smashable — vulnerable to bludgeoning, immune to psychic
        chest.is_smashable = True
        chest.smash_hp_max = 30
        chest.smash_hp = 30
        chest.smash_resistances = {
            "psychic": 100,     # immune to bard insults
            "bludgeoning": -25, # vulnerable to maces
            "slashing": 25,     # slightly resistant to blades
        }
        # Put hides inside the chest
        chest.receive_resource_from_reserve(8, 20)  # 8 = Hide
        print(f"  Created locked iron chest with 20 hide in {wolves_den.key}")

        # Drop a key on the floor
        key = create_object(KeyItem, key="rusty iron key", location=wolves_den)
        key.key_tag = "wolves_den_key"
        print(f"  Dropped rusty iron key in {wolves_den.key}")
    else:
        print("  ! Wolves Den room not found")

    # --- Skydancer's Ring at Castle Wall ---
    print("\n--- Castle Wall Ring ---\n")
    castle_wall = _find_room("Outside Castle Wall")
    if castle_wall:
        spawn_nft_item("Skydancer's Ring", castle_wall)
    else:
        print("  ! Outside Castle Wall not found — skipping ring")

    print("\n=== Done ===\n")
