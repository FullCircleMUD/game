# CLAUDE.md

> **THIS FILE is for TECHNICAL details only** — architecture, code patterns, APIs, implementation guidelines, and development workflow. For world building, lore, narratives, zone designs, NPC concepts, and creative direction, see **design/WORLD.md**. For economic design — pricing models, market structures, spawn algorithms, gold sinks, revenue models, and trade mechanics — see **design/ECONOMY.md**. Do not put world building or economic design content here.

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Game code for **FullCircleMUD** — a text-based MUD built on the Evennia framework (Python/Django) with real blockchain item ownership. This folder (`FullCircleMUD/`) is the Evennia game module and lives inside `EvenniaFCM/` (the Evennia game directory).

Domain: **fcmud.world**. Chain: **XRPL** (primary). Legacy Polygon contracts deployed but no longer in active use.

## Evennia Project Structure

```
EvenniaFCM/                     ← run `evennia start` from here
├── FullCircleMUD/              ← THIS repo — all game code
│   ├── blockchain/
│   │   ├── polygon/            ← Polygon Django app (legacy — models + migrations only)
│   │   │   ├── models.py       ← 14 models (retained for migration compatibility)
│   │   │   ├── db_router.py    ← routes app_label="polygon" → "blockchain" DB
│   │   │   └── migrations/     ← seed data migrations (resource types, NFT item types, dev data)
│   │   └── xrpl/               ← XRPL Django app — same service interfaces, no sync needed
│   │       ├── models.py       ← 12 models (unified FungibleGameState, NFTGameState, telemetry snapshots, etc.)
│   │       ├── services/       ← GoldService, ResourceService, NFTService, FungibleService, AMMService, TelemetryService, ResourceSpawnService, NFTSaturationService
│   │       ├── xrpl_amm.py      ← XRPL AMM pool queries, constant product pricing, swap execution
│   │       ├── currency_cache.py ← in-memory CurrencyType cache (resource_id ↔ currency_code)
│   │       ├── db_router.py    ← routes app_label="xrpl" → "xrpl" DB
│   │       └── migrations/     ← consolidated 0001_initial.py with seed data
│   ├── commands/
│   │   ├── account_cmds/       ← account-level commands (charcreate, chardelete, bank, wallet, import, export)
│   │   ├── all_char_cmds/      ← character commands (junk, get, drop, give, movement, wear, learn, recipes, etc.)
│   │   ├── class_skill_cmdsets/
│   │   ├── general_skill_cmds/
│   │   ├── npc_cmds/             ← NPC-injected commands (trainer, guildmaster, shopkeeper CmdSets)
│   │   ├── room_specific_cmds/ ← bank, inn, processing, crafting, harvesting, cemetery (bind), purgatory (release), tutorial
│   │   ├── unloggedin_cmds/    ← Xaman wallet auth commands (create/connect)
│   │   └── weapon_skill_cmds/
│   ├── combat/                   ← combat system (handler, attack resolution, side detection, reactive_spells)
│   ├── enums/                  ← game enumerations (abilities, alignment, condition, named_effect, damage_type, death_cause, hunger, mastery, skills, weapon types, wearslots, crafting types)
│   ├── registries/             ← base registry class (race/class registries are auto-collecting in their own __init__.py)
│   ├── rules/                  ← random tables, game rules
│   ├── server/
│   │   ├── conf/settings.py    ← contract addresses, chain config, XRPL config
│   │   ├── conf/inputfuncs.py  ← OOB response handlers (empty — will be populated for XRPL import/export)
│   │   └── walletwebclient.py  ← custom web client
│   ├── tests/
│   │   ├── blockchain_tests/   ← (deleted — Polygon services removed)
│   │   ├── xrpl_tests/         ← XRPL service tests (4 files, 71 tests)
│   │   ├── command_tests/      ← command tests (39+ files)
│   │   ├── typeclass_tests/    ← typeclass/mixin tests (21 files)
│   │   ├── server_tests/       ← server lifecycle tests (3 files)
│   │   ├── tutorial_tests/      ← tutorial system tests (4 files, 96 tests)
│   │   └── utils_tests/        ← utility tests (5 files)
│   ├── typeclasses/
│   │   ├── accounts/account_bank.py  ← AccountBank (FungibleInventoryMixin + wallet_address)
│   │   ├── actors/
│   │   │   ├── character.py          ← FCMCharacter (all mixins + DefaultCharacter)
│   │   │   ├── base_actor.py         ← BaseActor (shared ability scores, stats)
│   │   │   ├── npc.py                ← BaseNPC (shared NPC base, _EmptyNPCCmdSet)
│   │   │   ├── ai_handler.py         ← AIHandler state machine + AIMixin
│   │   │   ├── mob.py                ← CombatMob (AI-driven mobs with combat, common mobs deleted on death)
│   │   │   ├── npcs/                 ← NPC subtypes (TrainerNPC, GuildmasterNPC, ShopkeeperNPC [scaffolded], TutorialGuideNPC, LLMRoleplayNPC, BartenderNPC, QuestGivingShopkeeper, BakerNPC)
│   │   │   ├── mobs/                 ← mob subtypes (AggressiveMob, Rabbit, Wolf, DireWolf, CellarRat, Kobold, KoboldChieftain, Gnoll, GnollWarlord, TrainingDummy)
│   │   │   ├── races/               ← auto-collecting race registry (Race enum, RaceBase dataclass)
│   │   │   └── char_classes/        ← auto-collecting class registry (CharClass enum, CharClassBase dataclass)
│   │   ├── items/
│   │   │   ├── base_nft_item.py      ← BaseNFTItem (full at_post_move/at_object_delete dispatch)
│   │   │   ├── wearables/            ← WearableNFTItem (at_wear/at_remove hooks)
│   │   │   ├── holdables/            ← HoldableNFTItem (at_hold/at_remove hooks)
│   │   │   ├── weapons/              ← WeaponNFTItem + subclasses (Longsword, Dagger, Shortsword, Bow, Club, Greatclub, Spear, Axe, Greatsword, Mace, Hammer, Sling, etc.)
│   │   │   ├── consumables/          ← ConsumableNFTItem, CraftingRecipeNFTItem, SpellScrollNFTItem
│   │   │   └── components/           ← ComponentNFTItem (non-weapon crafting inputs, e.g. Shaft, Haft, Leather Straps)
│   │   ├── mixins/
│   │   │   ├── carrying_capacity.py   ← CarryingCapacityMixin (weight/encumbrance)
│   │   │   ├── effects_manager.py      ← EffectsManagerMixin (unified effect system — conditions + stat effects + named effects)
│   │   │   ├── damage_resistance.py   ← DamageResistanceMixin (resistance/vulnerability tracking)
│   │   │   ├── durability.py          ← DurabilityMixin (item durability)
│   │   │   ├── fungible_inventory.py  ← gold + resource service integration for any object
│   │   │   ├── item_restriction.py    ← ItemRestrictionMixin (class/race/level/alignment gates)
│   │   │   ├── quest_giver.py         ← QuestGiverMixin (quest accept/abandon/view/turn-in command)
│   │   │   ├── quest_tag.py           ← QuestTagMixin (fire_quest_event for quest-relevant objects)
│   │   │   ├── recipe_book.py         ← RecipeBookMixin (recipe learning and lookup)
│   │   │   └── wearslots/             ← BaseWearslotsMixin, HumanoidWearslotsMixin, DogWearslotsMixin
│   │   ├── world_objects/
│   │   │   └── corpse.py             ← Corpse (dropped on death, loot command, decay timers)
│   │   └── terrain/rooms/            ← RoomBase (zone/district tag helpers), RoomBank, RoomRecycleBin, RoomProcessing, RoomCrafting, RoomHarvesting, RoomInn, RoomCemetery, RoomPurgatory
│   ├── world/
│   │   ├── quests/              ← quest system (base_quest, quest_handler, registry, templates)
│   │   │   ├── guild/           ← guild quests (warrior_initiation, thief_initiation, mage_initiation, cleric_initiation)
│   │   │   └── templates/       ← quest templates (collect, visit, multi-step)
│   │   ├── recipes/             ← crafting recipes by skill
│   │   ├── spells/              ← spell registry and implementations
│   │   ├── prototypes/          ← item prototypes (one file per item)
│   │   ├── spawns/              ← zone spawn rule JSON files (one per zone)
│   │   ├── dungeons/            ← dungeon templates (DungeonTemplate, Cave of Trials, Rat Cellar)
│   │   ├── tutorial/            ← tutorial zone builders (hub, tutorial_1, tutorial_2, tutorial_3, tutorial_exit)
│   │   └── test_world/          ← test area builders, NPC/mob spawners
│   ├── utils/                    ← game utilities (item_parse, dice, experience, etc.)
│   └── web/                    ← web client overrides
├── evennia/                    ← Evennia framework (never modified, not in git)
├── secret_settings.py          ← private keys (not in git)
└── venv/                       ← Python venv (not in git, recreate with pip install evennia)
```

## Commands

```bash
# Activate venv (from EvenniaFCM/)
source venv/bin/activate

# Start/stop/restart game server
evennia start
evennia stop
evennia restart

# Open Django shell
evennia shell

# Migrations — XRPL (after changing blockchain/xrpl/models.py)
evennia makemigrations xrpl
evennia migrate --database xrpl
```

### Running Tests

**IMPORTANT:** Tests must be run from inside the `FullCircleMUD/` folder, not from `EvenniaFCM/`. Use `--settings settings` so Evennia picks up the project's `server/conf/settings.py` rather than the default Evennia settings. Import paths in tests are relative to `FullCircleMUD/`.

```bash
# From EvenniaFCM/FullCircleMUD/ (with venv activated):

# Run a specific test module
evennia test --settings settings tests.typeclass_tests.test_fungible_inventory

# Run multiple test modules at once
evennia test --settings settings tests.typeclass_tests.test_fungible_inventory tests.typeclass_tests.test_base_nft_item tests.command_tests.test_cmd_junk

# Run all tests
evennia test --settings settings tests
```

**Test base classes:**
- `EvenniaTest` — for testing typeclasses, mixins, models. Auto-creates `self.char1`, `self.char2`, `self.room1`, `self.room2`, `self.account`, `self.account2`.
- `EvenniaCommandTest` — adds `self.call(CmdClass(), "args")` for testing commands. Returns the output string. The `inputs` list feeds responses to `yield` prompts.

**Common test patterns:**
- Override `create_script` as a no-op (`def create_script(self): pass`) — the default `typeclasses.scripts.Script` has been repurposed.
- Set `room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"` when testing anything that uses FungibleInventoryMixin on rooms.
- Set `databases = "__all__"` on test classes that query the `blockchain` database (resource type lookups, mirror records, chain state).
- For NFT tests: create without location, set attributes via property, then `move_to()` — don't use `create_object(attributes=[...])` as kwargs don't reliably overwrite `AttributeProperty` defaults before hooks fire.
- **`self.call()` matching:** Evennia uses `startswith()` when `msg` is passed as a positional arg. Commands with headers/footers won't match — use `result = self.call(...); self.assertIn("text", result)` instead.
- **Token ID collisions:** Use high token IDs (e.g. 100+) in tests to avoid colliding with seed data (tokens 1–50) or records created by other test classes earlier in the run.

## Command Architecture

Commands are organized into three custom cmdsets that merge on top of Evennia's defaults:

```
commands/
├── default_cmdsets.py              ← loads Evennia defaults via super(), then merges custom cmdsets
├── all_char_cmds/
│   ├── cmdset_character_custom.py  ← CmdSetCharacterCustom (merged into CharacterCmdSet)
│   ├── cmd_override_*.py           ← overrides of Evennia default commands
│   └── cmd_*.py                    ← new custom commands
├── account_cmds/
│   ├── cmdset_account_custom.py    ← CmdSetAccountCustom (merged into AccountCmdSet)
│   └── cmd_*.py
├── class_skill_cmdsets/
│   ├── cmdset_base_char_class.py   ← CmdSetBaseCharClass (base for all class cmdsets)
│   ├── cmdset_warrior.py           ← CmdSetWarrior (bash, pummel, retreat, protect, taunt, offence, defence)
│   ├── cmdset_thief.py             ← CmdSetThief (picklock, pickpocket, disarm, stab, recite, sneak)
│   ├── cmdset_mage.py              ← CmdSetMage (empty — schools use cast/transcribe/memorise)
│   ├── cmdset_cleric.py            ← CmdSetCleric (turn)
│   ├── cmdset_bard.py              ← CmdSetBard (perform, inspire, mock, charm, divert, disguise, conceal, identify, sneak, stash, picklock, pickpocket, disarm)
│   ├── cmdset_berserker.py         ← CmdSetBerserker (frenzy, taunt)
│   ├── cmdset_paladin.py           ← CmdSetPaladin (protect, taunt, turn)
│   ├── cmdset_ninja.py             ← CmdSetNinja (stab, assassinate, recite, sneak, stash, picklock, pickpocket, disarm)
│   ├── cmdset_druid.py             ← CmdSetDruid (forage, track, summon, dismiss, shapeshift)
│   ├── cmdset_ranger.py            ← CmdSetRanger (forage, track, summon, dismiss)
│   └── class_skill_cmds/           ← CmdSkillBase + all skill command files (31 scaffolds + existing)
├── general_skill_cmds/
│   └── cmdset_general_skills.py    ← CmdSetGeneralSkills (dodge, assist, chart, build, sail, explore, tame, repair)
├── all_char_cmds/
│   ├── cmdset_socials.py           ← CmdSetSocials (50 data-driven social commands + socials list)
│   ├── socials_data.py             ← SOCIALS registry dict (message variants per social)
│   └── cmd_social.py               ← CmdSocialBase + factory + CmdSocials list command
└── unloggedin_cmds/
    ├── cmdset_unloggedin_custom.py ← CmdSetUnloggedinCustom (merged into UnloggedinCmdSet)
    └── cmd_override_*.py
```

**Adding a new custom command:**
1. Create `commands/all_char_cmds/cmd_mycommand.py` with a `Command` subclass
2. Import and `self.add(CmdMyCommand())` in `cmdset_character_custom.py`
3. Always add instances `()`, not bare class references

### Help Categories

Commands are organised into help categories via `help_category` on each command class. The categories are:

| Category | Commands |
|---|---|
| **Character** | stats, score, skills, fly, swim, where, hunger, languages (lang), weight, quests, remort, setdesc |
| **Combat** | attack, flee, dodge, assist, bash, pummel, stab, assassinate, frenzy, turn, protect, taunt, mock, consider |
| **Communication** | say, shout, whisper, pose, who |
| **Crafting** | learn, recipes, repair (skill) + room-specific: craft/forge/carve/sew/brew/enchant, available, process/mill/bake/smelt/saw/tan/weave, rates |
| **Exploration** | build, chart, sail, explore |
| **General** | look, scan, diagnose, exits |
| **Group** | follow, unfollow, nofollow, group |
| **Group Combat** | offence, defence, retreat |
| **Items** | get, drop, give, inventory, equipment, wear, wield, hold, remove, junk, loot, quaff, eat, put |
| **Magic** | cast, transcribe, memorise, forget, spells, recite |
| **Nature** | forage, track, summon, dismiss, shapeshift, tame |
| **Performance** | perform, inspire, charm, divert, identify |
| **Stealth** | hide (all chars), stash, case, conceal, disguise, picklock, pickpocket, disarm_trap |
| **System** | quit, nick, access, ic, ooc, sessions, option, colortest, quell, style, charcreate, chardelete |
| **Socials** | 50 data-driven social commands (bow, wave, laugh, shrug, etc.) + `socials` list command |
| **Blockchain** | bank, wallet, import, export (OOC only — hidden when puppeting) |

### Evennia Default Command Overrides

Several Evennia default commands are overridden with thin subclasses that only change `help_category` (or `locks`). These live at the top of the respective cmdset files:

**In `cmdset_character_custom.py`:** CmdPose→Communication, CmdNick→System, CmdSetDesc→Character, CmdAccess→System

**In `cmdset_account_custom.py`:** CmdIC→System, CmdOOC→System, CmdSessions→System, CmdWho→Communication, CmdOption→System, CmdPassword→superuser-only (`cmd:id(1)`), CmdNewPassword→superuser-only (`cmd:id(1)`), CmdColorTest→System, CmdQuell→System, CmdStyle→System

### OOC-Only Commands (`is_ooc()` Lock)

Commands that should only be available when NOT puppeting a character use the `is_ooc()` custom lock function (`server/conf/lockfuncs.py`). Evennia's `cmd:` lock controls both execution AND visibility in the help listing — a command that fails its `cmd:` lock is hidden from `help`.

```python
# server/conf/lockfuncs.py
def is_ooc(accessing_obj, accessed_obj, *args, **kwargs):
    if hasattr(accessing_obj, "get_all_puppets"):
        return not accessing_obj.get_all_puppets()
    return False
```

**Commands using `is_ooc()`:**
- `bank`, `wallet`, `import`, `export` — `locks = "cmd:is_ooc()"`
- `charcreate`, `chardelete` — `locks = "cmd:pperm(Player) and is_ooc()"`

### Multi-Perspective Messaging

Whenever a character performs a visible action (command, spell, skill, etc.), use multi-perspective messaging so different observers get the correct perspective. The preferred approach is `location.msg_contents()` with Evennia's `$You()` / `$conj()` substitution, or explicit first/second/third person messages:

```python
# Option A: Evennia's $You/$conj (used by wear/wield/hold/get/drop/remove/give)
caller.location.msg_contents(
    "$You() $conj(fire) a glowing missile at {target}!",
    from_obj=caller,
    mapping={"target": target},
)

# Option B: Explicit message dict (used by spells)
# Spell._execute returns: {"first": "...", "second": "...", "third": "..."}
caller.msg(result["first"])                           # caster sees
if target and target != caller and result.get("second"):
    target.msg(result["second"])                      # target sees
if caller.location and result.get("third"):
    caller.location.msg_contents(                     # room sees
        result["third"],
        exclude=[caller, target] if target != caller else [caller],
    )
```

**IMPORTANT:** `from_obj=caller` is required not just for `$You()/$conj()` substitution but also for HIDDEN/INVISIBLE visibility filtering. `RoomBase.msg_contents()` checks `from_obj` for visibility conditions — without it, messages bypass filtering entirely. See ConditionsMixin section for details.

## Blockchain Integration

### Settings (server/conf/settings.py)

```python
# XRPL (active — game code imports from here)
XRPL_NETWORK_URL        = "wss://s.altnet.rippletest.net:51233"
XRPL_ISSUER_ADDRESS     = "rMq4xJGybcSCw1gWMzcRpBMsHJosBSa6Ex"
XRPL_VAULT_ADDRESS      = "rhfi58eft1jpzHr2DYXirocq1tgUfAfgsA"
XRPL_ROOT_ADDRESS       = "rsANvPX4Uq6FSYqXQ4i7UTAXatcS3qQz59"
XRPL_GOLD_CURRENCY_CODE = "FCMGold"
XAMAN_API_KEY / XAMAN_API_SECRET  # in secret_settings.py

# Polygon (legacy — contracts still deployed, code untouched)
CONTRACT_GOLD      = "0x1c3510bfcc6bf24865b4f24b971070389BB39bd1"
CONTRACT_NFT       = "0xe8ae00eDC2683B2F9043053DE2d937779391C1Fd"
CONTRACT_RESOURCES = "0x7Ea239245C600497955742C60de14f3f7B08F9f2"
CONTRACT_VAULT     = "0x2ce942F34EcaeBFD24a7b25561aD9c164988B2d5"
CONTRACT_TREASURY  = "0xCcA970Dca1c1912091473B3EEB9a79B84D02C6ef"

GOLD_DISPLAY = {"name": "Gold", "unit": "coins", "description": "Gold coins."}
```

### Authentication — Xaman (XRPL Wallet)

Auth uses Xaman (formerly Xumm) server-side payloads — no client-side JS or OOB needed:

1. Player types `connect`
2. Server creates SignIn payload via Xaman API (`blockchain/xrpl/xaman.py`)
3. Server shows deeplink URL to player
4. Player signs on phone in Xaman app
5. Server polls Xaman API every 2 seconds for result (`evennia.utils.delay`)
6. On signed → extract r-address → if account exists, login; if not, prompt for username and create account

Root/bot password login (`connect root <password>`) still works as before.

### OOB (Out-of-Band) Communication Pattern

OOB is still used for import/export flows (currently behind "not yet available" guards):

```python
# Server → Client
session.msg(oob=("event_name", {"key": "value"}))

# Client → Server (result comes back via inputfunc)
# def inputfunc_name(session, *args, **kwargs):
#     payload = args[2]   ← result data is here
```

### Resource Type IDs

| ID | Name | Role in game |
|---|---|---|
| 1 | Wheat | Farming output |
| 2 | Flour | Miller output (Wheat → Flour) |
| 3 | Bread | Baker output (Flour → Bread) — feeds characters, hunger system |
| 4 | Iron Ore | Miner output |
| 5 | Iron Ingot | Smelter output (Iron Ore → Iron Ingot) → Blacksmith makes NFT items |
| 6 | Wood | Forestry output |
| 7 | Timber | Sawmill output (Wood → Timber) |
| 8 | Hide | Hunting output |
| 9 | Leather | Tannery output (Hide → Leather) |
| 10 | Cotton | Farming output |
| 11 | Cloth | Loom output (Cotton → Cloth) |
| 12 | Moonpetal | Gathering output → alchemy |
| 13 | Moonpetal Essence | Apothecary output (Moonpetal → Essence) → potion brewing |
| 14-22 | Alchemy herbs | Bloodmoss, Windroot, Arcane Dust, Ogre's Cap, Vipervine, Ironbark, Mindcap, Sage Leaf, Siren Petal |
| 23 | Copper Ore | Mining output → smelting |
| 24 | Copper Ingot | Smelter output → jewellery, bronze alloy |
| 25 | Tin Ore | Mining output → smelting |
| 26 | Tin Ingot | Smelter output → bronze/pewter alloys |
| 27 | Lead Ore | Mining output → smelting |
| 28 | Lead Ingot | Smelter output → pewter alloy |
| 29 | Pewter Ingot | Smelter alloy (Tin + Lead) → jewellery |
| 30 | Silver Ore | Mining output → smelting |
| 31 | Silver Ingot | Smelter output → jewellery (SKILLED) |
| 32 | Bronze Ingot | Smelter alloy (Copper + Tin) → blacksmithing (BASIC) |
| 33 | Ruby | Mining/drops → jewellery (EXPERT+) |
| 34 | Emerald | Mining/drops → jewellery (EXPERT+) |
| 35 | Diamond | Mining/drops → jewellery (EXPERT+) |
| 36 | Coal | Mining output → steel alloy |

## Service Encapsulation Pattern

**CRITICAL DESIGN RULE: Game code never calls service classes directly.**

All blockchain service calls must go through one of two encapsulation layers:

| Asset type | Encapsulation layer | Service called |
|---|---|---|
| Gold | `FungibleInventoryMixin` | `GoldService` |
| Resources | `FungibleInventoryMixin` | `ResourceService` |
| NFTs | `BaseNFTItem` hooks | `NFTService` |

**Why:** The encapsulation layers pair every service call with a local Evennia state update. Calling a service directly would desync the mirror DB from in-game attribute state.

**The only code that imports service classes:**
- `FungibleInventoryMixin` (`typeclasses/mixins/fungible_inventory.py`)
- `BaseNFTItem` (`typeclasses/items/base_nft_item.py`)
- Test files (mocking/verifying service calls)

Each service file has a prominent banner comment reinforcing this rule.

## Database Architecture

Two separate blockchain Django apps with identical service interfaces — game code switches chains by changing import paths only.

### Polygon (`blockchain/polygon/`, DB alias: `blockchain`)

Mirror DB tracking on-chain state. Requires external sync service for chain state. 14 models including chain state mirrors, reconciliation ledgers.

| Model | Purpose |
|---|---|
| `ResourceType` | Registry of valid resource types (seeded by migration) |
| `NFTItemType` | Registry of NFT templates (typeclass, prototype_key, default_metadata) |
| `NFTMirror` | NFT ownership — location, owner_on_chain, owner_in_game, character_key |
| `NFTGameTransferLog` | Audit log of in-game NFT movements |
| `GoldChainState` | On-chain ERC-20 balances (written exclusively by sync service) |
| `GoldGameState` | In-game gold — location-subdivided per wallet |
| `GoldGameTransferLog` | Audit log of in-game gold movements |
| `GoldChainTransferLog` | Reconciliation ledger for vault↔wallet gold transfers (keyed by tx_hash) |
| `ResourceChainState` | On-chain ERC-1155 balances (written exclusively by sync service) |
| `ResourceGameState` | In-game resources — location-subdivided per wallet |
| `ResourceGameTransferLog` | Audit log of in-game resource movements |
| `ResourceChainTransferLog` | Reconciliation ledger for vault↔wallet resource transfers (keyed by tx_hash + resource_id) |

### XRPL (`blockchain/xrpl/`, DB alias: `xrpl`)

Game is the sole DB writer — no sync service needed. No chain state mirrors. Gold and resources are both XRPL issued currencies, tracked in a unified `FungibleGameState` table. AMM liquidity handled natively by XRPL AMMs on-chain (no MARKETMAKER location).

| Model | Purpose |
|---|---|
| `CurrencyType` | Registry of currencies: 36 resources + FCMGold (maps resource_id ↔ currency_code) |
| `NFTItemType` | Registry of NFT templates |
| `FungibleGameState` | Unified gold + resource balances — keyed by (currency_code, wallet, location, character_key) |
| `NFTGameState` | NFT ownership — nftoken_id (64-char hex), taxon, location, item_type |
| `FungibleTransferLog` | Audit log of all fungible movements (gold + resources) |
| `NFTTransferLog` | Audit log of NFT movements |
| `XRPLTransactionLog` | Crash recovery for chain imports/exports (tx_hash, status) |
### Location System

XRPL tracks fungibles per wallet per **location**:

| Location | Meaning |
|---|---|
| `RESERVE` | Held by the issuer/vault, not yet in play |
| `SPAWNED` | In the game world (room, mob) with no player owner |
| `ACCOUNT` | In a player's AccountBank |
| `CHARACTER` | In a player character's inventory |
| `SINK` | Consumed assets (fees, crafting, eating, dust) awaiting reallocation |

**Reconciliation invariant (must always hold):**
```
RESERVE + SPAWNED + ACCOUNT + CHARACTER + SINK = vault on-chain balance
```

NFTs use a per-row location field. XRPL NFT locations: RESERVE, SPAWNED, AUCTION, ACCOUNT, CHARACTER, ONCHAIN.

### Service Interface

Game code imports from `blockchain.xrpl.services.*`: `GoldService`, `ResourceService`, `NFTService`, `FungibleService`, `AMMService`. Authentication uses Xaman wallet sign-in (`blockchain/xrpl/xaman.py`). All import/export/wallet commands are fully implemented for XRPL.

### Seed Migrations — XRPL

- `0001_initial.py` — All 8 models + seed data (37 CurrencyType rows, all NFTItemType rows including consumables, 200 blank NFT pool, gold reserve 1M, resource reserves 10k each)

## FungibleInventoryMixin (typeclasses/mixins/fungible_inventory.py)

The single point of entry for all gold and resource service operations. Mixed into `FCMCharacter`, `RoomBase`, and `AccountBank`. Stores data as Evennia Attributes (`self.db.gold` int, `self.db.resources` dict).

**Public API (fully implemented):**

| Method group | Methods |
|---|---|
| Queries | `get_gold()`, `has_gold()`, `get_resource()`, `has_resource()`, `get_all_resources()` |
| In-game transfers | `transfer_gold_to(target, amount)`, `transfer_resource_to(target, resource_id, amount)` |
| From reserve | `receive_gold_from_reserve(amount)`, `receive_resource_from_reserve(resource_id, amount)` |
| To reserve | `return_gold_to_reserve(amount)`, `return_resource_to_reserve(resource_id, amount)` |
| Chain boundary | `deposit_gold_from_chain(amount, tx_hash)`, `withdraw_gold_to_chain(amount, tx_hash)` |
| Chain boundary | `deposit_resource_from_chain(resource_id, amount, tx_hash)`, `withdraw_resource_to_chain(resource_id, amount, tx_hash)` |

**Classification helpers (used internally):**
- `_classify_fungible(obj)` → `"CHARACTER"` / `"ACCOUNT"` / `"WORLD"`
- `_get_wallet()` — CHARACTER: `account.wallet_address`, ACCOUNT: `self.wallet_address`, WORLD: vault address
- `_get_character_key()` — CHARACTER: `self.key`, others: `None`

`transfer_gold_to(None)` raises `ValueError` pointing to `return_gold_to_reserve()`. WORLD→WORLD transfers raise `ValueError` (unsupported).

Must call `self.at_fungible_init()` from `at_object_creation()`.

## Wearslot Mixin System (typeclasses/mixins/wearslots/)

Equipment slot management for any creature type. Items stay in `contents` — the wearslot dict holds references only. Weight boundary is at the character edge (`world ↔ contents`); `contents ↔ wearslots` is an internal shuffle with zero weight change.

### BaseWearslotsMixin

| Method | Returns | Purpose |
|---|---|---|
| `at_wearslots_init()` | — | Initialize `self.db.wearslots = {}` (call from `at_object_creation()`) |
| `wear(item)` | `(bool, str)` | Equip item, calls `item.at_wear(self)` after |
| `remove(item)` | `(bool, str)` | Unequip item, calls `item.at_remove(self)` after |
| `can_wear(item)` | `bool` | **Must override** — creature-type restrictions only (raises NotImplementedError) |
| `slot_is_available(item)` | `bool` | Any matching slot empty? |
| `get_available_slot(item)` | `str\|None` | First empty matching slot |
| `is_worn(item)` | `bool` | Is item in any wearslot? |
| `get_slot(slot_name)` | `obj\|None` | What's in this slot? (accepts enum or string) |
| `get_all_worn()` | `dict` | `{slot: item}` for occupied slots only |
| `get_carried()` | `list` | Contents minus worn items (for inventory display) |
| `equipment_cmd_output(header)` | `str` | Formatted equipment display |

**Validation order in `wear()`:** contents check → already worn → has wearslot → slot available → `can_use()` (item restrictions) → `can_wear()` (creature-type) → equip

**Slot names are the restriction mechanism.** If a dog has `DOG_NECK` and a human has `NECK`, items are naturally restricted by slot name matching. No separate creature-type gating needed.

### Child Mixins

- **HumanoidWearslotsMixin** — 19 slots from `HumanoidWearSlot` enum: HEAD, FACE, LEFT_EAR, RIGHT_EAR, NECK, CLOAK, BODY, LEFT_ARM, RIGHT_ARM, HANDS, LEFT_WRIST, RIGHT_WRIST, LEFT_RING_FINGER, RIGHT_RING_FINGER, WAIST, LEGS, FEET, WIELD, HOLD
- **DogWearslotsMixin** — 2 slots from `DogWearSlot` enum: DOG_NECK, DOG_BODY (proof of concept)

### Enums (enums/wearslot.py)

`HumanoidWearSlot` and `DogWearSlot` — single source of truth for slot names. Items declare their slot via `wearslot = AttributeProperty(HumanoidWearSlot.HEAD)`. WIELD/HOLD are slots in the dict — separate commands (`wield`/`hold`) will handle type checks at the command layer.

