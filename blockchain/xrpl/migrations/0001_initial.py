"""
XRPL blockchain app — initial migration.

Creates all models and seeds CurrencyType, NFTItemType, blank NFT pool,
and initial fungible RESERVE balances.
"""

import django.db.models.deletion
from decimal import Decimal
from django.db import migrations, models


# ─── Seed Data: CurrencyType ────────────────────────────────────────

CURRENCY_TYPES = [
    # Gold
    {"currency_code": "FCMGold", "resource_id": None, "name": "Gold", "unit": "coins", "description": "The primary currency of the realm.", "weight_per_unit_kg": "0.010", "is_gold": True},
    # Resources (resource_id 1-36, matching Polygon ResourceType IDs)
    {"currency_code": "FCMWheat", "resource_id": 1, "name": "Wheat", "unit": "bushels", "description": "Golden stalks of wheat, harvested from farmland.", "weight_per_unit_kg": "0.500", "is_gold": False},
    {"currency_code": "FCMFlour", "resource_id": 2, "name": "Flour", "unit": "sacks", "description": "Milled from wheat at the miller.", "weight_per_unit_kg": "0.400", "is_gold": False},
    {"currency_code": "FCMBread", "resource_id": 3, "name": "Bread", "unit": "loaves", "description": "Baked from flour. Restores hunger.", "weight_per_unit_kg": "0.200", "is_gold": False},
    {"currency_code": "FCMIronOre", "resource_id": 4, "name": "Iron Ore", "unit": "chunks", "description": "Raw iron ore, mined from the earth.", "weight_per_unit_kg": "1.500", "is_gold": False},
    {"currency_code": "FCMIronIngot", "resource_id": 5, "name": "Iron Ingot", "unit": "ingots", "description": "Smelted from iron ore. Used by blacksmiths.", "weight_per_unit_kg": "1.000", "is_gold": False},
    {"currency_code": "FCMWood", "resource_id": 6, "name": "Wood", "unit": "logs", "description": "Rough-cut logs felled from the forest.", "weight_per_unit_kg": "2.000", "is_gold": False},
    {"currency_code": "FCMTimber", "resource_id": 7, "name": "Timber", "unit": "planks", "description": "Sawn from wood at the sawmill. Used in construction and crafting.", "weight_per_unit_kg": "1.500", "is_gold": False},
    {"currency_code": "FCMHide", "resource_id": 8, "name": "Hide", "unit": "hides", "description": "Raw animal hide, stripped from game.", "weight_per_unit_kg": "1.000", "is_gold": False},
    {"currency_code": "FCMLeather", "resource_id": 9, "name": "Leather", "unit": "pieces", "description": "Tanned from hide at the tannery. Used by leatherworkers.", "weight_per_unit_kg": "0.800", "is_gold": False},
    {"currency_code": "FCMCotton", "resource_id": 10, "name": "Cotton", "unit": "bales", "description": "Raw cotton picked from the fields.", "weight_per_unit_kg": "0.300", "is_gold": False},
    {"currency_code": "FCMCloth", "resource_id": 11, "name": "Cloth", "unit": "bolts", "description": "Woven from cotton at the loom. Used by tailors.", "weight_per_unit_kg": "0.200", "is_gold": False},
    {"currency_code": "FCMMoonpetal", "resource_id": 12, "name": "Moonpetal", "unit": "petals", "description": "A silvery flower with mild magical properties. Common potion ingredient.", "weight_per_unit_kg": "0.050", "is_gold": False},
    {"currency_code": "FCMMoonEss", "resource_id": 13, "name": "Moonpetal Essence", "unit": "vials", "description": "Distilled from moonpetals at an apothecary. A base for basic potions.", "weight_per_unit_kg": "0.100", "is_gold": False},
    {"currency_code": "FCMBloodmoss", "resource_id": 14, "name": "Bloodmoss", "unit": "clumps", "description": "A dark red moss that grows in damp places. Used in healing potions.", "weight_per_unit_kg": "0.050", "is_gold": False},
    {"currency_code": "FCMWindroot", "resource_id": 15, "name": "Windroot", "unit": "roots", "description": "A light, fibrous root that smells of open air. Used in mobility potions.", "weight_per_unit_kg": "0.050", "is_gold": False},
    {"currency_code": "FCMArcaneDust", "resource_id": 16, "name": "Arcane Dust", "unit": "pinches", "description": "Ground from crystalline deposits. Resonates with magical energy.", "weight_per_unit_kg": "0.020", "is_gold": False},
    {"currency_code": "FCMOgresCap", "resource_id": 17, "name": "Ogre's Cap", "unit": "caps", "description": "A thick, brutish mushroom. Used in potions of strength.", "weight_per_unit_kg": "0.080", "is_gold": False},
    {"currency_code": "FCMVipervine", "resource_id": 18, "name": "Vipervine", "unit": "tendrils", "description": "A fast-growing creeping vine. Used in potions of agility.", "weight_per_unit_kg": "0.030", "is_gold": False},
    {"currency_code": "FCMIronbark", "resource_id": 19, "name": "Ironbark", "unit": "strips", "description": "Tough, resilient bark stripped from ironwood trees. Used in potions of endurance.", "weight_per_unit_kg": "0.100", "is_gold": False},
    {"currency_code": "FCMMindcap", "resource_id": 20, "name": "Mindcap", "unit": "caps", "description": "A luminescent mushroom found in deep caves. Used in potions of intellect.", "weight_per_unit_kg": "0.030", "is_gold": False},
    {"currency_code": "FCMSageLeaf", "resource_id": 21, "name": "Sage Leaf", "unit": "leaves", "description": "An aromatic herb prized by healers and seers. Used in potions of wisdom.", "weight_per_unit_kg": "0.020", "is_gold": False},
    {"currency_code": "FCMSirenPetal", "resource_id": 22, "name": "Siren Petal", "unit": "petals", "description": "An alluring flower with an intoxicating scent. Used in potions of charisma.", "weight_per_unit_kg": "0.030", "is_gold": False},
    {"currency_code": "FCMCopperOre", "resource_id": 23, "name": "Copper Ore", "unit": "chunks", "description": "Greenish-brown ore veined with native copper.", "weight_per_unit_kg": "1.500", "is_gold": False},
    {"currency_code": "FCMCopperIng", "resource_id": 24, "name": "Copper Ingot", "unit": "ingots", "description": "Smelted from copper ore. Used by jewellers and in bronze alloy.", "weight_per_unit_kg": "1.000", "is_gold": False},
    {"currency_code": "FCMTinOre", "resource_id": 25, "name": "Tin Ore", "unit": "chunks", "description": "Dark, heavy ore with a dull metallic sheen.", "weight_per_unit_kg": "1.500", "is_gold": False},
    {"currency_code": "FCMTinIngot", "resource_id": 26, "name": "Tin Ingot", "unit": "ingots", "description": "Smelted from tin ore. Used in bronze and pewter alloys.", "weight_per_unit_kg": "1.000", "is_gold": False},
    {"currency_code": "FCMLeadOre", "resource_id": 27, "name": "Lead Ore", "unit": "chunks", "description": "Dense, soft ore with a bluish-grey lustre.", "weight_per_unit_kg": "2.000", "is_gold": False},
    {"currency_code": "FCMLeadIngot", "resource_id": 28, "name": "Lead Ingot", "unit": "ingots", "description": "Smelted from lead ore. Used in pewter alloy.", "weight_per_unit_kg": "1.500", "is_gold": False},
    {"currency_code": "FCMPewterIng", "resource_id": 29, "name": "Pewter Ingot", "unit": "ingots", "description": "An alloy of tin and lead. Used by jewellers for basic adornments.", "weight_per_unit_kg": "1.200", "is_gold": False},
    {"currency_code": "FCMSilverOre", "resource_id": 30, "name": "Silver Ore", "unit": "chunks", "description": "Pale ore streaked with veins of native silver.", "weight_per_unit_kg": "1.500", "is_gold": False},
    {"currency_code": "FCMSilverIng", "resource_id": 31, "name": "Silver Ingot", "unit": "ingots", "description": "Smelted from silver ore. Prized by jewellers.", "weight_per_unit_kg": "1.000", "is_gold": False},
    {"currency_code": "FCMBronzeIng", "resource_id": 32, "name": "Bronze Ingot", "unit": "ingots", "description": "An alloy of copper and tin. Used by blacksmiths for basic weapons and armour.", "weight_per_unit_kg": "1.200", "is_gold": False},
    {"currency_code": "FCMRuby", "resource_id": 33, "name": "Ruby", "unit": "gems", "description": "A deep red gemstone. Prized by jewellers.", "weight_per_unit_kg": "0.050", "is_gold": False},
    {"currency_code": "FCMEmerald", "resource_id": 34, "name": "Emerald", "unit": "gems", "description": "A brilliant green gemstone. Prized by jewellers.", "weight_per_unit_kg": "0.050", "is_gold": False},
    {"currency_code": "FCMDiamond", "resource_id": 35, "name": "Diamond", "unit": "gems", "description": "A flawless clear gemstone. The rarest and most valuable.", "weight_per_unit_kg": "0.050", "is_gold": False},
    {"currency_code": "FCMCoal", "resource_id": 36, "name": "Coal", "unit": "lumps", "description": "Black mineral fuel. Used in steel smelting.", "weight_per_unit_kg": "0.500", "is_gold": False},
    # Proxy tokens (NFT AMM pricing engine — closed-loop, vault-only)
    {"currency_code": "PGold", "resource_id": None, "name": "P Gold", "unit": "coins", "description": "Proxy gold for NFT AMM pools. Vault-only.", "weight_per_unit_kg": "0.000", "is_gold": False, "initial_reserve": "250000"},
    {"currency_code": "PTrainDagger", "resource_id": None, "name": "P Train Dagger", "unit": "tokens", "description": "Proxy token for Training Dagger AMM pricing.", "weight_per_unit_kg": "0.000", "is_gold": False, "initial_reserve": "10000"},
    {"currency_code": "PTrainSSword", "resource_id": None, "name": "P Train SSword", "unit": "tokens", "description": "Proxy token for Training Shortsword AMM pricing.", "weight_per_unit_kg": "0.000", "is_gold": False, "initial_reserve": "10000"},
    {"currency_code": "PTrainLSword", "resource_id": None, "name": "P Train LSword", "unit": "tokens", "description": "Proxy token for Training Longsword AMM pricing.", "weight_per_unit_kg": "0.000", "is_gold": False, "initial_reserve": "10000"},
]


# ─── Seed Data: NFTItemType ─────────────────────────────────────────

_LONGSWORD_TC = "typeclasses.items.weapons.longsword_nft_item.LongswordNFTItem"
_DAGGER_TC = "typeclasses.items.weapons.dagger_nft_item.DaggerNFTItem"
_SHORTSWORD_TC = "typeclasses.items.weapons.shortsword_nft_item.ShortswordNFTItem"
_BOW_TC = "typeclasses.items.weapons.bow_nft_item.BowNFTItem"
_CLUB_TC = "typeclasses.items.weapons.club_nft_item.ClubNFTItem"
_SPEAR_TC = "typeclasses.items.weapons.spear_nft_item.SpearNFTItem"
_AXE_TC = "typeclasses.items.weapons.axe_nft_item.AxeNFTItem"
_GREATSWORD_TC = "typeclasses.items.weapons.greatsword_nft_item.GreatswordNFTItem"
_MACE_TC = "typeclasses.items.weapons.mace_nft_item.MaceNFTItem"
_HAMMER_TC = "typeclasses.items.weapons.hammer_nft_item.HammerNFTItem"
_SLING_TC = "typeclasses.items.weapons.sling_nft_item.SlingNFTItem"
_STAFF_TC = "typeclasses.items.weapons.staff_nft_item.StaffNFTItem"
_LANCE_TC = "typeclasses.items.weapons.lance_nft_item.LanceNFTItem"
_CROSSBOW_TC = "typeclasses.items.weapons.crossbow_nft_item.CrossbowNFTItem"
_BATTLEAXE_TC = "typeclasses.items.weapons.battleaxe_nft_item.BattleaxeNFTItem"
_RAPIER_TC = "typeclasses.items.weapons.rapier_nft_item.RapierNFTItem"
_WEARABLE_TC = "typeclasses.items.wearables.wearable_nft_item.WearableNFTItem"
_HOLDABLE_TC = "typeclasses.items.holdables.holdable_nft_item.HoldableNFTItem"
_CONTAINER_TC = "typeclasses.items.containers.container_nft_item.ContainerNFTItem"
_WEARABLE_CONTAINER_TC = "typeclasses.items.containers.wearable_container_nft_item.WearableContainerNFTItem"
_BASE_TC = "typeclasses.items.base_nft_item.BaseNFTItem"
_SHIP_TC = "typeclasses.items.untakeables.ship_nft_item.ShipNFTItem"
_POTION_TC = "typeclasses.items.consumables.potion_nft_item.PotionNFTItem"
_RECIPE_TC = "typeclasses.items.consumables.crafting_recipe_nft_item.CraftingRecipeNFTItem"
_SPELL_SCROLL_TC = "typeclasses.items.consumables.spell_scroll_nft_item.SpellScrollNFTItem"
_TORCH_TC = "typeclasses.items.holdables.torch_nft_item.TorchNFTItem"
_LANTERN_TC = "typeclasses.items.holdables.lantern_nft_item.LanternNFTItem"
_DISTRICT_MAP_TC = "typeclasses.items.maps.district_map_nft_item.DistrictMapNFTItem"
_ROUTE_MAP_TC = "typeclasses.items.maps.route_map_nft_item.RouteMapNFTItem"