## BaseNFTItem (typeclasses/items/base_nft_item.py)

The base typeclass for all blockchain-backed NFT items. Inherits `HiddenObjectMixin` (stashable via `stash` command) and `ItemRestrictionMixin`. Stores `token_id`, `chain_id`, `contract_address` as `AttributeProperty`. All service dispatch happens automatically via hooks.

### at_post_move dispatch (source → destination)

**Creation (source is None — item entering the game world):**

| Destination | Service call | Flow |
|---|---|---|
| `WORLD` (room) | `NFTService.spawn()` | RESERVE → SPAWNED |
| `CHARACTER` | `NFTService.craft_output()` | RESERVE → CHARACTER |
| `ACCOUNT` (bank) | `NFTService.deposit_from_chain()` | ONCHAIN → ACCOUNT |

**Movement (source is not None):**

| Source → Destination | Service call | Flow |
|---|---|---|
| `WORLD` → `CHARACTER` | `NFTService.pickup()` | SPAWNED → CHARACTER |
| `CHARACTER` → `WORLD` | `NFTService.drop()` | CHARACTER → SPAWNED |
| `CHARACTER` → `CHARACTER` | `NFTService.transfer()` | CHARACTER → CHARACTER |
| `CHARACTER` → `ACCOUNT` | `NFTService.bank()` | CHARACTER → ACCOUNT |
| `ACCOUNT` → `CHARACTER` | `NFTService.unbank()` | ACCOUNT → CHARACTER |
| `WORLD` → `WORLD` | *(no-op)* | stays SPAWNED |

**tx_hash for import:** Pass via `move_to(bank, tx_hash="0x...")` — Evennia forwards kwargs to `at_post_move`.

### at_object_delete dispatch (by current location)

| Location | Service call | Flow |
|---|---|---|
| `WORLD` (room) | `NFTService.despawn()` | SPAWNED → RESERVE |
| `CHARACTER` | `NFTService.craft_input()` | CHARACTER → RESERVE |
| `ACCOUNT` (bank) | `NFTService.withdraw_to_chain()` | ACCOUNT → ONCHAIN |

**tx_hash for export:** Stash on `obj.ndb.pending_tx_hash` before calling `obj.delete()` — ndb is still alive when the hook fires.

### Factory Methods (spawn/despawn lifecycle)

**Spawning** (blank token pool → game object):
1. `BaseNFTItem.assign_to_blank_token(item_type_name)` — picks lowest RESERVE blank token, assigns item_type + default_metadata via `NFTService.assign_item_type()` with `select_for_update()` for concurrency safety. Returns `(token_id, chain_id, contract_address)`.
2. `BaseNFTItem.spawn_into(token_id, location, chain_id, contract_address)` — creates Evennia object from NFTMirror data using `spawn()` for prototype application, applies metadata as attributes, calls `move_to(location)` to trigger hooks.

**Despawning** (game object → reserve):
- `obj.delete()` triggers `at_object_delete` → service dispatch → `NFTService._reset_token_identity(nft)` wipes `item_type=None`, `metadata={}` on all RESERVE return paths (despawn, craft_input, account_to_reserve).

### Static/class methods

- `BaseNFTItem._classify(obj)` → `"CHARACTER"` / `"ACCOUNT"` / `"WORLD"` / `None`
- `BaseNFTItem.get_nft_mirror(token_id, chain_id, contract_address)` → delegates to `NFTService.get_nft()` (read-only mirror lookup — use this instead of importing NFTService directly)

### Subclasses

- `TakeableNFTItem` — can be picked up (default `get: true()`)
- `UntakeableNFTItem` — cannot be picked up (overrides to `get: false()`)
- `WearableNFTItem` — base for armor/clothing/jewelry. `at_wear(wearer)` / `at_remove(wearer)` hooks apply/remove data-driven effects. `wearslot`, `wear_effects`, `max_durability`, `durability` AttributeProperties.
- `HoldableNFTItem` — base for shields/torches/orbs. `at_hold(holder)` / `at_remove(holder)` hooks apply/remove data-driven effects. `wear_effects`, `max_durability`, `durability`.
- `WeaponNFTItem` — weapon base class with mastery-scaled damage dicts. `at_wield(wielder)` / `at_remove(wielder)` hooks apply/remove data-driven effects.
- Weapon subclasses: `LongswordNFTItem`, `DaggerNFTItem`, `ShortswordNFTItem`, `BowNFTItem`, `ClubNFTItem`, `SpearNFTItem`, `AxeNFTItem`, `GreatswordNFTItem`, `MaceNFTItem`, `HammerNFTItem`, `SlingNFTItem`, `BlowgunNFTItem`, `BolaNFTItem`
- `ConsumableNFTItem` — base for single-use items. `consume(consumer)` calls `at_consume()` then deletes (returns to RESERVE).
- `CraftingRecipeNFTItem(ConsumableNFTItem)` — teaches recipe via `learn_recipe()` on consume. `recipe_key` AttributeProperty.
- `PotionNFTItem(ConsumableNFTItem)` — potion with mastery-scaled effects. `potion_effects`, `duration`, and `named_effect_key` baked at brew time. Anti-stacking via EffectsManagerMixin `has_effect()` — keyed by stat (e.g. `"potion_strength"`), so any two STR potions can't stack regardless of tier. Timed effects use `apply_named_effect()` directly (data-driven — `duration_type` auto-fills from registry, condition extracted from item data).
- `SpellScrollNFTItem(ConsumableNFTItem)` — spell scroll consumed via `transcribe` command. `spell_key` AttributeProperty.

All items inherit `ItemRestrictionMixin` via `BaseNFTItem` — any item can have usage restrictions set in its prototype.

## AccountBank (typeclasses/accounts/account_bank.py)

One `AccountBank` per player account. Created lazily on first bank room visit via `ensure_bank(account)` in `cmd_balance.py`. Not in the game world (`nohome=True`). Holds fungibles (via mixin) and NFTs (as Evennia contents).

```python
class AccountBank(FungibleInventoryMixin, DefaultObject):
    wallet_address = AttributeProperty(default=None)
```

The bank's `wallet_address` must match the account's `wallet_address` — `_get_wallet()` uses `self.wallet_address` for ACCOUNT-classified objects.

## Import / Export / Wallet Flow

All three commands are fully implemented for XRPL. All XRPL network calls run in worker threads via `deferToThread` (see Non-Blocking XRPL Pattern below).

- **`cmd_export.py`** — fungible: vault sends Payment (server-signed). NFT: vault creates sell offer → player accepts via Xaman. Uses `get_input()` callbacks (not `yield`) for interactive prompts.
- **`cmd_import.py`** — fungible: player signs Payment to vault via Xaman, on-chain verification before crediting. NFT: player creates sell offer via Xaman → vault accepts (server-signed). NFT selection uses numbered list from wallet. Uses `get_input()` callbacks.
- **`cmd_wallet.py`** — real-time XRPL query showing gold, resources (with display names), and numbered NFT list.

**XRPL transaction utilities** (`xrpl_tx.py`): `check_trust_line`, `send_payment`, `create_nft_sell_offer`, `accept_nft_sell_offer`, `get_transaction`, `verify_fungible_payment`, `get_wallet_balances`, `get_wallet_nfts`, currency hex encoding/decoding.

**XRPL AMM utilities** (`xrpl_amm.py`): Pool queries via `AMMInfo` request, constant product formula pricing (`calculate_buy_cost`, `calculate_sell_output`), swap quotes (`get_swap_quote`), batch multi-pool queries (`get_multi_pool_prices`), and swap execution (`execute_swap`) via vault-to-vault cross-currency Payment routed through AMM pools. Same async/sync wrapper pattern as `xrpl_tx.py`.

**AMMService** (`services/amm.py`): Game-level AMM operations. `get_buy_price` (ceil-rounded), `get_sell_price` (floor-rounded), `get_pool_prices` (batch for shop list). `buy_resource` / `sell_resource` execute on-chain swap then atomically update game state (4 debit/credit operations + transfer logs + tx log). Rounding rule: buys ceil-round up, sells floor-round down — favorable slippage goes to the game as micro-margin.

**AMM swap flow:**
1. Pre-check character has enough gold (buy) or resource (sell)
2. Execute on-chain swap — vault Payment to self with `SendMax` = rounded integer price
3. Atomic game state update — debit/credit the quoted integer amounts (not actual AMM amounts)
4. If swap fails (price moved beyond quoted ceiling) — no game state changed, player re-quotes

**Xaman payloads** (`xaman.py`): SignIn, TrustSet, Payment, NFTokenCreateOffer, NFTokenAcceptOffer.

**Replay protection**: All `deposit_from_chain()` and `withdraw_to_chain()` methods (fungible + NFT) check `XRPLTransactionLog` for existing confirmed tx_hash before processing. Uses `create()` (not `update_or_create`) inside `transaction.atomic()` so duplicate tx_hash hits the UNIQUE constraint and rolls back. Fungible imports additionally call `verify_fungible_payment()` to confirm on-chain transaction matches (destination, currency, amount, issuer, success status) before crediting — prevents amount mismatch attacks.

The FungibleInventoryMixin chain-boundary methods (`deposit_gold_from_chain()`, `withdraw_gold_to_chain()`, etc.) and BaseNFTItem hooks (`at_post_move`, `at_object_delete`) handle all state transitions. `spawn_into()` accepts `**kwargs` (e.g. `tx_hash`) passed through to `move_to` → `at_post_move`.

## Non-Blocking XRPL Pattern (deferToThread)

All XRPL network calls use `threads.deferToThread()` so the Twisted reactor stays responsive for other players. The sync wrappers in `xrpl_tx.py` and `xrpl_amm.py` (which use `asyncio.run()`) are kept as-is — the non-blocking change is at each **callsite**.

**Pattern:**
```python
from twisted.internet import threads

def func(self):
    caller.msg("|cProcessing...|n")  # immediate feedback
    d = threads.deferToThread(blocking_fn, arg1, arg2)
    d.addCallback(lambda result: _on_success(caller, result))
    d.addErrback(lambda failure: _on_error(caller, failure))
    # func() returns immediately — reactor keeps ticking
```

**Thread safety rules:**
- XRPL/network calls and Django ORM queries run in worker threads (safe — connection-per-thread)
- Evennia `self.db` attribute access must stay on the reactor thread (in callbacks)
- All callbacks check `caller.sessions.count() > 0` for disconnection safety

**Testing:** `tests/test_utils/sync_defer.py` provides `patch_deferToThread(module_path)` — replaces `deferToThread` with synchronous execution returning already-fired Deferreds. Also patch `_session_check` since test characters lack real sessions.

**Commands using this pattern:** `cmd_wallet.py`, `cmd_export.py`, `cmd_import.py`, `cmdset_shopkeeper.py`, `cmd_override_unconnected_connect.py`, `cmd_sync_nfts.py`, `cmd_sync_reserves.py`, `cmd_reconcile.py`.

## SINK Location & Reallocation

All consumption flows (gold fees, crafting inputs, eating, junking, AMM rounding dust) route to the **SINK** location in `FungibleGameState`. This separates consumed assets from unallocated reserve, giving visibility into what was consumed vs what's available to re-spawn.

**Consumption:** `return_gold_to_sink()` / `return_resource_to_sink()` — for fees, crafting, eating, junking, AMM dust. Routes to SINK.
**Cleanup:** `return_gold_to_reserve()` / `return_resource_to_reserve()` — for corpse decay, dungeon teardown, world rebuild. Routes to RESERVE.

**Reallocation:** A daily `ReallocationServiceScript` drains all SINK → RESERVE (100% for now). Gold burn to issuer deferred until vault signing is sorted.

**Admin commands:**
- `reconcile` — read-only audit showing Currency, On-Chain, Reserve, Distributed, Sink, Delta (delta should be 0)
- `sync_reserves` — recalculates RESERVE from: `on_chain - (SPAWNED + ACCOUNT + CHARACTER + SINK)`. Always run `reconcile` first.

**Query total in SINK:** `FungibleGameState.objects.filter(location="SINK").aggregate(Sum('balance'))['balance__sum']`

## Economy Telemetry

Hourly aggregation system that snapshots key economic metrics for the spawn algorithm and admin monitoring. Raw data already exists in transfer logs and game state tables — the telemetry system pre-computes summaries.

**Models:** `PlayerSession` (login/logout tracking), `EconomySnapshot` (global hourly metrics: players online, gold circulation/reserve/sinks, AMM trades, imports/exports), `ResourceSnapshot` (per-resource hourly: circulation by location, velocity, AMM prices).

**Service:** `TelemetryService` — `record_session_start()` / `record_session_end()` called from character puppet/unpuppet hooks. `take_snapshot()` called hourly by `TelemetryAggregatorScript` global script. `close_stale_sessions()` called on server boot for crash recovery.

**Admin command:** `economy` (superuser, OOC) — shows latest snapshot. `economy <resource>` for detailed single-resource history.

**Velocity categories:** produced (craft_output + pickup), consumed (craft_input), traded (amm_buy + amm_sell), exported (withdraw_to_chain), imported (deposit_from_chain).

## Resource Spawn Algorithm

Hourly service that replenishes `RoomHarvesting` nodes based on economy data. Resources drip-feed into rooms throughout the hour rather than spawning in a single batch.

### Architecture Overview

```
ResourceSpawnScript (hourly tick)
    │
    ▼
ResourceSpawnService.calculate_and_apply()
    │
    ├── 1. Gate: skip if no players online (EconomySnapshot)
    ├── 2. Single DB query: fetch ALL RoomHarvesting rooms, group by resource_id
    ├── 3. Get 7-day player-hours from PlayerSession
    │
    ▼  For each configured resource:
    │
    ├── 4. Baseline: 24h rolling avg of consumed_1h (ResourceSnapshot)
    │      └── Cold start fallback: default_spawn_rate from config
    ├── 5. Price modifier: AMM buy price vs target band
    ├── 6. Supply modifier: circulating supply per player-hour vs target
    ├── 7. spawn_amount = baseline × price_mod × supply_mod
    ├── 8. Calculate per-room allocations (weighted by spawn_rate_weight)
    │
    ▼
    9. Drip-feed: schedule delay() calls to distribute resources
       over the hour (max 12 ticks, min 5 min apart per room)
```

### Three-Factor Algorithm

**`spawn_amount = consumption_rate × price_modifier × supply_modifier`**