NFT_ITEM_TYPES = [
    # ── Weapons ──
    {"name": "Training Dagger", "typeclass": _DAGGER_TC, "prototype_key": "training_dagger", "description": "A blunt wooden dagger used for practice. Light and fast, but harmless.", "tracking_token": "PTrainDagger"},
    {"name": "Training Shortsword", "typeclass": _SHORTSWORD_TC, "prototype_key": "training_shortsword", "description": "A wooden practice shortsword. Lighter than a longsword, good for one-handed drills.", "tracking_token": "PTrainSSword"},
    {"name": "Training Longsword", "typeclass": _LONGSWORD_TC, "prototype_key": "training_longsword", "description": "A wooden practice sword. Won't cut much, but it'll bruise.", "tracking_token": "PTrainLSword"},
    {"name": "Training Bow", "typeclass": _BOW_TC, "prototype_key": "training_bow", "description": "A crude practice bow carved from a single piece of timber."},
    {"name": "Club", "typeclass": _CLUB_TC, "prototype_key": "club", "description": "A heavy wooden club. Simple, brutal, and effective."},
    {"name": "Iron Longsword", "typeclass": _LONGSWORD_TC, "prototype_key": "iron_longsword", "description": "A sturdy iron blade, forged by a competent smith."},
    {"name": "Iron Dagger", "typeclass": _DAGGER_TC, "prototype_key": "iron_dagger", "description": "A sharp iron dagger. Small but deadly in skilled hands."},
    {"name": "Iron Shortsword", "typeclass": _SHORTSWORD_TC, "prototype_key": "iron_shortsword", "description": "A well-forged iron shortsword. Quick and versatile."},
    {"name": "Spear", "typeclass": _SPEAR_TC, "prototype_key": "spear", "description": "An iron-tipped spear mounted on a wooden shaft."},
    {"name": "Iron Hand Axe", "typeclass": _AXE_TC, "prototype_key": "iron_hand_axe", "description": "A compact iron axe. Good for chopping more than just wood."},
    {"name": "Training Greatsword", "typeclass": _GREATSWORD_TC, "prototype_key": "training_greatsword", "description": "A heavy two-handed practice sword carved from timber."},
    {"name": "Bronze Dagger", "typeclass": _DAGGER_TC, "prototype_key": "bronze_dagger", "description": "A small bronze dagger. Light and quick, with a greenish sheen."},
    {"name": "Bronze Shortsword", "typeclass": _SHORTSWORD_TC, "prototype_key": "bronze_shortsword", "description": "A sturdy bronze shortsword. Quick and reliable."},
    {"name": "Bronze Longsword", "typeclass": _LONGSWORD_TC, "prototype_key": "bronze_longsword", "description": "A broad bronze blade. Heavier than iron but a solid weapon."},
    {"name": "Bronze Hand Axe", "typeclass": _AXE_TC, "prototype_key": "bronze_hand_axe", "description": "A compact bronze axe head mounted on a wooden haft."},
    {"name": "Bronze Spear", "typeclass": _SPEAR_TC, "prototype_key": "bronze_spear", "description": "A bronze-tipped spear mounted on a wooden shaft."},
    {"name": "Bronze Mace", "typeclass": _MACE_TC, "prototype_key": "bronze_mace", "description": "A heavy bronze mace head fixed to a wooden haft."},
    {"name": "Bronze Hammer", "typeclass": _HAMMER_TC, "prototype_key": "bronze_hammer", "description": "A solid bronze hammer head mounted on a wooden haft."},
    {"name": "Iron Mace", "typeclass": _MACE_TC, "prototype_key": "iron_mace", "description": "A heavy iron mace head fixed to a wooden haft. Crushes armour with brutal efficiency."},
    {"name": "Iron Hammer", "typeclass": _HAMMER_TC, "prototype_key": "iron_hammer", "description": "A solid iron hammer head mounted on a wooden haft. Delivers devastating blows."},
    {"name": "Shortbow", "typeclass": _BOW_TC, "prototype_key": "shortbow", "description": "A compact timber bow with good draw strength. Light and quick to fire."},
    {"name": "Quarterstaff", "typeclass": _STAFF_TC, "prototype_key": "quarterstaff", "description": "A sturdy timber staff as tall as a man. Simple but effective in trained hands."},
    {"name": "Training Lance", "typeclass": _LANCE_TC, "prototype_key": "training_lance", "description": "A long wooden lance with a blunted tip. Used for jousting practice and mounted drills."},
    {"name": "Crossbow", "typeclass": _CROSSBOW_TC, "prototype_key": "crossbow", "description": "A mechanical crossbow with an iron prod and timber stock. High damage, slow to reload."},
    {"name": "Iron Spiked Club", "typeclass": _CLUB_TC, "prototype_key": "iron_spiked_club", "description": "A heavy wooden club studded with iron spikes. Brutal and effective."},
    {"name": "Bronze Greatsword", "typeclass": _GREATSWORD_TC, "prototype_key": "bronze_greatsword", "description": "A massive two-handed bronze blade. Slow but devastating."},
    {"name": "Bronze Battleaxe", "typeclass": _BATTLEAXE_TC, "prototype_key": "bronze_battleaxe", "description": "A large two-handed bronze axe head mounted on a wooden haft. Heavy hits, slow recovery."},
    {"name": "Bronze Rapier", "typeclass": _RAPIER_TC, "prototype_key": "bronze_rapier", "description": "A thin bronze thrusting blade. Fast and precise, favouring dexterity over brute strength."},
    # ── Components ──
    {"name": "Stock", "typeclass": _BASE_TC, "prototype_key": "stock", "description": "A shaped timber stock designed to hold a crossbow mechanism."},
    {"name": "Shaft", "typeclass": _BASE_TC, "prototype_key": "shaft", "description": "A long, straight shaft of timber. Needs a metal head fitted at a smithy."},
    {"name": "Haft", "typeclass": _BASE_TC, "prototype_key": "haft", "description": "A short, sturdy wooden handle shaped for an axe or mace head."},
    {"name": "Leather Straps", "typeclass": _BASE_TC, "prototype_key": "leather_straps", "description": "Tough strips of leather cut for binding and reinforcement."},
    # ── Wearables ──
    {"name": "Leather Gloves", "typeclass": _WEARABLE_TC, "prototype_key": "leather_gloves", "description": "Sturdy leather gloves with reinforced palms."},
    {"name": "Leather Belt", "typeclass": _WEARABLE_TC, "prototype_key": "leather_belt", "description": "A wide leather belt with an iron buckle."},
    {"name": "Leather Boots", "typeclass": _WEARABLE_TC, "prototype_key": "leather_boots", "description": "Sturdy leather boots with double-stitched soles."},
    {"name": "Leather Cap", "typeclass": _WEARABLE_TC, "prototype_key": "leather_cap", "description": "A close-fitting leather cap with a short brim."},
    {"name": "Leather Pants", "typeclass": _WEARABLE_TC, "prototype_key": "leather_pants", "description": "Tough leather trousers with double-stitched seams."},
    {"name": "Bridle", "typeclass": _WEARABLE_TC, "prototype_key": "bridle", "description": "A simple leather bridle with iron bit and reins."},
    {"name": "Sling", "typeclass": _SLING_TC, "prototype_key": "sling", "description": "A simple leather sling for hurling stones. Light and easy to use."},
    {"name": "Leather Armor", "typeclass": _WEARABLE_TC, "prototype_key": "leather_armor", "description": "A gambeson reinforced with leather plates and straps. Offers solid protection without heavy metal."},
    {"name": "Studded Leather Armor", "typeclass": _WEARABLE_TC, "prototype_key": "studded_leather_armor", "description": "Leather armor reinforced with iron studs and rivets. Tougher than plain leather."},
    # ── Holdables ──
    {"name": "Wooden Shield", "typeclass": _HOLDABLE_TC, "prototype_key": "wooden_shield", "description": "A round wooden shield banded with iron."},
    {"name": "Ironbound Shield", "typeclass": _HOLDABLE_TC, "prototype_key": "ironbound_shield", "description": "A wooden shield bound with iron bands and rivets. Sturdier than plain wood."},
    {"name": "Wooden Torch", "typeclass": _TORCH_TC, "prototype_key": "wooden_torch", "description": "A sturdy timber torch wrapped in oil-soaked cloth. It burns bright but is consumed by its flame."},
    {"name": "Bronze Lantern", "typeclass": _LANTERN_TC, "prototype_key": "bronze_lantern", "description": "A reliable bronze lantern with a glass pane. Can be refueled with oil."},
    # ── Tailored ──
    {"name": "Gambeson", "typeclass": _WEARABLE_TC, "prototype_key": "gambeson", "description": "Layers of quilted cloth stitched over a linen lining. Light but protective."},
    {"name": "Coarse Robe", "typeclass": _WEARABLE_TC, "prototype_key": "coarse_robe", "description": "A rough-spun robe of undyed cloth. Simple and functional."},
    {"name": "Kippah", "typeclass": _WEARABLE_TC, "prototype_key": "kippah", "description": "A small embroidered skullcap. Worn as a sign of devotion."},
    {"name": "Brown Corduroy Pants", "typeclass": _WEARABLE_TC, "prototype_key": "brown_corduroy_pants", "description": "Sturdy brown corduroy trousers with a drawstring waist. Comfortable and hardwearing."},
    {"name": "Bandana", "typeclass": _WEARABLE_TC, "prototype_key": "bandana", "description": "A dark cloth bandana tied snugly around the head."},
    {"name": "Cloak", "typeclass": _WEARABLE_TC, "prototype_key": "cloak", "description": "A heavy, full-length cloak woven from thick cloth."},
    {"name": "Veil", "typeclass": _WEARABLE_TC, "prototype_key": "veil", "description": "A delicate cloth veil that frames the face."},
    {"name": "Scarf", "typeclass": _WEARABLE_TC, "prototype_key": "scarf", "description": "A long, finely woven scarf."},
    {"name": "Sash", "typeclass": _WEARABLE_TC, "prototype_key": "sash", "description": "A wide cloth sash."},
    {"name": "Warrior's Wraps", "typeclass": _WEARABLE_TC, "prototype_key": "warriors_wraps", "description": "Thick cloth strips wound tightly around the hands and wrists. They bolster the wearer's vitality."},
    # ── Containers ──
    {"name": "Backpack", "typeclass": _CONTAINER_TC, "prototype_key": "backpack", "description": "A sturdy leather backpack with wide straps and brass buckles."},
    {"name": "Panniers", "typeclass": _WEARABLE_CONTAINER_TC, "prototype_key": "panniers", "description": "Large leather saddlebags designed to hang from a mule's back."},
    # ── Potions ──
    {"name": "Potion of Life's Essence", "typeclass": _POTION_TC, "prototype_key": "lifes_essence", "description": "A glowing crimson potion that smells of bloodmoss and warmth."},
    {"name": "Potion of the Zephyr", "typeclass": _POTION_TC, "prototype_key": "the_zephyr", "description": "A pale blue potion that swirls like a miniature storm."},
    {"name": "Potion of the Wellspring", "typeclass": _POTION_TC, "prototype_key": "the_wellspring", "description": "A shimmering violet potion that hums with arcane resonance."},
    {"name": "Potion of the Bull", "typeclass": _POTION_TC, "prototype_key": "the_bull", "description": "A thick, earthy potion that smells of mushrooms and raw power."},
    {"name": "Potion of Cat's Grace", "typeclass": _POTION_TC, "prototype_key": "cats_grace", "description": "A quicksilver potion that shifts and flows like liquid shadow."},
    {"name": "Potion of the Bear", "typeclass": _POTION_TC, "prototype_key": "the_bear", "description": "A dark amber potion with flecks of bark suspended within."},
    {"name": "Potion of Fox's Cunning", "typeclass": _POTION_TC, "prototype_key": "foxs_cunning", "description": "A luminous golden potion that seems to glow from within."},
    {"name": "Potion of Owl's Insight", "typeclass": _POTION_TC, "prototype_key": "owls_insight", "description": "A clear, sage-scented potion with a faint green tint."},
    {"name": "Potion of the Silver Tongue", "typeclass": _POTION_TC, "prototype_key": "silver_tongue", "description": "An iridescent potion with a sweet, intoxicating aroma."},
    # ── Jewellery ──
    {"name": "Pewter Ring", "typeclass": _WEARABLE_TC, "prototype_key": "pewter_ring", "description": "A simple band of pewter, polished to a dull sheen."},
    {"name": "Copper Ring", "typeclass": _WEARABLE_TC, "prototype_key": "copper_ring", "description": "A warm-toned copper band with a faint green patina."},
    {"name": "Pewter Hoops", "typeclass": _WEARABLE_TC, "prototype_key": "pewter_hoops", "description": "A pair of small pewter hoops, lightly burnished."},
    {"name": "Copper Studs", "typeclass": _WEARABLE_TC, "prototype_key": "copper_studs", "description": "A pair of small copper studs with a warm, reddish gleam."},
    {"name": "Pewter Bracelet", "typeclass": _WEARABLE_TC, "prototype_key": "pewter_bracelet", "description": "A flat pewter bracelet with a hammered finish."},
    {"name": "Copper Bangle", "typeclass": _WEARABLE_TC, "prototype_key": "copper_bangle", "description": "A round copper bangle, smooth and warm to the touch."},
    {"name": "Pewter Chain", "typeclass": _WEARABLE_TC, "prototype_key": "pewter_chain", "description": "A simple chain of interlocking pewter links."},
    {"name": "Copper Chain", "typeclass": _WEARABLE_TC, "prototype_key": "copper_chain", "description": "A delicate chain of copper links with a warm lustre."},
    # ── Bronze Armor ──
    {"name": "Bronze Greaves", "typeclass": _WEARABLE_TC, "prototype_key": "bronze_greaves", "description": "Shaped bronze plates that protect the shins and calves."},
    {"name": "Bronze Bracers", "typeclass": _WEARABLE_TC, "prototype_key": "bronze_bracers", "description": "Curved bronze plates that protect the forearms."},
    {"name": "Bronze Helm", "typeclass": _WEARABLE_TC, "prototype_key": "bronze_helm", "description": "A sturdy bronze helmet with cheek guards and a nose piece."},
    # ── Enchanted Wearables ──
    {"name": "Rogue's Bandana", "typeclass": _WEARABLE_TC, "prototype_key": "rogues_bandana", "description": "A dark bandana imbued with arcane agility. It quickens the wearer's reflexes."},
    {"name": "Sage's Kippah", "typeclass": _WEARABLE_TC, "prototype_key": "sages_kippah", "description": "An embroidered skullcap humming with quiet wisdom."},
    {"name": "Titan's Cloak", "typeclass": _WEARABLE_TC, "prototype_key": "titans_cloak", "description": "A heavy cloak woven with threads of arcane might. It bolsters the wearer's strength."},
    {"name": "Veil of Grace", "typeclass": _WEARABLE_TC, "prototype_key": "veil_of_grace", "description": "A delicate veil that shimmers with enchantment. It heightens the wearer's presence."},
    {"name": "Professor's Scarf", "typeclass": _WEARABLE_TC, "prototype_key": "professors_scarf", "description": "A finely woven scarf crackling with arcane intellect."},
    {"name": "Sun Bleached Sash", "typeclass": _WEARABLE_TC, "prototype_key": "sun_bleached_sash", "description": "A sun-faded sash imbued with enduring vitality."},
    {"name": "Scout's Cap", "typeclass": _WEARABLE_TC, "prototype_key": "scouts_cap", "description": "A leather cap enchanted to sharpen the wearer's reflexes in combat."},
    {"name": "Pugilist's Gloves", "typeclass": _WEARABLE_TC, "prototype_key": "pugilists_gloves", "description": "Leather gloves hardened with arcane energy. They hum faintly when a fist is clenched."},
    {"name": "Cowboy Boots", "typeclass": _WEARABLE_TC, "prototype_key": "cowboy_boots", "description": "Tooled leather boots with pointed toes, enchanted to reveal the unseen."},
    {"name": "Title Belt", "typeclass": _WEARABLE_TC, "prototype_key": "title_belt", "description": "A championship belt of thick, enchanted leather that absorbs the force of blunt impacts."},
    {"name": "Rustler's Chaps", "typeclass": _WEARABLE_TC, "prototype_key": "rustlers_chaps", "description": "Rugged leather chaps enchanted to grant the wearer tireless stamina on long rides."},
    {"name": "Shepherd's Sling", "typeclass": _SLING_TC, "prototype_key": "shepherds_sling", "description": "A leather sling imbued with arcane precision. Stones thrown from it fly straighter and hit harder."},
    {"name": "Warden's Leather", "typeclass": _WEARABLE_TC, "prototype_key": "wardens_leather", "description": "Leather armor enchanted to turn aside piercing blows."},
    {"name": "Defender's Helm", "typeclass": _WEARABLE_TC, "prototype_key": "defenders_helm", "description": "A bronze helmet radiating protective magic. Critical blows glance harmlessly off its surface."},
    {"name": "Bracers of Deflection", "typeclass": _WEARABLE_TC, "prototype_key": "bracers_of_deflection", "description": "Bronze bracers shimmering with enchantment. Slashing blows slide off their surface."},
    {"name": "Greaves of the Vanguard", "typeclass": _WEARABLE_TC, "prototype_key": "greaves_of_the_vanguard", "description": "Bronze greaves crackling with arcane swiftness. The wearer is always first to act."},
    {"name": "Nightseer's Ring", "typeclass": _WEARABLE_TC, "prototype_key": "nightseers_ring", "description": "A copper ring etched with tiny runes that glow faintly in darkness."},
    {"name": "Skydancer's Ring", "typeclass": _WEARABLE_TC, "prototype_key": "skydancers_ring", "description": "A pewter ring carved with feathered motifs. The metal feels impossibly light, as though yearning to take flight."},
    {"name": "N95 Mask", "typeclass": _WEARABLE_TC, "prototype_key": "n95_mask", "description": "A tightly woven cloth mask that fits snugly over the nose and mouth."},
    {"name": "Aquatic N95", "typeclass": _WEARABLE_TC, "prototype_key": "aquatic_n95", "description": "A tightly woven cloth mask shimmering with enchantment. It filters breathable air from water itself."},
    {"name": "Runeforged Chain", "typeclass": _WEARABLE_TC, "prototype_key": "runeforged_chain", "description": "A copper chain inscribed with dwarven runes of war."},
    {"name": "Spellweaver's Bangle", "typeclass": _WEARABLE_TC, "prototype_key": "spellweavers_bangle", "description": "A copper bangle crackling with faint arcane sparks."},
    {"name": "Truewatch Studs", "typeclass": _WEARABLE_TC, "prototype_key": "truewatch_studs", "description": "Copper studs enchanted to sharpen the wearer's awareness."},
    # ── Ships ──
    {"name": "Cog",        "typeclass": _SHIP_TC, "prototype_key": "cog",        "default_metadata": {"ship_tier": 1}, "description": "A small, sturdy single-masted trading vessel."},
    {"name": "Caravel",    "typeclass": _SHIP_TC, "prototype_key": "caravel",    "default_metadata": {"ship_tier": 2}, "description": "A nimble two-masted ship capable of coastal voyages."},
    {"name": "Brigantine", "typeclass": _SHIP_TC, "prototype_key": "brigantine", "default_metadata": {"ship_tier": 3}, "description": "A fast two-masted vessel with square and lateen rigging."},
    {"name": "Carrack",    "typeclass": _SHIP_TC, "prototype_key": "carrack",    "default_metadata": {"ship_tier": 4}, "description": "A large three-masted merchant vessel built for long voyages."},
    {"name": "Galleon",    "typeclass": _SHIP_TC, "prototype_key": "galleon",    "default_metadata": {"ship_tier": 5}, "description": "A massive multi-decked ship, the pinnacle of naval architecture."},
    # ── Enchanted Gems ──
    {"name": "Enchanted Ruby", "typeclass": _BASE_TC, "prototype_key": "enchanted_ruby", "description": "A ruby pulsing with arcane energy. Its enchantment is hidden within."},
    # ── Maps ──
    {"name": "DistrictMap", "typeclass": _DISTRICT_MAP_TC, "prototype_key": "district_map", "description": "A parchment district map. Survey rooms to fill it in; trade it as an NFT."},
    {"name": "RouteMap", "typeclass": _ROUTE_MAP_TC, "prototype_key": "route_map", "description": "A chart showing a discovered route between two locations."},
    # ── Recipe Scrolls ──
    {"name": "Training Longsword Recipe", "typeclass": _RECIPE_TC, "prototype_key": "training_longsword_recipe", "description": "A scroll detailing how to carve a training longsword from timber."},
    {"name": "Wooden Shield Recipe", "typeclass": _RECIPE_TC, "prototype_key": "wooden_shield_recipe", "description": "A scroll showing how to shape timber into a sturdy round shield."},
    {"name": "Wooden Torch Recipe", "typeclass": _RECIPE_TC, "prototype_key": "wooden_torch_recipe", "description": "A scroll explaining how to fashion a simple torch from timber."},
    {"name": "Bronze Lantern Recipe", "typeclass": _RECIPE_TC, "prototype_key": "bronze_lantern_recipe", "description": "A scroll detailing how to forge a sturdy bronze lantern."},
    {"name": "Iron Longsword Recipe", "typeclass": _RECIPE_TC, "prototype_key": "iron_longsword_recipe", "description": "A scroll describing how to forge a longsword from iron ingots."},
    {"name": "Leather Boots Recipe", "typeclass": _RECIPE_TC, "prototype_key": "leather_boots_recipe", "description": "A scroll with patterns for cutting and stitching leather boots."},
    {"name": "Leather Gloves Recipe", "typeclass": _RECIPE_TC, "prototype_key": "leather_gloves_recipe", "description": "A scroll detailing how to craft leather gloves with reinforced palms."},
    {"name": "Leather Belt Recipe", "typeclass": _RECIPE_TC, "prototype_key": "leather_belt_recipe", "description": "A scroll showing how to cut and rivet a wide leather belt."},
    {"name": "Training Dagger Recipe", "typeclass": _RECIPE_TC, "prototype_key": "training_dagger_recipe", "description": "A scroll showing how to whittle a small practice dagger from timber."},
    {"name": "Training Shortsword Recipe", "typeclass": _RECIPE_TC, "prototype_key": "training_shortsword_recipe", "description": "A scroll detailing how to carve a wooden practice shortsword."},
    {"name": "Training Bow Recipe", "typeclass": _RECIPE_TC, "prototype_key": "training_bow_recipe", "description": "A scroll explaining how to shape timber into a crude practice bow."},
    {"name": "Club Recipe", "typeclass": _RECIPE_TC, "prototype_key": "club_recipe", "description": "A scroll describing how to fashion a heavy wooden club."},
    {"name": "Training Greatsword Recipe", "typeclass": _RECIPE_TC, "prototype_key": "training_greatsword_recipe", "description": "A scroll detailing how to carve a heavy two-handed practice sword from timber."},
    {"name": "Shaft Recipe", "typeclass": _RECIPE_TC, "prototype_key": "shaft_recipe", "description": "A scroll showing how to shape a long, straight timber shaft."},
    {"name": "Haft Recipe", "typeclass": _RECIPE_TC, "prototype_key": "haft_recipe", "description": "A scroll showing how to shape timber into a sturdy handle for axes and maces."},
    {"name": "Iron Dagger Recipe", "typeclass": _RECIPE_TC, "prototype_key": "iron_dagger_recipe", "description": "A scroll describing how to forge a small iron dagger."},
    {"name": "Iron Shortsword Recipe", "typeclass": _RECIPE_TC, "prototype_key": "iron_shortsword_recipe", "description": "A scroll with instructions for forging an iron shortsword."},
    {"name": "Spear Recipe", "typeclass": _RECIPE_TC, "prototype_key": "spear_recipe", "description": "A scroll explaining how to fit an iron head to a wooden shaft to make a spear."},
    {"name": "Ironbound Shield Recipe", "typeclass": _RECIPE_TC, "prototype_key": "ironbound_shield_recipe", "description": "A scroll detailing how to bind a wooden shield with iron bands."},
    {"name": "Crossbow Recipe", "typeclass": _RECIPE_TC, "prototype_key": "crossbow_recipe", "description": "A scroll detailing how to fit iron fittings and a prod to a timber stock to make a crossbow."},
    {"name": "Iron Spiked Club Recipe", "typeclass": _RECIPE_TC, "prototype_key": "iron_spiked_club_recipe", "description": "A scroll detailing how to stud a wooden club with iron spikes."},
    {"name": "Studded Leather Armor Recipe", "typeclass": _RECIPE_TC, "prototype_key": "studded_leather_armor_recipe", "description": "A scroll showing how to reinforce leather armor with iron studs and rivets."},
    {"name": "Bronze Dagger Recipe", "typeclass": _RECIPE_TC, "prototype_key": "bronze_dagger_recipe", "description": "A scroll describing how to forge a small dagger from bronze."},
    {"name": "Bronze Shortsword Recipe", "typeclass": _RECIPE_TC, "prototype_key": "bronze_shortsword_recipe", "description": "A scroll with instructions for forging a bronze shortsword."},
    {"name": "Bronze Longsword Recipe", "typeclass": _RECIPE_TC, "prototype_key": "bronze_longsword_recipe", "description": "A scroll describing how to forge a longsword from bronze ingots."},
    {"name": "Bronze Hand Axe Recipe", "typeclass": _RECIPE_TC, "prototype_key": "bronze_hand_axe_recipe", "description": "A scroll showing how to forge a bronze axe head and mount it on a haft."},
    {"name": "Bronze Spear Recipe", "typeclass": _RECIPE_TC, "prototype_key": "bronze_spear_recipe", "description": "A scroll explaining how to fit a bronze head to a shaft to make a spear."},
    {"name": "Bronze Mace Recipe", "typeclass": _RECIPE_TC, "prototype_key": "bronze_mace_recipe", "description": "A scroll showing how to cast a bronze mace head and mount it on a haft."},
    {"name": "Bronze Hammer Recipe", "typeclass": _RECIPE_TC, "prototype_key": "bronze_hammer_recipe", "description": "A scroll describing how to forge a bronze hammer head and mount it on a haft."},
    {"name": "Bronze Greatsword Recipe", "typeclass": _RECIPE_TC, "prototype_key": "bronze_greatsword_recipe", "description": "A scroll describing how to forge a massive two-handed greatsword from bronze ingots."},
    {"name": "Bronze Battleaxe Recipe", "typeclass": _RECIPE_TC, "prototype_key": "bronze_battleaxe_recipe", "description": "A scroll showing how to forge a bronze battleaxe head and mount it on a haft."},
    {"name": "Bronze Rapier Recipe", "typeclass": _RECIPE_TC, "prototype_key": "bronze_rapier_recipe", "description": "A scroll describing how to forge a thin, precise rapier from bronze ingots."},
    {"name": "Bronze Greaves Recipe", "typeclass": _RECIPE_TC, "prototype_key": "bronze_greaves_recipe", "description": "A scroll showing how to shape bronze plates into shin guards."},
    {"name": "Bronze Bracers Recipe", "typeclass": _RECIPE_TC, "prototype_key": "bronze_bracers_recipe", "description": "A scroll showing how to shape bronze plates into forearm guards."},
    {"name": "Bronze Helm Recipe", "typeclass": _RECIPE_TC, "prototype_key": "bronze_helm_recipe", "description": "A scroll showing how to forge a bronze helmet with cheek guards."},
    {"name": "Iron Hand Axe Recipe", "typeclass": _RECIPE_TC, "prototype_key": "iron_hand_axe_recipe", "description": "A scroll showing how to forge a compact iron hand axe."},
    {"name": "Leather Cap Recipe", "typeclass": _RECIPE_TC, "prototype_key": "leather_cap_recipe", "description": "A scroll showing how to cut and stitch a leather cap."},
    {"name": "Leather Pants Recipe", "typeclass": _RECIPE_TC, "prototype_key": "leather_pants_recipe", "description": "A scroll with patterns for cutting and stitching leather trousers."},
    {"name": "Bridle Recipe", "typeclass": _RECIPE_TC, "prototype_key": "bridle_recipe", "description": "A scroll explaining how to craft a simple leather bridle with iron bit."},
    {"name": "Sling Recipe", "typeclass": _RECIPE_TC, "prototype_key": "sling_recipe", "description": "A scroll showing how to cut and braid a leather sling."},
    {"name": "Gambeson Recipe", "typeclass": _RECIPE_TC, "prototype_key": "gambeson_recipe", "description": "A scroll with instructions for quilting layers of cloth into a gambeson."},
    {"name": "Coarse Robe Recipe", "typeclass": _RECIPE_TC, "prototype_key": "coarse_robe_recipe", "description": "A scroll showing how to cut and sew a simple cloth robe."},
    {"name": "Kippah Recipe", "typeclass": _RECIPE_TC, "prototype_key": "kippah_recipe", "description": "A scroll with patterns for embroidering a small devotional skullcap."},
    {"name": "Brown Corduroy Pants Recipe", "typeclass": _RECIPE_TC, "prototype_key": "brown_corduroy_pants_recipe", "description": "A scroll with patterns for cutting and stitching brown corduroy trousers."},
    {"name": "Bandana Recipe", "typeclass": _RECIPE_TC, "prototype_key": "bandana_recipe", "description": "A scroll showing how to cut and sew a cloth bandana."},
    {"name": "Cloak Recipe", "typeclass": _RECIPE_TC, "prototype_key": "cloak_recipe", "description": "A scroll with instructions for weaving a heavy cloth cloak."},
    {"name": "Veil Recipe", "typeclass": _RECIPE_TC, "prototype_key": "veil_recipe", "description": "A scroll showing how to cut and hem a delicate cloth veil."},
    {"name": "Scarf Recipe", "typeclass": _RECIPE_TC, "prototype_key": "scarf_recipe", "description": "A scroll showing how to weave a fine cloth scarf."},
    {"name": "Sash Recipe", "typeclass": _RECIPE_TC, "prototype_key": "sash_recipe", "description": "A scroll showing how to weave a cloth sash."},
    {"name": "Warrior's Wraps Recipe", "typeclass": _RECIPE_TC, "prototype_key": "warriors_wraps_recipe", "description": "A scroll showing how to wind thick cloth strips into hand wraps favoured by warriors."},
    {"name": "Backpack Recipe", "typeclass": _RECIPE_TC, "prototype_key": "backpack_recipe", "description": "A scroll with patterns for cutting and stitching a leather backpack."},
    {"name": "Panniers Recipe", "typeclass": _RECIPE_TC, "prototype_key": "panniers_recipe", "description": "A scroll showing how to craft leather saddlebags for a mule."},
    {"name": "Leather Straps Recipe", "typeclass": _RECIPE_TC, "prototype_key": "leather_straps_recipe", "description": "A scroll showing how to cut leather into tough binding straps."},
    {"name": "Leather Armor Recipe", "typeclass": _RECIPE_TC, "prototype_key": "leather_armor_recipe", "description": "A scroll showing how to reinforce a gambeson with leather plates and straps."},
    {"name": "Potion of Life's Essence Recipe", "typeclass": _RECIPE_TC, "prototype_key": "lifes_essence_recipe", "description": "A scroll describing how to brew a healing potion from moonpetal essence and bloodmoss."},
    {"name": "Potion of the Zephyr Recipe", "typeclass": _RECIPE_TC, "prototype_key": "the_zephyr_recipe", "description": "A scroll describing how to brew a mobility potion from moonpetal essence and windroot."},
    {"name": "Potion of the Wellspring Recipe", "typeclass": _RECIPE_TC, "prototype_key": "the_wellspring_recipe", "description": "A scroll describing how to brew a mana potion from moonpetal essence and arcane dust."},
    {"name": "Potion of the Bull Recipe", "typeclass": _RECIPE_TC, "prototype_key": "the_bull_recipe", "description": "A scroll describing how to brew a strength potion from moonpetal essence and ogre's cap."},
    {"name": "Potion of Cat's Grace Recipe", "typeclass": _RECIPE_TC, "prototype_key": "cats_grace_recipe", "description": "A scroll describing how to brew a dexterity potion from moonpetal essence and vipervine."},
    {"name": "Potion of the Bear Recipe", "typeclass": _RECIPE_TC, "prototype_key": "the_bear_recipe", "description": "A scroll describing how to brew a constitution potion from moonpetal essence and ironbark."},
    {"name": "Potion of Fox's Cunning Recipe", "typeclass": _RECIPE_TC, "prototype_key": "foxs_cunning_recipe", "description": "A scroll describing how to brew an intelligence potion from moonpetal essence and mindcap."},
    {"name": "Potion of Owl's Insight Recipe", "typeclass": _RECIPE_TC, "prototype_key": "owls_insight_recipe", "description": "A scroll describing how to brew a wisdom potion from moonpetal essence and sage leaf."},
    {"name": "Potion of the Silver Tongue Recipe", "typeclass": _RECIPE_TC, "prototype_key": "silver_tongue_recipe", "description": "A scroll describing how to brew a charisma potion from moonpetal essence and siren petal."},
    {"name": "Pewter Ring Recipe", "typeclass": _RECIPE_TC, "prototype_key": "pewter_ring_recipe", "description": "A scroll showing how to shape a pewter ingot into a simple ring."},
    {"name": "Copper Ring Recipe", "typeclass": _RECIPE_TC, "prototype_key": "copper_ring_recipe", "description": "A scroll showing how to shape a copper ingot into a simple ring."},
    {"name": "Pewter Hoops Recipe", "typeclass": _RECIPE_TC, "prototype_key": "pewter_hoops_recipe", "description": "A scroll showing how to hammer pewter into a pair of small hoops."},
    {"name": "Copper Studs Recipe", "typeclass": _RECIPE_TC, "prototype_key": "copper_studs_recipe", "description": "A scroll showing how to fashion copper into a pair of small ear studs."},
    {"name": "Pewter Bracelet Recipe", "typeclass": _RECIPE_TC, "prototype_key": "pewter_bracelet_recipe", "description": "A scroll showing how to hammer pewter into a flat bracelet."},
    {"name": "Copper Bangle Recipe", "typeclass": _RECIPE_TC, "prototype_key": "copper_bangle_recipe", "description": "A scroll showing how to bend copper into a round bangle."},
    {"name": "Pewter Chain Recipe", "typeclass": _RECIPE_TC, "prototype_key": "pewter_chain_recipe", "description": "A scroll showing how to link pewter into a simple chain necklace."},
    {"name": "Copper Chain Recipe", "typeclass": _RECIPE_TC, "prototype_key": "copper_chain_recipe", "description": "A scroll showing how to link copper into a delicate chain necklace."},
    # ── Spell scrolls ──
    {"name": "Scroll of Magic Missile", "typeclass": _SPELL_SCROLL_TC, "prototype_key": "magic_missile_scroll", "description": "A crackling scroll inscribed with arcane glyphs of force."},
    {"name": "Scroll of Acid Arrow", "typeclass": _SPELL_SCROLL_TC, "prototype_key": "acid_arrow_scroll", "description": "A scroll that reeks of acrid fumes. Green liquid beads along the edges of the parchment."},
    {"name": "Scroll of Antimagic Field", "typeclass": _SPELL_SCROLL_TC, "prototype_key": "antimagic_field_scroll", "description": "A dull grey scroll that seems to absorb light. Nearby magical items flicker when you hold it."},
    {"name": "Scroll of Blur", "typeclass": _SPELL_SCROLL_TC, "prototype_key": "blur_scroll", "description": "A scroll whose text seems to shimmer and shift. Your eyes can never quite focus on it."},
    {"name": "Scroll of Cone of Cold", "typeclass": _SPELL_SCROLL_TC, "prototype_key": "cone_of_cold_scroll", "description": "A frost-rimed scroll that numbs your fingers to the touch. Ice crystals cling to the wax seal."},
    {"name": "Scroll of Conjure Elemental", "typeclass": _SPELL_SCROLL_TC, "prototype_key": "conjure_elemental_scroll", "description": "A scroll that radiates heat from one edge, cold from another, and faint tremors from a third. The fourth edge hums with wind."},
    {"name": "Scroll of Death Mark", "typeclass": _SPELL_SCROLL_TC, "prototype_key": "death_mark_scroll", "description": "A scroll branded with a skull-shaped sigil that seems to stare at whoever you point it at."},
    {"name": "Scroll of Dimensional Lock", "typeclass": _SPELL_SCROLL_TC, "prototype_key": "dimensional_lock_scroll", "description": "A scroll etched with angular geometric patterns that seem to pin the air in place around it."},
    {"name": "Scroll of Drain Life", "typeclass": _SPELL_SCROLL_TC, "prototype_key": "drain_life_scroll", "description": "A pallid scroll with veins of dark ink that seem to pulse. It feels cold and slightly hungry."},
    {"name": "Scroll of Fireball", "typeclass": _SPELL_SCROLL_TC, "prototype_key": "fireball_scroll", "description": "A smouldering scroll radiating intense heat. The parchment edges are singed black."},
    {"name": "Scroll of Gate", "typeclass": _SPELL_SCROLL_TC, "prototype_key": "gate_scroll", "description": "A scroll of impossible depth. Looking into the parchment, you see a swirling vortex that seems to lead somewhere else entirely."},
    {"name": "Scroll of Greater Invisibility", "typeclass": _SPELL_SCROLL_TC, "prototype_key": "greater_invisibility_scroll", "description": "A scroll that seems to fade in and out of existence. Even when you hold it, your fingers feel like they are gripping empty air."},
    {"name": "Scroll of Group Resist", "typeclass": _SPELL_SCROLL_TC, "prototype_key": "group_resist_scroll", "description": "A large scroll with concentric elemental wards. The runes pulse outward in expanding rings."},
    {"name": "Scroll of Identify", "typeclass": _SPELL_SCROLL_TC, "prototype_key": "identify_scroll", "description": "A scroll covered in tiny, precise runes that seem to rearrange themselves to describe whatever you hold near it."},
    {"name": "Scroll of Invisibility", "typeclass": _SPELL_SCROLL_TC, "prototype_key": "invisibility_scroll", "description": "A scroll that is almost impossible to find once you set it down. The text is written in ink that is only visible from certain angles."},
    {"name": "Scroll of Invulnerability", "typeclass": _SPELL_SCROLL_TC, "prototype_key": "invulnerability_scroll", "description": "A pristine white scroll that radiates an aura of absolute certainty. Nothing can touch it."},
    {"name": "Scroll of Mage Armor", "typeclass": _SPELL_SCROLL_TC, "prototype_key": "mage_armor_scroll", "description": "A smooth scroll with faintly glowing runes. It feels slightly warm and protective to the touch."},
    {"name": "Scroll of Mass Confusion", "typeclass": _SPELL_SCROLL_TC, "prototype_key": "mass_confusion_scroll", "description": "A scroll covered in contradictory symbols and impossible shapes. Reading it gives you a headache."},
    {"name": "Scroll of Mass Revelation", "typeclass": _SPELL_SCROLL_TC, "prototype_key": "mass_revelation_scroll", "description": "A scroll that pulses with blinding white light along every rune. Nothing can hide from its gaze."},
    {"name": "Scroll of Phantasmal Killer", "typeclass": _SPELL_SCROLL_TC, "prototype_key": "phantasmal_killer_scroll", "description": "A scroll that shows you something different every time you look at it, and none of it is pleasant."},
    {"name": "Scroll of Power Word: Death", "typeclass": _SPELL_SCROLL_TC, "prototype_key": "power_word_death_scroll", "description": "A scroll of absolute darkness. The ink writhes and pulses as if alive, and a faint whisper escapes when you hold it close."},
    {"name": "Scroll of Raise Dead", "typeclass": _SPELL_SCROLL_TC, "prototype_key": "raise_dead_scroll", "description": "A scroll of cracked, bone-white parchment. The ink smells faintly of grave dirt."},
    {"name": "Scroll of Raise Lich", "typeclass": _SPELL_SCROLL_TC, "prototype_key": "raise_lich_scroll", "description": "A scroll bound in leather that is definitely not animal hide. Arcane sigils of binding and domination cover every surface."},
    {"name": "Scroll of Resist Elements", "typeclass": _SPELL_SCROLL_TC, "prototype_key": "resist_elements_scroll", "description": "A scroll inscribed with shifting elemental sigils that dance across the surface."},
    {"name": "Scroll of Scry", "typeclass": _SPELL_SCROLL_TC, "prototype_key": "scry_scroll", "description": "A scroll with a translucent centre. If you peer through it, distant shapes seem to move just beyond focus."},
    {"name": "Scroll of Shadowcloak", "typeclass": _SPELL_SCROLL_TC, "prototype_key": "shadowcloak_scroll", "description": "Dark ink forms shifting shadow patterns across this scroll's surface, seeming to absorb the light around it."},
    {"name": "Scroll of Shield", "typeclass": _SPELL_SCROLL_TC, "prototype_key": "shield_scroll", "description": "A translucent scroll that shimmers faintly as if surrounded by an invisible barrier."},
    {"name": "Scroll of Soul Harvest", "typeclass": _SPELL_SCROLL_TC, "prototype_key": "soul_harvest_scroll", "description": "A scroll of absolute darkness. Faint screaming can be heard when you press your ear to it."},
    {"name": "Scroll of Teleport", "typeclass": _SPELL_SCROLL_TC, "prototype_key": "teleport_scroll", "description": "A scroll inscribed with swirling spatial runes. The parchment seems to shift position when you are not looking directly at it."},
    {"name": "Scroll of True Sight", "typeclass": _SPELL_SCROLL_TC, "prototype_key": "true_sight_scroll", "description": "A scroll bearing the image of an open eye wreathed in golden light. It seems to watch you back."},
    {"name": "Scroll of Vampiric Touch", "typeclass": _SPELL_SCROLL_TC, "prototype_key": "vampiric_touch_scroll", "description": "A dark crimson scroll that stains your fingers when you touch it. The ink seems to writhe."},
]


# ─── Seed functions ──────────────────────────────────────────────────

def seed_currency_types(apps, schema_editor):
    CurrencyType = apps.get_model("xrpl", "CurrencyType")
    for ct in CURRENCY_TYPES:
        # Strip non-model keys before passing to ORM
        fields = {k: v for k, v in ct.items() if k != "initial_reserve"}
        CurrencyType.objects.update_or_create(
            currency_code=ct["currency_code"],
            defaults=fields,
        )


def remove_currency_types(apps, schema_editor):
    CurrencyType = apps.get_model("xrpl", "CurrencyType")
    CurrencyType.objects.filter(
        currency_code__in=[ct["currency_code"] for ct in CURRENCY_TYPES]
    ).delete()


def seed_nft_item_types(apps, schema_editor):
    NFTItemType = apps.get_model("xrpl", "NFTItemType")
    for item in NFT_ITEM_TYPES:
        NFTItemType.objects.update_or_create(
            name=item["name"],
            defaults=item,
        )


def remove_nft_item_types(apps, schema_editor):
    NFTItemType = apps.get_model("xrpl", "NFTItemType")
    NFTItemType.objects.filter(
        name__in=[item["name"] for item in NFT_ITEM_TYPES]
    ).delete()


# ── Game state seed constants ────────────────────────────────────────