- **Consumption rate** (baseline): 24h rolling average of `ResourceSnapshot.consumed_1h` — what players are actually using. The 24h window smooths across peak/off-peak hours and timezone differences. Falls back to `default_spawn_rate` from config when no data exists (cold start).
- **Price modifier**: AMM buy price vs target band. Price high → modifier > 1.0 (spawn more than consumed). Price mid-band → 1.0. Price low → modifier < 1.0 (spawn less). No AMM pool → 1.0. Two-segment linear interpolation clamped to `[modifier_min, modifier_max]`.
- **Supply modifier**: Circulating supply per player-hour vs target buffer. Oversupply (hoarding) → modifier < 1.0 (cut spawn to encourage selling). Undersupply → modifier > 1.0 (boost spawn). Uses 7-day `PlayerSession` window for player-hours. Zero player-hours → 1.0 (can't compute).

### Weighted Room Distribution

Each `RoomHarvesting` room has `spawn_rate_weight` (1-5, default 1) and `max_resource_count` (default 20). Total spawn is divided proportionally: `floor(weight × amount / total_weight)`, remainder to highest-weight rooms first. Rooms at max are skipped.

### Drip-Feed Distribution

Instead of dumping all resources at once, each room's hourly allocation is spread across the hour via `delay()` calls:
- Room due 1 → single drop at minute 0
- Room due 4 → 1 drop every 15 minutes
- Room due 12 → 1 drop every 5 minutes
- Room due 30 → drops of 2-3 every 5 minutes (capped at 12 ticks)

The `_apply_drip()` callback re-checks `max_resource_count` at apply time, so rooms that fill up between ticks won't overflow.

### Data Sources

All inputs come from existing models — the spawn service is purely a consumer:

| Data | Source | How Used |
|---|---|---|
| Hourly consumption | `ResourceSnapshot.consumed_1h` | 24h rolling avg baseline |
| AMM buy price | `ResourceSnapshot.amm_buy_price` | Price modifier |
| Circulating supply | `FungibleGameState` (CHARACTER + ACCOUNT) | Supply modifier |
| Player activity | `PlayerSession` (7-day window) | Per-player-hour calculation |
| Players online gate | `EconomySnapshot.players_online` | Skip spawn if nobody playing |
| Harvest rooms | `ObjectDB` (RoomHarvesting typeclass) | Single query, grouped by resource_id |

### Files

- **Config:** `world/economy/resource_spawn_config.py` — per-resource dict keyed by `resource_id`. Only raw gathering resources (wheat, ores, herbs, etc.), not processed (flour, ingots, cloth). Configurable: target price band, target supply per player-hour, default spawn rate, max per room, modifier min/max.
- **Service:** `blockchain/xrpl/services/resource_spawn.py` — `ResourceSpawnService` with static methods for calculation, allocation, and drip-feed scheduling.
- **Script:** `typeclasses/scripts/resource_spawn_service.py` — `ResourceSpawnScript`, thin hourly wrapper.
- **Tests:** `tests/script_tests/test_resource_spawn.py` — 47 tests covering modifiers, queries, allocation, drip-feed, and integration.
- **POC:** `commands/account_cmds/cmd_spawn_poc.py` — superuser `spawnpoc` command for testing with hardwired values against live rooms.

### Future

Zone activity tracking (backlog) will add a dynamic multiplier on top of static weights based on where players actually spend their time.

## NFT Saturation Service (daily snapshot)

Collects daily saturation data for the **saturation-based NFT item spawn algorithm** (loot selection logic is future work — this is the data collection layer).

### Concept

NFT items (scrolls, recipes, rare items) use **saturation** to control drop rates. Unlike resources, these items aren't consumed steadily — scrolls/recipes grant permanent knowledge, rare items circulate until exported/junked. Static drop rates would flood the game with items nobody needs.

**Two types of saturation:**

| Category | Saturation = | Data source |
|---|---|---|
| Scrolls & recipes | (players who know it + unlearned copies in player hands) / active players | `db.spellbook`, `db.recipe_book`, `NFTGameState` |
| Rare items | Count in circulation vs target ratio per active player | `NFTGameState` |

### Three Data Inputs

| Input | Source | Method |
|---|---|---|
| Active player count (7d) | `PlayerSession` — distinct character_keys with session in last 7 days | `get_active_player_count_7d()` |
| Knowledge counts | `ObjectDB` — iterate active characters, read `db.spellbook` + `db.granted_spells` + `db.recipe_book` | `get_knowledge_counts()` |
| Unlearned copies | `NFTGameState` — scroll/recipe NFTs in CHARACTER or ACCOUNT locations | `get_unlearned_copy_counts()` |
| NFT circulation | `NFTGameState` — all non-scroll/recipe NFTs in CHARACTER + ACCOUNT + SPAWNED | `get_nft_circulation_counts()` |

### Snapshot Model

`SaturationSnapshot` — one row per tracked item per day. Fields: `day`, `item_key`, `category` (spell/recipe/item), `active_players_7d`, `known_by`, `unlearned_copies`, `in_circulation`, `saturation`.

### Files

- **Service:** `blockchain/xrpl/services/nft_saturation.py` — `NFTSaturationService` with static methods for data collection. Entry point: `take_daily_snapshot()`.
- **Script:** `typeclasses/scripts/nft_saturation_service.py` — `NFTSaturationScript`, daily (86400s) wrapper.
- **Model:** `SaturationSnapshot` in `blockchain/xrpl/models.py`.
- **Tests:** `tests/script_tests/test_nft_saturation.py` — 34 tests covering all data collection methods and integration.

### Future

The loot selection algorithm will consume these snapshots: mob dies → roll for drop → query latest saturation → weight toward undersaturated items → pick one. See `design/ECONOMY.md` § Spawn Algorithms for full design.

## Character Delete Protection

`FCMCharacter.at_object_delete()` returns `False` (blocking deletion) if the character holds any NFTs, gold, or resources. Account-level `CmdCharDelete` automatically moves all assets to the AccountBank before deletion: removes worn equipment, moves NFTs via `move_to(bank)`, transfers gold/resources via `transfer_*_to(bank)`, then deletes the empty character.

## Junk Command (commands/all_char_cmds/cmd_junk.py)

Permanently destroys items, gold, or resources. For gold and resources, calls `return_gold_to_reserve()` / `return_resource_to_reserve()` (CHARACTER → RESERVE, bypasses SPAWNED). For NFTs, `delete()` triggers `at_object_delete(CHARACTER)` → `NFTService.craft_input()`. Includes Y/N confirmation via `yield` pattern.

## Key Evennia Patterns

- Use `session.puppet` (not `session.puppets`) to get the character
- Use `threads.deferToThread()` for blocking XRPL/network calls — keeps reactor responsive (see Non-Blocking XRPL Pattern below)
- `AttributeProperty` is accessed directly (`account.wallet_address`), not via `.db`
- Room CmdSets merge automatically — no need to add/remove on player enter/exit
- Use `yield` pattern for Y/N confirmations in simple commands; use `get_input()` callbacks in async commands that use `deferToThread` (yield is incompatible with deferred callbacks)
- `at_after_move` is **deprecated** in Evennia 6.0 — use `at_post_move` instead
- `at_object_creation()` fires BEFORE `create_object()`'s `attributes` parameter is applied — `AttributeProperty` values are `None` during this hook
- `move_to(**kwargs)` forwards all kwargs to `at_post_move()` — use this to pass `tx_hash`
- Creating with `location=` triggers `at_post_move` immediately during `create_object` with no way to pass kwargs. Always create `nohome=True`, set attributes, then `move_to()` when hooks need kwargs or attributes.

## CRITICAL: Never Use Django Queryset Bulk Deletes on Game Objects

**`ObjectDB.objects.filter(...).delete()` must NEVER be used in game code.** Django bulk deletes bypass Evennia's object lifecycle hooks — `at_object_delete()` will not fire, creating orphaned mirror DB records.

Always delete Evennia objects individually via `obj.delete()`.

Queryset bulk deletes are acceptable ONLY in test `tearDown` methods for cleaning up non-Evennia tables.

## Wallet Address Lookup Pattern

```python
# Find an account from a wallet address
from evennia.accounts.models import AccountDB
account = AccountDB.objects.get_by_attribute(key="wallet_address", value=addr)

# Get a character's wallet from a command
wallet = caller.account.attributes.get("wallet_address")
```

## Transaction Model

All on-chain XRPL transactions (import/export) are signed by players via Xaman wallet. The game server creates payloads and polls for results but never holds private keys or pays transaction fees.

## What's Built and Working

- Xaman (XRPL wallet) sign-in authentication (server-side polling, no client-side JS)
- Custom Account class with `wallet_address` AttributeProperty
- BankRoom typeclass with restricted CmdSet
- Full bank room command suite: `balance`, `withdraw`, `deposit` (NFTs + fungibles)
- Account-level commands: `bank` (view account bank), `wallet` (live XRPL query), `export` (full XRPL), `import` (full XRPL)
- Export command: fungible (gold/resources) via vault Payment + NFT via sell offer → Xaman accept
- Import command: fungible via Xaman Payment to vault + NFT via Xaman sell offer → vault accepts
- Wallet command: real-time XRPL query showing gold, resources (with display names), and numbered NFT list
- Trust line auto-check: export detects missing trust lines and sends Xaman TrustSet payload
- XRPL transaction utilities: `xrpl_tx.py` (check_trust_line, send_payment, create_nft_sell_offer, get_wallet_balances, get_wallet_nfts)
- Xaman API: SignIn, TrustSet, NFTokenAcceptOffer payloads with delay-based polling
- XRPL service layer active: GoldService, ResourceService, NFTService, FungibleService, AMMService, TelemetryService, ResourceSpawnService, NFTSaturationService
- Service encapsulation: all service access via FungibleInventoryMixin or BaseNFTItem hooks
- FungibleInventoryMixin with 29 public methods including chain boundary deposit/withdraw
- BaseNFTItem with full 9-path at_post_move dispatch + 3-path at_object_delete dispatch
- NFT blank token pool: assign_to_blank_token() → spawn_into() factory methods, identity wipe on reserve return
- NFTItemType registry with typeclass, prototype_key, default_metadata
- Weapon system: WeaponNFTItem + subclasses (Longsword, Dagger, Shortsword, Bow, Club, Spear, Axe, Greatsword, Mace, Hammer, Sling)
- Item prototypes in `world/prototypes/` package (weapons, wearables, holdables, components, consumables/recipes, consumables/potions, consumables/scrolls, containers) — one file per item, vanilla and enchanted variants
- AccountBank container for account-level asset storage
- Junk command wired to service layer for gold, resources, and NFTs
- Character delete protection
- SPAWNED_IN_GAME tracking for fungibles in the game world
- AMM buy/sell/price methods on FungibleInventoryMixin (buy_from_pool, sell_to_pool, get_pool_price)
- AMM shopkeeper commands: list (batch pool prices), quote buy/sell (with pending quote on ndb), accept, instant buy, instant sell (with "sell all" support)
- AMMService: on-chain XRPL AMM swap execution via OfferCreate, 6-operation atomic accounting (player integers + AMM decimals against RESERVE), transfer + tx logging
- xrpl_amm.py: pool queries (AMMInfo), constant product formula pricing (ceil-rounded buys, floor-rounded sells), batch multi-pool queries, swap execution with balance change extraction from tx metadata
- AMM superuser tools: `amm_check` (pool state viewer), `reconcile` (on-chain vs DB comparison), `test_amm_trades` management command (live integration test)
- Hunger/eating system (Bread is resource ID 3). HungerService and RegenerationService only process puppeted characters (`has_account` check) — unpuppeted characters are skipped. Forage command (SURVIVALIST skill, Druid/Ranger): restores hunger directly (no bread production), mastery scales yield (BASIC=1..GM=5), 15-min cooldown matching hunger cycle, NO hunger_free_pass_tick (bread retains economic advantage). Solo auto-applies, party gets interactive allocation prompt. Requires forageable terrain (not urban/underground/dungeon/water).
- Get/drop/give commands wired to service layer
- Superuser wallet injection: at_post_login() backfills vault wallet + bank for superuser account
- Wearslot mixin system: BaseWearslotsMixin, HumanoidWearslotsMixin (19 slots), DogWearslotsMixin (proof of concept)
- WearableNFTItem, HoldableNFTItem, WeaponNFTItem base classes with data-driven at_wear/at_wield/at_hold hooks
- Data-driven item effects system: `wear_effects` on prototypes, nuclear recalculate pattern via `_recalculate_stats()` on BaseActor — supports `stat_bonus`, `damage_resistance`, `condition` (with optional companion effects), `hit_bonus`, and `damage_bonus` effect types. Conditions remain ref-counted (incremental). Numeric stats rebuilt from scratch on every equip/unequip/buff change. Companion effects on compound conditions deduplicated via `_accumulated_companions` set during recalculate.
- DamageResistanceMixin: integer percentage resistances/vulnerabilities, clamped to [-75, 75] on read, reusable across any typeclass
- DurabilityMixin: `max_durability`, `durability`, `repairable` AttributeProperties on all item types, `repair_to_full()` method
- CarryingCapacityMixin: weight tracking for NFTs and fungibles with encumbrance
- WearSlot enums (HumanoidWearSlot, DogWearSlot) as single source of truth for slot names
- Worn item guards: drop/give/deposit/junk reject equipped items via `exclude_worn` on character search
- Score command — consolidated character sheet in a 4-column boxed layout (~16 lines). Header: name, race, alignment, classes, level, XP. Body: vitals (HP/MP/MV with color-coded health), ability scores (current + base), combat modifiers (AC, crit, init, att/round), resistances/vulnerabilities. Footer: active conditions, levels-to-spend hint. Hand-built f-strings with `_pad()` helper for color-code-aware alignment. 23 tests.
- Stats command — focused "base vs effective" breakdown showing how equipment, spells, and ability modifiers change stats. Three sections: Ability Scores (base, effective, modifier), Vitals (HP/Mana/Move max with CON breakdown), Combat (AC, crit, initiative with DEX breakdown, attacks/round). Boxed layout matching score style. 14 tests.
- RoomInn typeclass with stew/ale/menu commands
- 36 resource types seeded (basic crafting chains, alchemy herbs, metals/ores/alloys, gems, coal)
- EffectsManagerMixin: unified effect system replacing ConditionsMixin. Three layers: (1) ref-counted condition flags, (2) stat effect dispatch (backward compat, mostly superseded by nuclear recalculate), (3) named effects with anti-stacking, messaging, and lifecycle management (combat_rounds/seconds/permanent). **Nuclear recalculate pattern:** `_recalculate_stats()` on BaseActor rebuilds all Tier 2 numeric stats from scratch (base → racial → equipment → active buffs) on every equip/unequip/buff change. Conditions remain incremental with ref-counting. **Effect Registry** on NamedEffect enum (`effect_condition`, `effect_duration_type` properties) — single source of truth for each effect's associated condition and duration type. **Convenience methods** (`apply_stunned()`, `apply_invisible()`, `apply_shield_buff()`, etc.) are the preferred API — each method is the single entry point for its effect, internally calling `apply_named_effect()` with registry auto-fill. **`break_effect()`** generic method for force-removing effects without end messages. `apply_named_effect()` accepts NamedEffect enum directly and uses `_UNSET` sentinel for auto-fill from registry. Combat handler integration: `tick_combat_round()` + `clear_combat_effects()`. NamedEffect enum validates keys + provides message registry. Condition enum trimmed to 12 active flags. Unsorted effects list in `named_effect.py` forces classification before implementation. MANDATORY for all new effects. **Admin tool:** `recalc [target]` command forces nuclear recalculate on any character (for debugging stat desync).
- **PlayerPreferencesMixin** (`typeclasses/mixins/player_preferences.py`): data-driven toggleable boolean preferences for player characters. `PREFERENCES` registry dict maps user-facing names to `AttributeProperty` attrs + descriptions. `CmdToggle` (`toggle`) reads the registry automatically — no command changes needed to add new preferences. **Gated preferences:** optional `gate` callable + `gate_fail` message on registry entries for conditional prefs (e.g. reactive spells requiring memorisation). Gate fails → pref hidden from display and valid options list. Return convention: `toggle_preference()` → `(key, new_val)` on success, `(None, fail_msg)` on gate fail, `None` if unknown. Current preferences: `brief` (skip room descs), `autoexit` (show exits), `smite` (reactive spell, gated), `shield` (reactive spell, gated). To add a new preference: (1) add `AttributeProperty` on the mixin, (2) add `PREFERENCES` entry, (3) optionally add `gate`/`gate_fail`.
- Reactive Shield spell: auto-cast abjuration spell via `at_wielder_about_to_be_hit` weapon hook. Toggle via `toggle shield` (unified player preference system, `shield_active` attribute). Three gates: toggle ON + memorised + mana. Mana cost 3/5/7/9/12 per trigger. Scaling: BASIC +4/1rnd, SKILLED +4/2rnd, EXPERT +5/2rnd, MASTER +5/3rnd, GM +6/3rnd. Uses EffectsManagerMixin named effect for AC bonus + duration + cleanup.
- Stun/Prone refactored to named effects: no longer use condition flags (were cosmetic). Tracked as named effects with `duration_type="combat_rounds"`. Combat handler checks `has_effect("stunned")` / `has_effect("prone")` instead of old `skip_actions` counter.
- SLOWED refactored to named effect: applied as named effect with condition flag (for future movement system) + 3 round combat_rounds duration + auto-cleanup on combat end
- Blowgun weapon: `BlowgunNFTItem` — missile/finesse, always-1 damage, poison-focused mastery path. Poison DoT (hybrid timing: combat rounds in combat, seconds out), CON-save paralysis (size-gated, HUGE+ immune), melee penalty at low mastery. `PoisonDoTScript` for per-tick damage. Anti-stacking replaces existing poison. 36 tests.
- Bola weapon: `BolaNFTItem` — missile/finesse, always-1 bludgeoning damage, entangle-focused CC weapon. On-hit contested DEX roll entangles target (action denial + advantage to enemies). Save-each-round escape (STR vs original attacker roll as DC). Max duration cap per mastery tier (1-6 rounds). Size-gated: HUGE+ immune. Anti-stacking (can't re-entangle). 28 tests.
- Greatsword weapon: `GreatswordNFTItem` — two-handed melee, pure offense archetype (no parries, no extra attacks). CLEAVE: cascading AoE hits after successful primary attack (25%/50%/75% chances scaling with mastery, chain breaks on first fail). EXECUTIONER (GM only): bonus `execute_attack()` on any kill (primary or cleave), 1 per round via `executioner_used` flag on CombatHandler. Executioner attack can itself cleave. 27 tests.
- Battleaxe weapon: `BattleaxeNFTItem` — two-handed melee, cleave + sunder. Nerfed cleave (20/40/60% chances vs greatsword's 25/50/75%). SUNDER: stacking AC penalty on hit (d100 vs 20/25/25/30% chance, -1/-1/-2/-2 AC per proc, +1/+1/+2/+2 extra armour durability). Tracks via `target.db.sunder_stacks`, AC floor of 10. 27 tests.
- Handaxe weapon: `AxeNFTItem` — one-handed melee, reduced sunder + extra attacks. Lighter sunder than battleaxe (10/15/15/20% chance, always -1 AC, +1 armour durability per proc). Extra attack at MASTER/GM. Pairs with shield for balanced offense/defense. 22 tests.
- Dagger weapon: `DaggerNFTItem` — melee/finesse, speed + crit focused mastery path. No parries. Extra attacks: +1 at SKILLED/EXPERT/MASTER/GM. Crit threshold reduction: -1 at EXPERT/MASTER, -2 at GM (crits on 18+). Off-hand attacks: +1 at MASTER/GM (requires dual-wield weapon in HOLD). `can_dual_wield = True`. 25 tests.
- Shortsword weapon: `ShortswordNFTItem` — melee, dual-wield specialist with light parry. Parries: 1 at SKILLED+. Off-hand attacks: 1 at SKILLED/EXPERT/MASTER, 2 at GM. Off-hand penalty: -4 SKILLED, -2 EXPERT, 0 MASTER/GM. No main-hand extra attacks. `can_dual_wield = True`. 24 tests.
- Bow weapon: `BowNFTItem` — missile, premier ranged DPS. SLOWING SHOT: contested roll (d20 + DEX + mastery vs d20 + STR) at SKILLED+, applies SLOWED (1/2/2/3 rounds). Extra attack at MASTER/GM. 16 tests.
- Crossbow weapon: `CrossbowNFTItem` — missile, anti-tank single-hit. KNOCKBACK: d100 vs 15/20/25/30% chance to apply PRONE (1 round, grants advantage to all attackers). No extra attacks. HUGE+ immune. 17 tests.
- Sling weapon: `SlingNFTItem` — missile, no class restrictions. CONCUSSIVE DAZE: d100 vs 10/15/20/25% chance to apply STUNNED (1 round). HUGE+ immune. 17 tests.
- Shuriken weapon: `ShurikenNFTItem` — missile/finesse, ninja only. Multi-throw (1/1/1/2/2/3 total attacks). Crit threshold: -1 at SKILLED/EXPERT, -2 at MASTER/GM. CONSUMABLE: hit moves shuriken to target inventory, miss to room floor (recoverable). Auto-equips next shuriken from inventory. Unbreakable (no durability loss). 20 tests.
- Mace weapon: `MaceNFTItem` — anti-armor specialist. CRUSH: bonus damage = min(mastery_cap, target.armor_class - 12). Scales with how armored the target is (useless vs unarmored). Cap: 0/0/2/3/4/5. Extra attack at MASTER/GM. 18 tests.
- Club weapon: `ClubNFTItem` — simple one-handed bludgeon. LIGHT STAGGER: d100 vs 10/15/15/20% chance to apply STAGGERED (-2 hit penalty, 1 round). Extra attack at MASTER/GM. 17 tests.
- Greatclub weapon: `GreatclubNFTItem` — two-handed brute weapon. HEAVY STAGGER: d100 vs 15/20/25/30% chance to apply STAGGERED (-3/-4 hit penalty, 1-2 rounds at MASTER+). No extra attacks. 16 tests.
- Hammer weapon: `HammerNFTItem` — DEVASTATING BLOW: crit damage multiplier. at_crit() multiplies already-doubled crit damage by 1.0/1.0/1.25/1.5/1.75/2.0 (up to ~4x base at GM). Build-around weapon: stack crit threshold reduction gear. No extra attacks. 14 tests.
- Spear weapon: `SpearNFTItem` — REACH COUNTER: support/backline weapon. When an enemy hits an ally, spear wielder counter-attacks from reach (0/0/1/1/2/3 counters/round). Counter-attacks use `_is_riposte=True` (can't be parried, don't cascade). No parries, no extra attacks. `_check_reach_counters()` in combat_utils.py. 11 tests.
- Staff weapon: `StaffNFTItem` — PARRY SPECIALIST: highest parries in the game (0/0/2/2/3/4). Parry advantage at EXPERT+. Riposte at MASTER+. Two-handed, bludgeoning. THE caster defense weapon. Hit bonuses: -2/0/+2/+3/+4/+5. No extra attacks. 28 tests.
- Lance weapon: `LanceNFTItem` — MOUNTED POWERHOUSE: devastating when mounted, terrible on foot. Unmounted: disadvantage on all attacks, no crit bonus, no extra attacks, no prone. Mounted: crit threshold (0/0/-1/-2/-2/-3), extra attacks at MASTER+ (0/0/0/0/1/1), prone on first hit/round (0/0/15/20/20/25%). Only weapon that can prone HUGE (GARGANTUAN always immune). Size-gated via immune sets. `wielder.ndb.lance_prone_used` tracking. 25 tests.
- Ninjatō weapon: `NinjatoNFTItem` — PURE OFFENSE: ninja signature sword. Extra attacks (0/0/0/1/1/1), crit threshold (0/0/0/-1/-1/-2), off-hand (0/0/1/1/1/2). Finesse, dual-wield. Highest total attacks in game (4 at GM dual-wielding). No parries. Ninja only. 30 tests.
- Nunchaku weapon: `NunchakuNFTItem` — STUN SPECIALIST: contested DEX vs CON stun on hit. SKILLED+: STUNNED 1 round. MASTER+: win by >=5 → PRONE. GM: 2-round effects, 2 checks/round. Extra attacks at MASTER+ (0/0/0/0/1/1), off-hand (0/0/1/1/1/2). HUGE+ immune. Warrior/ninja/barbarian. 23 tests.
- Sai weapon: `SaiNFTItem` — DISARM + PARRY: contested DEX vs STR on hit, win → `force_drop_weapon()` (mobs: floor, players: inventory). Parries (0/0/1/2/2/3), parry advantage at MASTER+, riposte at GM. Off-hand (0/0/1/1/1/2). HUGE+ immune to disarm. Ninja only. 21 tests.
- STAGGERED named effect: hit penalty debuff via stat_bonus on total_hit_bonus. Used by club (-2) and greatclub (-3/-4). Anti-stacking. Combat-round duration.
- Save-each-round mechanic: generic infrastructure in `effects_manager.py` — any named effect can use `save_dc`/`save_stat`/`save_messages` params on `apply_named_effect()`. `tick_combat_round()` rolls saves before decrementing duration; success = immediate removal. **Save DC convention:** always use the caster's **full contested total** (d20 + ability + mastery), not the raw d20 roll. Used by Entangle (STR saves), Hold (WIS saves), and Bola (STR saves).
- Mage Armor spell: manually-cast abjuration self-buff, seconds-based timer (wall-clock). Scaling: +3/+3/+4/+4/+5 AC, 1/2/2/3/3 hours. Anti-stacking via `has_effect("mage_armored")` with mana refund. Stacks with Shield (up to +11 AC at GM). 14 tests.
- ItemRestrictionMixin: data-driven item usage restrictions (class/race/alignment/level/attribute/mastery gates) on BaseNFTItem
- RecipeBookMixin: recipe learning, lookup, and filtering on FCMCharacter
- Crafting system: RoomCrafting rooms (smithy, woodshop, tailor, apothecary, jeweller, wizard's workshop), craft/available/repair commands, recipe-driven NFT spawning with timed delays and progress bars. 52+ recipes across 7 skills (carpentry, blacksmithing, leatherworking, tailoring, alchemy, jewellery, enchanting). Repair command restores durability on damaged items at reduced material cost (total_materials - 1, or explicit repair_ingredients), awards 50% craft XP.
- Processing system: RoomProcessing rooms with multi-recipe support (smelter handles multiple ore→ingot conversions + alloys), process/rates commands, per-recipe cost overrides, resource conversion with timed delays
- Consumable items: ConsumableNFTItem base, CraftingRecipeNFTItem for recipe teaching, SpellScrollNFTItem for spell learning
- Container system: ContainerNFTItem (leather backpack, panniers) with capacity limits and nested inventory
- Potion system: PotionNFTItem with 9 alchemy potions. Mastery-scaled at brew time (BASIC→GRANDMASTER): stat bonus potions scale +1/60s to +5/300s, restore potions scale dice 2d4+1 to 10d4+5. Uses EffectsManagerMixin named effects for timed buffs — `apply_named_effect(duration_type="seconds")` with stat-keyed anti-stacking (e.g. `"potion_strength"`). When effect is already active, potion is NOT consumed (saved). Scaling tables in `world/prototypes/consumables/potions/potion_scaling.py`.
- Universal ability score modifier pattern: cached stats hold equipment/spell bonuses only, ability modifiers always computed at check time. Effective properties implemented: `effective_ac` (DEX), `effective_initiative` (DEX), `effective_hp_max` (CON per level), `effective_stealth_bonus` (DEX), `effective_hit_bonus` (self-contained, inspects wielded weapon for STR/DEX + weapon-type bonus + mastery), `effective_damage_bonus` (same pattern), `get_max_capacity()` override (STR). Used by regen service, stats command, combat system, and chargen.
- Enchanting system: mage-only crafting skill (`skills.ENCHANTING`), recipes auto-granted at mastery level-up (no recipe scrolls needed), transforms vanilla items into enchanted variants with effects/restrictions. 8 BASIC recipes using Arcane Dust (resource ID 15) in Wizard's Workshop rooms. Vanilla items (bandana, kippah, cloak, veil, scarf, sash, leather_cap, leather_gloves) are crafted by tailors/leatherworkers with no effects; enchanters transform them into named enchanted versions (Rogue's Bandana +1 DEX, Sage's Kippah +1 WIS, Titan's Cloak +1 STR, Veil of Grace +1 CHA, Professor's Scarf +1 INT, Sun Bleached Sash +1 CON, Scout's Cap +1 initiative, Pugilist's Gloves +1 hit/dam unarmed).
- Weapon-type-specific hit/damage bonuses: `hit_bonuses` and `damage_bonuses` dicts on FCMCharacter keyed by `WeaponType.value` string, with `hit_bonus`/`damage_bonus` effect types in `apply_effect()`/`remove_effect()`. Enables items like Pugilist's Gloves (+1 hit/+1 dam for unarmed only).
- Weapon class restrictions: `_WEAPON_CLASSES` mapping in `enums/weapon_type.py` gates which classes can train mastery in each weapon type. Any class can still equip any weapon at UNSKILLED. Chargen weapon skill selection filtered by class.
- Magic system: spell registry, base Spell class with cooldown system and description/mechanics fields, SpellbookMixin, SpellScrollNFTItem, 5 commands (cast/transcribe/memorise/forget/spells), spell_utils (apply_spell_damage, get_room_enemies, get_room_all), multi-perspective messaging, spell aliases, school enum integration. Evocation school: Magic Missile (BASIC), Frostbolt (BASIC, 1d6 cold + contested SLOWED 1-5 rounds), Fireball (EXPERT, unsafe AoE), Cone of Cold (MASTER, safe AoE + SLOWED), Power Word: Death (GM, instant kill). SLOWED mechanic: caps attacks at 1/round, blocks off-hand, per-round sluggish message — enforced in combat_handler, registered as named effect callback. Abjuration school: Shield (BASIC, reactive), Mage Armor (BASIC, long-duration AC), Resist (SKILLED, element resistance via spell_arg + DamageResistanceMixin) implemented; Antimagic Field, Group Resist, Invulnerability scaffolded. Spell argument system: `has_spell_arg` on Spell class + cmd_cast parsing for spells needing extra params. Necromancy school: Drain Life (BASIC, implemented — damage + self-heal), Vampiric Touch (SKILLED, implemented — touch attack, heals past max HP, VAMPIRIC effect with escalating mana cost + 10min timer), Soul Harvest (EXPERT, implemented — unsafe AoE drain), plus scaffolds for Raise Dead, Raise Lich, Death Mark. Divine healing: Cure Wounds (BASIC, friendly heal). Scroll prototypes for all mage spells. 150+ tests across 4 test files.
- Race system: auto-collecting registry in `typeclasses/actors/races/`, frozen `RaceBase` dataclass, auto-generated `Race` enum from registry keys, `Ability` enum for `ability_score_bonuses`, 5 races (Human, Dwarf, Elf, Halfling remort-1, Aasimar remort-2) with 45 tests. Each race defines `racial_languages` (e.g. Dwarf→dwarven, Elf→elfish, Aasimar→celestial).
- Character class system: auto-collecting registry in `typeclasses/actors/char_classes/`, frozen `CharClassBase` dataclass, auto-generated `CharClass` enum from registry keys, `Ability` enum for `prime_attribute` and `multi_class_requirements`, 2 classes (Warrior, Thief) with level 1-40 progression tables, 42 tests
- `Ability` enum (`enums/abilities_enum.py`) used across race and class systems for validation and typo prevention
- Character creation wizard: EvMenu-based guided flow (race → class → alignment → point buy → weapon skills → starting skills → languages → starting knowledge → name → confirm → create) with CON modifier in HP display and effective HP at creation
- Condition messaging: FCMCharacter overrides `add_condition()`/`remove_condition()` with first/third person messages. RoomBase overrides `msg_contents()` for HIDDEN/INVISIBLE visibility filtering. Conditions include DEAF (blocks hearing speech) and COMPREHEND_LANGUAGES (bypasses language garbling).
- Language system: 8 languages in `Languages` enum (Common, Dwarven, Elfish, Halfling, Celestial, Kobold, Goblin, Dragon). `db.languages` stores known languages as set of strings. Chargen step 9 grants racial + INT-bonus language picks. Deterministic garble engine (`utils/garble.py`) with per-language syllable palettes — same word always garbles the same way. Three language-aware communication commands: `say/dw <msg>` (room speech), `whisper/dw Char = msg` (private), `shout/dw <msg>` (room + muffled partial text in adjacent rooms with direction). Switch parsing handles both `/switch` in cmdname and in args (Evennia base Command puts switches in args in the live game). SILENCED blocks speech, DEAF blocks hearing, INVISIBLE shows "Someone", COMPREHEND_LANGUAGES bypasses garble. `languages` command lists known languages.
- FLY condition gating: `fly up` requires FLY condition, fall damage (10 HP/level) on FLY removal while airborne
- Underwater breath timer: BreathTimerScript (CON-based duration: `30 + CON_mod * 15` seconds, min 10s), drowning damage when expired, WATER_BREATHING bypasses entirely
- Death system: `die()` creates corpse, strips items/gold/resources to corpse, stops combat handler, enters purgatory (60s timer or 50g early release), 5% XP penalty, HP reset to 1. Drowning and starvation trigger death. Default home set to Limbo at character creation; `_purgatory_release()` falls back to Limbo if home is None. `at_post_puppet` reschedules purgatory timer if character stuck on login.
- Corpse with loot/loot all commands and decay timers
- Cemetery rooms with `bind` command — sets character's `home` as respawn point on death (upgrades from Limbo default). Configurable `bind_cost` (default 1 gold) on RoomCemetery.
- XP levelling: `highest_xp_level_earned` guard prevents duplicate level rewards after death XP loss. Level 40 cap prevents infinite recursion.
- NPC hierarchy: BaseNPC → TrainerNPC (training system complete), GuildmasterNPC (QuestGiverMixin + BaseNPC, quest system + level caps), ShopkeeperNPC (AMM shop commands), QuestGivingShopkeeper (QuestGiverMixin + LLMRoleplayNPC + ShopkeeperCmdSet + quest-aware context + shop command prompt injection), QuestGivingLLMTrainer (QuestGiverMixin + LLMMixin + TrainerNPC — LLM chat + training, no quest required), BartenderNPC (QuestGiverMixin + LLMRoleplayNPC, quest-aware with 5 player states), CombatMob (AI-driven mobs with combat + respawn). QuestGiverMixin (`typeclasses/mixins/quest_giver.py`) — shared quest accept/abandon/view/turn-in command, used by all quest-giving NPCs. Two-tier CmdSet visibility (`call:true()` + `_EmptyNPCCmdSet`). Service NPCs inject role commands. BakerNPC (QuestGivingShopkeeper subclass) — Bron at Goldencrust Bakery, trades flour/bread, 4 quest states (pitch/active/done/generic) + level gate. Millhaven NPC spawner (`world/game_world/spawn_millhaven_npcs.py`): Rowan (bartender), Bron (baker), Master Oakwright (woodshop trainer+quest), Sergeant Grimjaw (warrior guildmaster), Corporal Hask (warrior trainer), Shadow Mistress Vex (thief guildmaster), Whisper (thief trainer), Archmage Tindel (mage guildmaster), Apprentice Selene (mage trainer), Brother Aldric (cleric guildmaster), Sister Maeve (cleric trainer), Old Silas (beggar LLM NPC in Beggar's Alley), Gemma (jeweller LLM trainer, BASIC), Merchant Harlow (general store shopkeeper, flour+bread), Farmer Bramble (wheat farmer shopkeeper at Goldwheat Farm), Goodwife Tilly (cotton farmer shopkeeper at Brightwater farmhouse), Ratwick (fence LLM NPC in The Broken Crown, regular memory, NFT shop placeholder), Big Bjorn (lumberjack LLM shopkeeper at Millhaven Sawmill, sings Lumberjack Song on arrival, wheat/flour placeholder for wood/timber AMM), Old Buckshaw (trapper LLM shopkeeper at Trapper's Hut in southern woods, coureur des bois personality, wheat placeholder for hide AMM).
- Mob AI system: AIHandler state machine (`typeclasses/actors/ai_handler.py`), CombatMob base class (`typeclasses/actors/mob.py`). TICKER_HANDLER-driven AI loop, `delay()` for one-shot reactions. Room notification via `at_new_arrival()` in `RoomBase.at_object_receive()`. Area-restricted wandering via `mob_area` tags. Anti-stacking: `max_per_room` attribute (default 0 = unlimited) prevents same-type mobs from wandering into a room that already has that many of them — e.g. Wolf uses `max_per_room=1` so wolves don't gang up on players. AggressiveMob (`typeclasses/actors/mobs/aggressive_mob.py`) — CombatMob subclass with arrival aggro + wander scan; used directly as prototype typeclass for JSON-configured mobs (sewer rats). Animal mobs: Rabbit (flees threats), Wolf (AggressiveMob, L2, 12HP, 1d4 — attacks players + hunts rabbits, max 1 per room), DireWolf (AggressiveMob, L3, 30HP, 2d6 — attacks players, 25% dodge), CellarRat (AggressiveMob, L1, 4HP, 1d2 — dungeon mob). Kobold (AggressiveMob, L2, 14HP, 1d4 — pack courage: fights with 1+ allies, flees solo, fights when cornered; mid-combat flee if allies die; aggro_hp_threshold=0.7). Gnoll (AggressiveMob, L4, 40HP, 1d6+2 — Rampage: at_kill() fires instant execute_attack() on next player, max 2/room, aggro_hp_threshold=0.25, flees when wounded). Kill hook: `at_kill(victim)` on CombatMob base (no-op), called from `combat_utils.py` after `weapon.at_kill()` when target HP ≤ 0. Mobs use same command interface as players (`CmdSetMobCombat` + `execute_cmd()`) — enables future LLM AI with zero refactoring.
- Zone Spawn Script system: `ZoneSpawnScript` (`typeclasses/scripts/zone_spawn_script.py`) — persistent Evennia Script that maintains mob populations for static zones. One script per zone, reads spawn rules from JSON files (`world/spawns/<zone>.json`). Ticks every 15 seconds, audits population per rule, spawns replacements when below target. Each rule specifies typeclass, area_tag, target count, max_per_room, respawn_seconds, desc, and optional attrs. Common mobs (`is_unique=False`) are **deleted** on death — the script spawns fresh objects. Rule identity = `typeclass + area_tag` (same mob type can have different rules per patch). `area_tag` serves double duty: spawn room pool AND AI wander containment. Factory method: `ZoneSpawnScript.create_for_zone("zone_key")` loads JSON + does initial `populate()`. Supports hot-reload of JSON config. Procedural dungeons are out of scope — they manage their own mobs internally. **Two spawn systems by design:** (1) ZoneSpawnScript for commodity mobs (fixed-level, guaranteed spawns, population maintenance — rabbits, wolves, rats), (2) a separate rare/boss mob spawn system (future) with spawn chance, unique conditions, time/weather gating, one-at-a-time enforcement. Item/resource drops handled by separate spawn scripts, not traditional loot tables. Static zones use fixed-level mobs (e.g. Millhaven = levels 1-2); procedural zones will have their own spawn mechanism with level scaling.
- LLM NPC system: `LLMMixin` (`typeclasses/mixins/llm_mixin.py`) adds LLM-powered dialogue to any NPC/mob. `LLMService` (`llm/service.py`) — centralized OpenRouter API client with sliding-window rate limiting (global 60/min + per-NPC 6/min), per-NPC cooldown (5s), daily cost cap ($5). Prompt templates in `llm/prompts/` loaded via `llm/prompt_loader.py` with `lru_cache`. Configurable speech detection modes per-NPC (`llm_speech_mode`): `"name_match"` (free — pattern match NPC name), `"llm_decide"` (LLM decides relevance), `"always"` (respond to all speech), `"whisper_only"` (cheapest). Hookable triggers: `llm_hook_say`, `llm_hook_whisper`, `llm_hook_arrive`, `llm_hook_leave`, `llm_hook_combat` — each enabled per-NPC. `CmdSay` notifies LLM NPCs of room speech; `CmdWhisper` extended to notify on whispers. Response delivery matches incoming mode (whisper→whisper back, say→say to room). Memory abstraction: `_store_memory`/`_get_relevant_memories` — Phase 1 rolling list in `db` attributes, designed for future pgvector swap. Response sanitization strips quotes, command prefixes, newlines, truncates to 500 chars. Non-blocking via `deferToThread` + `reactor.callFromThread`. First actor class: `LLMRoleplayNPC` (`typeclasses/actors/npcs/llm_roleplay_npc.py`). `BartenderNPC` (`typeclasses/actors/npcs/bartender_npc.py`) — quest-aware subclass of LLMRoleplayNPC for Rowan. Overrides `_get_context_variables()` to inject `{quest_context}` based on player's tutorial/quest state. Level gate (level >= 3 → generic bartender). 5 states: new player pitch (tutorial + quest offer), quest pitch (tutorial done, steer to cellar), quest active (encouragement), tutorial suggest (quest done, suggest tutorial), generic (friendly bartender). Prompt template (`bartender.md`) has fixed frame (identity, personality, location, memories) + single `{quest_context}` variable containing state-specific knowledge + rules. `QuestGivingShopkeeper` (`typeclasses/actors/npcs/quest_giving_shopkeeper.py`) — generic typeclass combining LLMRoleplayNPC + ShopkeeperCmdSet. Injects `{quest_context}` (state-specific LLM instructions) and `{shop_commands}` (formatted command list with color codes so NPC can guide players). Override `_build_quest_context()` in subclasses. `BakerNPC` (`typeclasses/actors/npcs/baker_npc.py`) — Bron the Baker, QuestGivingShopkeeper subclass. 4 quest states: pitch flour quest, quest active (encouragement), quest done (uncomfortably grateful), generic baker. Trades flour (ID 2) and bread (ID 3). Short-term memory only. 17 tests. 11 bartender tests. Conversation engagement: after responding, NPC stays engaged with that speaker for `llm_engagement_timeout` seconds (default 60) — follow-up messages don't need the NPC's name. Available commands from NPC's cmdset injected into prompt as `{available_commands}` — NPC won't agree to actions it can't perform. Default model: `openai/gpt-4o-mini` via OpenRouter. Settings in `settings.py` (`LLM_ENABLED`, `LLM_API_BASE_URL`, `LLM_API_KEY`, etc.). Test NPC "Chatty" spawned on dirt track 3 via `spawn_npcs.py`. **Vector memory system** (`ai_memory/` Django app): persistent NPC memory with OpenAI embeddings stored as binary blobs in separate `ai_memory.db3` SQLite database (survives game DB wipes). Dual memory system per NPC: `llm_use_vector_memory=False` (default) uses rolling list in `db` attributes, `True` uses `ai_memory` with semantic search via numpy cosine similarity. `LLMService.create_embedding()` generates vectors via OpenAI `text-embedding-3-small`. Temporal awareness: `_time_ago_str()` produces natural time references ("yesterday", "back in December"), injected via `{last_seen}` template variable and timestamped memory entries. Name-based fallback matching enables memory survival across game DB wipes (Evennia object IDs change but NPC names don't). Migrate: `evennia migrate --database ai_memory`. 52 tests (27 LLM NPC + 25 ai_memory).
- Combat system: real-time (twitch) combat via per-combatant `CombatHandler` scripts (`combat/combat_handler.py`). Shared `execute_attack()` (`combat/combat_utils.py`) fires all 14 weapon hooks in order. `enter_combat()` creates handlers on all combatants + group members. `get_sides()` detects allies/enemies (PvP-aware). `CmdAttack` command (`attack`/`kill`/`att`/`k`). Count-based advantage/disadvantage: `{target_id: int}` rounds remaining, consumed 1 per attack, minimum 1 per round decrement for unused entries. `set_advantage(target, rounds=N)` takes max of existing and new. `consume_advantage(target)` on attack, `decrement_advantages()` at end of each tick. Weapon speed determines attack interval. Group combat: one member attacks, whole group enters combat. Bystanders without combat handlers stay out. Both players and mobs use identical attack resolution path. `CmdDodge` gives up attacker's next action to give all enemies disadvantage (1 round) — uses `skip_next_action` flag and `at_combat_tick()` hook for mob AI decisions (DireWolf: 75% attack, 25% dodge). `CmdFlee` (`flee`/`run`/`escape`): in combat, DEX check (d20 + DEX mod vs DC 10) — success flees through random open exit and leaves combat, failure loses the action and all enemies get 1 round advantage; out of combat, comic panic run through random exit (auto-success) with mocking room message. CmdSkillBase mastery branch: callers with `skill_mastery_levels` get full mastery dispatch, callers without (animal mobs) get `mob_func()` fallback. Parry system: weapons with `get_parries_per_round() > 0` attempt automatic parries against melee weapon attacks (not unarmed/animal). Parry roll = d20 + DEX mod + mastery hit bonus vs attacker's total hit; success blocks damage, both weapons lose 1 durability. Parries reset each tick. Durability loss on combat: weapon -1 on hit, body armor -1 on hit, both weapons -1 on parry, helmet -1 when CRIT_IMMUNE downgrades a crit. Multi-attack: `effective_attacks_per_round` property on BaseActor composes `attacks_per_round` (base + condition effects like HASTED) + weapon `get_extra_attacks()` mastery bonus. Combat handler reads this single property. HASTED non-stacking: `newly_gained`/`fully_removed` gates prevent double stat bonus from multiple haste sources. Finesse weapons: `is_finesse = True` on weapon → `effective_hit_bonus`/`effective_damage_bonus` use `max(STR, DEX)` instead of just STR. Riposte system: after a successful parry, if defender's weapon has `has_riposte()`, fires a free counter-attack (`execute_attack(defender, attacker, _is_riposte=True)`). Riposte attacks skip the parry check to prevent infinite recursion. Longsword mastery path: custom hit bonuses (-2/0/+2/+4/+4/+5), parries (0/0/1/2/2/3), +1 attack at MASTER+, parry advantage at GRANDMASTER. Rapier mastery path: finesse, custom hit bonuses (-2/0/+2/+3/+4/+5), parries (0/0/1/1/2/3), riposte at EXPERT+, parry advantage at GRANDMASTER. 74 combat tests.
- Training system: gold cost with CHA modifier discount, per-skill trainer mastery caps, progress bars via `delay()`, d100 success rolls, per-trainer 1-hour cooldown on failure, enum-driven skill/weapon access validation. 55 tests.
- GuildmasterNPC: guild info, quest management, join class, advance level commands. Per-guildmaster `max_advance_level` caps (forces exploration to find senior guildmasters), `next_guildmaster_hint` redirect messages. Full multiclass requirement checks (race/alignment/remort/ability scores/quest completion).
- Quest system: FCMQuest base class with step-based progression, FCMQuestHandler (lazy_property on character), quest registry with `@register_quest` decorator, QuestTagMixin on rooms, QuestGiverMixin on NPCs (shared quest command). Templates: CollectQuest, VisitQuest, MultiStepQuest. Guild quests: Warrior Initiation (rat cellar check — instant if already done, else send to clear rats), Thief Initiation (VisitQuest — reach Cave of Trials boss room), Mage Initiation (deliver 1 Ruby), Cleric Initiation (feed bread to beggar in Beggar's Alley — QuestTagMixin room trigger). CmdQuests character command for quest log. 87 quest command tests + 21 mixin tests.
- Test world NPC spawner (`world/test_world/spawn_npcs.py`) — Warriors Guild: Sergeant Grimjaw (trainer), Warlord Thane (guildmaster, level 5 cap). Thieves Guild: Whisper (trainer, skilled mastery), Shadow Mistress Vex (guildmaster, level 5 cap). Mages Guild: Archmage Tindel (trainer in Wizard's Workshop, skilled mastery), High Magus Elara (guildmaster, level 5 cap). Temple: Brother Aldric (trainer in Temple Sanctum, skilled mastery), High Priestess Maren (guildmaster, level 5 cap).
- World objects system: non-NFT world fixtures and items
  - WorldFixture: immovable, `get:false`, HiddenObjectMixin + InvisibleObjectMixin, combined `is_visible_to()` check
  - WorldItem(HiddenObjectMixin): takeable non-NFT items, `can_export=False`, `can_bank=True`, `is_visible_to()` for room display filtering
  - KeyItem(WorldItem): consumable keys matched by `key_tag`, `can_bank=False`, consumed on successful unlock
  - WorldSign(WorldFixture): ASCII art sign templates (post/hanging/wall/stone), read-only
  - WorldChest(SmashableMixin, LockableMixin, CloseableMixin, ContainerMixin, FungibleInventoryMixin, WorldFixture): closeable + lockable + smashable container, starts closed, contents gated on open state
  - ExitDoor(SmashableMixin, LockableMixin, CloseableMixin, InvisibleObjectMixin, HiddenObjectMixin, ExitVerticalAware): closeable/lockable/smashable exit, blocks traverse when closed/locked, display name shows state
  - **MRO rule**: SmashableMixin first, then LockableMixin MUST come before CloseableMixin so `can_open()` gate works via `super()` chain
- Closeable/Lockable mixins (reusable across chests, doors, future objects):
  - CloseableMixin: `is_open`, `open()`/`close()`, `can_open()` hook for subclass gates
  - LockableMixin: `is_locked`, `lock_dc`, `key_tag`, `relock_seconds`, `unlock()` (key-based), `picklock()` (SUBTERFUGE skill-based), auto-relock via RelockTimerScript
  - RelockTimerScript: one-shot timer that re-locks and closes its parent object
- SmashableMixin: `is_smashable`, `smash_hp`/`smash_hp_max`, `smash_resistances` (dict of damage_type → % reduction, 100=immune, negative=vulnerable), `take_smash_damage(raw, damage_type)` → `(dealt, broke)`, `at_smash_break()` forces open. Scaffold only — no player command yet.
- TrapMixin (`typeclasses/mixins/trap.py`): reusable mixin for trapped objects (doors, chests, exits, rooms). Attributes: `is_trapped`, `trap_armed`, `trap_detected` (global), `trap_find_dc`, `trap_disarm_dc`, `trap_one_shot`, `trap_reset_seconds`, `trap_damage_dice`, `trap_damage_type`, `trap_effect_key`/`trap_effect_duration`/`trap_effect_duration_type` (named effects), `trap_is_alarm`, `trap_description`. Methods: `detect_trap(finder)`, `trigger_trap(victim, room)` (damage + named effects + alarm + one-shot + reset timer), `disarm_trap(character)` (d20 + SUBTERFUGE mastery + DEX mod vs DC, fail triggers trap), hooks: `at_trap_trigger()`, `at_trap_disarm()`. TrapResetScript re-arms + re-hides after `trap_reset_seconds`.
  - TrapChest(TrapMixin, WorldChest): trapped chest, fires trap on `open()` and `at_smash_break()`, shows "(trapped)" when detected
  - TrapDoor(TrapMixin, ExitDoor): trapped door, fires trap on `at_open()` and `at_smash_break()`, shows "(trapped)" when detected
  - TripwireExit(TrapMixin, ExitVerticalAware): tripwire on exit, triggers on traverse if undetected (blocks movement), safe step-over if detected, shows "(tripwire)" when detected
  - PressurePlateRoom(TrapMixin, RoomBase): pressure plate room, freezes first character on entry (`pressure_plate_victim`), explosion on attempted leave (AoE all occupants), `check_pre_leave()` called from FCMCharacter.`at_pre_move()`, `at_trap_disarm()` unfreezes victim
  - **MRO rule**: TrapMixin goes first in class hierarchy (e.g., `TrapChest(TrapMixin, WorldChest)`)
  - Passive trap detection: `FCMCharacter._check_traps_on_entry()` in `at_post_move()`, passive_dc = 10 + effective_perception_bonus vs trap_find_dc
  - Generic room pre-leave hook: `FCMCharacter.at_pre_move()` calls `self.location.check_pre_leave()` if available — extensible for future movement-blocking mechanics
- Hidden/Invisible object mixins (separate from character conditions):
  - HiddenObjectMixin: `is_hidden`, `find_dc`, `discovered_by` set, `discover()` broadcasts and reveals to room
  - InvisibleObjectMixin: `is_invisible`, DETECT_INVIS gate
  - Room appearance filtering: `get_display_things()`, `get_display_characters()`, `get_display_exits()` all filter by hidden/invisible state
- CircleMUD-style room display:
  - Template overhaul: no section labels (`Exits:`, `Characters:`, `Things:`), empty sections suppressed entirely, color scheme: |c cyan room name + exits, |g green objects, |y yellow characters
  - Brief mode: `brief` toggle skips room descriptions on movement. `look` always shows full description (passes `ignore_brief=True`).
  - Compact auto-exit line: `|c[ Exits: n e s w ]|n` — abbreviates cardinal directions, shows full name for non-cardinal exits. Only shown when player has `auto_exits=True`. Closed/locked doors hidden from auto-exits (filtered in `get_display_exits()`).
  - Characters shown one-per-line with descriptive sentences (not comma-separated list): NPCs use `room_description` if set, PCs use position-based templates ("Bob is resting here.", "Sally stands here."). Visibility tags `(invisible)`/`(hidden)` appended for lookers who pass detection checks.
  - `room_description` AttributeProperty on BaseActor (`None`, `autocreate=False`) — custom sentence for how the character appears in the room list. Supports `{name}` placeholder. Set via `roomdesc` command (200 char max, `roomdesc clear` to reset). `get_room_description()` method returns position-aware display: uses room_description at standing, switches to position suffix at other positions.
  - `exits` command (alias `ex`): verbose exit listing showing direction, destination, description, and door state (closed/locked). Canonical compass ordering. Hides "This is an exit." default. Darkness check. Available regardless of auto_exits setting.
  - `look <direction>` support: direction parsing in `cmd_override_look.py`, shows exit destination and door state.
- Position/posture system:
  - `position` AttributeProperty on BaseActor (default `"standing"`). Values: `"standing"`, `"sitting"`, `"resting"`, `"sleeping"`, `"fighting"`.
  - Posture commands: `sit`, `rest`, `sleep`, `stand`, `wake` — with combat guard (can't change posture while fighting), same-position guard, room messages.
  - Movement blocking: `at_pre_move()` in FCMCharacter blocks movement unless position is `"standing"` or `"fighting"`.
  - Regen multipliers: `REGEN_MULTIPLIERS` class dict on BaseActor — `standing: 1, sitting: 1, resting: 2, sleeping: 3, fighting: 0`. Applied in `RegenerationService.regenerate()`.
  - Combat integration: `combat_handler.start_combat()` sets `position="fighting"`, `stop_combat()` sets `position="standing"`. `ndb.combat_target` tracks current combat target for room display ("Bob is here, fighting a goblin!").
  - Position-aware room display templates: `_POSITION_TEMPLATES` dict on BaseActor for default display per position. `get_room_description()` dispatches between custom room_description and templates.
  - 18 posture tests + 6 room description tests.
- World interaction commands:
  - `open`/`close`: closeable objects in room (chests, doors)
  - `unlock`: key-based unlocking (searches inventory for matching KeyItem, consumed on use)
  - `lock`: lock a closed lockable object
  - `search`: d20 + alertness mastery bonus + WIS mod vs hidden object find_dc, also detects traps (objects, exits, rooms) by rolling vs trap_find_dc
  - `picklock` (alias `pl`): SUBTERFUGE skill command, d20 + mastery bonus + DEX mod vs lock_dc
  - `case`: SUBTERFUGE skill command. Scout a target's inventory before pickpocketing. Per-item visibility roll based on mastery (BASIC 50% → GM 90%). Vague gold display (tiers not exact amounts). Results cached 5 minutes. Does not break HIDDEN.
  - `pickpocket` (alias `pp`): SUBTERFUGE skill command. Steal gold/resources/items from a cased target. Contested roll: d20 + DEX mod + SUBTERFUGE bonus vs 10 + target perception. HIDDEN gives advantage. Always breaks HIDDEN. Failure alerts target, aggressive mobs aggro. Requires combat-enabled room (PvP room for player targets). 60s per-target cooldown.
  - `stab` (aliases `backstab`, `bs`): STAB skill command. 5e-style Sneak Attack — when the thief has advantage (from HIDDEN, target ENTANGLED, etc.), adds bonus damage dice to next attack. Scaling: BASIC +2d6, SKILLED +4d6, EXPERT +6d6, MASTER +8d6, GM +10d6. Crits double the bonus dice. Once per round. Can be used as opener from stealth (enters combat, sets advantage, queues attack) or mid-combat whenever advantage exists. Uses generic `bonus_attack_dice` mechanism on CombatHandler (consumed by `execute_attack()`).
  - `assist`: BATTLESKILLS general skill (all classes). In combat: give up your attack to grant an ally advantage against all enemies. Mastery scaling: BASIC 1 round, SKILLED 2, EXPERT 3, MASTER 4, GM 5 rounds. Out of combat: set `non_combat_advantage` on target for their next skill check. Uses `get_sides()` for ally/enemy detection. 18 tests.
  - `bash` (alias `b`): BASH skill (warrior). High risk/high reward combat maneuver — contested STR + mastery vs target STR. Success: target PRONE 1 round (loses turn + enemies get advantage via on-apply callback). Failure: basher DEX save DC 10 or fall prone. Multi-round cooldown scaling: BASIC 7, SKILLED 6, EXPERT 5, MASTER 4, GM 3 rounds. Cooldown only prevents re-use — normal attacks continue.
  - `pummel` (alias `p`): PUMMEL skill (warrior, paladin). Low risk/low reward combat maneuver — contested STR + mastery vs target DEX. Success: target STUNNED 1 round (loses turn, no advantage for enemies). Failure: nothing happens. Multi-round cooldown scaling: BASIC 8, SKILLED 7, EXPERT 6, MASTER 5, GM 4 rounds.
  - `disarm` (alias `dis`): SUBTERFUGE skill command. Disarm a detected trap on objects, exits, or rooms. Supports room keywords ("floor", "ground", "plate", "room", "pressure") for pressure plates. Delegates to `target.disarm_trap(caller)` on TrapMixin. Failed disarm triggers the trap.
  - `identify` (alias `id`): LORE skill command (bard). Identify items and creatures using bardic knowledge. No mana cost. Reuses Identify spell's `_identify_actor()` and `_identify_item()` template builders directly (imported from `world/spells/divination/identify.py`). LORE mastery maps 1:1 to identification tier (BASIC=tier 1 through GM=tier 5). Same level gating as the spell for actors, same `identify_mastery_gate` check for items. PvP room restriction for identifying other players. Overrides `func()` directly (no per-mastery dispatch). 11 tests.
  - `protect`: PROTECT skill (warrior, paladin). Toggle-based tanking — `protect <ally>` to start intercepting attacks aimed at that ally, `protect` or `protect <same ally>` to stop. Flat percentage intercept chance per mastery: BASIC 40%, SKILLED 50%, EXPERT 60%, MASTER 70%, GM 80%. On intercept, protector takes the full damage (using protector's own resistances/armor). Multiple protectors on one target supported (each rolls independently, first success wins). Stores `protecting = target.id` on protector's CombatHandler. Intercept hook in `execute_attack()` step 8b: after damage calculation, before `take_damage()` — swaps local `target` variable so protector's armor takes durability loss and kill check applies to protector. Must be in combat, target must be an ally in combat.
  - `taunt`: PROTECT skill (warrior, paladin). Taunt a mob to provoke it into attacking you. Two modes: **Opener** (out of combat) — contested d20 + CHA mod + mastery bonus vs d20 + target WIS mod. Success: mob attacks taunter (mob is initiator — important for future crime tracking). Failure: 5-minute per-character cooldown. **In combat** — same contested roll, success switches mob's target to taunter. Round-based cooldown scales with mastery (BASIC 6, SKILLED 5, EXPERT 4, MASTER 3, GM 2). Only works on CombatMob instances (not players). TAUNT skill enum removed — taunt is now a command under PROTECT.
  - `offence` (alias `offense`): STRATEGY skill (warrior, paladin). Group leader command — toggles offensive stance for leader + all followers in combat in same room. Stat bonuses via named effects (`stat_bonus` type): BASIC +2 hit/-1 AC, SKILLED +3 hit/-1 AC, EXPERT +3 hit/+1 dam/-1 AC, MASTER +3 hit/+2 dam/-1 AC, GM +3 hit/+3 dam/no AC penalty. Mutually exclusive with defence. `duration=None, duration_type="combat_rounds"` = permanent in combat, auto-cleaned on combat end.
  - `defence` (alias `defense`): STRATEGY skill (warrior, paladin). Mirror of offence — toggles defensive stance. BASIC +2 AC/-2 hit, SKILLED +2 AC/-2 hit, EXPERT +3 AC/-1 hit, MASTER +4 AC/-1 hit, GM +5 AC/no hit penalty. Mutually exclusive with offence.
  - `retreat` (alias `ret`): STRATEGY skill (warrior, paladin). Group leader command — strategic withdrawal. Single leader roll: d20 + INT mod + CHA mod + mastery bonus vs DC 10. Success: stop combat + move entire group (leader + followers in combat in same room) through chosen/random exit. Failure: nobody moves, enemies get 1 round advantage against leader. Optional direction argument. Captures enemies before movement, stops combat before moving.
  - `sail`: SEAMANSHIP general skill (all classes). Sea travel via dock gateway rooms (RoomGateway with `boat_level` condition). Two-pass ship selection: `sail` lists routes, `sail <dest>` shows qualifying ships (auto-sails if single ship), `sail <dest> <#>` sails with chosen ship. Ship ownership via NFTMirror — ships are NFTs that don't spawn as in-game objects (`prototype_key=None`). 5 ship types (Cog/Caravel/Brigantine/Carrack/Galleon) mapped 1:1 to mastery tiers (BASIC–GRANDMASTER) via `ShipType` enum. `BaseNFTItem.get_qualifying_ships()` / `get_best_ship_tier()` / `get_character_ships()` as single point of entry for ship queries. `_check_boat_level()` validator in `cmd_travel.py` for gateway condition checks. Test world docks: Town Dock (off dt6) ↔ Beach Dock (off beach room), `boat_level: 1, food_cost: 1`. 23 tests.
  - Container access (get/put from) gated on `is_open` state
- Non-combat advantage/disadvantage system: `db.non_combat_advantage` / `db.non_combat_disadvantage` boolean flags on actors. All non-combat d20 skill checks use `dice.roll_with_advantage_or_disadvantage()`. Cancellation: both True → normal roll. Consumed after each check. See "CRITICAL: Non-Combat Advantage/Disadvantage" section for full pattern.
- Skill command scaffolds: 24 scaffold commands covering remaining skills in the enum. Each extends CmdSkillBase (mastery dispatch with `mob_func()` fallback for animal mobs) with design notes as docstrings. Commands print `"'{key}' Command using Skill '{skill}' - {Tier}"` at each mastery level. Fully implemented (not scaffolds): dodge, assist, stab, bash, pummel, protect, taunt, offence, defence, retreat, sail, disarm, identify. General skills: dodge, assist (implemented), chart, build, sail (implemented — see below), explore, tame, repair. Warrior: bash, pummel, protect, taunt, offence, defence, retreat (implemented), frenzy. Thief: sneak, stab (implemented — see above), assassinate, recite. Bard: perform, inspire, mock, charm, divert, disguise, conceal, identify (implemented — LORE skill, reuses Identify spell templates). Druid/Ranger: forage (implemented — see hunger system), track, summon, dismiss, shapeshift (alias ss). Cleric: turn. PARRY and SHARPSHOOTER removed from enum (moving to weapon mastery perks). TAUNT removed from skills enum (merged into PROTECT). STRATEGIST renamed to STRATEGY.
- Follow/Group system: `follow <player>`, `unfollow`, `nofollow` toggle, `group` display. Chain-resolution (A follows B follows C → A's leader is C). Auto-follow on exit traversal via `FCMCharacter.at_post_move()` with `move_type in ("follow", "teleport")` guard — followers cascade on normal moves but NOT on teleports or follow moves. Collects all followers (direct + indirect) at the leader level. `nofollow` removes existing followers. Underpins strategy skill group buffs, dungeon entry, XP sharing.
- Procedural dungeon system: lazy room creation on a coordinate grid with tag-based tracking. Two dungeon types: `"instance"` (boss at termination depth, dead-end) and `"passage"` (connects two world rooms via `DungeonPassageExit`). Three instance modes: `"solo"` (one per player), `"group"` (leader + followers), `"shared"` (one instance per entrance, anyone joins, `empty_collapse_delay` keeps alive). Two entry triggers determined by builder placement (not template): `DungeonEntranceRoom` (command `enter dungeon`) or `DungeonTriggerExit` (movement-triggered, walk through exit). Same template works with either trigger. `DungeonTemplate` frozen dataclass (`dungeon_type`, `instance_mode`, `boss_depth`, exit budget, lifetime, room/boss generators). `DungeonInstanceScript` orchestrator with state machine (active→collapsing→done), 60s tick. `DungeonExit` with lazy creation (exits point to self until traversed). Manhattan distance depth. Three collapse safety nets (lifetime, post-boss linger, empty instance with optional delay for shared). Server restart cleanup in `at_server_startstop.py`. Teleport moves do not cascade followers (`at_post_move` guard). Cave of Trials test template with depth-scaled descriptions. Deep Woods Passage template (`world/dungeons/templates/deep_woods_passage.py`) — passage type, group mode, boss_depth=5, low branching (max 1 new exit per room), forest-themed descriptions at 3 depth tiers. Rat Cellar template (`world/dungeons/templates/rat_cellar.py`) — instance type, solo mode, 1-room dungeon (max_unexplored_exits=0, max_new_exits_per_room=0), spawns 3 CellarRat + 1 RatKing boss, `allow_death=False` with defeat_destination_key="The Harvest Moon", post_boss_linger_seconds=60. `QuestDungeonTriggerExit` (`typeclasses/terrain/exits/quest_dungeon_trigger_exit.py`) — subclass of DungeonTriggerExit with `quest_key` and `fallback_destination_id`; routes to fallback room when quest complete, auto-accepts quest on first entry, creates dungeon instance for in-progress quest. 38 dungeon tests.
- Zone/District/Terrain tagging: Every room has `category="zone"` and `category="district"` Evennia tags. RoomBase provides `set_zone()`, `get_zone()`, `set_district()`, `get_district()`, `set_terrain()`, `get_terrain()` helpers. Two spatial concepts: **zone** (top-level region), **district** (sub-region within zone). **Terrain** (`category="terrain"`, `enums/terrain_type.py`): URBAN, RURAL, FOREST, MOUNTAIN, DESERT, SWAMP, COASTAL, UNDERGROUND, DUNGEON, WATER, ARCTIC, PLAINS. Used by forage command and future systems (tracking, weather, mounts, spawning). Test world zones: `test_economic_zone` (wolf/guild/market/resource/bank districts), `test_water_fly_zone` (beach/ocean districts), `arena_zone` (arena/infirmary districts), `system_zone` (purgatory/recycle bin). Game world zones: `millhaven` (millhaven_town, millhaven_farms, millhaven_woods, millhaven_sewers, millhaven_mine, millhaven_deep_woods, millhaven_faerie_hollow, millhaven_southern districts).
- Help category system: 14 categories (Character, Combat, Communication, Crafting, Exploration, Group, Group Combat, Items, Magic, Nature, Performance, Stealth, System, Blockchain). Thin overrides of Evennia defaults for recategorisation. `is_ooc()` custom lock function hides blockchain commands (bank, wallet, import, export) and character management commands (charcreate, chardelete) when puppeting. Password command restricted to developer-only.
- Game world build system (`world/game_world/`): Separate from test world. Entry point: `build_game_world.py`. Soft rebuild: `soft_rebuild_game_world.py` (zone-tag-based cleanup, preserves players/system rooms). Millhaven Town district (`millhaven_town.py`): ~35 rooms, ~70 exits. The Old Trade Way (8-segment E-W road), 2×2 Townsquare, The Harvest Moon Inn (with stairwell chain: ground→cellar stairwell→rat cellar quest dungeon [QuestDungeonTriggerExit south] / permanent cellar [post-quest], ground→first floor→hallway→bedrooms), crafting shops (smithy, leathershop, tailor, woodshop, apothecary, The Gilded Setting jeweller [RoomCrafting, jeweller type, BASIC mastery]), Goldencrust Bakery (RoomProcessing), Order of the Golden Scale bank (RoomBank, brass sign detail with banking commands), Millhaven Post Office (RoomPostOffice, east of bank, services board detail with mail commands), guild halls (warriors/mages/temple with back rooms), The Iron Company (warrior guild back room — Sergeant Grimjaw guildmaster + Corporal Hask trainer), general store, stables, residential houses, Millhaven Cemetery (RoomCemetery, north of road_far_east), Hilda's Distillery (east of apothecary), secret passage (Gareth→Abandoned House). District intersection rooms stub future connections: road_far_east→Woods, cellar_stairwell→Sewers, abandoned_house→Sewers. Limbo connects down/up to The Harvest Moon. Zone tag: `millhaven`, district tag: `millhaven_town`. Millhaven Farms district (`millhaven_farms.py`): ~56 rooms. The Old Trade Way continues west (10 road segments), Goldwheat Farm (fencelines, 4 wheat edge fields, 4-room wheat maze with one-way exits — maze rooms are RoomHarvesting for wheat resource_id=1, edge fields are NOT harvestable), Millhaven Windmill (RoomProcessing — wheat→flour), South Fork road (4 rooms), Brightwater Cotton Farm (farmyard, cotton barn, drying shed, 3×3 cotton field grid, 4-room underground tunnel/vault with exit to south fork), Abandoned Farm (ruined buildings, 4×2 overgrown field grid). Connects west from town's road_far_west. Zone tag: `millhaven`, district tag: `millhaven_farms`. Millhaven Woods district (`millhaven_woods.py`): ~93 rooms. Forest Path East (interface from town's road_far_east), 17-room winding main path (east through light woods to wooded foothills, alternating east/northeast/southeast directions), Millhaven Sawmill (RoomProcessing — wood→timber, 2-room spur north), Millhaven Smelter (RoomProcessing — ores→ingots including alloys, 2-room spur south), 10×6 southern woods exploration grid (60 rooms) with boundary self-loops (west/east/south edges loop back to same room creating infinite-forest feel), POI rooms in grid (Game Trail Crossing, Stone Cairn, Fallen Giant, Berry Bramble, Rabbit Warren, Trapper's Hut, Old Snare Line, Fox Earth, Hollow Log, Spring-fed Pool). Grid row 1 connects north to main path rooms 5-14. Northern woods row (10 "Dense Woods" rooms north of main path rooms 5-14) — denser transition zone, all funnel north via one-way exits into single Edge of the Deep Woods entry room. Deep woods entry south exit returns to middle of northern row (asymmetric). Deep woods entry north: procedural passage (DungeonTriggerExit) to deep_woods_clearing, wired in build_game_world.py. Connects east from town's road_far_east. Zone tag: `millhaven`, district tag: `millhaven_woods`. Millhaven Sewers district (`millhaven_sewers.py`): ~26 rooms. Sewer proper (18 rooms, terrain UNDERGROUND): main north-south spine (Sewer Entrance→Main Drain→Drain Junction→Flooded Tunnel→Deep Sewer→Overflow Chamber→Crumbling Wall) with 3 dead-end branches (Blocked Grate, Rat Nest, Collapsed Section); cistern branch (Old Cistern→Waterlogged Passage→Fungal Grotto→Narrow Crawlway→Ancient Drain→Overflow Chamber) with 2 dead ends (Submerged Alcove, Bricked-Up Passage) — connects abandoned house entrance to main spine. Thieves' Lair (8 rooms, terrain DUNGEON): hidden behind crumbling wall (find_dc=20), Thieves' Tunnel→Guard Post→Thieves' Hall hub with Planning Room (east), Barracks (west), Training Alcove (east of guard post), Stolen Goods (south)→Shadow Mistress's Chamber (east). Cross-district hidden doors in `build_game_world.py`: cellar stairwell→sewer entrance (west, find_dc=16), abandoned house→old cistern (down, find_dc=18). Both routes are 10 moves to Thieves' Hall. Zone tag: `millhaven`, district tag: `millhaven_sewers`. Millhaven Abandoned Mine district (`millhaven_mine.py`): 17 rooms. Surface (3): Abandoned Miners' Camp (hub, arrival from deep woods), Windroot Hollow (RoomHarvesting — windroot resource_id=15, gather), Mine Entrance. Upper Mine / Copper Level (5, terrain UNDERGROUND): Entry Shaft, Copper Drift (RoomHarvesting — copper ore resource_id=23, mine), Copper Seam (RoomHarvesting — copper ore), Timbered Corridor, Ore Cart Track. Kobold Territory (3): Kobold Lookout, Flooded Gallery (dead end), Descent Shaft (down). Lower Mine / Tin Level (4): Lower Junction, Tin Seam (RoomHarvesting — tin ore resource_id=25, mine), Tin Vein (RoomHarvesting — tin ore), Kobold Warren. Deep Mine / Mystery (2): Ancient Passage (pre-human stonework matching sewer ruins), Sealed Door (future content hook). All harvest rooms resource_count=0 — spawn script sets amounts. Connection point: miners_camp (west, procedural passage from deep_woods_clearing — wired in build_game_world.py). Zone tag: `millhaven`, district tag: `millhaven_mine`. All game world harvest rooms (wheat, cotton, wood, ores, windroot, arcane dust) use resource_count=0 — the resource spawn script dynamically sets actual amounts based on economy and demand. Faerie Hollow district (`millhaven_faerie_hollow.py`): 5 rooms. Deep Woods Clearing (static midpoint between procedural deep woods passages, named "Deep Woods" to blend in, tagged `millhaven_deep_woods`), Shimmering Threshold (transition room), Faerie Hollow (main chamber, faerie NPCs future), Moonlit Glade (offering altar, quest interaction point), Crystalline Grotto (RoomHarvesting — arcane dust resource_id=16, gather). Entrance from clearing is an ExitDoor with `is_invisible=True` (requires DETECT_INVIS condition to see), always open, direction north, key "a shimmer in the air". Return exit is visible. Zone tag: `millhaven`, district tags: `millhaven_deep_woods` (clearing) and `millhaven_faerie_hollow` (hollow rooms). Millhaven Southern District (`millhaven_southern.py`): ~30 rooms. Two entrances: town's south_road→Rat Run and farms' south_fork_end→Countryside Road (both wired in build_game_world.py). Rougher Town (6, URBAN): Rat Run, Low Market crossroads, Fence's Stall, Gaol, The Broken Crown tavern, South Gate. Countryside (4, RURAL): Countryside Road, Farmstead Fork, Bandit Holdfast, Bandit Camp. Moonpetal Fields (7, PLAINS): Moonpetal Approach + 2x3 RoomHarvesting grid (moonpetal resource_id=12, gather) — primary moonpetal supply for all potions. Gnoll Territory (5, PLAINS): Wild Grasslands, Gnoll Hunting Grounds (hub), Ravaged Farmstead, Gnoll Camp, Gnoll Lookout. Barrow Underground (5): Barrow Hill (PLAINS, hidden door find_dc=18), Barrow Entrance, Bone-Strewn Passage, Ancient Catacombs (Ancient Builders glyphs), Necromancer's Study (all UNDERGROUND). Borderlands (2, PLAINS): Southern Approach, Borderlands Gate (zone exit placeholder, SKILLED cartography). Zone tag: `millhaven`, district tag: `millhaven_southern`.
- Day/Night cycle and lighting system:
  - DayNightService (`typeclasses/scripts/day_night_service.py`): global persistent script, ticks every 30s, detects phase transitions (DAWN/DAY/DUSK/NIGHT), broadcasts to all connected players. `get_time_of_day()` module-level function for any code to query current phase. TIME_FACTOR=24 (1 real hour = 1 game day).
  - TimeOfDay enum (`enums/time_of_day.py`): DAWN (5-7), DAY (8-17), DUSK (18-20), NIGHT (21-4). `is_light` property, `from_hour()` class method.
  - Room darkness: `natural_light` AttributeProperty on RoomBase (None = derive from terrain). `has_natural_light` property: UNDERGROUND/DUNGEON = False, all others = True, explicit override supported. `always_lit` AttributeProperty (False, autocreate=False) — permanently lit rooms skip all darkness checks (no LitFixture needed). `is_dark(looker)` checks `always_lit` first, then natural light + phase, room light sources, carried light sources, DARKVISION condition. Dark rooms: "Unknown" name, pitch black desc, no exits/characters/things shown.
  - Room details: `details` AttributeProperty on RoomBase (default empty dict). Maps keyword strings to description text. `look <keyword>` checks room details as fallback after object search fails — real objects always take priority. Not visible in room contents listing. Not visible in darkness (existing darkness gate in CmdLook fires first). Zone builder scripts set `details` dict on rooms. Multiple keywords can share the same description text. 7 tests.
  - LightSourceMixin (`typeclasses/mixins/light_source.py`): reusable mixin for any light-emitting object. `is_lit`, `fuel_remaining`, `max_fuel`, `fuel_infinite` attributes. `light()`, `extinguish()`, `refuel()` methods. Manages LightBurnScript lifecycle.
  - LightBurnScript (`typeclasses/scripts/light_burn.py`): per-item fuel burn timer (30s ticks). Low-fuel warnings at 25% and 10%. Consumable lights (torches) destroyed at zero, reusable lights (lanterns) extinguished.
  - TorchNFTItem (`typeclasses/items/holdables/torch_nft_item.py`): consumable holdable NFT light source (600s default fuel). Destroyed when fuel runs out. Display name shows lit/fuel status.
  - LanternNFTItem (`typeclasses/items/holdables/lantern_nft_item.py`): reusable holdable NFT light source (1800s default fuel). Kept when fuel runs out, needs refueling.
  - LitFixture (`typeclasses/world_objects/lit_fixture.py`): permanent world light source (lamppost, sconce). Always lit, infinite fuel.
  - Commands: `light`/`ignite` (light a held/carried light source, auto-holds if possible), `extinguish`/`douse`/`snuff` (put out a lit source), `refuel`/`refill` (consume 1 wheat [oil placeholder, resource ID 1] to refuel a lantern to full).
  - Crafting: Wooden Torch (BASIC carpentry, 1 Timber, WOODSHOP), Bronze Lantern (BASIC blacksmithing, 1 Bronze Ingot, SMITHY). Both registered as NFTItemTypes with prototypes and recipe scrolls.
  - 66 tests across typeclass and command test suites.
- Weather & Seasons system (Phase 1 — foundation):
  - Season enum (`enums/season.py`): SPRING (days 0-89), SUMMER (90-179), AUTUMN (180-269), WINTER (270-359). `from_day()` class method. 360-day game year, 90 days per season (1 season ≈ 3.75 real days at TIME_FACTOR=24).
  - SeasonService (`typeclasses/scripts/season_service.py`): global persistent script, ticks every 300s (5 min), detects season transitions, broadcasts to all connected players. `get_season()` and `get_day_of_year()` free functions callable from anywhere.
  - Weather enum (`enums/weather.py`): CLEAR, CLOUDY, RAIN, STORM, SNOW, FOG, BLIZZARD, HEAT_WAVE.
  - ClimateZone enum (`enums/climate_zone.py`): TEMPERATE, ARCTIC, DESERT, TROPICAL, COASTAL.
  - WeatherService (`typeclasses/scripts/weather_service.py`): global persistent script, ticks every 180s (3 min). Per-zone weather state machine with probabilistic transitions based on (ClimateZone, Season, current_weather). State persisted in `db.zone_weather` dict. Only rolls for zones with connected players. `get_weather(zone_name)` free function callable from anywhere — returns Weather.CLEAR for unknown zones.
  - Weather transition tables (`utils/weather_tables.py`): 5 climates × 4 seasons = 20 probability tables. `ZONE_CLIMATES` dict maps zone names to ClimateZone (default TEMPERATE). `roll_next_weather()` and `get_climate_for_zone()` functions.
  - Weather descriptions (`utils/weather_descs.py`): exposed room desc lines, sheltered (muffled indoor) desc lines, broadcast transition messages, sheltered broadcast variants.
  - Three-tier weather exposure on RoomBase: `sheltered` AttributeProperty (None = derive from terrain). `is_subterranean` (UNDERGROUND/DUNGEON — no weather at all), `is_sheltered` (URBAN or explicit override — muffled sounds, no effects), `is_weather_exposed` (everything else — full weather). Weather line appended to room desc via `_get_weather_desc_line()` in `get_display_desc()`.
  - 43 tests across script and typeclass test suites.
- DurabilityDecayService (`typeclasses/scripts/durability_decay_service.py`): global persistent script, ticks every 3600s (1 game day). Loops all IC (online/puppeted) characters, calls `reduce_durability(1)` on each equipped item via `get_all_worn()`. No offline catch-up — items only decay while you're playing. Uses `delay()` to stagger per-character processing. `get_game_day_number()` free function for absolute day tracking. Material durability tiers in game days: Cloth=720, Silk/Leather/Wood=1440, Hardwood/Wyvern leather=2880, Bronze/Copper/Silver=3600, Iron=5400, Steel=7200, Mithral/Adamantine=9000. Combat wear (1 per hit/parry) stacks on top. 11 tests.
- ResourceSpawnScript (`typeclasses/scripts/resource_spawn_service.py`): global persistent script, ticks every 3600s (1 hour). Delegates to `ResourceSpawnService.calculate_and_apply()` which reads economy snapshots and replenishes `RoomHarvesting` nodes. Three-factor algorithm: consumption baseline × AMM price modifier × supply-per-player-hour modifier. Single DB query for all rooms, grouped by resource_id. Weighted allocation by per-room `spawn_rate_weight` (1-5), drip-fed across the hour via `delay()` (max 12 ticks, min 5 min apart). Config in `world/economy/resource_spawn_config.py`. 47 tests.
- ZoneSpawnScript (`typeclasses/scripts/zone_spawn_script.py`): persistent per-zone script maintaining mob populations. Reads JSON spawn rules from `world/spawns/<zone>.json`. Ticks every 15s, counts living mobs per rule (`typeclass + area_tag`), spawns replacements when below target respecting per-rule `respawn_seconds` cooldown and `max_per_room`. Mobs tagged with `category="spawn_zone"` for tracking. Factory: `ZoneSpawnScript.create_for_zone("zone_key")`. Supports JSON hot-reload. Static zones only — procedural dungeons manage their own mobs. 22 tests.
- Server lifecycle (`server/conf/at_server_startstop.py`): `at_server_init()` registers dungeon templates (cave_dungeon, deep_woods_passage, rat_cellar). `at_server_start()` runs on every boot: ensures global scripts (RegenerationService, HungerService, DayNightService, SeasonService, WeatherService, DurabilityDecayService, ResourceSpawnScript) exist via `_ensure_global_scripts()` (creates missing, skips existing — no duplicates), clears spawned items (3-sweep: NFT objects → orphaned DB rows → local fungible state), collapses stale dungeon instances, restarts corpse/purgatory/mob timers. Global scripts are independent of world building — adding a new service means appending to the `_GLOBAL_SCRIPTS` list.
- Tutorial zone system: per-player instanced tutorial with LLM-powered guide NPC. Infrastructure: `TutorialInstanceScript` (lifecycle manager — create rooms, spawn guide NPC, strip items on exit, return resources, per-chunk graduation rewards once per account), `TutorialCompletionExit` (triggers instance collapse on traversal), `TutorialGuideNPC` (LLM-powered guide "Pip" that follows the player and speaks about each room using `guide_context`), tutorial hub (static room, idempotent builder, 3 `ExitTutorialStart` exits + 1 `ExitTutorialReturn` exit). Entry flow: new characters spawn in Harvest Moon Inn (bartender NPC "Rowan" greets via `llm_hook_arrive`), first-puppet simplified offer in `at_post_puppet()`, `enter tutorial` / `skip tutorial` / `leave tutorial` / `start tutorial 1|2|3` commands on character cmdset. Each room has `guide_context` (LLM prompt for the guide) and `tutorial_text` (static fallback if LLM unavailable). `llm_hook_arrive` wired in `FCMCharacter.at_post_move()` — iterates room contents calling `at_llm_player_arrive()` on LLM NPCs. Tutorial 1 (Survival Basics): 9 rooms (Welcome Hall → Observation Chamber → Supply Room → The Armoury → Open Courtyard → The Dim Passage → Training Arena → The Pantry → Tutorial Complete). Key items: Ring of Flight, Ring of Water Breathing, training longsword, leather cap, torch, training dummy mob, bread, gold. Graduation reward: 2 bread, 50 gold, wooden training dagger. Tutorial 2 (Economic Loop): 6 rooms (The Harvest Field [RoomHarvesting, wheat] → The Woodlot [RoomHarvesting, wood] → The Windmill [RoomProcessing, wheat→flour] → The Bakery [RoomProcessing, flour+wood→bread] → The Vault [RoomBank] → Tutorial Complete). First-run: 20 gold. Graduation reward: 100 gold, 10 wheat, 5 wood. Tutorial 3 (Growth & Social): 7 rooms (Hall of Records → The Speaking Chamber → Hall of Skills → The Training Grounds [TrainerNPC, blacksmith/carpenter/alchemist] → The Guild Hall [GuildmasterNPC, warrior] → The Companion Room [companion NPC] → Tutorial Complete). First-run: 1 general skill point + 50 gold. Graduation reward: 100 gold, 1 skill point. Fixtures: mirror, message board, skill tome. All tutorial items flagged `db.tutorial_item = True` and stripped on exit. Tutorial rooms use tags (`tutorial_room`, `tutorial_exit`, `tutorial_item`, `tutorial_mob`) for cleanup. Anti-exploitation: per-account flags gate first-run rewards and graduation rewards. LLM prompt templates: `llm/prompts/tutorial_guide.md`, `llm/prompts/bartender.md`. Bartender spawn: `world/game_world/spawn_millhaven_npcs.py`. 96 tests.
- Player trade system: `trade <player>` initiates safe atomic item+gold swap between two players in the same room. TradeHandler state machine on `ndb.tradehandler`, temporary CmdSetTrade with offer/accept/decline/status/end commands. Gold support in offers (`offer sword and 500 gold`). Items move via `move_to()` (triggers NFT hooks), gold via `transfer_gold_to()`. 60-second timeout on invitation. Combat gate, weight checks, worn item exclusion. 25 tests.
- Mail system (Post Office): character-to-character async messaging available at RoomPostOffice rooms. Uses Evennia's `Msg` class with `category="mail"` tags. Commands: `mail` (inbox), `mail <#>` (read), `mail <char>=<subject>/<body>` (send), `mail reply <#>=<msg>`, `mail delete <#>`. Unread notification on login via `at_post_puppet()`. 15 tests.
- Trading Post (bulletin board): placeable TradingPost object with CmdSet. All boards read from same `BulletinListing` model (global data — post in one town, visible everywhere). Commands: `browse`/`listings` (paginated, 20/page), `post <WTS/WTB> <message>` (10 gold fee, gold sink), `remove <#>` (own listings only). Listings expire after 7 days, 200 char message limit. 15 tests.
- Markets web page (`/markets/`): live AMM price dashboard rendering hourly ResourceSnapshot data. Tabbed layout (Resources + NFTs placeholder). Shows buy/sell price, spread, circulation, and 1h volume for all resources. MarketsView queries latest snapshot batch from ResourceSnapshot + CurrencyType models.
- Consider command (`commands/all_char_cmds/cmd_consider.py`): CircleMUD-style `consider <target>` — graduated difficulty messages based on level difference between caller and target. 10 difficulty tiers from "Do you feel lucky, punk?" (much weaker) to "You ARE mad!" (much stronger). Guards: target must be in room, must have `get_level()`. 9 tests.
- Social commands system (`commands/all_char_cmds/cmd_social.py`, `socials_data.py`, `cmdset_socials.py`): 50 CircleMUD-style data-driven social commands (applaud, blush, bounce, bow, cackle, cheer, chuckle, clap, comfort, cringe, cry, curtsey, dance, drool, facepalm, flex, frown, gasp, giggle, glare, grin, groan, grovel, growl, high5, hug, kiss, laugh, lick, nod, nudge, pat, peer, point, poke, ponder, pout, salute, shake, shrug, sigh, slap, smile, smirk, snicker, thank, wave, wink, yawn). Dynamic class generation via `_make_social_cmd()` factory — each social is a real Command subclass with its own key/aliases/help. Message variants: no-target (self + room), targeted (self + victim + room), self-target (self + room). Room messages use `$You()/$conj()` via `msg_contents(from_obj=caller)` for automatic perspective + HIDDEN/INVISIBLE filtering. Guards: sleeping blocked, hidden blocked. `CmdSetSocials` loaded as sub-CmdSet in `CmdSetCharacterCustom`. `socials` command lists all available socials with count. 14 tests.
- Scan command (`commands/all_char_cmds/cmd_scan.py`): CircleMUD-style `scan` — looks up to 3 rooms in each cardinal/vertical direction, reports characters spotted with distance labels (nearby/not far off/far off). Respects visibility: HIDDEN/INVISIBLE filtering, dark rooms block scanning, closed doors block scanning. Sorted by canonical direction order. 11 tests.
- Semicolon command stacking (`server/conf/inputfuncs.py`): overrides Evennia's `text()` input function to split on `;` and process each command sequentially. `get sword;wield sword` executes as two separate commands.
- Diagnose command (`commands/all_char_cmds/cmd_diagnose.py`): CircleMUD-style `diagnose [target]` — HP percentage mapped to 7 descriptive tiers from "excellent condition" to "awful condition". Shows HP numbers. No args = self. 7 tests.
- Enhanced `who` command (`commands/account_cmds/cmdset_account_custom.py`): MUD-style player listing showing character name, level, class, race, and idle time instead of Evennia's bare-bones account names. Admin view adds Location column. OOC players shown with "(OOC)" tag. 5 tests.
- Tests across blockchain, command, typeclass, server, and utility test suites

## CRITICAL: Ability Score Modifier Pattern — Compute at Check Time, NEVER Cache

**This is a universal pattern with NO EXCEPTIONS.**

Cached stats (`armor_class`, `initiative_bonus`, `total_hit_bonus`, `total_damage_bonus`, `max_carrying_capacity_kg`, etc.) store ONLY bonuses from equipment and spell/potion effects. These are rebuilt from scratch by `_recalculate_stats()` (nuclear recalculate) whenever equipment or buffs change — never incrementally adjusted for numeric stats.

Ability score modifiers (`get_attribute_bonus(score)` = `floor((score-10)/2)`) and skill mastery bonuses are **NEVER** baked into cached stats. They are **ALWAYS** computed at the point of use — when the combat roll, capacity check, or skill check actually happens.

```python
# Implemented effective properties on BaseActor:
effective_ac                = armor_class + get_attribute_bonus(dexterity)           # @property
effective_initiative        = initiative_bonus + get_attribute_bonus(dexterity)     # @property
effective_hp_max            = hp_max + (get_attribute_bonus(constitution) * total_level)  # @property
effective_stealth_bonus     = stealth_bonus + get_attribute_bonus(dexterity) + STEALTH mastery bonus  # @property
effective_perception_bonus  = perception_bonus + get_attribute_bonus(wisdom) + ALERTNESS mastery bonus  # @property
effective_hit_bonus         = total_hit_bonus + hit_bonuses[weapon_type] + get_attribute_bonus(str/dex) + weapon mastery  # @property
effective_damage_bonus      = total_damage_bonus + damage_bonuses[weapon_type] + get_attribute_bonus(str/dex) + weapon mastery  # @property
effective_attacks_per_round = attacks_per_round + weapon.get_extra_attacks()      # @property
get_max_capacity()          = max_carrying_capacity_kg + get_attribute_bonus(strength) * 5  # override

# Not yet implemented (deferred — different caster classes use different stats):
# effective_mana_max — INT for mages, WIS for clerics/druids, CHA for sorcerers/bards
# effective_move_max — needs design
```

**Three-layer architecture for stat bonuses:**
1. **Tier 1 — Base** (`base_strength`, `base_armor_class`, etc.) — permanent source of truth. Set once at creation (point buy + racial bonuses). Never touched by recalculate.
2. **Tier 2 — Current** (`strength`, `armor_class`, `total_hit_bonus`, `stealth_bonus`, etc.) — rebuilt from scratch by `_recalculate_stats()`. Equals base + racial effects + equipment + active spell/potion buffs. No manual increment/decrement.
3. **Tier 3 — Effective** (`effective_ac`, `effective_stealth_bonus`, etc.) — @property that adds ability modifier + mastery to Tier 2. Single number the decision layer uses.

**Nuclear recalculate pattern:** Instead of tracking individual +/- when gear or buffs change, `_recalculate_stats()` resets all Tier 2 stats to base/zero, then re-accumulates every effect source (racial effects, worn equipment, active named effects). Triggers on: equip/unequip, buff apply/expire, potion effect start/end. Eliminates stat drift from missed or double-applied effects. Conditions (DARKVISION, STUNNED, etc.) remain incremental with ref-counting — only numeric stats are recalculated.

**Why Tier 3 exists:** Ability modifiers depend on context — finesse weapons use dex instead of str, monks may use wis, different weapons grant different mastery bonuses. Caching them would require cascading recalculation on every ability score change. Computing at check time is simpler, correct, and context-aware.

**Where documented in code:** `BaseActor._recalculate_stats()`, `BaseActor._accumulate_effect()`, `CarryingCapacityMixin` (capacity attribute comment).

## CRITICAL: Non-Combat Advantage/Disadvantage — Mandatory Roll Pattern

**This is a universal pattern. All non-combat d20 skill checks MUST follow it.**

### Two Systems — Combat vs Non-Combat

**In combat:** Advantage/disadvantage is tracked per-target on the `CombatHandler` script (`advantage_against = {target_id: int}` rounds remaining). Managed by `set_advantage()`, `has_advantage()`, `consume_advantage()`, `decrement_advantages()`. This system is consumed by `execute_attack()` in `combat/combat_utils.py`. Combat advantage has no interaction with the non-combat system below.

**Out of combat:** Two boolean flags live directly on the actor:
- `db.non_combat_advantage` — set by `assist` command, buffs, environmental effects, etc.
- `db.non_combat_disadvantage` — set by traps, curses, environmental hazards, debuffs, etc.

### Resolution Rules (5e Model)

| Advantage | Disadvantage | Result |
|---|---|---|
| False | False | Normal roll (1d20) |
| True | False | Roll with advantage (best of 2d20) |
| False | True | Roll with disadvantage (worst of 2d20) |
| True | True | **Cancel out** → normal roll (1d20) |

Both flags are **consumed after the roll** — reset to `False` regardless of success/failure.

### Mandatory Implementation Pattern

**Every non-combat d20 skill check** (picklock, hide, search, pickpocket, stash, perception, etc.) MUST use the dice roller's `roll_with_advantage_or_disadvantage()` method. Raw `random.randint(1, 20)` or `dice.roll("1d20")` are **NOT permitted** for skill checks.

```python
from utils.dice_roller import dice

# Read and consume non-combat advantage/disadvantage from the actor
has_adv = getattr(character.db, "non_combat_advantage", False)
has_dis = getattr(character.db, "non_combat_disadvantage", False)
roll = dice.roll_with_advantage_or_disadvantage(advantage=has_adv, disadvantage=has_dis)
character.db.non_combat_advantage = False
character.db.non_combat_disadvantage = False
```

The dice roller already handles cancellation internally (`utils/dice_roller.py` — `roll_with_advantage_or_disadvantage()`).

**What sets these flags:**
- `non_combat_advantage`: `assist` command (BATTLESKILLS), future buffs/spells
- `non_combat_disadvantage`: traps, curses, environmental hazards, future debuffs

**What does NOT use this system:** Combat rolls (attack resolution, flee checks, saving throws in combat) — these use the combat handler's per-target advantage/disadvantage tracking instead.

## Point Buy and Remort Model

### Ability Score Point Buy

All six ability scores (`strength`, `dexterity`, `constitution`, `intelligence`, `wisdom`, `charisma`) start at **8**. Players spend points from a budget to raise them during character creation. Standard 5e cost table:

| Score | 8 | 9 | 10 | 11 | 12 | 13 | 14 | 15 |
|-------|---|---|----|----|----|----|----|----|
| Cost  | 0 | 1 | 2  | 3  | 4  | 5  | 7  | 9  |

- Default budget: **27 points** (`FCMCharacter.point_buy = AttributeProperty(27)`)
- Range: 8–15 before racial bonuses. Racial bonuses (from `RaceBase.ability_score_bonuses`) applied after point buy and can push scores above 15 or below 8.
- `point_buy` persists on the character — it is NOT consumed during creation. It records the character's point budget, which can grow over time via remort perks.

### Remort System

When a character reaches max level, they can **remort** — reset to level 1 while keeping accumulated advantages. `num_remorts` (AttributeProperty on FCMCharacter) tracks how many times a character has remorted.

**On remort, the player chooses from a set of perks:**
- Additional point buy points (increases `point_buy` for future stat rebuilds)
- Bonus base HP, Mana, or Move
- Other advantages TBD

**Remort gates access to content:**
- Some races, classes, equipment, and items have `min_remorts` requirements
- ItemRestrictionMixin already supports `min_remorts` checks: `character.num_remorts >= value`
- CharClassBase already has `min_remorts` field for class eligibility
- Example: a legendary weapon might require `min_remorts: 5`

This creates a long-term progression loop — characters grow more powerful across remort cycles, unlocking content that first-life characters cannot access.

## Data-Driven Item Effects System

Items declare effects in their prototype's `wear_effects` list. On wear/remove, conditions are applied/removed incrementally (ref-counted), then `_recalculate_stats()` rebuilds all numeric stats from scratch.

**Supported effect types:**

| Type | Format | Example |
|---|---|---|
| `stat_bonus` | `{"type": "stat_bonus", "stat": "<name>", "value": <int>}` | `{"type": "stat_bonus", "stat": "armor_class", "value": 1}` |
| `damage_resistance` | `{"type": "damage_resistance", "damage_type": "<type>", "value": <int>}` | `{"type": "damage_resistance", "damage_type": "piercing", "value": 50}` |
| `condition` | `{"type": "condition", "condition": "<name>"}` | `{"type": "condition", "condition": "darkvision"}` |
| `condition` (compound) | `{"type": "condition", "condition": "<name>", "effects": [...]}` | `{"type": "condition", "condition": "hasted", "effects": [{"type": "stat_bonus", "stat": "attacks_per_round", "value": 1}]}` |
| `hit_bonus` | `{"type": "hit_bonus", "weapon_type": "<WeaponType.value>", "value": <int>}` | `{"type": "hit_bonus", "weapon_type": "unarmed", "value": 1}` |
| `damage_bonus` | `{"type": "damage_bonus", "weapon_type": "<WeaponType.value>", "value": <int>}` | `{"type": "damage_bonus", "weapon_type": "unarmed", "value": 1}` |

**Weapon-type-specific bonuses (`hit_bonus`/`damage_bonus`):** Stored in `hit_bonuses` and `damage_bonuses` dicts on FCMCharacter, keyed by `WeaponType.value` string (e.g. `"unarmed"`, `"long_sword"`, `"dagger"`). Multiple sources stack additively. Rebuilt from scratch during `_recalculate_stats()`. At combat time, look up `character.hit_bonuses.get(weapon_type_value, 0)`.

**Supported stats for `stat_bonus`:** Any AttributeProperty on FCMCharacter — `strength`, `dexterity`, `constitution`, `intelligence`, `wisdom`, `charisma`, `armor_class`, `crit_threshold`, `initiative_bonus`, `attacks_per_round`, `stealth_bonus`, `move_max`, etc. **Important:** Tier 2 stats store equipment/spell bonuses only — ability score modifiers are computed at check time via Tier 3 @properties (see "Ability Score Modifier Pattern" section above).

**Damage types for `damage_resistance`:** `slashing`, `piercing`, `bludgeoning`, `fire`, `cold`, `lightning`, `acid`, `poison`, `magic`, `force` (see `enums/damage_type.py`). Values are integer percentages — `50` means 50% resistance. Capped to [-75, 75] on read via `get_resistance()`.

**Flow:** `wear()` → `item.at_wear(wearer)` → loops condition-type effects only via `apply_effect()` (ref-counted) → calls `wearer._recalculate_stats()` (rebuilds all numeric stats from equipment + buffs + racial effects). `remove()` reverses conditions then recalculates. Named effects (spells/potions) follow the same pattern: `apply_named_effect()` / `remove_named_effect()` handle conditions incrementally, then call `_recalculate_stats()`.

**Stacking rules:** Standalone `stat_bonus` effects stack additively (two +1 STR rings = +2 STR — both counted during recalculate). Compound `condition` effects with nested `"effects"` only apply companion bonuses once per condition during recalculate — wearing a second haste item increments the condition ref count but the companion stat bonus is only accumulated once (tracked via `_accumulated_companions` set during recalculate).

**Prototypes only apply at spawn time** — editing a prototype affects new spawns only. Existing items keep their original values. This is intentional for an NFT game (legacy items).

## DamageResistanceMixin (typeclasses/mixins/damage_resistance.py)

Provides damage resistance/vulnerability tracking for any typeclass — characters, NPCs, mobs, pets, mounts, destructible objects.

- `damage_resistances` — AttributeProperty dict of raw integer percentages (e.g. `{"piercing": 50, "fire": -25}`)
- `get_resistance(damage_type)` — returns effective value clamped to [-75, 75]. Returns 0 for missing types.
- `apply_resistance_effect(effect)` / `remove_resistance_effect(effect)` — add/subtract from raw dict
- Raw values stored unclamped to prevent drift (see module docstring for detailed explanation)

Mixed into BaseActor: `class BaseActor(EffectsManagerMixin, DamageResistanceMixin, DefaultCharacter)` — EffectsManagerMixin replaces the old ConditionsMixin and absorbs `apply_effect`/`remove_effect`.

## Damage Pipeline — `BaseActor.take_damage()` (typeclasses/actors/base_actor.py)

Central damage application method. **ALL damage sources must call `take_damage()` instead of modifying `.hp` directly.** This ensures consistent resistance/vulnerability handling and death logic.

**Signature:** `take_damage(self, raw_damage, damage_type=None, cause="combat", ignore_resistance=False) → int`

**Resistance/Vulnerability Rules:**
- Positive resistance: `reduction = max(1, floor(damage * resistance / 100))` — even 1% always saves at least 1 HP
- Negative resistance (vulnerability): `extra = max(1, floor(damage * abs(resistance) / 100))` — even -1% always adds at least 1 HP
- Final damage: `max(1, damage)` — minimum 1 HP always dealt
- If min-1-damage and min-1-resistance collide, min damage wins

**Parameters:**
- `damage_type` — string (e.g. `"fire"`, `"piercing"`) for `get_resistance()` lookup. `None` skips resistance.
- `cause` — passed to `die()` on death (`"combat"`, `"spell"`, `"fall"`, `"drowning"`)
- `ignore_resistance` — `True` for environmental damage (fall, drowning) that bypasses all resistances

**Callers:**
- `execute_attack()` in `combat/combat_utils.py` — weapon combat damage
- `apply_spell_damage()` in `world/spells/spell_utils.py` — thin wrapper (converts `DamageType` enum to string)
- `_check_fall()` in `base_actor.py` — fall damage (`ignore_resistance=True`)
- `BreathTimerScript` in `typeclasses/scripts/breath_timer.py` — drowning (`ignore_resistance=True`)

## ItemRestrictionMixin (typeclasses/mixins/item_restriction.py)

Data-driven item usage restrictions mixed into `BaseNFTItem`. Default is unrestricted — items only become restricted when a prototype sets restriction fields.

**Restriction fields (all `AttributeProperty` with empty/zero defaults):**

| Field | Logic | Description |
|---|---|---|
| `required_classes` | OR | Character has ANY listed class → pass |
| `excluded_classes` | AND-NOT | Character has ANY listed class → fail (vetoes) |
| `min_class_levels` | ALL | Each `{class: level}` must be met |
| `required_races` | OR | Character's race in list → pass |
| `excluded_races` | AND-NOT | Character's race in list → fail |
| `required_alignments` | OR | Character's alignment in list → pass |
| `excluded_alignments` | AND-NOT | Character's alignment in list → fail |
| `min_total_level` | ≥ | `character.total_level >= value` |
| `min_remorts` | ≥ | `character.num_remorts >= value` |
| `min_attributes` | ALL | Each `{ability: score}` must be met |
| `min_mastery` | ALL | Each `{skill: level}` must be met |

- `can_use(character)` → `(bool, str)` — checks all restrictions, short-circuits on first failure
- `is_restricted` property — `True` if any field is non-default
- Hooked into `wear()` validation chain in `BaseWearslotsMixin` — `can_use()` runs before `can_wear()`

## EffectsManagerMixin (typeclasses/mixins/effects_manager.py)

Unified effect system that replaces ConditionsMixin. Provides three composable layers:

### Layer 1 — Condition Flags (ref-counted)

Reference-counted condition flags. Multiple sources of the same condition don't collide — DARKVISION from a racial innate (count=1) plus a spell (count=2) won't be lost when the spell expires (count back to 1).

- `_add_condition_raw(condition)` → silent internal use, returns `True` if newly gained
- `_remove_condition_raw(condition)` → silent internal use, returns `True` if fully removed
- `add_condition(condition)` → public API, returns `True` if newly gained. BaseActor overrides for messaging + side effects
- `remove_condition(condition)` → public API, returns `True` if fully removed. BaseActor overrides for messaging + side effects
- `has_condition(condition)` → `bool` (count > 0)
- `get_condition_count(condition)` → raw ref count
- Item-granted conditions: `{"type": "condition", "condition": "darkvision"}` in `wear_effects`
- Condition enum: `enums/condition.py` — 11 actively-used condition flags with start/end messages. Cross-references `enums/named_effect.py`.

### Layer 2 — Stat Effect Dispatch (backward compatible, mostly superseded)

- `apply_effect(effect_dict)` → applies a single effect incrementally (stat_bonus, damage_resistance, condition, hit_bonus, damage_bonus)
- `remove_effect(effect_dict)` → symmetric reversal
- **Mostly superseded by nuclear recalculate:** Equipment `at_wear()`/`at_remove()` and named effects now only use `apply_effect()`/`remove_effect()` for condition-type effects (ref-counting). All numeric stat effects are handled by `_recalculate_stats()` instead.
- Still used directly for: condition application in at_wear/at_remove loops, backward compatibility in tests

### Layer 3 — Named Effects

Tracked, timed, anti-stacking effects that compose from the three building blocks (condition flag + stat effects + lifecycle). One call sets everything up; removal reverses everything cleanly.

#### Effect Registry (Single Source of Truth)

Each `NamedEffect` enum member carries its associated condition and duration type via properties on the enum:

- `NamedEffect.INVISIBLE.effect_condition` → `Condition.INVISIBLE`
- `NamedEffect.SHIELD.effect_duration_type` → `"combat_rounds"`

Registry dicts (`_EFFECT_CONDITIONS`, `_EFFECT_DURATION_TYPES`) in `enums/named_effect.py` define these mappings. When `apply_named_effect()` is called, condition and duration_type auto-fill from the registry unless explicitly overridden.

**Sentinel semantics** (`_UNSET` sentinel in `effects_manager.py`):
- `condition=_UNSET` (default) → auto-fill from registry
- `condition=None` (explicit) → override registry, no condition
- `condition=Condition.X` (explicit) → override registry with this condition

#### Convenience Methods (Preferred API)

**ALWAYS use convenience methods when one exists for the effect.** Each method is the single entry point for its effect — any source (spell, weapon, potion, scroll, trap) that applies the effect calls the same method. This guarantees consistency.

| Category | Method | Parameters |
|---|---|---|
| **Combat conditions** | `apply_stunned()` | `duration_rounds, source=None` |
| | `apply_prone()` | `duration_rounds, source=None` |
| | `apply_slowed()` | `duration_rounds, source=None` |
| | `apply_paralysed()` | `duration_rounds, source=None, save_dc=None, save_stat="wisdom", save_messages=None, messages=None` |
| | `apply_entangled()` | `duration_rounds, source=None, save_dc=None, save_stat="strength", save_messages=None, messages=None` |
| | `apply_blurred()` | `duration_rounds` |
| **Combat stat effects** | `apply_shield_buff()` | `ac_bonus, duration_rounds, mana_cost=0` |
| | `apply_staggered()` | `hit_penalty, duration_rounds, source=None` |
| | `apply_sundered()` | `ac_penalty, duration_rounds, source=None` |
| **Seconds-based buffs** | `apply_invisible()` | `duration_seconds` |
| | `apply_sanctuary()` | `duration_seconds` |
| | `apply_mage_armor()` | `ac_bonus, duration_seconds` |
| | `apply_shadowcloaked()` | `stealth_bonus, duration_seconds, source=None` |
| | `apply_true_sight()` | `duration_seconds, detect_invis=False` |
| | `apply_holy_sight()` | `duration_seconds, detect_invis=False` |
| | `apply_resist_element()` | `element, resistance_pct, duration_seconds, source=None` |
| **Script-managed** | `apply_poisoned()` | `ticks` |
| | `apply_acid_arrow_dot()` | `dot_rounds` |
| | `apply_vampiric()` | `source=None` |
| **Stances** | `apply_offensive_stance()` | `effects, source=None` |
| | `apply_defensive_stance()` | `effects, source=None` |

#### break_effect() — Force Removal Without Messages

`break_effect(named_effect)` removes an effect immediately: zeros condition refs, calls `_recalculate_stats()` to rebuild numeric stats, stops timers. Does NOT send end messages — the caller handles context-specific messaging (e.g. "You attack and your invisibility shatters!").

```python
target.break_effect(NamedEffect.INVISIBLE)  # or break_invisibility() alias
target.break_effect(NamedEffect.SANCTUARY)  # or break_sanctuary() alias
```

#### Low-Level API

- `apply_named_effect(key, source=None, effects, condition, duration, duration_type, messages, save_dc, save_stat, save_messages)` → accepts `NamedEffect` enum or string key. Auto-fills condition and duration_type from registry via `_UNSET` sentinel. Applies conditions incrementally, then calls `_recalculate_stats()` for numeric stat effects. Returns `True` if applied, `False` if already active (anti-stacking).
- `remove_named_effect(key)` → clears condition flag, calls `_recalculate_stats()` to rebuild numeric stats without removed effect, sends end messages, cleans up timers. Returns `True` if removed.

**Use `apply_named_effect()` directly only when:** no convenience method exists (e.g. data-driven potions where effect key, stat bonuses, and condition come from item data baked at craft time).

**Anti-stacking rule of thumb:** Effects with stat bonuses (AC, damage, etc.) MUST anti-stack — double Shield = double AC is broken. Effects that only set a boolean condition flag (INVISIBLE, DETECT_INVIS) with no stat impact do NOT need anti-stacking — conditions are ref-counted, so multiple sources just increment the count. `has_condition()` is a boolean gate (count > 0), so ref count 1 and ref count 50 behave identically. Multiple sources = safe redundancy. When the condition needs to be broken (e.g. attacking breaks invisibility), zero the entire ref count rather than decrementing.
- `has_effect(key)` → `bool` check if a named effect is active
- `get_named_effect(key)` → full effect record or `None`
- `tick_combat_round()` → decrements all `combat_rounds` effects by 1, auto-removes expired. Called by combat handler each tick.
- `clear_combat_effects()` → removes ALL `combat_rounds` effects. Called on combat end by `stop_combat()`.

**Named effect record** (persisted in `active_effects` AttributeProperty dict):

```python
active_effects = {
    "shield": {
        "condition": None,           # optional Condition flag
        "effects": [{"type": "stat_bonus", "stat": "armor_class", "value": 4}],
        "duration": 2,               # rounds/seconds remaining
        "duration_type": "combat_rounds",  # or "seconds" or None
        "messages": {
            "start": "A barrier forms!",
            "end": "The barrier fades.",
            "start_third": "{name} is surrounded by a barrier!",
            "end_third": "The barrier around {name} fades.",
        },
    },
}
```

**Lifecycle types:**

| `duration_type` | Mechanism | Cleanup |
|---|---|---|
| `"combat_rounds"` | Combat handler calls `actor.tick_combat_round()` each tick | `clear_combat_effects()` on combat end |
| `"seconds"` | EffectTimerScript (one-shot timer) auto-removes on expiry | Timer calls `remove_named_effect(key)` |
| `None` | Permanent until explicitly removed | Caller responsible |

### Decision Tree — When to Use What

| Scenario | Method | Example |
|---|---|---|
| Equipment bonuses | `apply_effect()` / `remove_effect()` in `wear_effects` | Sword +1 AC |
| Combat condition (stun/prone/slow/etc.) | Convenience method: `target.apply_stunned(rounds)` | Unarmed stun (1 round) |
| Timed combat buff (AC/hit/etc.) | Convenience method: `target.apply_shield_buff(ac, rounds)` | Shield (+4 AC, 2 rounds) |
| Seconds-based buff | Convenience method: `target.apply_invisible(seconds)` | Invisibility spell (300s) |
| Script-managed effect | Convenience method: `target.apply_poisoned(ticks)` | Blowgun poison DoT |
| Force-remove without messages | `target.break_effect(NamedEffect.INVISIBLE)` | Attack breaks invisibility |
| Data-driven effect (potions) | `apply_named_effect()` directly (auto-fill from registry) | STR potion (+2 STR, 300s) |
| Direct condition (legacy) | `add_condition()` / `remove_condition()` | Equipment `wear_effects` |

**MANDATORY: The EffectsManagerMixin is the ONLY approved system for applying, tracking, and removing effects on actors. Use convenience methods when one exists; fall back to `apply_named_effect()` only for data-driven effects (e.g. potions). Use `apply_effect()`/`remove_effect()` only for equipment `wear_effects`. Do NOT create ad-hoc solutions (custom scripts, manual HP/stat manipulation, direct condition flag manipulation outside of equipment wear_effects, or any other pattern that bypasses this system). If you believe a deviation is necessary, you MUST discuss it with the developer and get explicit human approval before proceeding — do not implement alternatives on your own.**

### NamedEffect Enum (enums/named_effect.py)

All named effect keys are validated against the `NamedEffect` enum — unknown keys are rejected with a `ValueError`. To add a new named effect:

1. Check the **unsorted effects list** at the bottom of `enums/named_effect.py`
2. Classify the effect: NamedEffect (lifecycle-managed), Condition (ref-counted flag), or both
3. Add a member to the appropriate enum(s) with detailed usage comments
4. Remove the entry from the unsorted list
5. Add start/end messages to the message registries
6. Add entry to `_EFFECT_CONDITIONS` if the effect has an associated Condition
7. Add entry to `_EFFECT_DURATION_TYPES` (`"combat_rounds"`, `"seconds"`, or `None`)
8. Add a convenience method on EffectsManagerMixin (e.g. `apply_my_effect()`)

**Current NamedEffect members:** STUNNED, PRONE, SLOWED, PARALYSED, ENTANGLED, POISONED, ACID_ARROW, SHIELD, MAGE_ARMORED, BLURRED, INVISIBLE, TRUE_SIGHT, SHADOWCLOAKED, SANCTUARY, VAMPIRIC, STAGGERED, SUNDERED, OFFENSIVE_STANCE, DEFENSIVE_STANCE, RESIST_FIRE, RESIST_COLD, RESIST_LIGHTNING, RESIST_ACID, RESIST_POISON, POTION_STRENGTH, POTION_DEXTERITY, POTION_CONSTITUTION, POTION_INTELLIGENCE, POTION_WISDOM, POTION_CHARISMA, POTION_TEST

**Current Condition members:** SILENCED, DEAF, HIDDEN, INVISIBLE, DETECT_INVIS, DARKVISION, FLY, WATER_BREATHING, HASTED, COMPREHEND_LANGUAGES, CRIT_IMMUNE, SANCTUARY, PARALYSED, SLOWED

SLOWED and PARALYSED appear in both — named effect for lifecycle, condition flag for gameplay checks (movement speed / Remove Paralysis spell targeting).

### Named Effect On-Apply Callbacks (enums/named_effect.py)

Side effects that must ALWAYS happen when a named effect is applied are registered as callbacks in `_ON_APPLY_CALLBACKS` at the bottom of `enums/named_effect.py`. This ensures consistency regardless of whether the effect is applied by a weapon, spell, command, or trap.

Callbacks receive `(target, source, duration)` and are called automatically by `apply_named_effect()` after the effect is recorded.

| Effect | Callback | Side Effect |
|---|---|---|
| PRONE | `_grant_advantage_to_enemies` | All enemies of target get advantage for duration rounds |
| ENTANGLED | `_grant_advantage_to_enemies` | All enemies of target get advantage for duration rounds |
| PARALYSED | `_grant_advantage_to_enemies` | All enemies of target get advantage for duration rounds |
| STUNNED | None | Action denial only — no advantage (key differentiator from prone) |
| All others | None | No mechanical side effects beyond core effect system |

To add a new callback: define the function in `named_effect.py` and add it to `_ON_APPLY_CALLBACKS`. Use lazy imports inside callbacks to avoid circular dependencies.

### Early Cancellation (Dispel Pattern)

To cancel a named effect early (e.g. dispel magic, cleanse, death):

```python
# Remove a single effect — reverses stats, clears condition, sends end messages
target.remove_named_effect("shield")

# Remove ALL combat-round effects (used by stop_combat)
target.clear_combat_effects()

# Check before removing (e.g. targeted dispel)
if target.has_effect("slowed"):
    target.remove_named_effect("slowed")
```

`remove_named_effect()` is fully symmetric — it reverses everything `apply_named_effect()` set up: stat effects, condition flags, timers, and messaging. Safe to call even if the effect isn't active (returns `False`).

### Two Code Paths (Both Correct)

| Path | Condition handling | Messaging | Used by |
|---|---|---|---|
| Named effects | `_add_condition_raw` (silent) | Effect's `messages` dict | Spells, abilities, stun/prone |
| Legacy | `add_condition` (BaseActor override) | Condition enum messages | Equipment `wear_effects`, direct condition calls |

### When NOT to Add a Condition Flag

A `Condition` flag is a ref-counted boolean for **gameplay mechanics that check state** — can this actor fly? are they hidden? can they breathe underwater? The game code calls `has_condition()` to make decisions.

**Do NOT add a Condition flag just for spell targeting or status display.** The named effect system already provides `has_effect()` which serves the same purpose. Adding a Condition flag that nothing checks for gameplay purposes creates dead processing — a flag that just gets set and cleared with no mechanic consuming it. This is exactly the fragmentation the unified effects system was built to eliminate.

**Example — Poison DoT (CORRECT):**
Poison is a **NamedEffect only**. A "Remove Poison" spell checks `has_effect("poisoned")`. The status display checks `has_effect("poisoned")`. There is no `Condition.POISONED` because no gameplay mechanic needs a ref-counted condition flag — nothing in the codebase calls `has_condition(Condition.POISONED)` to make a gameplay decision.

**Example — SLOWED (CORRECT dual-system):**
SLOWED is **both** a NamedEffect AND a Condition because a future movement speed system needs `has_condition(Condition.SLOWED)` to reduce movement speed. The named effect manages lifecycle; the condition flag exists because a concrete gameplay mechanic will check it.

**Rule of thumb:** If the only consumers of the flag would be "Remove X" spells or status display, use `has_effect()` — that's what it's for. Only add a `Condition` when a **separate gameplay system** needs to check the state (movement, visibility, breathing, speech, etc.).

**Example — Poison timing fork:**
When an effect could be applied in or out of combat, fork `duration_type` at apply time based on context rather than building hybrid timing:
```python
# In blowgun at_hit(): check target's combat state at the moment of application
if target.scripts.get("combat_handler"):
    duration_type = "combat_rounds"
else:
    duration_type = "seconds"

target.apply_named_effect(
    key="poisoned",
    duration=poison_ticks,
    duration_type=duration_type,
    ...
)
```
This keeps poison within the unified effect system. The 99% case is combat (attack → combat starts). The edge case (invisible attacker, no combat) uses seconds. Both paths use `apply_named_effect()` — no custom scripts, no hybrid mechanisms.

### Examples

```python
# ── Convenience methods (PREFERRED) ──────────────────────────
# Combat condition — weapon stun
target.apply_stunned(1, source=attacker)

# Combat buff — reactive shield
wielder.apply_shield_buff(ac_bonus=4, duration_rounds=2, mana_cost=5)

# Seconds-based buff — invisibility spell
caster.apply_invisible(duration_seconds=300)

# Combat debuff — weapon sunder
target.apply_sundered(ac_penalty=-2, duration_rounds=2, source=attacker)

# Elemental resistance — resist spell
target.apply_resist_element("fire", resistance_pct=40, duration_seconds=30, source=caster)

# Force-remove without messages — attack breaks invisibility
target.break_invisibility()  # alias for break_effect(NamedEffect.INVISIBLE)

# ── Low-level apply_named_effect (data-driven potions) ───────
# Potion: effect key, stats, condition come from item data
consumer.apply_named_effect(
    key=effect_key,          # e.g. "potion_strength"
    effects=stat_effects,    # from potion_effects data
    condition=condition,     # from potion_effects data (explicit override)
    duration=self.duration,  # duration_type auto-fills from registry
    messages={"end": f"The effects of {self.key} wear off."},
)

# Early cancellation (e.g. dispel magic) — reverses everything + sends end messages
target.remove_named_effect("shield")

# Remove ALL combat effects (on combat end)
target.clear_combat_effects()
```

### Room Visibility Filtering (RoomBase.msg_contents override)

`RoomBase.msg_contents()` checks `from_obj` for HIDDEN/INVISIBLE conditions before broadcasting:
- **HIDDEN actor:** message suppressed entirely (returns immediately)
- **INVISIBLE actor:** all room contents without DETECT_INVIS are added to `exclude` list

**CRITICAL:** All `msg_contents` callers must pass `from_obj=caller` for visibility filtering to work. Without `from_obj`, the override has no actor to check and the message bypasses filtering.

### Dual-Message Helper (RoomBase.msg_contents_with_invis_alt)

For actions where invisible actors produce observable side-effects (tools moving, equipment operating), use the dual-message helper instead of `msg_contents`:

```python
caller.location.msg_contents_with_invis_alt(
    f"{caller.key} begins crafting at the {room.key}.",         # DETECT_INVIS see this
    f"Tools seem to fly around the {room.key} on their own...", # everyone else sees this
    from_obj=caller,
)
```

- **HIDDEN:** message suppressed entirely (same as msg_contents)
- **INVISIBLE:** DETECT_INVIS recipients get `normal_msg`, others get `invis_msg`
- **Normal:** standard `msg_contents` with `normal_msg`

Used by: `cmd_craft.py` (begin/finish), `cmd_repair.py` (begin/finish), `cmd_process.py` (begin).

### NPC Interaction Gating

Inn commands (`cmd_ale.py`, `cmd_stew.py`) gate the entire action if the caller is HIDDEN or INVISIBLE — the bartender can't see you to serve you. This is checked explicitly at the top of `func()` rather than relying on `msg_contents` filtering.

### Automatic Condition Messaging (BaseActor overrides)

`BaseActor.add_condition()` and `remove_condition()` override the mixin to send messages:
- **First person:** `self.msg(cond_enum.get_start_message())` / `get_end_message()`
- **Third person:** `self.location.msg_contents(cond_enum.get_start_message_third_person(self.key), ...)` / `get_end_message_third_person()`

Visibility-aware timing prevents conditions from filtering their own announcements:
- **add_condition:** snapshots `was_hidden`/`was_invisible` BEFORE incrementing — gaining INVISIBLE itself is seen by everyone
- **remove_condition:** checks `has_condition(HIDDEN)`/`has_condition(INVISIBLE)` AFTER decrementing — losing INVISIBLE itself is seen by everyone

### Condition-Specific Side Effects (BaseActor.add/remove_condition)

Beyond messaging, certain conditions trigger gameplay effects on gain/loss:
- **FLY removal:** `_check_fall()` — if `room_vertical_position > 0`, character falls to ground (position reset to 0) with 10 HP damage per height level
- **WATER_BREATHING gain:** `stop_breath_timer()` — cancels active underwater breath timer
- **WATER_BREATHING removal:** `start_breath_timer()` — starts breath timer if `room_vertical_position < 0` (underwater)

### Stealth & HIDDEN Condition

Hide command (`commands/all_char_cmds/cmd_hide.py`) — available to ALL characters (not class-gated). Contested check: `d20 + effective_stealth_bonus` vs best passive perception in room (`10 + effective_perception_bonus`). Binary outcome — hidden from everyone or nobody. Unskilled characters can attempt but suffer -2 penalty from UNSKILLED mastery bonus. `best_passive_perception(room, exclude)` helper accepts single object or set/list of exclusions.

**Movement while HIDDEN:** `FCMCharacter.at_post_move()` automatically rolls stealth vs best perceiver in destination room on entry. Success = stay hidden. Fail = revealed with messaging. Check is on **entry only**, not exit. No separate sneak command — movement while HIDDEN *is* sneaking.

**Search reveals hidden characters:** `cmd_search.py` rolls active perception (`d20 + effective_perception_bonus`) vs passive stealth (`10 + effective_stealth_bonus`).

**Attack from hide:** `cmd_attack.py` checks HIDDEN before combat — breaks hide, grants 1 round advantage via `combat_handler.set_advantage(target, rounds=1)`.

**Restrictions:** Cannot hide in combat (`scripts.get("combat_handler")`). Aggressive/noisy actions (attacking, speaking) break hide.

### Stash Command (Object Concealment)

Stash command (`commands/class_skill_cmdsets/class_skill_cmds/cmd_stash.py`) — STEALTH class skill (thief, ninja, bard). Two branches:

- **Object stashing:** `stash <object>` — physically hides objects in the current room. Rolls `d20 + effective_stealth_bonus`; result becomes the object's `find_dc`. Object disappears from room display via existing `is_visible_to()` filtering. Found via `search` command (uses `discover()` to reveal).
- **Actor stashing:** `stash <ally>` — hides an ally using the stasher's stealth roll. Rolls `d20 + effective_stealth_bonus` vs `best_passive_perception(room, exclude={caller, target})`. On success, applies HIDDEN condition to the target. Target then follows normal hidden rules — they use their own stealth if they move, and all standard hidden-breaking triggers work. Cannot stash yourself (use `hide` instead), cannot stash someone already hidden or in combat.

**Stash vs Conceal:** Two distinct commands for hiding things:
- `stash` (STEALTH, thief/ninja/bard) — physical concealment. Tucks something behind stones, buries under debris. DEX-based.
- `conceal` (MISDIRECTION, bard-only) — magical glamour. Makes something unremarkable via bardic magic. CHA-based. Scaffold only, not yet implemented.

**HiddenObjectMixin coverage:** All three item base classes support hiding:
- `BaseNFTItem` — all NFT items (weapons, armor, consumables, containers)
- `WorldItem` — non-NFT takeables (keys, novelty items)
- `WorldFixture` — immovable world objects (signs, chests) — had the mixin originally

All default to `is_hidden=False`. Room display filtering (`get_display_things()`) already handles `is_visible_to()`.

### Case & Pickpocket (SUBTERFUGE Skill)

Two linked commands forming a scout-then-steal workflow for thieves/ninjas/bards:

**Case** (`commands/class_skill_cmdsets/class_skill_cmds/cmd_case.py`) — passive observation of a target's inventory. Each item has a mastery-dependent % chance of being revealed (BASIC 50%, SKILLED 60%, EXPERT 70%, MASTER 80%, GM 90%). Gold shown as vague tiers ("a few coins", "some gold", "a decent purse", "a heavy coin purse", "a fortune"). Resources show type but not quantity ("some wheat"). Results cached for 5 minutes — repeat shows same results. Does NOT break HIDDEN (purely observational).

**Pickpocket** (`commands/class_skill_cmdsets/class_skill_cmds/cmd_pickpocket.py`) — steal something revealed by case. Syntax: `pickpocket <thing> from <target>`. Contested roll: `d20 + DEX mod + SUBTERFUGE mastery bonus` vs `10 + target.effective_perception_bonus`. HIDDEN gives advantage (roll twice, take best). HIDDEN always breaks after attempt.

Gate chain: parse "from" syntax → find target → not self → not in combat → room allows combat → PvP room for player targets → BASIC+ mastery → not immortal NPC → must have cased → target still has item → 60s per-target cooldown.

Success: gold (`1d6 + mastery_bonus`, capped), resource (`1d4 + mastery_bonus//2`, capped), or item (moved to thief). Failure: target alerted, room message, aggressive CombatMobs aggro via `mob_attack()`.

**Thief combo:** `hide` → `case` (stays hidden) → `pickpocket` (advantage from hidden, then revealed).

### Breath Timer (typeclasses/scripts/breath_timer.py)

Per-character `BreathTimerScript` attached when diving underwater without WATER_BREATHING. Ticks every 2 seconds. Duration: `max(10, 30 + CON_modifier * 15)` seconds. After breath expires, deals `max(1, effective_hp_max // 20)` drowning damage per tick (~5% HP). Triggers `die("drowning")` when HP reaches 0.

## Crafting & Processing System

### Recipe System (world/recipes/)

Recipes are Python dicts registered in `world/recipes/__init__.py`. One file per recipe, organised by skill subdirectory (carpentry, blacksmithing, leatherworking, tailoring, alchemy, jewellery, enchanting). 52+ recipes across 7 skill categories.

```python
# world/recipes/carpentry/training_longsword.py
RECIPE_TRAINING_LONGSWORD = {
    "key": "training_longsword",
    "name": "Training Longsword",
    "skill": skills.CARPENTER,
    "crafting_type": RoomCraftingType.WOODSHOP,
    "min_mastery": MasteryLevel.BASIC,
    "ingredients": {7: 3},          # 3 Timber (resource ID → quantity)
    "output_prototype": "training_longsword",
}

# Recipes can also consume NFT items as ingredients:
RECIPE_SPEAR = {
    "key": "spear",
    "name": "Spear",
    "skill": skills.BLACKSMITH,
    "crafting_type": RoomCraftingType.SMITHY,
    "min_mastery": MasteryLevel.BASIC,
    "ingredients": {5: 1},          # 1 Iron Ingot
    "nft_ingredients": {"shaft": 1},  # 1 Shaft (carpenter component NFT)
    "output_prototype": "spear",
}
```

Helpers: `get_recipe(key)`, `get_recipes_for_crafting_type(type)`, `get_recipes_for_skill(skill)`, `get_recipe_by_output_prototype(prototype_key)` (reverse lookup), `compute_repair_cost(recipe)` (auto-compute or explicit `repair_ingredients`)

### Enchanting System (world/recipes/enchanting/)

Enchanting is a **mage-only** crafting skill (`skills.ENCHANTING`) that transforms vanilla items into enchanted variants with magical effects. Key design decisions:

**Recipes auto-granted at mastery level-up** — no recipe scrolls needed (unlike other crafting skills). This means:
- No recipe scroll prototypes in `world/prototypes/consumables/recipes/` for enchanting
- No recipe scroll entries in migration 0007
- Enchanters learn recipes automatically when they reach the required mastery tier

**Item split — vanilla vs enchanted:**
- **Vanilla items** (tailored/leathered): simple names (Bandana, Kippah, Cloak, Veil, Scarf, Sash, Leather Cap, Leather Gloves), no effects, no class restrictions. Crafted by tailors/leatherworkers.
- **Enchanted items**: named variants (Rogue's Bandana, Sage's Kippah, etc.) with effects and optional class restrictions. Created by enchanters transforming vanilla items.
- **Non-enchantable items** keep their effects baked in: Gambeson (+1 AC, excludes mage), Coarse Robe (+10 mana), Brown Corduroy Pants (+10 move), Warrior's Wraps (+10 HP, excludes mage/cleric/thief).

**Three tiers of enchanting ingredients (planned):**
- BASIC/SKILLED: Arcane Dust (resource ID 15) — 2 per recipe
- EXPERT/MASTER: mid-game ingredient (TBD)
- GRANDMASTER: late-game ingredient (TBD)

**Enchanting scope:**
- **Wearables**: deterministic (fixed recipe per item — vanilla + dust → named enchanted variant)
- **Gems**: probabilistic (d100 roll tables) — enchanter turns raw gem + dust into "Enchanted Ruby/Emerald/Diamond" with random effects and optional race/class restrictions. Effects hidden until examined/identified.
- **Weapons**: NOT directly enchanted — get enchanted gems inset by jeweller instead

**Gem enchanting architecture** (`world/recipes/enchanting/gem_tables.py`):
- Roll tables keyed by gem type → mastery level → d100 ranges with effects
- Separate restriction table: 1-20 = random race restriction, 21-50 = random class restriction, 51-100 = no restriction
- One `NFTItemType` per gem tier (Enchanted Ruby, Enchanted Emerald, Enchanted Diamond) — NOT one per effect variant
- Effects stored as `db.gem_effects` and `db.gem_restrictions` on the spawned item (regular Evennia attributes)
- Ruby available at BASIC (5 mastery tables planned), Emerald at EXPERT (3 tables), Diamond at GM only (1 table)
- `cmd_craft.py` detects `output_table` field in recipe and calls `roll_gem_enchantment()` after spawn

**Gem insetting** (`cmd_inset.py` — jeweller skill, `RoomCraftingType.JEWELLER`):
- Standalone command `inset <gem> in <weapon>` (aliases: `ins`) — NOT a recipe through `cmd_craft`
- Jeweller consumes enchanted gem and transfers its effects to a weapon
- Host weapon keeps its original `NFTItemType`/typeclass but gets effects + name override in NFTMirror metadata
- Extends `weapon.wear_effects` with gem effects (preserves original prototype effects)
- Stores `gem_effects` and `gem_restrictions` as db attrs on the weapon
- Persists name, wear_effects, gem_effects, gem_restrictions to NFTMirror metadata for despawn/respawn survival
- LLM name generator stub (`llm/name_generator.py`) — returns hardcoded "LLMName" until LLM integration
- Mastery requirements by gem tier: Ruby → BASIC, Emerald → EXPERT, Diamond → GRANDMASTER
- Single gem per weapon (no double-insetting), weapon must not be wielded
- Progress bar (2 ticks × 3 seconds), 10 XP per inset

**Room type:** `RoomCraftingType.WIZARDS_WORKSHOP` — enchanting-specific crafting rooms.

**Command aliases:** `enchant`/`enc`/`ench`/`en` (active — added to `cmd_craft.py` aliases and verb/gerund maps).

### RecipeBookMixin (typeclasses/mixins/recipe_book.py)

Mixed into `FCMCharacter`. Stores known recipes in `self.db.recipe_book` dict for O(1) lookup.

- `learn_recipe(recipe_key)` → `(bool, str)` — validates recipe exists, skill requirement met
- `knows_recipe(recipe_key)` → `bool`
- `get_known_recipes(skill=None, crafting_type=None)` → filtered list

### RoomProcessing (typeclasses/terrain/rooms/room_processing.py)

Resource refinement rooms (windmill, bakery, smelter, tannery, sawmill, textile mill). Converts input resources → output resource for a gold fee. Supports multi-recipe rooms (e.g. smelter handles iron ore → iron ingot, copper ore → copper ingot, alloys) and multi-input recipes (e.g. bakery: flour + wood → bread). Each recipe can have its own cost override or fall back to the room default.

Commands: `process <resource>` (aliases: `mill`, `bake`, `smelt`, `saw`, `tan`, `weave`) — auto-selects recipe by input match. `rates` — shows all available conversions and costs. Configurable delay with progress bar.

### RoomCrafting (typeclasses/terrain/rooms/room_crafting.py)

Skilled NFT item crafting rooms (smithy, woodshop, tailor, apothecary, etc.). Each room has a `crafting_type` and `mastery_level` that gates which recipes can be made there.

Commands: `craft` (aliases: `forge`, `carve`, `sew`, `brew`, `enchant` + prefix abbreviations like `cr`, `cra`, `fo`, `br`, `enc`, `ench`, `en`, etc.), `available`, `repair` (aliases: `rep`, `repa`, `repai`). Configurable delay with progress bar scaled by mastery level. Craft spawns NFTs via `BaseNFTItem.assign_to_blank_token()` + `spawn_into()`. For potions, post-spawn mastery scaling overrides `potion_effects` and `duration` from `potion_scaling.py` tables based on the brewer's alchemy mastery. For gem enchanting, post-spawn roll table sets `gem_effects` and `gem_restrictions` from `gem_tables.py` based on the enchanter's mastery. Repair restores durability to max at reduced material cost (dual mode: auto-compute `total_materials - 1` or explicit `repair_ingredients` on recipe), awards 50% craft XP.

### Consumable Items (typeclasses/items/consumables/)

- `ConsumableNFTItem` — base for single-use NFT items. `consume(consumer)` calls `at_consume()`, deletes item on success (returned to RESERVE via standard hooks).
- `CraftingRecipeNFTItem` — teaches a recipe when consumed. `recipe_key` AttributeProperty matches `world.recipes` registry.
- `PotionNFTItem` — potion with `potion_effects` list, `duration`, and `named_effect_key`. `at_consume()` applies instant restore effects directly, then timed effects (stat_bonus, condition) via `apply_named_effect(duration_type="seconds")`. Anti-stacking via `has_effect(key)` — keyed by stat (e.g. `"potion_strength"`), blocks consumption when effect is already active (potion saved). Supports dice-based restore (`"dice": "2d4+1"`) and int-based (`"value": 8`). Mastery scaling applied post-spawn by `cmd_craft.py` from `potion_scaling.py` tables.
- `SpellScrollNFTItem` — spell scroll with `spell_key`. Consumed via `transcribe` command to learn spells.

### New Commands

| Command | Location | Purpose |
|---|---|---|
| `learn` | all_char_cmds | Consume recipe NFT to learn recipe (Y/N confirmation) |
| `recipes` | all_char_cmds | Show all known recipes grouped by skill |
| `craft`/`forge`/`carve`/`sew`/`brew` | room_specific (crafting) | Craft NFT items from recipes |
| `available` | room_specific (crafting) | Show craftable recipes in current room |
| `repair`/`rep` | room_specific (crafting) | Repair damaged item (reduced material cost, 50% XP) |
| `process`/`mill`/`bake`/`smelt`/`saw`/`tan`/`weave` | room_specific (processing) | Convert resources |
| `rates` | room_specific (processing) | Show conversion rates and costs |

## Prototype Structure (world/prototypes/)

One file per item, organised by category. Evennia discovers all prototypes via `PROTOTYPE_MODULES = ["world.prototypes"]` and wildcard imports in `__init__.py`.

```
world/prototypes/
├── __init__.py              ← imports * from all subpackages
├── weapons/                 ← 18 weapons (training_*, iron_*, bronze_*, club, spear, sling)
├── wearables/               ← organised by slot subdirectory (vanilla + enchanted variants)
│   ├── head/               ← bandana, kippah, leather_cap + enchanted: rogues_bandana, sages_kippah, scouts_cap
│   ├── face/               ← veil + enchanted: veil_of_grace
│   ├── body/               ← gambeson, coarse_robe, leather_armor
│   ├── legs/               ← brown_corduroy_pants, leather_pants
│   ├── neck/               ← scarf, copper_chain, pewter_chain + enchanted: professors_scarf
│   ├── finger/             ← copper_ring, pewter_ring
│   ├── wrist/              ← copper_bangle, pewter_bracelet
│   ├── ear/                ← copper_studs, pewter_hoops
│   ├── hands/              ← leather_gloves, warriors_wraps + enchanted: pugilists_gloves
│   ├── feet/               ← leather_boots
│   ├── waist/              ← leather_belt, sash + enchanted: sun_bleached_sash
│   ├── cloak/              ← cloak + enchanted: titans_cloak
│   └── bridle/             ← bridle
├── holdables/               ← wooden_shield, ironbound_shield
├── components/              ← shaft, haft, leather_straps (BaseNFTItem)
├── consumables/             ← all single-use NFT items
│   ├── potions/             ← 9 alchemy potions (PotionNFTItem)
│   ├── recipes/             ← recipe scroll prototypes (CraftingRecipeNFTItem) — no scrolls for enchanting
│   ├── scrolls/             ← spell scroll prototypes (SpellScrollNFTItem)
│   └── wands/               ← (placeholder)
└── containers/              ← backpack, panniers (ContainerNFTItem)
```

## Magic System Architecture

Spell system for mages and clerics. Spells are **class-based** (one Python class per spell) with a **registry** for discovery. This differs from recipes which are data-driven dicts — spells need per-tier execution logic that is genuinely different code, not just parametric scaling.

### Why Class-Based, Not Data-Driven

Some spells scale parametrically (magic missile: 1/2/3/4/5 missiles) but many have qualitatively different behavior per mastery tier:
- **Teleport**: basic=within area, skilled=within zone, expert=within continent, master=within world, GM=across worlds
- **Summon**: basic=rat, GM=dragon (different creatures, AI, duration)
- **Invisibility**: basic=breaks on attack, expert=breaks on cast only, GM=doesn't break

A unified class-per-spell system avoids the confusion of maintaining two systems (parametric vs custom) and lets any spell evolve from simple to complex without migration.

### Spell Architecture

```python
# world/spells/registry.py
SPELL_REGISTRY = {}

def register_spell(cls):
    SPELL_REGISTRY[cls.key] = cls()
    return cls

# world/spells/evocation/magic_missile.py
@register_spell
class MagicMissile(Spell):
    key = "magic_missile"
    aliases = ["mm"]
    name = "Magic Missile"
    school = skills.EVOCATION          # skills enum member
    min_mastery = MasteryLevel.BASIC
    mana_cost = {1: 5, 2: 8, 3: 10, 4: 14, 5: 16}
    target_type = "hostile"

    def _execute(self, caster, target):
        tier = self.get_caster_tier(caster)
        missiles = tier
        total_damage = sum(dice.roll("1d4+1") for _ in range(missiles))
        target.hp = max(0, target.hp - total_damage)
        s = "s" if missiles > 1 else ""
        return (True, {
            "first":  f"You fire {missiles} glowing missile{s} at {target.key}...",
            "second": f"{caster.key} fires {missiles} glowing missile{s} at you...",
            "third":  f"{caster.key} fires {missiles} glowing missile{s} at {target.key}...",
        })
```

**Base `Spell` class** (`world/spells/base_spell.py`) handles: mastery check, cooldown check, mana deduction, dispatch to `_execute()`. Subclass per spell implements `_execute(caster, target)` which returns `(bool, dict)` with first/second/third person messages. Validation failures return `(False, str)`. Each spell also has `description` (short flavour text) and `mechanics` (multi-line rules/scaling text) for the future `spellinfo` command.

**Class attributes:**
- `key` — unique registry key (e.g. `"magic_missile"`)
- `aliases` — shorthand names (e.g. `["mm"]`), default `[]`
- `name` — display name (e.g. `"Magic Missile"`)
- `school` — `skills` enum member (e.g. `skills.EVOCATION`). Use `spell.school_key` property for string lookups against `class_skill_mastery_levels` dict.
- `min_mastery` — `MasteryLevel` enum (BASIC=1 through GRANDMASTER=5)
- `mana_cost` — dict `{tier: cost}` (e.g. `{1: 5, 2: 8, ...}`)
- `target_type` — `"hostile"`, `"friendly"`, `"self"`, or `"none"`

**File structure**: `world/spells/<school>/<spell_name>.py` — one file per spell, organised by school/domain.

**Discovery**: `@register_spell` decorator populates `SPELL_REGISTRY`. `__init__.py` per school folder imports all spell modules so decorators fire at import time.

**Registry helpers**: `get_spell(key)`, `get_spells_for_school(school)`, `list_spell_keys()`

**SpellbookMixin** (`typeclasses/mixins/spellbook.py`): mixed into `FCMCharacter`. Provides `learn_spell()`, `knows_spell()`, `memorise_spell()`, `forget_spell()`, `is_memorised()`, `get_memorisation_cap()`, `get_known_spells()`, `get_memorised_spells()`. Storage: `db.spellbook` and `db.memorised_spells` (both `{spell_key: True}` dicts).

**Commands**: `cast`, `transcribe`, `memorise`/`memorize`, `forget`, `spells` — all in `commands/all_char_cmds/`.

**Implemented spells (29 of 50)**: Evocation — MagicMissile, FlameBurst, Frostbolt, Fireball, ConeOfCold, PowerWordDeath. Abjuration — Shield (reactive), MageArmor, Resist, Shadowcloak. Necromancy — DrainLife, VampiricTouch, SoulHarvest. Conjuration — AcidArrow. Divination — Identify, TrueSight. Illusion — Blur, Invisibility. Divine Healing — CureWounds. Divine Protection — Sanctuary. Divine Judgement — Smite (reactive). Divine Revelation — HolyInsight, HolySight. Divine Dominion — Command, Hold. Nature Magic — Entangle, CallLightning. Plus `smite` toggle command and reactive spell system (`combat/reactive_spells.py`). 318+ spell tests.

**Spell utility helpers** (`world/spells/spell_utils.py`): `apply_spell_damage(target, raw_damage, damage_type)` — applies damage with resistance check, triggers death. `get_room_enemies(caster)` — gets enemies via combat sides or NPC detection fallback. `get_room_all(caster)` — all living entities including caster (for unsafe AoE).

**Scroll prototypes**: Every mage spell has a corresponding scroll prototype in `world/prototypes/consumables/scrolls/`. Cleric spells are auto-learned on skill-up (no scrolls needed).

### Mage vs Cleric Differences

| Aspect | Mage | Cleric |
|---|---|---|
| Schools | evocation, conjuration, divination, abjuration, necromancy, illusion (6 casting schools — enchanting is a crafting skill, not casting) | divine_healing, divine_protection, divine_revelation, divine_dominion (cleric/paladin); divine_judgement (**paladin only**); nature_magic (druid/ranger) |
| Learning | `transcribe <scroll>` — consumes spell scroll NFT | Auto-learn all spells at new skill tier when gaining a domain skill level (deferred) |
| Spellbook | Learned via transcribe | Populated automatically on skill-up |
| Memorise/Forget | Yes — memorise has delay, forget is instant | Same |
| Cast | From memory, costs mana | Same |
| Memorise cap | floor(mage_class_level / 4) + get_attribute_bonus(intelligence) + extra_memory_slots | floor(cleric_class_level / 4) + get_attribute_bonus(wisdom) + extra_memory_slots |

### Memory Slot System

- `extra_memory_slots` — cacheable stat from equipment (via `stat_bonus` effect type), follows standard pattern
- Cap checked at **memorise time only** — buff INT/WIS to memorise extra spells, they stay memorised when buff drops
- If spells are forgotten while at lower ability, re-memorising uses the lower cap
- Same universal pattern: `effective_cap = floor(class_level / 4) + get_attribute_bonus(ability) + extra_memory_slots`

### Spell Scroll NFTs

- `SpellScrollNFTItem` — `ConsumableNFTItem` subclass with `spell_key` AttributeProperty
- Mages consume via `transcribe` command — Y/N confirmation, then spell added to spellbook, scroll consumed
- Scrolls can also be cast directly (one-time use, no transcription, lower/no level requirement) — deferred

### Spell Design Rules

**Mana cost rule:** 1 mana per average point of damage. Round halves up (3.5 → 4). Conditions, utility, and AoE do NOT add extra cost — the damage formula IS the cost.

**Damage scaling tiers:**
- Starter spells (learned at BASIC): +1d6 per tier (or +1 missile for Magic Missile)
- Intermediate spells (learned at SKILLED): +2d6 per tier
- Big spells (learned at EXPERT+): +3d6 per tier — clearly superior, reward for mastery investment

**Cooldown rules:** Spell-specific cooldowns (can still take other actions, just can't recast that spell). Defaults by min_mastery tier: BASIC/SKILLED = 0, EXPERT = 1 round, MASTER = 2 rounds, GM = 3 rounds. Override via `cooldown` class attribute on individual spells. Tracked in `caster.db.spell_cooldowns`.

**Duration storage convention:** `_DURATION` dicts store values in their **natural human-readable unit**, then convert to the effect system's unit in `_execute()`:
- **Seconds-based effects** (`duration_type="seconds"`): store in **minutes** (e.g. `{1: 1, 2: 2, 3: 5}`), convert `* 60` before passing to `apply_named_effect()`. Examples: Invisibility, Sanctuary, Shadowcloak, True Sight.
- **Hours-based effects**: store in **hours** in `_SCALING` tuples, convert `* 3600`. Example: Mage Armor.
- **Combat-round effects** (`duration_type="combat_rounds"`): store in **rounds** directly — no conversion needed. Use `_ROUNDS` or `_SCALING` dict. Examples: Shield, Blur.
- **Display**: compute display string from the stored unit directly (e.g. `f"({duration_minutes} minutes)"`), not by reverse-converting from seconds.

**Recast refresh pattern** (for self-buffs like Invisibility, Sanctuary): if the effect is already active, compare new duration vs remaining time via `get_effect_remaining_seconds()`. Only refresh (remove + reapply) if gaining time. If existing is stronger, refund mana and return `(False, {...})`. This prevents downgrading a MASTER-tier cast with a BASIC recast.

**Range rules:** Spells follow the same range system as weapons:
- **Melee spells**: same room, same height only
- **Ranged spells**: same room different height, or adjacent room in same area
- Actors in melee cannot use ranged spells (same as ranged weapons)
- Actors at range cannot use melee spells
- Future feat (like Crossbow Expert) may allow ranged spells in melee

**AoE types:**
- **Unsafe AoE** (e.g. Fireball, Call Lightning): hits EVERYTHING in the room including caster and allies. DEX save for half damage (DC = caster d20 + ability + mastery). Safe to cast at range (flying vs ground, or across area rooms).
- **Safe AoE** (e.g. Cone of Cold): hits enemies only. Diminishing accuracy: 1st enemy 100%, 2nd 80%, 3rd 60%, 4th 40%, 5th+ 20%. The price of safety is you might not catch all enemies.
- This creates genuine tactical choice: guaranteed damage to everyone (including yourself) vs selective targeting with diminishing accuracy.

**Creature size tiers** (scaling mechanic for summons, knockback, reanimation):

| Mastery | Size | Examples |
|---|---|---|
| BASIC | Small | rat, sprite, imp, snake |
| SKILLED | Medium | wolf, skeleton, minor elemental |
| EXPERT | Large | bear, ogre, greater elemental |
| MASTER | Huge | giant, wyvern, treant |
| GM | Gargantuan | ancient dragon, titan |

### Evocation Spell Progression

**Implemented spells:**

| Spell | Min Tier | Type | Range | Damage | Mana (per tier) | Cooldown | Notes |
|---|---|---|---|---|---|---|---|
| Magic Missile | BASIC | single target | any | 1d4+1 × tier missiles | 5/8/10/14/16 | 0 | auto-hit, force damage |
| Frostbolt | BASIC | single target | any | 1d6 cold + contested SLOWED | 5/8/10/14/16 | 0 | flat damage, utility via debuff |
| Flame Burst | SKILLED | safe AoE | melee | 3d6→6d6 fire | 11/14/18/21 | 0 | safe AoE, diminishing accuracy |
| Fireball | EXPERT | unsafe AoE | any | 8d6/11d6/14d6 fire, DEX save half | 28/39/49 | 1 | hits everything incl. caster |
| Cone of Cold | MASTER | safe AoE | any | 10d6/13d6 cold | 35/46 | 2 | diminishing accuracy + SLOWED |
| Power Word: Death | GM | single target | any | instant kill | 100 | 3 | contested save, nat 20 always kills |

**Planned spells (not yet implemented):**

| Spell | Min Tier | Type | Range | Damage | Mana (per tier) | Notes |
|---|---|---|---|---|---|---|
| Lightning Bolt | SKILLED | single target | ranged | 4d6→10d6 lightning | 14/21/28/35 | high single-target |
| Chain Lightning | EXPERT | multi-target | ranged | 6d6→10d6 primary, bounces | 21/28/35 | bounces = tier count, -1d6/bounce |

### Abjuration Spell Progression

Shield, Mage Armor, Resist, and Shadowcloak implemented. Remaining spells scaffolded. Dependencies for remaining: dispel mechanics.

**Implemented spells:**

| Spell | Min Tier | Type | Mechanic | Mana | Cooldown | Notes |
|---|---|---|---|---|---|---|
| Shield | BASIC | self (reactive) | +4/+4/+5/+5/+6 AC, 1/2/2/3/3 rounds | 3/5/7/9/12 | 0 | **IMPLEMENTED** — Reactive only (like Smite). Auto-triggers when about to be hit via `check_reactive_shield()` in `combat/reactive_spells.py`. Toggle via `toggle shield` (unified player preference system, `shield_active` attribute). Three gates: toggle ON + memorised + mana. Anti-stacking via `has_effect("shield")`. |
| Mage Armor | BASIC | self | +3/+3/+4/+4/+5 AC, 1/2/2/3/3 hours | 3/5/7/9/12 | 0 | Long-duration maintenance buff. Uses seconds-based timer (wall-clock). Anti-stacking via `has_effect("mage_armored")`. Stacks with Shield (up to +11 AC at GM). Mana refunded on anti-stacking rejection. |
| Resist | SKILLED | friendly | 20%/30%/40%/60% resistance to chosen element, 30s | 8/10/14/16 | 0 | First spell using `has_spell_arg` — `cast resist fire [target]`. Per-element named effects (resist_fire, resist_cold, etc.) — different elements can coexist. Anti-stacking per element. Uses DamageResistanceMixin via Layer 2 dispatch. |
| Shadowcloak | SKILLED | group | +4/+6/+8/+10 stealth_bonus, 4/6/8/10 min | 12/15/20/24 | 0 | Group stealth buff — self if solo, all same-room group members if in a follow chain. Uses `stat_bonus` on `stealth_bonus` via named effect system. Anti-stacking per target. First spell using group targeting via `get_group_leader()` + `get_followers(same_room=True)`. |

**Scaffolded spells:**

| Spell | Min Tier | Type | Mechanic | Mana (per tier) | Cooldown | Notes |
|---|---|---|---|---|---|---|
| Antimagic Field | EXPERT | unsafe AoE | Dispels all spell+potion effects, suppresses casting. 1/2/3 rounds | 28/39/49 | default | "Fireball of abjuration" — strips YOUR buffs too |
| Group Resist | MASTER | party | 40%/60% resistance, 30s, whole party | 56/64 | 2 | 4x individual Resist cost |
| Invulnerability | GM | self | Total damage+condition immunity, 1 round | 100 | 3 | mirror of PWD |

### Necromancy Spell Progression

**Implemented spells:**

| Spell | Min Tier | Type | Damage | Mana (per tier) | Cooldown | Notes |
|---|---|---|---|---|---|---|
| Drain Life | BASIC | single target | 2d6→6d6 cold | 5/8/10/14/16 | 0 | heals caster 100%, capped at max HP |
| Vampiric Touch | SKILLED | single target (touch) | 1d6→4d6 cold | dynamic (% of max mana) | 0 | Touch attack (d20+INT+mastery vs AC). Heals 100% PAST max HP. VAMPIRIC effect with 10min timer (resets each drain). Escalating mana cost (3%→95%). Bonus HP lost on expiry (floor 1 HP). |
| Soul Harvest | EXPERT | unsafe AoE | 8d6→14d6 cold | 28/39/49 | 1 | drains ALL living except caster, caster heals total |

**Scaffolded spells:**

| Spell | Min Tier | Mechanic | Mana (per tier) | Notes |
|---|---|---|---|---|
| Disease | BASIC | Contested INT+mastery vs CON. DISEASED — disables ALL regen (HP, mana, move). Duration scales with tier. | 5/8/10/14/16 | Countered by Purify (SKILLED+). Useful vs regen-heavy mobs. Needs DISEASED condition + named effect. |
| Raise Dead | SKILLED | Raise 1/2/3/4 corpses, 2/5/10/30 min duration | 15/25/40/60 | player corpses with gear protected. Needs pet system |
| Raise Lich | MASTER | Raise one corpse as lich minion (casts Drain Life) | 50/70 | replaces existing lich. Needs pet system + NPC AI |
| Death Mark | GM | Marks target 1 round — ALL damage heals attacker | 100 | party burst window. Needs damage pipeline hook |

**Design identity**: life manipulation — steal, drain, corrupt, raise. The selfish school. Core: damage-to-heal conversion. Counterplay: cold resistance, silence/stun, Antimagic Field, Purify.

### Conjuration Spell Progression

Acid Arrow implemented. Remaining spells scaffolded. Dependencies: room teleport flags (no_teleport_to/no_teleport_out), world tag, pet system, waygate system.

**Implemented spells:**

| Spell | Min Tier | Type | Mechanic | Mana | Cooldown | Notes |
|---|---|---|---|---|---|---|
| Acid Arrow | BASIC | single target | 1d4+1 acid/round x tier rounds (DoT) | 5/8/10/14/16 | 0 | Pure DoT workhorse — same total damage budget as Magic Missile but delivered over time. Uses AcidDoTScript (combat-round ticks via combat_handler). Anti-stacking: new cast replaces old. |

**Scaffolded spells:**

| Spell | Min Tier | Type | Mechanic | Mana (per tier) | Cooldown | Notes |
|---|---|---|---|---|---|---|
| Teleport | SKILLED | self | Self-teleport: district→zone→world range | 15/25/40/40 | 60s | respects no_teleport_to/out room flags |
| Dimensional Lock | EXPERT | unsafe AoE | DIMENSION_LOCKED on all — no flee/teleport/summon | 28/39/49 | 0 | save scales: normal→disadvantage→no save |
| Conjure Elemental | MASTER | summon | Elemental combat pet, 10/30 min | 56/64 | 0 | needs pet system |
| Gate | GM | portal | Walk-through portal to discovered waygate | 100 | 300s | party can use. Needs waygate system |

**Design identity**: summoning, teleportation, dimensional control. The "Fireball" is Dimensional Lock (area control, not damage). Counterplay: WIS saves, Antimagic Field.

### Divination Spell Progression

True Sight implemented. No damage spells — pure utility and intelligence. Mirror Image and Foresight deferred for design discussion.

| Spell | Min Tier | Type | Mechanic | Mana (per tier) | Cooldown | Notes |
|---|---|---|---|---|---|---|
| **Identify** | BASIC | utility | Reveals actor stats + NFT item properties (dynamic templates). Actors: level-gated (1-5=BASIC…36+=GM), PCs only in PvP rooms. Items: weapons/armor/holdables/consumables/containers, no mastery gate | 5/8/10/14/16 | 0 | **IMPLEMENTED** (actor + item branches) — target_type="any". World fixture/resource branches deferred |
| **True Sight** | SKILLED | self-buff | Tiered perception: SKILLED=see HIDDEN, EXPERT=+auto-detect traps (no roll), MASTER=+see INVISIBLE. Duration: 5/10/30/60 min | 15/25/40/40 | 0 | **IMPLEMENTED** — NamedEffect TRUE_SIGHT, DETECT_INVIS only at MASTER+. db.true_sight_tier stored for trap detection in _check_traps_on_entry(). Traps auto-detected on cast and room entry at EXPERT+ |
| Scry | SKILLED | remote | Remote mob intel: alive/zone→room/HP→stats→items | 15/25/40/60 | 30s | range scales with tier |
| Mass Revelation | EXPERT | unsafe AoE | Strips HIDDEN+INVISIBLE from ALL in room (allies too) | 28/39/49 | 0 | "Fireball of divination" |

**Design identity**: knowledge, sight, revelation. No damage. The support school. Counterplay: Greater Invisibility, Antimagic Field.

### Illusion Spell Progression

Blur implemented. Mirror Image deferred for design discussion.

| Spell | Min Tier | Type | Mechanic | Mana (per tier) | Cooldown | Notes |
|---|---|---|---|---|---|---|
| **Blur** | BASIC | self-buff | BlurScript sets 1 disadvantage on all enemies per round. Multi-attackers only lose 1 attack's accuracy | 5/8/10/14/16 | 0 | **IMPLEMENTED** — 3/4/5/6/7 rounds. Uses NamedEffect BLURRED + BlurScript |
| **Invisibility** | SKILLED | self-buff | Standard INVISIBLE — breaks on attack/cast | 15/25/40/40 | 0 | **IMPLEMENTED** — NamedEffect INVISIBLE + Condition.INVISIBLE. Duration: 5/10/30/60 min. break_invisibility() zeros all refs + stops timer. Recast refreshes duration (only if gaining time, else mana refunded). |
| Mass Confusion | EXPERT | unsafe AoE | CONFUSED — random target selection, caster included | 28/39/49 | 0 | "Fireball of illusion". Foresight auto-saves |
| Greater Invisibility | MASTER | friendly-buff | INVISIBLE but doesn't break on action | 56/64 | 0 | uses INVISIBLE + db flag |
| Phantasmal Killer | GM | single target | Contested WIS save, 20d6 psychic / half on save | 100 | 0 | can kill from fright |

**Design identity**: deception, misdirection, confusion. The trickster school. Core: denial of information. Counterplay: True Sight, Mass Revelation, WIS saves.

### Divine Healing Spell Progression

Cleric/paladin healing domain. Core identity: restore, cure, protect from death.

| Spell | Min Tier | Type | Mechanic | Mana (per tier) | Cooldown | Notes |
|---|---|---|---|---|---|---|
| **Cure Wounds** | BASIC | friendly | Heal 1d8+WIS per tier | 5/8/10/14/16 | 0 | **IMPLEMENTED** — workhorse heal, WIS modifier scaling |
| Purify | SKILLED | friendly | Remove conditions from target. Tier-gated: SKILLED=POISONED/BLINDED, EXPERT=+DISEASED, MASTER=+SLOWED, GM=+PARALYSED. Cures all eligible conditions in one cast. | 8/10/14/16 | 0 | Divine counter to necromantic corruption and debuffs. |
| Mass Heal | EXPERT | group | Heal all allies in room | TBD | 1 | "Fireball of healing" — the party-save button |
| Death Ward | GM | friendly | Preemptive buff — intercepts death, target survives on 1 HP, effect consumed | TBD | 3 | Hooks into `take_damage()`/`die()` to intercept lethal damage. Named effect consumed on trigger |

**Design identity**: restoration, preservation, anti-death. The selfless school. Counterplay: Antimagic Field, silence/stun.

### Divine Protection Spell Progression

Cleric/paladin defensive domain. Core identity: wards, buffs, sanctification. Sanctuary implemented.

**Implemented spells:**

| Spell | Min Tier | Type | Mechanic | Mana (per tier) | Cooldown | Notes |
|---|---|---|---|---|---|---|
| **Sanctuary** | BASIC | self | Enemies cannot target caster. Breaks on attack or hostile spell cast | 5/8/10/14/16 | 0 | **IMPLEMENTED** — NamedEffect SANCTUARY + Condition.SANCTUARY. Duration: 1/2/3/4/5 min. break_sanctuary() zeros all refs + stops timer. Recast refreshes (only if gaining time, else mana refunded). Combat hooks: target protected (attack blocked), attacker loses sanctuary on offensive action. |

**Scaffolded spells:**

| Spell | Min Tier | Type | Mechanic | Mana (per tier) | Cooldown | Notes |
|---|---|---|---|---|---|---|
| Holy Aura | EXPERT | group | AC + resistance buff to all allies in room | TBD | 1 | Group defensive buff |
| Divine Aegis | GM | friendly | Total damage immunity on target for short duration | TBD | 3 | Thematic parallel to Abjuration's Invulnerability |

**Design identity**: protection, warding, sanctification. The guardian school. Counterplay: Antimagic Field, wait it out.

### Divine Judgement Spell Progression

**Paladin only.** Holy damage domain. Core identity: righteous wrath, radiant strikes. Smite implemented.

**Implemented spells:**

| Spell | Min Tier | Type | Mechanic | Mana (per tier) | Cooldown | Notes |
|---|---|---|---|---|---|---|
| **Smite** | BASIC | self (reactive) | +1d6/+2d6/+3d6/+4d6/+5d6 bonus radiant damage per weapon hit | 3/5/7/9/12 | 0 | **IMPLEMENTED** — Reactive only (like Shield). Auto-triggers on weapon hit via `check_reactive_smite()` in `combat/reactive_spells.py`. Toggle via `toggle smite` (unified player preference system, `smite_active` attribute). Three gates: toggle ON + memorised + mana. Respects radiant resistance. |

**Scaffolded spells:**

| Spell | Min Tier | Type | Mechanic | Mana (per tier) | Cooldown | Notes |
|---|---|---|---|---|---|---|
| Holy Fire | EXPERT | safe AoE | Radiant damage to enemies | TBD | 1 | Paladin's Fireball — safe AoE fits righteous precision |
| Wrath of God | GM | unsafe AoE | Massive radiant damage + BLINDED/STUNNED | TBD | 3 | Ultimate paladin nuke |

**Design identity**: righteous destruction, holy wrath. The smiter school. Counterplay: radiant resistance, Antimagic Field.

### Divine Revelation Spell Progression

Cleric/paladin knowledge domain. Mirrors Divination for divine casters. Core identity: divine sight, holy knowledge. Holy Insight and Holy Sight implemented.

**Implemented spells:**

| Spell | Min Tier | Type | Mechanic | Mana (per tier) | Cooldown | Notes |
|---|---|---|---|---|---|---|
| **Holy Insight** | BASIC | any | Identify clone + Divine Sight (alignment, evil/undead detection, divine aura) | 5/8/10/14/16 | 0 | **IMPLEMENTED** — Extends Identify base class. Shares `_identify_actor()`/`_identify_item()`. Adds divine-flavoured text + evil/undead detection at tier 2+. target_type="any". |
| **Holy Sight** | SKILLED | self | Divine mirror of True Sight with different tier order: SKILLED=traps, EXPERT=+INVISIBLE, MASTER=+HIDDEN. Duration 5/10/30/60 min. | 15/25/40/40 | 0 | **IMPLEMENTED** — NamedEffect HOLY_SIGHT + `db.holy_sight_tier`. `_can_see_hidden()` helper in room_base.py. Integration: room_base (3 checks), hidden_object, character trap detection. 23 tests. |

**Design identity**: divine knowledge, holy sight. The oracle school. Mirrors Divination.

### Divine Dominion Spell Progression

Cleric/paladin control domain. Core identity: command, compel, holy authority. Command and Hold implemented.

**Implemented spells:**

| Spell | Min Tier | Type | Mechanic | Mana (per tier) | Cooldown | Notes |
|---|---|---|---|---|---|---|
| **Command** | BASIC | single target (hostile) | `cast command <halt\|grovel\|drop\|flee> <target>`. Contested WIS vs WIS. Halt=STUNNED (1/2/2/3/3 rounds), Grovel=PRONE (1/1/2/2/3 rounds), Drop=force_drop_weapon, Flee=execute_cmd("flee") | 5/8/10/14/16 | 0 | **IMPLEMENTED** — `has_spell_arg`. Combat-only. HUGE+ immune. 33 tests. |
| **Hold** | EXPERT | single target (hostile) | Contested WIS vs WIS. PARALYSED with per-round WIS save (DC = caster's full total). Size gate scales: EXPERT=medium, MASTER=large, GM=huge. GARGANTUAN immune. Duration 3/4/5 rounds. | 28/39/49 | 1 | **IMPLEMENTED** — Renamed from hold_person. Same save-each-round pattern as Entangle. 24 tests. |

**Scaffolded spells:**

| Spell | Min Tier | Type | Mechanic | Mana (per tier) | Cooldown | Notes |
|---|---|---|---|---|---|---|
| Word of God | GM | unsafe AoE | Mass stun all enemies in room, no save first round | TBD | 3 | Ultimate cleric CC |

**Design identity**: authority, compulsion, divine command. The controller school. Counterplay: WIS saves, Antimagic Field.

### Nature Magic Spell Progression

Druid/ranger nature domain. Core identity: natural forces, entanglement, storms. Entangle and Call Lightning implemented.

**Implemented spells:**

| Spell | Min Tier | Type | Mechanic | Mana (per tier) | Cooldown | Notes |
|---|---|---|---|---|---|---|
| **Entangle** | BASIC | single target (hostile) | Contested WIS+mastery vs STR. ENTANGLED 1/2/3/4/5 rounds + save-each-round STR escape. Save DC = caster's full total (d20+WIS+mastery). | 5/8/10/14/16 | 0 | **IMPLEMENTED** — Uses NamedEffect ENTANGLED with save_dc/save_stat. Grants advantage to all enemies via on-apply callback. |
| **Call Lightning** | EXPERT | unsafe AoE | Lightning storm hits EVERYTHING in room (caster, allies, enemies). DEX save for half damage (DC = caster d20 + WIS + mastery). 6d6/9d6/12d6 lightning damage. | 21/32/42 | 1 | **IMPLEMENTED** — Same pattern as Fireball but 2d6 less per tier (nature trades damage for CC). WIS-based save DC (vs Fireball's INT). 14 tests. |

**Scaffolded spells:**

| Spell | Min Tier | Type | Mechanic | Mana (per tier) | Cooldown | Notes |
|---|---|---|---|---|---|---|
| Earthquake | GM | unsafe AoE | Massive damage to all in room + STUNNED/knockdown | TBD | 3 | Hits everything including caster and allies |

**Design identity**: natural forces, control, elemental power. The primal school. Counterplay: lightning resistance, Antimagic Field.

## Weapon Skill Architecture

Weapon mastery effects live **inside the weapon item subclasses**, not in a separate registry. The weapon object already exists, already has combat hooks, and already knows its type. No indirection needed.

### Hierarchy

```
WeaponNFTItem              ← base, combat hooks default to no-op, has_riposte() default False
├── LongswordNFTItem       ← DONE: parry + extra attack mastery path
├── RapierNFTItem          ← DONE: finesse + parry + riposte mastery path
├── GreatswordNFTItem      ← DONE: cleave AoE + executioner mastery path
├── BattleaxeNFTItem       ← DONE: nerfed cleave + stacking sunder mastery path
├── AxeNFTItem             ← DONE: reduced sunder + extra attack mastery path
├── DaggerNFTItem          ← DONE: finesse + extra attacks + crit threshold + dual-wield off-hand
├── ShortswordNFTItem      ← DONE: dual-wield specialist + light parry
├── BowNFTItem             ← DONE: contested slowing shot + extra attack mastery path
├── CrossbowNFTItem        ← DONE: knockback/prone mastery path (no extra attacks)
├── SlingNFTItem           ← DONE: concussive daze/stun mastery path
├── ShurikenNFTItem        ← DONE: multi-throw + crit scaling + consumable (hit→target, miss→room)
├── BlowgunNFTItem         ← DONE: poison DoT + paralysis mastery path
├── BolaNFTItem            ← DONE: entangle CC mastery path
├── SpearNFTItem           ← DONE: reach counter (counter-attack when allies hit) mastery path
├── StaffNFTItem           ← DONE: parry specialist (most parries, early parry advantage, riposte)
├── LanceNFTItem           ← DONE: mounted powerhouse (crit threshold, prone HUGE, extra attacks; nerfed on foot)
├── MaceNFTItem            ← DONE: anti-armor crush (bonus dmg vs high AC) + extra attack mastery path
├── ClubNFTItem            ← DONE: light stagger (hit penalty debuff) + extra attack mastery path
├── GreatclubNFTItem       ← DONE: heavy stagger (bigger penalty/duration), two-handed
├── HammerNFTItem          ← DONE: devastating blow (crit damage multiplier) mastery path
├── NinjatoNFTItem         ← DONE: pure offense — extra attacks + crit scaling + dual-wield. Ninja's signature sword (4 attacks at GM)
├── NunchakuNFTItem        ← DONE: contested DEX vs CON stun on hit, PRONE at MASTER+. Speed weapon with dual-wield
├── SaiNFTItem             ← DONE: disarm (unequips target weapon) + parry specialist + riposte at GM. Ninja defensive weapon
└── ...

UnarmedWeapon              ← DONE: pure Python singleton (NOT a DB object)
                             Mimics WeaponNFTItem interface. Returned by
                             get_weapon() when PC has no wielded weapon.
                             Stun/knockdown at SKILLED+.
```

### How It Works

Each weapon type subclass overrides mastery-related methods (`get_mastery_hit_bonus`, `get_parries_per_round`, `get_extra_attacks`, `get_offhand_attacks`, `get_offhand_hit_modifier`, `get_parry_advantage`, `has_riposte`, `get_mastery_crit_threshold_modifier`, `get_reach_counters_per_round`, `get_stun_checks_per_round`, `get_disarm_checks_per_round`) with mastery-tier lookup tables. The combat handler and `execute_attack()` call these methods generically — no weapon-specific branching in combat code.

```python
class LongswordNFTItem(WeaponNFTItem):
    def get_parries_per_round(self, wielder):
        mastery = self.get_wielder_mastery(wielder)
        return _LONGSWORD_PARRIES.get(mastery, 0)
```

### Mastery vs Individual Weapon Power

- **Mastery effects** = weapon TYPE skill (spear technique). Same across ALL spears — wooden spear, iron spear, Spear of the Gods all get the same mastery behavior
- **Individual weapon power** = prototype data (damage dice, wear_effects, stat bonuses). A Spear of the Gods has higher base damage, +hit bonuses, maybe fire damage — but that's prototype data, not mastery

```python
WOODEN_SPEAR = {
    "typeclass": "typeclasses.items.weapons.SpearNFTItem",
    "key": "wooden spear",
    "damage_dice": "1d6",
    "wear_effects": [],
}

SPEAR_OF_THE_GODS = {
    "typeclass": "typeclasses.items.weapons.SpearNFTItem",
    "key": "Spear of the Gods",
    "damage_dice": "2d8+3",
    "wear_effects": [
        {"type": "stat_bonus", "stat": "total_hit_bonus", "value": 3},
        {"type": "damage_resistance", "damage_type": "fire", "value": 15},
    ],
}
```

Both use `SpearNFTItem`, both get identical mastery effects. The prototype makes one a stick and the other legendary.

### Crit Threshold System

`base_crit_threshold` is an `AttributeProperty(20)` on BaseActor, modified by equipment on/off and spell/potion effects. `effective_crit_threshold` is a `@property` that computes `base_crit_threshold + weapon.get_mastery_crit_threshold_modifier(wielder)`. Combat uses `attacker.effective_crit_threshold` (not the old `crit_threshold` AttributeProperty, which was deleted). Only daggers currently modify crit threshold (-1 at EXPERT/MASTER, -2 at GM).

### Dual-Wield System

**`can_dual_wield` flag:** Boolean `AttributeProperty(False)` on `WeaponNFTItem`. Weapons with `can_dual_wield = True` (shortsword, dagger) can be equipped via `cmd_hold` into the HOLD slot in addition to `cmd_wield` into the WIELD slot. No new wearslot enum value — the weapon's wearslot stays WIELD. `cmd_hold` just checks the flag.

**Main hand mastery drives everything:**
- All mastery bonuses (hit, damage, crit threshold, parries, extra attacks) come from the **main hand weapon** (WIELD slot) only
- The off-hand weapon's mastery bonuses are **completely ignored** — no crit bonus, no extra attacks, no mastery hit/damage bonus from the held weapon
- Off-hand attacks only occur if the main hand weapon grants them via `get_offhand_attacks(wielder)` AND a `can_dual_wield` weapon is equipped in HOLD

**Enchantment bonuses from off-hand DO apply:**
- Magical bonuses (+1 hit, +1 damage, etc.) from the off-hand weapon's `wear_effects` apply to the **character's stats** (total_hit_bonus, total_damage_bonus, etc.) as they already do via the wear_effects system
- This means a held +1 dagger affects hit and damage for both main hand and off-hand attacks
- But mastery-based bonuses (from `get_mastery_*` methods) are main hand only

**Off-hand attack flow:**
- Main hand weapon's `get_offhand_attacks(wielder)` determines how many off-hand attacks (0 if no method or weapon doesn't grant them)
- Main hand weapon's `get_offhand_hit_modifier(wielder)` determines the off-hand hit penalty
- Off-hand attacks use the **off-hand weapon's damage dice** (`get_damage_roll()`) — so weapon quality matters for off-hand
- Off-hand attacks take durability from the off-hand weapon

**Dual-wield weapons:** Shortsword, Dagger (others may be added later).

### Finesse Weapons

Weapons that use `max(STR, DEX)` for hit/damage rolls. `is_finesse = AttributeProperty(False)` on WeaponNFTItem base class. Subclasses like RapierNFTItem set `is_finesse = True`. `effective_hit_bonus`/`effective_damage_bonus` on BaseActor check the wielded weapon's `is_finesse` flag: finesse = `max(STR, DEX)`, missile = DEX, melee = STR.

### Unarmed Weapon Singleton

Pure Python singleton (`typeclasses/items/weapons/unarmed_weapon.py`) — NOT an Evennia DB object. Mimics `WeaponNFTItem` interface so combat code treats unarmed PCs identically to armed ones. Stateless — all mutable state on wielder/combat_handler.

**`get_weapon(actor)`** helper in `combat_utils.py` returns: wielded weapon if equipped, `UNARMED` singleton if actor has wearslots but no weapon (PC boxing), or `None` for animal mobs (no wearslots, use `damage_dice` attribute). All combat code uses `get_weapon()` instead of direct `get_slot("WIELD")`.

**`force_drop_weapon(target, weapon=None)`** — shared disarm utility in `combat_utils.py`. Conditional behaviour: mobs/NPCs drop weapon to room floor (`move_to(location)`), player characters unequip to inventory only (no item loss). Guards: UnarmedWeapon immune, must have wielded weapon. Used by both Command spell (Drop word) and Sai weapon disarm. Returns `(bool, weapon_name)`.

**Mastery progression (UNSKILLED → GRANDMASTER):**
- Damage: 1 / 1d2 / 1d3 / 1d4 / 1d6 / 1d8
- Hit/damage bonus: standard MasteryLevel.bonus (-2/0/+2/+4/+6/+8)
- Extra attacks: 0/0/0/1/1/1

**Stun/Knockdown (SKILLED+):** On-hit contested roll (d20 + STR + mastery vs d20 + CON). Size-gated: HUGE+ immune. First hit per round only (first 2 at GM). Stun check count tracked via `stun_checks_remaining` on combat handler, reset each tick.
- SKILLED/EXPERT: win → STUNNED 1 round (lose action)
- MASTER: win by <5 → STUNNED 1 round, win by >=5 → PRONE 1 round (lose action + all enemies get 1 round advantage)
- GM: same as MASTER but 2 rounds duration (STUNNED/PRONE + advantage)

**Parry immunity:** Unarmed attacks cannot be parried (weapon-on-weapon only, gated by `isinstance(weapon, UnarmedWeapon)` check in `execute_attack()`).

**Multi-round skip:** `skip_actions` counter on combat handler replaces `skip_next_action` for stun/prone. Decrements each tick; condition cleared when counter reaches 0 via `_clear_stun_prone()`.

**Mob size:** `CombatMob.size` AttributeProperty (stored as string, e.g. `"medium"`, `"large"`). Default `"medium"`. DireWolf overrides to `"large"`. `_get_actor_size()` helper converts to `ActorSize` enum for comparison.

### Reaction System Architecture (Planned)

**Key architectural decision:** the combat reaction system (Shield spell on hit, Counter Spell, etc.) is NOT a separate system. Instead, weapon hooks serve as the universal reaction engine:

- **Unarmed weapon singleton:** every humanoid always has a "weapon" — real or a stateless `UnarmedWeapon` singleton. This means weapon hooks fire for ALL combatants, not just armed ones.
- **Base hooks handle universal reactions:** `WeaponNFTItem.at_wielder_hit()` checks if the defender has reaction spells configured (e.g. Shield). Weapon subclasses override hooks but **always call `super()`** to ensure universal reactions fire.
- **The 14 existing weapon hooks ARE the reaction pipeline.** No separate reaction system needed.
- **`spellconfig` menu command:** players configure reaction conditions via a template/menu UI. Single condition per rule only (no compound AND/OR). Storage: `db.reaction_rules` on character.
- **Reactions cost resources** (mana for casters, movement for martial) — not free.

## Race System (typeclasses/actors/races/)

Auto-collecting registry pattern. Each race is a frozen `RaceBase` dataclass instance in its own file. `__init__.py` imports all race files via `from ... import *`, scans the module namespace for `RaceBase` instances, and builds `RACE_REGISTRY`. A `Race` enum is auto-generated from registry keys (`Race.HUMAN`, `Race.DWARF`, `Race.ELF`).

**Key fields:** `key`, `display_name`, `description`, `ability_score_bonuses` (Dict[Ability, int]), `racial_weapon_proficiencies` (List[WeaponType]), `required_alignments`/`excluded_alignments` (List[Alignment]), `min_remort` (int).

**Methods:** `at_taking_race(character)` — applies ability score bonuses via `setattr`. `get_valid_alignments()` — returns filtered alignment list.

**Adding a new race:** Create `typeclasses/actors/races/my_race.py` with a `RaceBase` instance, add `from typeclasses.actors.races.my_race import *` to `__init__.py`. Done — `Race.MY_RACE` auto-generates.

**Lookup API:** `get_race(key)`, `list_races()`, `get_available_races(num_remorts)`, `Race` enum.

## Character Class System (typeclasses/actors/char_classes/)

Same auto-collecting registry pattern as races. Each class is a frozen `CharClassBase` dataclass in its own file. `CLASS_REGISTRY` and `CharClass` enum auto-generated.

**Key fields:** `key`, `display_name`, `description`, `prime_attribute` (Ability), `level_progression` (Dict[int, Dict] for levels 1-40), `multi_class_requirements` (Dict[Ability, int]), `min_remort`, `required_races`/`excluded_races` (List[str]), `required_alignments`/`excluded_alignments` (List[Alignment]), `class_cmdset` (Optional[Type[CmdSet]]).

**Level progression per level:** `weapon_skill_pts`, `class_skill_pts`, `general_skill_pts`, `hp_gain`, `mana_gain`, `move_gain`.

**Methods:**
- `char_can_take_class(character)` — checks race, alignment, remort requirements
- `at_char_first_gaining_class(character)` — adds cmdset, applies level 1 progression, inits `db.classes[key]`
- `at_gain_subsequent_level_in_class(character)` — increments level, applies progression, deducts `levels_to_spend`
- `get_valid_alignments()` — filtered alignment list

**Multiclassing:** Characters track classes in `db.classes = {"warrior": {"level": 1, ...}, "thief": {"level": 2, ...}}`. Stats stack additively.

**Lookup API:** `get_char_class(key)`, `list_char_classes()`, `get_available_char_classes(num_remorts)`, `CharClass` enum.

## NPC Architecture (typeclasses/actors/npc.py + npcs/)

NPCs share the full `BaseActor` infrastructure (ability scores, HP/mana/move, conditions, damage resistance, combat stats, effect system) plus `FungibleInventoryMixin` (gold and resources — classified as "WORLD" for blockchain service dispatch). They do NOT include other player-specific mixins (carrying capacity, wearslots, recipe book, spellbook, remort).

### CmdSet Visibility Pattern

NPCs use a two-tier system for command visibility:

1. **`call:true()` lock** on `BaseNPC.at_object_creation()` — required for Evennia's cmdhandler to merge the NPC's CmdSets into nearby characters' command pools. Without it, NPC commands are invisible to players. (`DefaultCharacter` does NOT set this lock by default.)

2. **`_EmptyNPCCmdSet`** — replaces the inherited character CmdSet as the default. Without this, player commands (stats, skills, look, etc.) from the NPC would leak into nearby characters' command pools.

Role-specific CmdSets (TrainerCmdSet, etc.) are added separately and contain only the NPC's interaction commands.

### Service NPCs vs Combat Mobs

- **Service NPCs** (trainers, shopkeepers, guildmasters): `call:true()` + `_EmptyNPCCmdSet` default + role CmdSet. Players interact via injected commands.
- **Combat mobs**: `CombatMob` subclass with `is_immortal=False`, AI state machine, combat handler, death + corpse. Use `_EmptyNPCCmdSet` + `CmdSetMobCombat` (combat commands only). AI decides WHEN to attack, `mob_attack()` calls `execute_cmd("attack target")` → same CmdAttack + CombatHandler path as players. On death, a `Corpse` is created in the room (immediately lootable, despawns after `corpse_despawn_delay` seconds — default 300). All mob contents, gold, and resources transfer to the corpse. Common mobs (`is_unique=False`) are deleted after death — `ZoneSpawnScript` handles respawning fresh objects. Unique/boss mobs use legacy delay-based `_respawn()`. Future LLM AI just swaps the decision-maker.

### NPC Hierarchy

```
BaseActor
└── BaseNPC                    ← is_pc=False, is_immortal=True, call:true(), _EmptyNPCCmdSet
    ├── TrainerNPC             ← trains skills/weapons, sells recipes
    ├── GuildmasterNPC         ← QuestGiverMixin + BaseNPC — guild info, quest mgmt, join class, advance level
    ├── ShopkeeperNPC          ← buys/sells resources via AMM pools (list/quote/accept/buy/sell)
    ├── LLMRoleplayNPC         ← LLMMixin + BaseNPC — LLM-powered dialogue
    │   ├── BartenderNPC       ← QuestGiverMixin + LLMRoleplayNPC — quest-aware bartender (Rowan)
    │   └── QuestGivingShopkeeper ← QuestGiverMixin + LLMRoleplayNPC + ShopkeeperCmdSet
    │       └── BakerNPC       ← quest-aware baker (Bron) with flour quest context
    ├── QuestGivingLLMTrainer  ← QuestGiverMixin + LLMMixin + TrainerNPC — quest + LLM + training
    │   └── OakwrightNPC       ← quest-aware carpenter (Master Oakwright) with timber quest context
    └── CombatMob              ← is_immortal=False, AI + combat, awards XP on kill (10 * level). Common mobs deleted on death (ZoneSpawnScript respawns). Unique mobs use legacy delay _respawn().
        ├── AggressiveMob      ← attacks players on sight (at_new_arrival + ai_wander scan). Used directly as prototype typeclass for sewer rats etc.
        │   ├── Wolf           ← L2, 12HP, 1d4. Attacks players + hunts rabbits, max 1 per room
        │   ├── DireWolf       ← L3, 30HP, 2d6. Attacks players, 25% dodge, retreats when wounded
        │   ├── CellarRat      ← L1, 4HP, 1d2. Dungeon mob, no wander
        │   ├── Kobold         ← L2, 14HP, 1d4. Pack courage — fights with allies, flees solo, fights when cornered
        │   ├── KoboldChieftain ← L3, 28HP, 1d6+1. Unique boss, fixed position, 20% dodge, rally cry at 50% HP
        │   ├── Gnoll          ← L4, 40HP, 1d6+2. Rampage — instant free attack on kill, max 2/room, flees at 25%
        │   │   └── GnollWarlord ← L6, 75HP, 2d6+3. Unique boss, inherits Rampage, never flees, 20% dodge
        └── Rabbit             ← flees threats, no combat
```

### TrainerNPC + Training System

TrainerNPC teaches skills and weapons to characters. Configuration per instance:

| Attribute | Type | Purpose |
|---|---|---|
| `trainable_skills` | `list[str]` | Skill keys this trainer teaches |
| `trainable_weapons` | `list[str]` | WeaponType value strings this trainer teaches |
| `trainer_class` | `str` | Class key (determines skill point pool) |
| `trainer_masteries` | `dict` | `{skill_key: mastery_int}` — max teachable level + success chance |
| `recipes_for_sale` | `dict` | `{recipe_key: gold_cost}` for recipe purchases |

**Training flow:**
1. Validate skill/weapon access via enum-driven lookup (`_CLASS_MAPPINGS_LOOKUP` for skills, `_WEAPON_CLASSES` for weapons)
2. Check trainer mastery > character's current mastery
3. Calculate gold cost with CHA modifier discount/surcharge: `final = max(1, round(base * (1 - cha_mod * 0.05)))`
4. Y/N confirmation showing cost, success chance, training time
5. Deduct gold (non-refundable), start progress bar with `delay()` chain
6. On completion: d100 roll vs success chance based on mastery gap
   - **Success:** deduct skill points, advance mastery level
   - **Failure:** gold lost, skill points kept, 1-hour cooldown with this trainer

**Commands (injected via TrainerCmdSet):** `train` (list/train skills), `buy recipe` (list/buy recipes)

**Key files:** `typeclasses/actors/npcs/trainer.py`, `commands/npc_cmds/cmdset_trainer.py`, `tests/command_tests/test_cmd_train.py` (55 tests)

### ShopkeeperNPC + AMM Trading

ShopkeeperNPC buys and sells resources with prices driven by live XRPL AMM pools. Configuration per instance:

| Attribute | Type | Purpose |
|---|---|---|
| `tradeable_resources` | `list[int]` | Resource IDs this shop trades (e.g. `[1, 2, 3]` for wheat, flour, bread) |
| `shop_name` | `str` | Display name shown in list/quote output |

**Commands (injected via ShopkeeperCmdSet):**
- `list` / `browse` — batch-queries AMM pools for all tradeable resources, shows buy/sell prices per unit
- `quote buy/sell <amount> <item>` — gets live AMM price, stores pending quote on `caller.ndb.pending_quote`
- `accept` — executes the pending quote (validates player still in room, still has funds)
- `buy <amount> <item>` — instant buy at current market price (no quote step)
- `sell <amount> <item>` / `sell all <item>` — instant sell at current market price

**Pricing:** Constant product formula (x * y = k) with AMM trading fee. Buy prices ceil-rounded, sell prices floor-rounded — all gold amounts are integers. Favorable slippage goes to the game. See **design/ECONOMY.md** for the full AMM trade accounting model (6-operation dual-side accounting, rounding dust profit, buy/sell margin mechanics).

**Superuser commands:**
- `amm_check` / `amm_check <resource>` — query AMM pool states (reserves, fees). Read-only, no trades
- `reconcile` / `recon` — compare vault on-chain balances vs game-state DB per currency. Shows Reserve, Distributed, Sink, Delta
- `sync_reserves` — recalculate RESERVE from on-chain vault state: `RESERVE = on_chain - (SPAWNED + ACCOUNT + CHARACTER + SINK)`. Always run `reconcile` first
- `sync_nfts` — sync on-chain NFTs with game DB (placeholder → real NFToken IDs)

**Integration test (manual, testnet only):**
```
evennia test_amm_trades           # test all detected pools
evennia test_amm_trades wheat     # test only wheat pool
evennia test_amm_trades --dry-run # query pools, no trades
```
Runs buy/sell trades at [1, 5, 10, 50, 100] units per pool, verifies margin >= 0 on every trade, cleans up test data afterward.

**Key files:** `typeclasses/actors/npcs/shopkeeper.py`, `commands/npc_cmds/cmdset_shopkeeper.py`, `blockchain/xrpl/services/amm.py`, `blockchain/xrpl/xrpl_amm.py`, `commands/account_cmds/cmd_amm_check.py`, `commands/account_cmds/cmd_reconcile.py`, `blockchain/xrpl/management/commands/test_amm_trades.py`, `tests/xrpl_tests/test_amm_service.py` (17 tests), `tests/command_tests/test_cmd_shopkeeper.py` (19 tests)

### QuestGiverMixin (typeclasses/mixins/quest_giver.py)

Shared mixin for any NPC that offers quests. Provides:
- `quest_key` AttributeProperty — the quest this NPC offers
- `CmdNPCQuest` command (`quest` / `quest accept` / `quest abandon`) — view, accept, abandon, turn-in via `progress()` on view
- `QuestGiverCmdSet` — Union-merged cmdset with the quest command
- `get_quest_completion_message(caller, quest)` hook — override for custom completion text

Used by: GuildmasterNPC, BartenderNPC, QuestGivingShopkeeper (and its subclass BakerNPC).

### GuildmasterNPC + Quest System

GuildmasterNPC manages multiclassing and class level advancement. Uses QuestGiverMixin for quest commands. The `quest_key` property delegates to `multi_class_quest_key` for backward compatibility.

**GuildmasterNPC attributes** (`typeclasses/actors/npcs/guildmaster.py`):

| Attribute | Type | Purpose |
|---|---|---|
| `guild_class` | `str` | Class key this guild serves (e.g. `"warrior"`) |
| `multi_class_quest_key` | `str\|None` | Quest required before joining as multiclass |
| `max_advance_level` | `int` | Highest class level this guildmaster can grant (default 40) |
| `next_guildmaster_hint` | `str\|None` | RP flavour text pointing to the next guildmaster |

**Commands:**
- `quest` / `quest accept` / `quest abandon` — via QuestGiverMixin (shared across all quest-giving NPCs)
- `guild` — shows guild info, class description, requirements, character progress, quest status (GuildmasterCmdSet)
- `join` — join guild class with full requirement checks (race/alignment/remort/ability/quest) (GuildmasterCmdSet)
- `advance` — spend pending level, guildmaster-specific level cap with RP redirect message (GuildmasterCmdSet)

**Level cap system:** Each guildmaster has a `max_advance_level`. When a character reaches it, they get an RP message directing them to the next guildmaster (via `next_guildmaster_hint`). Creates natural world progression — starter guildmasters cap at low levels, forcing exploration.

**Key files:** `typeclasses/actors/npcs/guildmaster.py`, `commands/npc_cmds/cmdset_guildmaster.py`, `typeclasses/mixins/quest_giver.py`, `tests/command_tests/test_quests.py`

### BartenderNPC (typeclasses/actors/npcs/bartender_npc.py)

Quest-aware bartender for the Harvest Moon Inn. Uses QuestGiverMixin (quest command for rat_cellar quest) + LLMRoleplayNPC (LLM dialogue). Injects `{quest_context}` into the LLM prompt based on the player's tutorial and quest state.

**State machine** (level gate at 3): new player → tutorial/quest pitch → quest active → tutorial suggest → generic bartender.

**Key files:** `typeclasses/actors/npcs/bartender_npc.py`, `llm/prompts/bartender.md`, `tests/typeclass_tests/test_bartender_npc.py`

### QuestGivingShopkeeper + BakerNPC

QuestGivingShopkeeper combines QuestGiverMixin + LLMRoleplayNPC + ShopkeeperCmdSet. Provides LLM dialogue with quest-aware context injection + AMM shop commands. Injects `{quest_context}` and `{shop_commands}` template variables into the LLM prompt.

BakerNPC is a QuestGivingShopkeeper subclass for Bron at the Goldencrust Bakery. Trades flour (ID 2) and bread (ID 3). Quest-aware prompt states: pitch → active → grateful → generic (level gate at 3).

**Key files:** `typeclasses/actors/npcs/quest_giving_shopkeeper.py`, `typeclasses/actors/npcs/baker_npc.py`, `llm/prompts/baker.md`, `tests/typeclass_tests/test_quest_giving_shopkeeper.py`, `tests/typeclass_tests/test_quest_giver_mixin.py`

### Quest System (world/quests/)

Step-based quest engine with registry pattern (same as spells/races/classes).

**Architecture:**
- `FCMQuest` base class (`world/quests/base_quest.py`) — `step_<name>()` methods, `progress()` dispatches to current step, status tracking (active/completed/failed), help text per step
- `FCMQuestHandler` (`world/quests/quest_handler.py`) — lazy_property on FCMCharacter, stores quest state in Evennia attributes (category `fcm_quests`). API: `add()`, `remove()`, `get()`, `has()`, `is_completed()`, `active()`, `completed()`, `all()`
- `QuestTagMixin` on rooms — `quest_tags` AttributeProperty + `fire_quest_event()` for location-triggered progression
- Quest registry with `@register_quest` decorator, `get_quest()` lookup, auto-imports from `world.quests.guild`

**Quest templates** (`world/quests/templates/`): CollectQuest, VisitQuest, MultiStepQuest — reusable bases for common patterns.

**Warrior Initiation** (`world/quests/guild/warrior_initiation.py`): Rat cellar check quest. Sergeant Grimjaw sends player to clear rats from Harvest Moon cellar. If player already completed `rat_cellar` quest, instant induction on accept. Otherwise, `step_clear_rats` checks on return. Acceptance gated on: levels_to_spend > 0, not already warrior, race/alignment/remort/multiclass requirements. On completion, deducts 1 level, auto-grants warrior level 1. reward_xp=100. BartenderNPC has a level gate bypass: players with active `warrior_initiation` quest can access Rowan's rat quest pitch even above level 3.

**Thief Initiation** (`world/quests/guild/thief_initiation.py`): VisitQuest — reach the Cave of Trials boss room ("BINGO!"). Boss room has `quest_tags=["thief_initiation"]`, triggering `fire_quest_event(char, "enter_room")` on entry. On completion, auto-grants thief level 1.

**Mage Initiation** (`world/quests/guild/mage_initiation.py`): Single-step resource delivery (1 Ruby, ID 33). On completion, auto-grants mage level 1. Guildmaster is turn-in point.

**Cleric Initiation** (`world/quests/guild/cleric_initiation.py`): "Feed the Hungry" — Brother Aldric sends player to give bread to Old Silas (beggar) in Beggar's Alley behind the temple. Beggar's Alley has `quest_tags=["cleric_initiation"]`, triggering `step_feed_beggar(event_type="enter_room")` on entry. Step checks for bread (resource ID 3) in inventory — if present, consumes it and completes. If not, shows hint. On completion, auto-grants cleric level 1. Evil alignments excluded.

**Rat Cellar** (`world/quests/rat_cellar.py`): First combat quest. key="rat_cellar", quest_type="main", reward_xp=100, reward_gold=10, repeatable=False. Accepted via `quest accept` at Rowan (BartenderNPC). QuestDungeonTriggerExit gates cellar entrance: quest active → dungeon instance, not accepted or completed → ordinary cellar (fallback room). Single step `step_clear_cellar` completes on `boss_killed` event (fired by RatKing.die()). No-death: defeated players teleport to inn at 1 HP, bartender heals them (RoomInn._check_rat_quest_defeat — gated on active rat_cellar quest + hp <= 1).

**Baker's Flour** (`world/quests/bakers_flour.py`): Starter delivery quest. key="bakers_flour", quest_type="side", reward_xp=100, reward_gold=4, repeatable=False. Accepted via `quest accept` at Bron (BakerNPC). Single step `step_deliver_flour` — bring 3 Flour (resource ID 2) to Bron. Turn-in via `quest` command at Bron (progress() checks inventory, consumes flour via `return_resource_to_sink`, completes). Story: Bron's flour delivery from Goldwheat Farm hasn't arrived.

**Oakwright's Timber** (`world/quests/oakwright_timber.py`): Starter delivery quest. key="oakwright_timber", quest_type="side", reward_xp=100, reward_gold=5, repeatable=False. Accepted via `quest accept` at Master Oakwright (OakwrightNPC). Single step `step_deliver_timber` — bring 4 Timber (resource ID 7) to Oakwright. Same turn-in pattern as Baker's Flour. Story: Oakwright's timber supplier hasn't delivered.

**Character command:** `CmdQuests` (key=`"quests"`, aliases=`["quest log", "questlog"]`) — view quest log, show details for specific quests. No conflict with `CmdNPCQuest` (key=`"quest"`) from QuestGiverMixin.

**Adding a new quest:**
1. Create `world/quests/guild/my_quest.py` (or appropriate subfolder)
2. Decorate with `@register_quest`
3. Define `key`, `name`, `desc`, `start_step`, step methods
4. Import in the subfolder's `__init__.py`

**87 tests** in `tests/command_tests/test_quests.py`.

## Coding Conventions

- **Prefer enums over raw strings** for validation and typo prevention. When a field references a fixed set of values (ability scores, weapon types, alignments, damage types, skills, etc.), use the corresponding enum rather than raw strings. Examples: `WeaponType.BATTLEAXE` not `"battleaxe"`, `Ability.STR` not `"strength"`, `skills.STEALTH.value` not `"stealth"`. Enum `.value` can be extracted when writing to storage (e.g. `weapon.value` for dict keys). Skill commands should set `skill = skills.ENUM.value` (not a raw string) so renaming a skill in the enum automatically propagates.

## Future Roadmap

- **More spells** — Evocation complete at BASIC/SKILLED/EXPERT/MASTER/GM tiers (Flame Burst moved to SKILLED). Remaining evocation: Lightning Bolt (SKILLED), Chain Lightning (EXPERT). Cleric/paladin domains planned with BASIC/EXPERT/GM spells: Divine Healing (Purify, Mass Heal, Death Ward), Divine Protection (Sanctuary, Holy Aura, Divine Aegis), Divine Judgement (paladin only — Smite, Holy Fire, Wrath of God), Divine Revelation (Holy Insight), Divine Dominion (Command, Hold Person, Word of God). Nature Magic for druid/ranger: Entangle, Call Lightning, Earthquake. `spellinfo` command planned (structure ready — description/mechanics fields on all spells).
- **Weapon mastery effects** — ALL 24 weapon types DONE (was 25 — katana + wakizashi merged into ninjatō). Every weapon has unique mastery mechanics.
- **Combat expansion** — multi-attack (attacks_per_round > 1), combat skill commands (bash, assassinate, etc.), spell casting in combat, ranged vs melee distance checks, combat prompt/status display, LLM-driven mob AI
- **Blockchain sync service** — built as `FCM-Blockchain-Sync-Service/` (standalone Django app). Polls `eth_getLogs` for events on all five contracts, updates `GoldChainState` and `ResourceChainState` (sole writer for these tables), and stamps reconciliation ledger (`GoldChainTransferLog`, `ResourceChainTransferLog`) with `chain_adjusted=True`. Game-side deposit/withdraw methods stamp `game_adjusted=True`. 46 tests. See `FCM-Blockchain-Sync-Service/CLAUDE.md` for details.
- **More recipes** — expand crafting recipes across all skills and mastery tiers (bronze weapons, steel weapons, more jewellery, etc.)
- **NPC system** — BaseNPC + TrainerNPC + GuildmasterNPC complete. QuestGiverMixin extracts quest accept/abandon/view/turn-in into a shared mixin used by GuildmasterNPC, BartenderNPC, and QuestGivingShopkeeper. LLM-powered NPCs: BartenderNPC (Rowan, quest-aware with per-player prompt states), BakerNPC (Bron, QuestGivingShopkeeper subclass with AMM shop + quest context). ShopkeeperNPC with full AMM integration (list/quote/accept/buy/sell commands). CombatMob with AI state machine, combat handler integration, corpse-on-death, and respawn implemented (Rabbit, Wolf, DireWolf). Mobs use same command interface as players. Item/resource drops handled by separate spawn scripts (not traditional loot tables). Future: XP rewards, LLM AI (zero refactoring needed — just swap decision-maker).
- **NPC market maker AMM** — resource trading via XRPL AMM liquidity pools (ShopkeeperNPC). Quote→accept flow, instant buy/sell, "sell all". OfferCreate swap execution with 6-operation accounting. Superuser tools: `amm_check`, `reconcile`, `test_amm_trades`. See **design/ECONOMY.md** for economic design (pricing model, tracker tokens, market tiers, spawn algorithms). 17 AMM service + 19 shopkeeper command tests.
- **Remort system** — perk choices on remort (extra point buy, bonus HP/Mana/Move) and content gating via `min_remorts`. Infrastructure exists (num_remorts on character, min_remorts on classes/items/races) but the actual remort flow is not yet implemented.