BLANK_TOKEN_COUNT = 200
INITIAL_GOLD_RESERVE = Decimal("1000000")
INITIAL_RESOURCE_RESERVE = Decimal("100000")


def _get_vault_address():
    """Read vault address from settings so seed data stays in sync."""
    from django.conf import settings
    return settings.XRPL_VAULT_ADDRESS


def seed_blank_nft_pool(apps, schema_editor):
    """Create 200 blank NFTGameState rows in RESERVE for the vault."""
    vault = _get_vault_address()
    NFTGameState = apps.get_model("xrpl", "NFTGameState")
    for i in range(1, BLANK_TOKEN_COUNT + 1):
        NFTGameState.objects.update_or_create(
            nftoken_id=str(i),
            defaults={
                "uri_id": i,
                "taxon": 0,
                "owner_in_game": vault,
                "location": "RESERVE",
                "item_type": None,
                "metadata": {},
            },
        )


def remove_blank_nft_pool(apps, schema_editor):
    vault = _get_vault_address()
    NFTGameState = apps.get_model("xrpl", "NFTGameState")
    NFTGameState.objects.filter(
        nftoken_id__in=[str(i) for i in range(1, BLANK_TOKEN_COUNT + 1)],
        owner_in_game=vault,
    ).delete()


def seed_fungible_reserves(apps, schema_editor):
    """Create RESERVE balance rows for gold (1M), resources (100k), and proxy tokens (per-token amounts)."""
    vault = _get_vault_address()
    FungibleGameState = apps.get_model("xrpl", "FungibleGameState")
    for ct in CURRENCY_TYPES:
        if "initial_reserve" in ct:
            balance = Decimal(ct["initial_reserve"])
        elif ct["is_gold"]:
            balance = INITIAL_GOLD_RESERVE
        else:
            balance = INITIAL_RESOURCE_RESERVE
        FungibleGameState.objects.update_or_create(
            currency_code=ct["currency_code"],
            wallet_address=vault,
            location="RESERVE",
            defaults={"balance": balance},
        )


def remove_fungible_reserves(apps, schema_editor):
    vault = _get_vault_address()
    FungibleGameState = apps.get_model("xrpl", "FungibleGameState")
    FungibleGameState.objects.filter(
        wallet_address=vault,
        location="RESERVE",
        currency_code__in=[ct["currency_code"] for ct in CURRENCY_TYPES],
    ).delete()


# ─── Migration ───────────────────────────────────────────────────────

class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        # ── CurrencyType ──
        migrations.CreateModel(
            name="CurrencyType",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("currency_code", models.CharField(max_length=40, unique=True)),
                ("resource_id", models.PositiveIntegerField(blank=True, null=True, unique=True)),
                ("name", models.CharField(max_length=50)),
                ("unit", models.CharField(max_length=30)),
                ("description", models.TextField(blank=True, default="")),
                ("weight_per_unit_kg", models.DecimalField(decimal_places=3, default=0, help_text="Weight in kg per single unit of this currency.", max_digits=6)),
                ("is_gold", models.BooleanField(default=False)),
            ],
            options={
                "verbose_name": "Currency Type",
                "verbose_name_plural": "Currency Types",
                "ordering": ["currency_code"],
            },
        ),
        # ── NFTItemType ──
        migrations.CreateModel(
            name="NFTItemType",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=100, unique=True)),
                ("typeclass", models.CharField(max_length=255)),
                ("prototype_key", models.CharField(blank=True, max_length=255, null=True)),
                ("description", models.TextField(blank=True, default="")),
                ("default_metadata", models.JSONField(default=dict)),
                ("tracking_token", models.CharField(blank=True, help_text="Proxy token currency code for AMM pricing. NULL = not tradeable.", max_length=40, null=True, unique=True)),
            ],
            options={
                "verbose_name": "NFT Item Type",
                "verbose_name_plural": "NFT Item Types",
            },
        ),
        # ── FungibleGameState ──
        migrations.CreateModel(
            name="FungibleGameState",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("currency_code", models.CharField(db_index=True, max_length=40)),
                ("wallet_address", models.CharField(db_index=True, max_length=50)),
                ("location", models.CharField(choices=[("RESERVE", "Reserve"), ("SPAWNED", "Spawned"), ("ACCOUNT", "Account"), ("CHARACTER", "Character")], default="RESERVE", max_length=10)),
                ("character_key", models.CharField(blank=True, max_length=255, null=True)),
                ("balance", models.DecimalField(decimal_places=6, max_digits=36)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Fungible Game State",
                "verbose_name_plural": "Fungible Game States",
            },
        ),
        migrations.AddIndex(
            model_name="fungiblegamestate",
            index=models.Index(fields=["currency_code"], name="xrpl_fungib_currenc_idx"),
        ),
        migrations.AddIndex(
            model_name="fungiblegamestate",
            index=models.Index(fields=["wallet_address"], name="xrpl_fungib_wallet__idx"),
        ),
        migrations.AddConstraint(
            model_name="fungiblegamestate",
            constraint=models.CheckConstraint(condition=models.Q(location__in=["RESERVE", "SPAWNED", "ACCOUNT", "CHARACTER", "SINK"]), name="xrpl_fungible_location_valid"),
        ),
        migrations.AddConstraint(
            model_name="fungiblegamestate",
            constraint=models.CheckConstraint(condition=(models.Q(location="CHARACTER", character_key__isnull=False) | (~models.Q(location="CHARACTER") & models.Q(character_key__isnull=True))), name="xrpl_fungible_character_key_iff_character"),
        ),
        migrations.AddConstraint(
            model_name="fungiblegamestate",
            constraint=models.CheckConstraint(condition=models.Q(balance__gt=0), name="xrpl_fungible_balance_positive"),
        ),
        migrations.AddConstraint(
            model_name="fungiblegamestate",
            constraint=models.UniqueConstraint(condition=~models.Q(location="CHARACTER"), fields=["currency_code", "wallet_address", "location"], name="xrpl_fungible_unique_plain"),
        ),
        migrations.AddConstraint(
            model_name="fungiblegamestate",
            constraint=models.UniqueConstraint(condition=models.Q(location="CHARACTER"), fields=["currency_code", "wallet_address", "location", "character_key"], name="xrpl_fungible_unique_character"),
        ),
        # ── NFTGameState ──
        migrations.CreateModel(
            name="NFTGameState",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("nftoken_id", models.CharField(max_length=64, unique=True)),
                ("uri_id", models.PositiveIntegerField(blank=True, help_text="Permanent ID matching the on-chain URI (/nft/<uri_id>).", null=True, unique=True)),
                ("taxon", models.PositiveIntegerField()),
                ("owner_in_game", models.CharField(blank=True, max_length=50, null=True)),
                ("location", models.CharField(choices=[("RESERVE", "Reserve"), ("SPAWNED", "Spawned"), ("AUCTION", "Auction"), ("ACCOUNT", "Account"), ("CHARACTER", "Character"), ("ONCHAIN", "On Chain")], default="RESERVE", max_length=10)),
                ("character_key", models.CharField(blank=True, max_length=255, null=True)),
                ("item_type", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="nft_states", to="xrpl.nftitemtype")),
                ("metadata", models.JSONField(default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "NFT Game State",
                "verbose_name_plural": "NFT Game States",
            },
        ),
        migrations.AddIndex(
            model_name="nftgamestate",
            index=models.Index(fields=["owner_in_game"], name="xrpl_nftgam_owner_i_idx"),
        ),
        migrations.AddIndex(
            model_name="nftgamestate",
            index=models.Index(fields=["taxon"], name="xrpl_nftgam_taxon_idx"),
        ),
        migrations.AddConstraint(
            model_name="nftgamestate",
            constraint=models.CheckConstraint(condition=models.Q(location__in=["RESERVE", "SPAWNED", "AUCTION", "ACCOUNT", "CHARACTER", "ONCHAIN"]), name="xrpl_nft_location_valid"),
        ),
        migrations.AddConstraint(
            model_name="nftgamestate",
            constraint=models.CheckConstraint(condition=(models.Q(location="CHARACTER", character_key__isnull=False) | (~models.Q(location="CHARACTER") & models.Q(character_key__isnull=True))), name="xrpl_nft_character_key_iff_character"),
        ),
        migrations.AddConstraint(
            model_name="nftgamestate",
            constraint=models.CheckConstraint(condition=(models.Q(location="ONCHAIN", owner_in_game__isnull=True) | (~models.Q(location="ONCHAIN") & models.Q(owner_in_game__isnull=False))), name="xrpl_nft_owner_iff_not_onchain"),
        ),
        # ── FungibleTransferLog ──
        migrations.CreateModel(
            name="FungibleTransferLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("currency_code", models.CharField(max_length=40)),
                ("from_wallet", models.CharField(max_length=50)),
                ("to_wallet", models.CharField(max_length=50)),
                ("amount", models.DecimalField(decimal_places=6, max_digits=36)),
                ("transfer_type", models.CharField(max_length=30)),
                ("timestamp", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "verbose_name": "Fungible Transfer Log",
                "verbose_name_plural": "Fungible Transfer Logs",
            },
        ),
        migrations.AddIndex(
            model_name="fungibletransferlog",
            index=models.Index(fields=["currency_code"], name="xrpl_fungtr_currenc_idx"),
        ),
        migrations.AddIndex(
            model_name="fungibletransferlog",
            index=models.Index(fields=["from_wallet"], name="xrpl_fungtr_from_wa_idx"),
        ),
        migrations.AddIndex(
            model_name="fungibletransferlog",
            index=models.Index(fields=["to_wallet"], name="xrpl_fungtr_to_wall_idx"),
        ),
        migrations.AddIndex(
            model_name="fungibletransferlog",
            index=models.Index(fields=["timestamp"], name="xrpl_fungtr_timesta_idx"),
        ),
        migrations.AddConstraint(
            model_name="fungibletransferlog",
            constraint=models.CheckConstraint(condition=models.Q(amount__gt=0), name="xrpl_fungible_transfer_amount_positive"),
        ),
        migrations.AddConstraint(
            model_name="fungibletransferlog",
            constraint=models.CheckConstraint(condition=~models.Q(from_wallet=models.F("to_wallet")), name="xrpl_fungible_transfer_not_self"),
        ),
        # ── NFTTransferLog ──
        migrations.CreateModel(
            name="NFTTransferLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("nftoken_id", models.CharField(max_length=64)),
                ("from_wallet", models.CharField(max_length=50)),
                ("to_wallet", models.CharField(max_length=50)),
                ("transfer_type", models.CharField(max_length=30)),
                ("timestamp", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "verbose_name": "NFT Transfer Log",
                "verbose_name_plural": "NFT Transfer Logs",
            },
        ),
        migrations.AddIndex(
            model_name="nfttransferlog",
            index=models.Index(fields=["nftoken_id"], name="xrpl_nfttr_nftoken_idx"),
        ),
        migrations.AddIndex(
            model_name="nfttransferlog",
            index=models.Index(fields=["timestamp"], name="xrpl_nfttr_timesta_idx"),
        ),
        migrations.AddConstraint(
            model_name="nfttransferlog",
            constraint=models.CheckConstraint(condition=~models.Q(from_wallet=models.F("to_wallet")), name="xrpl_nft_transfer_not_self"),
        ),
        # ── XRPLTransactionLog ──
        migrations.CreateModel(
            name="XRPLTransactionLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("tx_hash", models.CharField(max_length=64, unique=True)),
                ("tx_type", models.CharField(max_length=20)),
                ("currency_code", models.CharField(blank=True, max_length=40, null=True)),
                ("nftoken_id", models.CharField(blank=True, max_length=64, null=True)),
                ("amount", models.DecimalField(blank=True, decimal_places=6, max_digits=36, null=True)),
                ("wallet_address", models.CharField(max_length=50)),
                ("status", models.CharField(default="pending", max_length=10)),
                ("ledger_index", models.PositiveBigIntegerField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "XRPL Transaction Log",
                "verbose_name_plural": "XRPL Transaction Logs",
            },
        ),
        migrations.AddIndex(
            model_name="xrpltransactionlog",
            index=models.Index(fields=["status"], name="xrpl_xrpltx_status_idx"),
        ),
        migrations.AddIndex(
            model_name="xrpltransactionlog",
            index=models.Index(fields=["wallet_address"], name="xrpl_xrpltx_wallet_idx"),
        ),
        # ── PlayerSession (telemetry) ──
        migrations.CreateModel(
            name="PlayerSession",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("account_id", models.IntegerField(help_text="Evennia account ID (AccountDB.id)")),
                ("character_key", models.CharField(help_text="Character db_key at session start", max_length=80)),
                ("started_at", models.DateTimeField()),
                ("ended_at", models.DateTimeField(blank=True, null=True)),
            ],
        ),
        migrations.AddIndex(
            model_name="playersession",
            index=models.Index(fields=["started_at"], name="xrpl_session_started_idx"),
        ),
        migrations.AddIndex(
            model_name="playersession",
            index=models.Index(fields=["account_id", "started_at"], name="xrpl_session_acct_started_idx"),
        ),
        # ── EconomySnapshot (telemetry) ──
        migrations.CreateModel(
            name="EconomySnapshot",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("hour", models.DateTimeField(unique=True)),
                ("players_online", models.IntegerField(default=0, help_text="Players online at snapshot time")),
                ("unique_players_1h", models.IntegerField(default=0, help_text="Distinct accounts active in past hour")),
                ("unique_players_24h", models.IntegerField(default=0, help_text="Distinct accounts active in past 24 hours")),
                ("unique_players_7d", models.IntegerField(default=0, help_text="Distinct accounts active in past 7 days")),
                ("gold_circulation", models.DecimalField(decimal_places=6, default=0, help_text="Total gold in CHARACTER + ACCOUNT locations", max_digits=36)),
                ("gold_reserve", models.DecimalField(decimal_places=6, default=0, help_text="Total gold in RESERVE location", max_digits=36)),
                ("gold_sinks_1h", models.DecimalField(decimal_places=6, default=0, help_text="Gold in SINK location (consumed, awaiting reallocation)", max_digits=36)),
                ("gold_spawned_1h", models.DecimalField(decimal_places=6, default=0, help_text="Gold spawned (pickup from SPAWNED) in the past hour", max_digits=36)),
                ("amm_trades_1h", models.IntegerField(default=0, help_text="Number of AMM trades in the past hour")),
                ("amm_volume_gold_1h", models.DecimalField(decimal_places=6, default=0, help_text="Total gold volume through AMM in the past hour", max_digits=36)),
                ("imports_1h", models.IntegerField(default=0, help_text="Fungible imports from chain in the past hour")),
                ("exports_1h", models.IntegerField(default=0, help_text="Fungible exports to chain in the past hour")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "ordering": ["-hour"],
            },
        ),
        # ── ResourceSnapshot (telemetry) ──
        migrations.CreateModel(
            name="ResourceSnapshot",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("hour", models.DateTimeField()),
                ("currency_code", models.CharField(max_length=40)),
                ("in_character", models.DecimalField(decimal_places=6, default=0, help_text="Total in player inventories", max_digits=36)),
                ("in_account", models.DecimalField(decimal_places=6, default=0, help_text="Total in player banks", max_digits=36)),
                ("in_spawned", models.DecimalField(decimal_places=6, default=0, help_text="Total spawned in world (ground, mob loot, chests)", max_digits=36)),
                ("in_reserve", models.DecimalField(decimal_places=6, default=0, help_text="Total in game vault reserve", max_digits=36)),
                ("in_sink", models.DecimalField(decimal_places=6, default=0, help_text="Total consumed (fees, crafting, dust) awaiting reallocation", max_digits=36)),
                ("produced_1h", models.DecimalField(decimal_places=6, default=0, help_text="craft_output + pickup (from SPAWNED) in past hour", max_digits=36)),
                ("consumed_1h", models.DecimalField(decimal_places=6, default=0, help_text="craft_input in past hour", max_digits=36)),
                ("traded_1h", models.DecimalField(decimal_places=6, default=0, help_text="amm_buy + amm_sell volume (resource side) in past hour", max_digits=36)),
                ("exported_1h", models.DecimalField(decimal_places=6, default=0, help_text="withdraw_to_chain in past hour", max_digits=36)),
                ("imported_1h", models.DecimalField(decimal_places=6, default=0, help_text="deposit_from_chain in past hour", max_digits=36)),
                ("amm_buy_price", models.DecimalField(blank=True, decimal_places=6, help_text="Gold cost to buy 1 unit from AMM", max_digits=36, null=True)),
                ("amm_sell_price", models.DecimalField(blank=True, decimal_places=6, help_text="Gold received from selling 1 unit to AMM", max_digits=36, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "ordering": ["-hour"],
            },
        ),
        migrations.AddConstraint(
            model_name="resourcesnapshot",
            constraint=models.UniqueConstraint(fields=["hour", "currency_code"], name="xrpl_unique_resource_snapshot_hour"),
        ),
        # ── BulletinListing (trading post) ──
        migrations.CreateModel(
            name="BulletinListing",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("account_id", models.IntegerField(help_text="Evennia account ID of poster")),
                ("character_name", models.CharField(help_text="Character name at time of posting", max_length=80)),
                ("listing_type", models.CharField(choices=[("WTS", "Want to Sell"), ("WTB", "Want to Buy")], max_length=3)),
                ("message", models.CharField(max_length=200)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("expires_at", models.DateTimeField()),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="bulletinlisting",
            index=models.Index(fields=["expires_at"], name="xrpl_bulletinli_expires_idx"),
        ),
        # ── SaturationSnapshot (daily NFT item saturation) ──
        migrations.CreateModel(
            name="SaturationSnapshot",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("day", models.DateField()),
                ("item_key", models.CharField(max_length=80)),
                ("category", models.CharField(choices=[("spell", "Spell"), ("recipe", "Recipe"), ("item", "Item")], max_length=10)),
                ("active_players_7d", models.IntegerField()),
                ("eligible_players", models.IntegerField(default=0)),
                ("known_by", models.IntegerField(default=0)),
                ("unlearned_copies", models.IntegerField(default=0)),
                ("in_circulation", models.IntegerField(default=0)),
                ("saturation", models.FloatField(default=0.0)),
            ],
            options={
                "ordering": ["-day"],
            },
        ),
        migrations.AddConstraint(
            model_name="saturationsnapshot",
            constraint=models.UniqueConstraint(fields=["day", "item_key", "category"], name="xrpl_unique_saturation_day_item"),
        ),
        # ── Seed data ──
        migrations.RunPython(seed_currency_types, remove_currency_types),
        migrations.RunPython(seed_nft_item_types, remove_nft_item_types),
        migrations.RunPython(seed_blank_nft_pool, remove_blank_nft_pool),
        migrations.RunPython(seed_fungible_reserves, remove_fungible_reserves),
    ]
