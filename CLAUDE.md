# CLAUDE.md

> **THIS FILE is for TECHNICAL details only** — architecture, code patterns, APIs, implementation guidelines, and development workflow. Detailed system designs live in `design/` docs: **COMBAT_SYSTEM.md** (combat, weapons, stealth), **EFFECTS_SYSTEM.md** (effects, conditions, damage), **SPELL_SKILL_DESIGN.md** (spells, crafting recipes), **CRAFTING_SYSTEM.md** (crafting/processing architecture), **NPC_QUEST_SYSTEM.md** (NPCs, quests), **INVENTORY_EQUIPMENT.md** (items, equipment, weight), **ECONOMY.md** (pricing, markets, spawning), **WORLD.md** (lore, zones, creative), **COMBAT_AI_MEMORY.md** (combat AI memory, strategy bot, adaptive mob behavior), **LORE_MEMORY.md** (embedded world knowledge for NPCs). Do not put world building or economic design content here.

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Game code for **FullCircleMUD** — a text-based MUD built on the Evennia framework (Python/Django) with real blockchain item ownership. This folder (`src/game/`) is the Evennia game module and lives inside `src/` (the Evennia game directory).

Domain: **fcmud.world**. Chain: **XRPL** (primary). Legacy Polygon contracts deployed but no longer in active use.

## Evennia Project Structure

```
FCM/src/                        ← run `evennia start` from here
├── game/                       ← THIS repo — all game code
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
│   ├── combat/                   ← combat system (handler, attack resolution, side detection, reactive_spells, height_utils)
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
│   │   │   ├── ai_handler.py         ← AIHandler state machine + StateMachineAIMixin (alias AIMixin)
│   │   │   ├── mob.py                ← CombatMob(CombatMixin, StateMachineAIMixin, BaseNPC) — convenience class for fightable mobs
│   │   │   ├── npcs/                 ← NPC subtypes (TrainerNPC, GuildmasterNPC, ShopkeeperNPC [scaffolded], TutorialGuideNPC, LLMRoleplayNPC, BartenderNPC, QuestGivingShopkeeper, BakerNPC)
│   │   │   ├── mobs/                 ← mob subtypes (AggressiveMob, Rabbit, Wolf, DireWolf, CellarRat, Kobold, KoboldChieftain, Gnoll, GnollWarlord, Crow, TrainingDummy)
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
│   │   │   ├── combat_mixin.py       ← CombatMixin (combat handler access, enter/exit combat, initiate_attack)
│   │   │   ├── height_aware_mixin.py ← HeightAwareMixin (room_vertical_position — composed into BaseActor, Corpse, BaseNFTItem, WorldFixture, WorldItem)
│   │   │   ├── aggressive_mixin.py   ← AggressiveMixin (aggro on sight, height matching, wander scan)
│   │   │   ├── flying_mixin.py       ← FlyingMixin (innate flight, Condition.FLY, ascend/descend)
│   │   │   ├── swimming_mixin.py     ← SwimmingMixin (innate swimming, Condition.WATER_BREATHING, dive/surface)
│   │   │   ├── innate_ranged_mixin.py ← InnateRangedMixin (mob_weapon_type="missile", cross-height attacks)
│   │   │   ├── mob_behaviours/        ← reusable mob behavior mixins (PackCourageMixin, RampageMixin, TacticalDodgeMixin)
│   │   │   ├── climbable_mixin.py    ← ClimbableMixin (climbable_heights, climb_dc — data mixin for climbable fixtures)
│   │   │   ├── switch_mixin.py      ← SwitchMixin (toggle on/off — levers, buttons, valves; at_activate/at_deactivate hooks)
│   │   │   └── wearslots/             ← BaseWearslotsMixin, HumanoidWearslotsMixin, DogWearslotsMixin
│   │   ├── world_objects/
│   │   │   ├── corpse.py             ← Corpse (dropped on death, loot command, decay timers)
│   │   │   ├── climbable_fixture.py  ← ClimbableFixture(ClimbableMixin, WorldFixture) — drainpipes, ladders, ropes, trees
│   │   │   └── switch_fixture.py    ← SwitchFixture(SwitchMixin, WorldFixture) — levers, buttons, valves
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
# Activate venv (from FCM/src/)
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

**IMPORTANT:** Tests must be run from inside the `FCM/src/game/` folder, not from `FCM/src/`. Use `--settings settings` so Evennia picks up the project's `server/conf/settings.py` rather than the default Evennia settings. Import paths in tests are relative to `FCM/src/game/`.

**IMPORTANT:** When running the full test suite, **always capture output to a temp file** so it can be examined without truncation. The suite takes ~2.5 hours — do not rely on piping through `tail` or terminal output limits which will truncate failure tracebacks and waste the entire run.

```bash
# Full suite — capture to file for review
evennia test --settings settings tests 2>&1 | tee /tmp/test_results.txt

# Then examine failures:
grep -A 10 "FAIL:\|ERROR:" /tmp/test_results.txt
```

```bash
# From FCM/src/game/ (with venv activated):

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
| **Character** | stats, score, skills, fly, swim, climb, where, hunger, languages (lang), weight, quests, remort, setdesc |
| **Combat** | attack, flee, dodge, assist, bash, pummel, stab, assassinate, frenzy, turn, protect, taunt, mock, consider |
| **Communication** | say (alias: talk), shout, whisper, pose, who |
| **Crafting** | learn, recipes, repair (skill) + room-specific: craft/forge/carve/sew/brew/enchant, available, process/mill/bake/smelt/saw/tan/weave, rates |
| **Exploration** | build, chart, sail, explore |
| **General** | look (aliases: examine, exam), scan, diagnose, exits, go, pull/push/turn/flip |
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

> **Resource types:** See `blockchain/xrpl/models.py` `CurrencyType` for the canonical resource ID → currency code mapping. See `design/ECONOMY.md` for resource roles and economic design.

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

## Inventory & Equipment System

> **See `design/INVENTORY_EQUIPMENT.md`** for the authoritative reference on: inventory storage (items in `contents`, fungibles as attributes), equipment (wearslots, wear effects, equip flow), carrying capacity (nuclear weight recalculate), NFT ownership model (states, transitions, container cascading), data-driven item effects (`wear_effects`), ItemRestrictionMixin, and the nuclear recalculate systems (`_recalculate_stats()`, `_recalculate_item_weight()`, `_at_balance_changed()`).
>
> Key mixins/classes covered there: `FungibleInventoryMixin`, `BaseWearslotsMixin`, `HumanoidWearslotsMixin`, `CarryingCapacityMixin`, `BaseNFTItem`, `WearableNFTItem`, `WeaponNFTItem`, `HoldableNFTItem`, `ItemRestrictionMixin`.

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

> **Design:** See `design/ECONOMY.md` § SINK Location for the economic rationale and reallocation rules.

**Consumption:** `return_gold_to_sink()` / `return_resource_to_sink()` — for fees, crafting, eating, junking, AMM dust. Routes to SINK.
**Cleanup:** `return_gold_to_reserve()` / `return_resource_to_reserve()` — for corpse decay, dungeon teardown, world rebuild. Routes to RESERVE.

**Reallocation:** A daily `ReallocationServiceScript` drains all SINK → RESERVE (100% for now). Gold burn to issuer deferred until vault signing is sorted.

**Admin commands:**
- `reconcile` — read-only audit showing Currency, On-Chain, Reserve, Distributed, Sink, Delta (delta should be 0)
- `sync_reserves` — recalculates RESERVE from: `on_chain - (SPAWNED + ACCOUNT + CHARACTER + SINK)`. Always run `reconcile` first.

**Query total in SINK:** `FungibleGameState.objects.filter(location="SINK").aggregate(Sum('balance'))['balance__sum']`

## Economy Telemetry

> **Design:** See `design/TELEMETRY.md` for metric definitions and snapshot design. See `design/ECONOMY.md` for how telemetry drives spawn rates.

Hourly aggregation system that snapshots key economic metrics for the spawn algorithm and admin monitoring. Raw data already exists in transfer logs and game state tables — the telemetry system pre-computes summaries.

**Models:** `PlayerSession` (login/logout tracking), `EconomySnapshot` (global hourly metrics: players online, gold circulation/reserve/sinks, AMM trades, imports/exports), `ResourceSnapshot` (per-resource hourly: circulation by location, velocity, AMM prices).

**Service:** `TelemetryService` — `record_session_start()` / `record_session_end()` called from character puppet/unpuppet hooks. `take_snapshot()` called hourly by `TelemetryAggregatorScript` global script. `close_stale_sessions()` called on server boot for crash recovery.

**Admin command:** `economy` (superuser, OOC) — shows latest snapshot. `economy <resource>` for detailed single-resource history.

**Velocity categories:** produced (craft_output + pickup), consumed (craft_input), traded (amm_buy + amm_sell), exported (withdraw_to_chain), imported (deposit_from_chain).

## Unified Spawn System

> **Source of truth:** See `design/UNIFIED_ITEM_SPAWN_SYSTEM.md` for the full Calculator + Distributor architecture — resource two-factor algorithm, gold three-factor algorithm, knowledge saturation model, rare NFT POC, tag-driven distribution, drip-feed mechanics, quest debt integration, and implementation file paths.

**Implementation:** `blockchain/xrpl/services/spawn/` — `SpawnService` orchestrator, 4 calculators (Resource, Gold, Knowledge, RareNFT), 2 distributor families (Fungible, NFT). Hourly cycle via `UnifiedSpawnScript`. Daily saturation snapshots via `NFTSaturationScript` (86400s interval) stored in `SaturationSnapshot` model. 174+ tests in `tests/spawn_tests/`.

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

## CRITICAL: Room/Object Lookup Convention — Always Filter by District Tag

**Evennia's `db_key` is NOT globally unique.** Multiple rooms/objects across different zones can share the same key (e.g. "The Vault" in the sewers AND in a future mine dungeon). The unique identifier is the `dbref` (auto-incrementing integer, e.g. `#247`).

**When searching for rooms or objects by name in code, ALWAYS filter by district or zone tag:**

```python
# WRONG — may return objects from multiple zones
ObjectDB.objects.filter(db_key="The Vault")

# RIGHT — scoped to a specific district
ObjectDB.objects.filter(
    db_key="The Vault",
    db_tags__db_key="millholm_sewers",
    db_tags__db_category="district",
)

# ALSO RIGHT — search within a known room's contents
for obj in room.contents:
    if obj.key == "a heavy iron chest":
        ...
```

**Alternatives for guaranteed unique lookup:**
- Store the `dbref` (`.id`) at build time and look up by ID later
- Use a unique tag (e.g. `tags.add("thief_gauntlet_chest", category="quest_fixture")`)
- Search within a known room's `.contents` (already scoped)

This convention applies to all game code — quests, zone builders, fixtures, NPC spawners, and any system that needs to find a specific room or object.

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
- Full inventory & equipment system — see `design/INVENTORY_EQUIPMENT.md` for details (FungibleInventoryMixin, BaseNFTItem, wearslots, CarryingCapacityMixin, nuclear recalculate, NFT ownership)
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
- DamageResistanceMixin: integer percentage resistances/vulnerabilities, clamped to [-75, 75] on read, reusable across any typeclass
- DurabilityMixin: `max_durability`, `durability`, `repairable` AttributeProperties on all item types, `repair_to_full()` method
- Worn item guards: drop/give/deposit/junk reject equipped items via `exclude_worn` on character search
- Score command — consolidated character sheet in a 4-column boxed layout (~16 lines). Header: name, race, alignment, classes, level, XP. Body: vitals (HP/MP/MV with color-coded health), ability scores (current + base), combat modifiers (AC, crit, init, att/round), resistances/vulnerabilities. Footer: active conditions, levels-to-spend hint. Hand-built f-strings with `_pad()` helper for color-code-aware alignment. 23 tests.
- Stats command — focused "base vs effective" breakdown showing how equipment, spells, and ability modifiers change stats. Three sections: Ability Scores (base, effective, modifier), Vitals (HP/Mana/Move max with CON breakdown), Combat (AC, crit, initiative with DEX breakdown, attacks/round). Boxed layout matching score style. 14 tests.
- RoomInn typeclass with stew/ale/menu commands
- 36 resource types seeded (basic crafting chains, alchemy herbs, metals/ores/alloys, gems, coal)
- EffectsManagerMixin: unified effect system replacing ConditionsMixin. Three layers: (1) ref-counted condition flags, (2) stat effect dispatch (backward compat, mostly superseded by nuclear recalculate), (3) named effects with anti-stacking, messaging, and lifecycle management (combat_rounds/seconds/permanent). **Nuclear recalculate pattern:** `_recalculate_stats()` on BaseActor rebuilds all Tier 2 numeric stats from scratch (base → racial → equipment → active buffs) on every equip/unequip/buff change. Conditions remain incremental with ref-counting. **Effect Registry** on NamedEffect enum (`effect_condition`, `effect_duration_type` properties) — single source of truth for each effect's associated condition and duration type. **Convenience methods** (`apply_stunned()`, `apply_invisible()`, `apply_shield_buff()`, etc.) are the preferred API — each method is the single entry point for its effect, internally calling `apply_named_effect()` with registry auto-fill. **`break_effect()`** generic method for force-removing effects without end messages. `apply_named_effect()` accepts NamedEffect enum directly and uses `_UNSET` sentinel for auto-fill from registry. Combat handler integration: `tick_combat_round()` + `clear_combat_effects()`. NamedEffect enum validates keys + provides message registry. Condition enum trimmed to 12 active flags. Unsorted effects list in `named_effect.py` forces classification before implementation. MANDATORY for all new effects. **Admin tool:** `recalc [target]` command forces nuclear recalculate on any character (for debugging stat desync).
- **PlayerPreferencesMixin** (`typeclasses/mixins/player_preferences.py`): data-driven toggleable boolean preferences for player characters. `PREFERENCES` registry dict maps user-facing names to `AttributeProperty` attrs + descriptions. `CmdToggle` (`toggle`) reads the registry automatically — no command changes needed to add new preferences. **Gated preferences:** optional `gate` callable + `gate_fail` message on registry entries for conditional prefs (e.g. reactive spells requiring memorisation). Gate fails → pref hidden from display and valid options list. Return convention: `toggle_preference()` → `(key, new_val)` on success, `(None, fail_msg)` on gate fail, `None` if unknown. Current preferences: `afk` (AFK status), `brief` (skip room descs), `prompt` (text prompt after commands), `autoexit` (show exits), `nofollow` (block followers), `smite` (reactive spell, gated), `shield` (reactive spell, gated). To add a new preference: (1) add `AttributeProperty` on the mixin, (2) add `PREFERENCES` entry, (3) optionally add `gate`/`gate_fail`.
- AFK system: `afk` command or `toggle afk` to flag yourself as away. "(AFK)" shown in room descriptions and `who` list. Targeted `say to` and `whisper` notify sender that target is AFK. Moving while AFK shows a reminder but does not auto-clear.
- Text prompt system: customisable status prompt after every command via `msg(prompt=...)`. Token-based format string (`%h/%H` HP, `%m/%M` Mana, `%v/%V` Move, `%g` Gold, `%x` XP, `%l` Level). Default: `"%hH %mM %vV > "`. `prompt` command to customise, `toggle prompt` to disable. Coexists with OOB vitals for webclient.
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
- FLY condition gating: `fly up` requires FLY condition, fall damage (10 HP/level) on FLY removal while airborne. Fall safety: if a ClimbableMixin fixture in the room supports the character's current height, character slides down safely instead of taking damage.
- Climbable fixtures: `ClimbableFixture(ClimbableMixin, WorldFixture)` — drainpipes, ladders, ropes, trees. `climbable_heights` set defines supported heights (e.g. {0, 1}), `climb_dc` optional DEX check (0=auto). `CmdClimb` (`climb up/down <target>`) changes `room_vertical_position` within supported heights without requiring FLY. Enables height-routed exits for non-flying characters. First instance: drainpipe in Back Alley behind Artisan's Way, leading to rooftop entry point.
- Underwater breath timer: BreathTimerScript (CON-based duration: `30 + CON_mod * 15` seconds, min 10s), drowning damage when expired, WATER_BREATHING bypasses entirely
- Death system: `die()` creates corpse, strips items/gold/resources to corpse, stops combat handler, enters purgatory (60s timer or 50g early release), 5% XP penalty, HP reset to 1. Drowning and starvation trigger death. Two separate location bindings: `respawn_location` (death respawn, set by cemetery `bind`, default Millholm Cemetery) and `home` (future recall, default Harvest Moon Inn). Death fallback chain: `respawn_location → home → Limbo`. Defeat (non-lethal) uses `defeat_destination → home`. `at_post_puppet` backfills both defaults and reschedules purgatory timer if stuck.
- Corpse with loot/loot all commands and decay timers
- Cemetery rooms with `bind` command — sets character's `respawn_location` as death respawn point. Configurable `bind_cost` (default 1 gold) on RoomCemetery.
- XP levelling: `highest_xp_level_earned` guard prevents duplicate level rewards after death XP loss. Level 40 cap prevents infinite recursion.
- NPC hierarchy: BaseNPC → TrainerNPC (training system complete), GuildmasterNPC (QuestGiverMixin + BaseNPC, quest system + level caps), ShopkeeperNPC (AMM shop commands), QuestGivingShopkeeper (QuestGiverMixin + LLMRoleplayNPC + ShopkeeperCmdSet + quest-aware context + shop command prompt injection), QuestGivingLLMTrainer (QuestGiverMixin + LLMMixin + TrainerNPC — LLM chat + training, no quest required), BartenderNPC (QuestGiverMixin + LLMRoleplayNPC, quest-aware with 5 player states), CombatMob (AI-driven mobs with combat + respawn). QuestGiverMixin (`typeclasses/mixins/quest_giver.py`) — shared quest accept/abandon/view/turn-in command, used by all quest-giving NPCs. Two-tier CmdSet visibility (`call:true()` + `_EmptyNPCCmdSet`). Service NPCs inject role commands. BakerNPC (QuestGivingShopkeeper subclass) — Bron at Goldencrust Bakery, trades flour/bread, 4 quest states (pitch/active/done/generic) + level gate. Millholm NPC spawner (`world/game_world/zones/millholm/npcs.py`): Rowan (bartender), Bron (baker), Master Oakwright (woodshop trainer+quest), Sergeant Grimjaw (warrior guildmaster), Corporal Hask (warrior trainer), Shadow Mistress Vex (thief guildmaster), Whisper (thief trainer), Archmage Tindel (mage guildmaster), Apprentice Selene (mage trainer), Brother Aldric (cleric guildmaster), Sister Maeve (cleric trainer), Old Silas (beggar LLM NPC in Beggar's Alley), Gemma (jeweller LLM trainer, BASIC), Merchant Harlow (LLM shopkeeper, general store, flour/bread/timber/leather/cloth, `always` speech mode), Farmer Bramble (wheat farmer shopkeeper at Goldwheat Farm), Goodwife Tilly (cotton farmer shopkeeper at Brightwater farmhouse), Ratwick (fence LLM NPC in The Broken Crown, regular memory, NFT shop placeholder), Big Bjorn (lumberjack LLM shopkeeper at Millholm Sawmill, sings Lumberjack Song on arrival, wheat/flour placeholder for wood/timber AMM), Old Buckshaw (trapper LLM shopkeeper at Trapper's Hut in southern woods, coureur des bois personality, wheat placeholder for hide AMM), Grim Thackery (smelter LLM shopkeeper at Millholm Smelter, Four Yorkshiremen personality, trades copper ore/tin ore).
- Mob AI system: Composable mixin architecture (see `design/NPC_MOB_ARCHITECTURE.md`). **CombatMixin** (`typeclasses/mixins/combat_mixin.py`) — unified combat capability for all actors (players + mobs + hybrid NPCs): `get_combat_handler()`, `is_in_combat`, `enter_combat()`, `exit_combat()`, `initiate_attack()` (replaces `mob_attack()`), `hp_fraction`, `is_low_health`. Non-PCs get `CmdSetMobCombat` injected at creation. Composed into both `FCMCharacter` and `CombatMob`. **StateMachineAIMixin** (`typeclasses/actors/ai_handler.py`) — tick-driven AI state machine (renamed from `AIMixin`, backward-compat alias exists). AIHandler dispatches to `self.obj.ai_<state>()` methods. **AggressiveMixin** (`typeclasses/mixins/aggressive_mixin.py`) — attacks players on sight: `at_new_arrival()` aggro, `_try_match_height()` height adjustment, `_schedule_attack()`/`_execute_attack()` delayed attack, `ai_wander()` scan-for-targets override. **FlyingMixin** (`typeclasses/mixins/flying_mixin.py`) — innate flight: grants `Condition.FLY`, sets `preferred_height`, `ascend()`/`descend()`. **SwimmingMixin** (`typeclasses/mixins/swimming_mixin.py`) — innate swimming: grants `Condition.WATER_BREATHING`, sets `preferred_depth`, `dive()`/`surface()`. **InnateRangedMixin** (`typeclasses/mixins/innate_ranged_mixin.py`) — innate ranged attack: `mob_weapon_type="missile"`, cross-height attacks via `height_utils.can_reach_target()`. Convenience classes: `CombatMob(CombatMixin, StateMachineAIMixin, BaseNPC)`, `AggressiveMob(AggressiveMixin, CombatMob)`. Room notification via `at_new_arrival()` in `RoomBase.at_object_receive()`. Area-restricted wandering via `mob_area` tags. Anti-stacking: `max_per_room` attribute (default 0 = unlimited). **Mob behavior mixins** (`typeclasses/mixins/mob_behaviours/`): reusable plug-and-play behaviors composed into mobs. **PackCourageMixin** — only fights with N+ allies of same type, flees when alone, cornered fights regardless; uses `self.__class__` for ally counting, configurable `flee_message`. **RampageMixin** — on-kill instant chain attack on next living player, configurable `rampage_message`. **TacticalDodgeMixin** — configurable `dodge_chance` per combat tick, executes CmdDodge. Concrete mobs: Rabbit (flees threats), Wolf (AggressiveMob, L2, 12HP, 1d4, max 1/room), DireWolf (TacticalDodgeMixin + AggressiveMob, L3, 30HP, 2d6, 25% dodge), CellarRat (AggressiveMob, L1, 4HP, 1d2), Kobold (PackCourageMixin + AggressiveMob, L2, 14HP, 1d4, pack courage), Gnoll (RampageMixin + AggressiveMob, L4, 40HP, 1d6+2, Rampage), Crow (FlyingMixin + PackCourageMixin + AggressiveMob, L1, 4HP, 1d2, flying pack predator — needs 3+ to attack, re-ascends when idle). Kill hook: `at_kill(victim)` on CombatMob base. Mobs use same command interface as players (`CmdSetMobCombat` + `execute_cmd()`).
- Zone Spawn Script system: `ZoneSpawnScript` (`typeclasses/scripts/zone_spawn_script.py`) — persistent Evennia Script that maintains mob populations for static zones. One script per zone, reads spawn rules from JSON files (`world/spawns/<zone>.json`). Ticks every 15 seconds, audits population per rule, spawns replacements when below target. Each rule specifies typeclass, area_tag, target count, max_per_room, respawn_seconds, desc, and optional attrs. Common mobs (`is_unique=False`) are **deleted** on death — the script spawns fresh objects. Rule identity = `typeclass + area_tag` (same mob type can have different rules per patch). `area_tag` serves double duty: spawn room pool AND AI wander containment. Factory method: `ZoneSpawnScript.create_for_zone("zone_key")` loads JSON + does initial `populate()`. Supports hot-reload of JSON config. Procedural dungeons are out of scope — they manage their own mobs internally. **Two spawn systems by design:** (1) ZoneSpawnScript for commodity mobs (fixed-level, guaranteed spawns, population maintenance — rabbits, wolves, rats), (2) a separate rare/boss mob spawn system (future) with spawn chance, unique conditions, time/weather gating, one-at-a-time enforcement. Item/resource drops handled by separate spawn scripts, not traditional loot tables. Static zones use fixed-level mobs (e.g. Millholm = levels 1-2); procedural zones will have their own spawn mechanism with level scaling.
- LLM NPC system: `LLMMixin` (`typeclasses/mixins/llm_mixin.py`) adds LLM-powered dialogue to any NPC/mob. `LLMService` (`llm/service.py`) — centralized OpenRouter API client with sliding-window rate limiting (global 60/min + per-NPC 6/min), per-NPC cooldown (5s), daily cost cap ($5). Prompt templates in `llm/prompts/` loaded via `llm/prompt_loader.py` with `lru_cache`. Configurable speech detection modes per-NPC (`llm_speech_mode`): `"name_match"` (free — pattern match NPC name), `"llm_decide"` (LLM decides relevance), `"always"` (respond to all speech), `"whisper_only"` (cheapest). Hookable triggers: `llm_hook_say`, `llm_hook_whisper`, `llm_hook_arrive`, `llm_hook_leave`, `llm_hook_combat` — each enabled per-NPC. `CmdSay` notifies LLM NPCs of room speech; `CmdWhisper` extended to notify on whispers. Response delivery matches incoming mode (whisper→whisper back, say→say to room). Memory abstraction: `_store_memory`/`_get_relevant_memories` — rolling list in `db` attributes or vector memory via `ai_memory` app. Response sanitization strips quotes, command prefixes, newlines, truncates to 500 chars. Non-blocking via `deferToThread` + `reactor.callFromThread`. First actor class: `LLMRoleplayNPC` (`typeclasses/actors/npcs/llm_roleplay_npc.py`). `BartenderNPC` (`typeclasses/actors/npcs/bartender_npc.py`) — quest-aware subclass of LLMRoleplayNPC for Rowan. Overrides `_get_context_variables()` to inject `{quest_context}` based on player's tutorial/quest state. Level gate (level >= 3 → generic bartender). 5 states: new player pitch (tutorial + quest offer), quest pitch (tutorial done, steer to cellar), quest active (encouragement), tutorial suggest (quest done, suggest tutorial), generic (friendly bartender). Prompt template (`bartender.md`) has fixed frame (identity, personality, location, memories) + single `{quest_context}` variable containing state-specific knowledge + rules. `QuestGivingShopkeeper` (`typeclasses/actors/npcs/quest_giving_shopkeeper.py`) — generic typeclass combining LLMRoleplayNPC + ShopkeeperCmdSet. Injects `{quest_context}` (state-specific LLM instructions) and `{shop_commands}` (formatted command list with color codes so NPC can guide players). Override `_build_quest_context()` in subclasses. `BakerNPC` (`typeclasses/actors/npcs/baker_npc.py`) — Bron the Baker, QuestGivingShopkeeper subclass. 4 quest states: pitch flour quest, quest active (encouragement), quest done (uncomfortably grateful), generic baker. Trades flour (ID 2) and bread (ID 3). Short-term memory only. 17 tests. 11 bartender tests. Conversation engagement: after responding, NPC stays engaged with that speaker for `llm_engagement_timeout` seconds (default 60) — follow-up messages don't need the NPC's name. Available commands from NPC's cmdset injected into prompt as `{available_commands}` — NPC won't agree to actions it can't perform. Default model: `openai/gpt-4o-mini` via OpenRouter. Settings in `settings.py` (`LLM_ENABLED`, `LLM_API_BASE_URL`, `LLM_API_KEY`, etc.). Test NPC "Chatty" spawned on dirt track 3 via `spawn_npcs.py`. **Vector memory system** (`ai_memory/` Django app): persistent NPC memory with OpenAI embeddings in separate `ai_memory` database (survives game DB wipes). Dual-backend storage: on PostgreSQL (Railway), uses pgvector `VectorField(1536)` with HNSW index for sub-linear cosine similarity search; on SQLite (local dev), uses `BinaryField` with numpy cosine similarity in a Python loop. Backend detected automatically from `settings.DATABASES["ai_memory"]["ENGINE"]` — no configuration needed. Dual memory system per NPC: `llm_use_vector_memory=False` (default) uses rolling list in `db` attributes, `True` uses `ai_memory` with semantic search. `LLMService.create_embedding()` generates vectors via OpenAI `text-embedding-3-small`. Temporal awareness: `_time_ago_str()` produces natural time references ("yesterday", "back in December"), injected via `{last_seen}` template variable and timestamped memory entries. Name-based fallback matching enables memory survival across game DB wipes (Evennia object IDs change but NPC names don't). Migrate: `evennia migrate --database ai_memory`. See `design/DATABASE.md § pgvector for AI Memory` for architecture details. 52 tests (27 LLM NPC + 25 ai_memory).
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
  - `look around` alias: treated as bare `look`. `look at <target>` strips the `at` prefix. `examine`/`exam` aliased to `look`.
  - `go <direction>` command: strips the `go` prefix and executes the bare direction. For players who type `go north` instead of `north`.
  - `say to <target> <message>`: directed speech. `Bob says to Rowan: "hello"`. If target not found in room, treats whole string as undirected message. `talk` aliased to `say`. LLM NPCs in `name_match` mode trigger on directed speech (`say to Rowan`) in addition to name-in-message.
  - `wield <holdable>`: suggests `hold <item>` instead of generic "not a weapon" error.
  - `get <item>`: tries full multi-word name as item match before container split fallback. `get leather backpack` finds the item, not "leather from backpack". `f` shorthand for `from` in container syntax (`get lea f bac`). Gold synonyms: `coins`, `coin`, `gold coins` all work as `gold`.
- Position/posture system:
  - `position` AttributeProperty on BaseActor (default `"standing"`). Values: `"standing"`, `"sitting"`, `"resting"`, `"sleeping"`, `"fighting"`.
  - Posture commands: `sit`, `rest`, `sleep`, `stand`, `wake` — with combat guard (can't change posture while fighting), same-position guard, room messages.
  - Movement blocking: `at_pre_move()` in FCMCharacter blocks movement unless position is `"standing"` or `"fighting"`. Movement costs 1 move point per room transition (move_type `"move"`, `"follow"`, or `"traverse"`). Teleports are free. At 0 move, character is "too exhausted to move."
  - Movement cost for combat actions: bash (2), pummel (1), stab (2), dodge (1), retreat (2), taunt (1). Checked after cooldown, before execution. "Too exhausted" blocks the action.
  - **Shared combat skill cooldown (GCD):** Single `skill_cooldown` counter on CombatHandler. Using any combat skill (bash, pummel, taunt, stab) blocks all others until cooldown expires. Each skill sets its own mastery-scaled duration. Decrements by 1 each combat tick. Normal auto-attacks are unaffected.
  - Regen multipliers: `REGEN_MULTIPLIERS` class dict on BaseActor — `standing: 1, sitting: 1, resting: 2, sleeping: 3, fighting: 0`. Applied in `RegenerationService.regenerate()`.
  - Combat integration: `combat_handler.start_combat()` sets `position="fighting"`, `stop_combat()` sets `position="standing"`. `ndb.combat_target` tracks current combat target for room display ("Bob is here, fighting a goblin!").
  - Position-aware room display templates: `_POSITION_TEMPLATES` dict on BaseActor for default display per position. `get_room_description()` dispatches between custom room_description and templates.
  - 18 posture tests + 6 room description tests.
- SwitchMixin (`typeclasses/mixins/switch_mixin.py`): generic toggle mechanism for fixtures. `is_activated` state, configurable `switch_verb`/`switch_name` for messaging, `can_deactivate` flag for one-way switches. `at_activate(caller)`/`at_deactivate(caller)` hooks — override in subclass or builder to define the effect. `SwitchFixture(SwitchMixin, WorldFixture)` concrete typeclass for levers, buttons, valves. `CmdSwitch` command (`pull`/`push`/`turn`/`flip` aliases) toggles switches in the room.
- World interaction commands:
  - `open`/`close`: closeable objects in room (chests, doors)
  - `unlock`: key-based unlocking (searches inventory for matching KeyItem, consumed on use)
  - `lock`: lock a closed lockable object
  - `pull`/`push`/`turn`/`flip`: toggle SwitchMixin objects (levers, buttons, valves)
  - `search`: d20 + alertness mastery bonus + WIS mod vs hidden object find_dc, also detects traps (objects, exits, rooms) by rolling vs trap_find_dc
  - `picklock` (alias `pl`): SUBTERFUGE skill command, d20 + mastery bonus + DEX mod vs lock_dc
  - `case`: SUBTERFUGE skill command. Scout a target's inventory before pickpocketing. Per-item visibility roll based on mastery (BASIC 50% → GM 90%). Vague gold display (tiers not exact amounts). Results cached 5 minutes. Does not break HIDDEN.
  - `pickpocket` (alias `pp`): SUBTERFUGE skill command. Steal gold/resources/items from a cased target. Contested roll: d20 + DEX mod + SUBTERFUGE bonus vs 10 + target perception. HIDDEN gives advantage. Always breaks HIDDEN. Failure alerts target, aggressive mobs aggro. Requires combat-enabled room (PvP room for player targets). 60s per-target cooldown.
  - `stab` (aliases `backstab`, `bs`): STAB skill command. 5e-style Sneak Attack — when the thief has advantage (from HIDDEN, target ENTANGLED, etc.), adds bonus damage dice to next attack. Scaling: BASIC +2d6, SKILLED +4d6, EXPERT +6d6, MASTER +8d6, GM +10d6. Crits double the bonus dice. Shared combat skill cooldown: BASIC 6, SKILLED 5, EXPERT 4, MASTER 3, GM 2 rounds. Can be used as opener from stealth (enters combat, sets advantage, queues attack) or mid-combat whenever advantage exists. Uses generic `bonus_attack_dice` mechanism on CombatHandler (consumed by `execute_attack()`).
  - `assist`: BATTLESKILLS general skill (all classes). In combat: give up your attack to grant an ally advantage against all enemies. Mastery scaling: BASIC 1 round, SKILLED 2, EXPERT 3, MASTER 4, GM 5 rounds. Out of combat: set `non_combat_advantage` on target for their next skill check. Uses `get_sides()` for ally/enemy detection. 18 tests.
  - `bash` (alias `b`): BASH skill (warrior). High risk/high reward combat maneuver — contested STR + mastery vs target STR. Success: target PRONE 1 round (loses turn + enemies get advantage via on-apply callback). Failure: basher DEX save DC 10 or fall prone. Shared combat skill cooldown: BASIC 7, SKILLED 6, EXPERT 5, MASTER 4, GM 3 rounds.
  - `pummel` (alias `p`): PUMMEL skill (warrior, paladin). Low risk/low reward combat maneuver — contested STR + mastery vs target DEX. Success: target STUNNED 1 round (loses turn, no advantage for enemies). Failure: nothing happens. Shared combat skill cooldown: BASIC 8, SKILLED 7, EXPERT 6, MASTER 5, GM 4 rounds.
  - `disarm` (alias `dis`): SUBTERFUGE skill command. Disarm a detected trap on objects, exits, or rooms. Supports room keywords ("floor", "ground", "plate", "room", "pressure") for pressure plates. Delegates to `target.disarm_trap(caller)` on TrapMixin. Failed disarm triggers the trap.
  - `identify` (alias `id`): LORE skill command (bard). Identify items and creatures using bardic knowledge. No mana cost. Reuses Identify spell's `_identify_actor()` and `_identify_item()` template builders directly (imported from `world/spells/divination/identify.py`). LORE mastery maps 1:1 to identification tier (BASIC=tier 1 through GM=tier 5). Same level gating as the spell for actors, same `identify_mastery_gate` check for items. PvP room restriction for identifying other players. Overrides `func()` directly (no per-mastery dispatch). 11 tests.
  - `protect`: PROTECT skill (warrior, paladin). Toggle-based tanking — `protect <ally>` to start intercepting attacks aimed at that ally, `protect` or `protect <same ally>` to stop. Flat percentage intercept chance per mastery: BASIC 40%, SKILLED 50%, EXPERT 60%, MASTER 70%, GM 80%. On intercept, protector takes the full damage (using protector's own resistances/armor). Multiple protectors on one target supported (each rolls independently, first success wins). Stores `protecting = target.id` on protector's CombatHandler. Intercept hook in `execute_attack()` step 8b: after damage calculation, before `take_damage()` — swaps local `target` variable so protector's armor takes durability loss and kill check applies to protector. Must be in combat, target must be an ally in combat.
  - `taunt`: PROTECT skill (warrior, paladin). Taunt a mob to provoke it into attacking you. Two modes: **Opener** (out of combat) — contested d20 + CHA mod + mastery bonus vs d20 + target WIS mod. Success: mob attacks taunter (mob is initiator — important for future crime tracking). Failure: 5-minute per-character cooldown. **In combat** — same contested roll, success switches mob's target to taunter. Shared combat skill cooldown: BASIC 6, SKILLED 5, EXPERT 4, MASTER 3, GM 2 rounds. Only works on CombatMob instances (not players). TAUNT skill enum removed — taunt is now a command under PROTECT.
  - `offence` (alias `offense`): STRATEGY skill (warrior, paladin). Group leader command — toggles offensive stance for leader + all followers in combat in same room. Stat bonuses via named effects (`stat_bonus` type): BASIC +2 hit/-1 AC, SKILLED +3 hit/-1 AC, EXPERT +3 hit/+1 dam/-1 AC, MASTER +3 hit/+2 dam/-1 AC, GM +3 hit/+3 dam/no AC penalty. Mutually exclusive with defence. `duration=None, duration_type="combat_rounds"` = permanent in combat, auto-cleaned on combat end.
  - `defence` (alias `defense`): STRATEGY skill (warrior, paladin). Mirror of offence — toggles defensive stance. BASIC +2 AC/-2 hit, SKILLED +2 AC/-2 hit, EXPERT +3 AC/-1 hit, MASTER +4 AC/-1 hit, GM +5 AC/no hit penalty. Mutually exclusive with offence.
  - `retreat` (alias `ret`): STRATEGY skill (warrior, paladin). Group leader command — strategic withdrawal. Single leader roll: d20 + INT mod + CHA mod + mastery bonus vs DC 10. Success: stop combat + move entire group (leader + followers in combat in same room) through chosen/random exit. Failure: nobody moves, enemies get 1 round advantage against leader. Optional direction argument. Captures enemies before movement, stops combat before moving.
  - `sail`: SEAMANSHIP general skill (all classes). Sea travel via dock gateway rooms (RoomGateway with `boat_level` condition). Two-pass ship selection: `sail` lists routes, `sail <dest>` shows qualifying ships (auto-sails if single ship), `sail <dest> <#>` sails with chosen ship. Ship ownership via NFTMirror — ships are NFTs that don't spawn as in-game objects (`prototype_key=None`). 5 ship types (Cog/Caravel/Brigantine/Carrack/Galleon) mapped 1:1 to mastery tiers (BASIC–GRANDMASTER) via `ShipType` enum. `BaseNFTItem.get_qualifying_ships()` / `get_best_ship_tier()` / `get_character_ships()` as single point of entry for ship queries. `_check_boat_level()` validator in `cmd_travel.py` for gateway condition checks. Test world docks: Town Dock (off dt6) ↔ Beach Dock (off beach room), `boat_level: 1, food_cost: 1`. 23 tests.
  - Container access (get/put from) gated on `is_open` state
- Non-combat advantage/disadvantage system: `db.non_combat_advantage` / `db.non_combat_disadvantage` boolean flags on actors. All non-combat d20 skill checks use `dice.roll_with_advantage_or_disadvantage()`. Cancellation: both True → normal roll. Consumed after each check. See "CRITICAL: Non-Combat Advantage/Disadvantage" section for full pattern.
- Skill command scaffolds: 24 scaffold commands covering remaining skills in the enum. Each extends CmdSkillBase (mastery dispatch with `mob_func()` fallback for animal mobs) with design notes as docstrings. Commands print `"'{key}' Command using Skill '{skill}' - {Tier}"` at each mastery level. Fully implemented (not scaffolds): dodge, assist, stab, bash, pummel, protect, taunt, offence, defence, retreat, sail, disarm, identify. General skills: dodge, assist (implemented), chart, build, sail (implemented — see below), explore, tame, repair. Warrior: bash, pummel, protect, taunt, offence, defence, retreat (implemented), frenzy. Thief: sneak, stab (implemented — see above), assassinate, recite. Bard: perform, inspire, mock, charm, divert, disguise, conceal, identify (implemented — LORE skill, reuses Identify spell templates). Druid/Ranger: forage (implemented — see hunger system), track, summon, dismiss, shapeshift (alias ss). Cleric: turn. PARRY and SHARPSHOOTER removed from enum (moving to weapon mastery perks). TAUNT removed from skills enum (merged into PROTECT). STRATEGIST renamed to STRATEGY.
- Follow/Group system: `follow <player>`, `unfollow`, `nofollow` toggle, `group` display. Chain-resolution (A follows B follows C → A's leader is C). Auto-follow on exit traversal via `FCMCharacter.at_post_move()` with `move_type in ("follow", "teleport")` guard — followers cascade on normal moves but NOT on teleports or follow moves. Collects all followers (direct + indirect) at the leader level. `nofollow` removes existing followers. Underpins strategy skill group buffs, dungeon entry, XP sharing.
- Procedural dungeon system: lazy room creation on a coordinate grid with tag-based tracking. Two dungeon types: `"instance"` (boss at termination depth, dead-end) and `"passage"` (connects two world rooms via `DungeonPassageExit`). Three instance modes: `"solo"` (one per player), `"group"` (leader + followers), `"shared"` (one instance per entrance, anyone joins, `empty_collapse_delay` keeps alive). Two entry triggers determined by builder placement (not template): `DungeonEntranceRoom` (command `enter dungeon`) or `DungeonTriggerExit` (movement-triggered, walk through exit). Same template works with either trigger. `DungeonTemplate` frozen dataclass (`dungeon_type`, `instance_mode`, `boss_depth`, exit budget, lifetime, room/boss generators). `DungeonInstanceScript` orchestrator with state machine (active→collapsing→done), 60s tick. `DungeonExit` with lazy creation (exits point to self until traversed). Manhattan distance depth. Three collapse safety nets (lifetime, post-boss linger, empty instance with optional delay for shared). Server restart cleanup in `at_server_startstop.py`. Teleport moves do not cascade followers (`at_post_move` guard). Cave of Trials test template with depth-scaled descriptions. Deep Woods Passage template (`world/dungeons/templates/deep_woods_passage.py`) — passage type, group mode, boss_depth=5, low branching (max 1 new exit per room), forest-themed descriptions at 3 depth tiers. Rat Cellar template (`world/dungeons/templates/rat_cellar.py`) — instance type, solo mode, 1-room dungeon (max_unexplored_exits=0, max_new_exits_per_room=0), spawns 3 CellarRat + 1 RatKing boss, `allow_death=False` with defeat_destination_key="The Harvest Moon", post_boss_linger_seconds=60. `QuestDungeonTriggerExit` (`typeclasses/terrain/exits/quest_dungeon_trigger_exit.py`) — subclass of DungeonTriggerExit with `quest_key` and `fallback_destination_id`; routes to fallback room when quest complete, auto-accepts quest on first entry, creates dungeon instance for in-progress quest. 38 dungeon tests.
- Zone/District/Terrain tagging: Every room has `category="zone"` and `category="district"` Evennia tags. RoomBase provides `set_zone()`, `get_zone()`, `set_district()`, `get_district()`, `set_terrain()`, `get_terrain()` helpers. Two spatial concepts: **zone** (top-level region), **district** (sub-region within zone). **Terrain** (`category="terrain"`, `enums/terrain_type.py`): URBAN, RURAL, FOREST, MOUNTAIN, DESERT, SWAMP, COASTAL, UNDERGROUND, DUNGEON, WATER, ARCTIC, PLAINS. Used by forage command and future systems (tracking, weather, mounts, spawning). Test world zones: `test_economic_zone` (wolf/guild/market/resource/bank districts), `test_water_fly_zone` (beach/ocean districts), `arena_zone` (arena/infirmary districts), `system_zone` (purgatory/recycle bin). Game world zones: `millholm` (millholm_town, millholm_farms, millholm_woods, millholm_sewers, millholm_mine, millholm_deep_woods, millholm_faerie_hollow, millholm_southern districts).
- Help category system: 14 categories (Character, Combat, Communication, Crafting, Exploration, Group, Group Combat, Items, Magic, Nature, Performance, Stealth, System, Blockchain). Thin overrides of Evennia defaults for recategorisation. `is_ooc()` custom lock function hides blockchain commands (bank, wallet, import, export) and character management commands (charcreate, chardelete) when puppeting. Password command restricted to developer-only.
- Game world build system (`world/game_world/`): Separate from test world. Entry point: `deploy_world.py` (`deploy_world()` / `soft_deploy_world()`). Shared cleanup utility: `zone_utils.py` (`clean_zone(zone_key)`). Zones live in `world/game_world/zones/<zone_key>/` — each zone has its own `soft_deploy.py` with `clean_zone()`, `build_zone()`, and `soft_deploy()`. Millholm is the only built zone; all others are stubs. Millholm Town district (`zones/millholm/town.py`): ~35 rooms, ~70 exits. The Old Trade Way (8-segment E-W road), 2×2 Townsquare, The Harvest Moon Inn (with stairwell chain: ground→cellar stairwell→rat cellar quest dungeon [QuestDungeonTriggerExit south] / permanent cellar [post-quest], ground→first floor→hallway→bedrooms), crafting shops (smithy, leathershop, tailor, woodshop, apothecary, The Gilded Setting jeweller [RoomCrafting, jeweller type, BASIC mastery]), Goldencrust Bakery (RoomProcessing), Order of the Golden Scale bank (RoomBank, brass sign detail with banking commands), Millholm Post Office (RoomPostOffice, east of bank, services board detail with mail commands), guild halls (warriors/mages/temple with back rooms), The Iron Company (warrior guild back room — Sergeant Grimjaw guildmaster + Corporal Hask trainer), general store, stables, residential houses, Millholm Cemetery (RoomCemetery, north of road_far_east), Hilda's Distillery (east of apothecary), secret passage (Gareth→Abandoned House). District intersection rooms stub future connections: road_far_east→Woods, cellar_stairwell→Sewers, abandoned_house→Sewers. Limbo connects down/up to The Harvest Moon. Zone tag: `millholm`, district tag: `millholm_town`. Millholm Farms district (`zones/millholm/farms.py`): ~56 rooms. The Old Trade Way continues west (10 road segments), Goldwheat Farm (fencelines, 4 wheat edge fields, 4-room wheat maze with one-way exits — maze rooms are RoomHarvesting for wheat resource_id=1, edge fields are NOT harvestable), Millholm Windmill (RoomProcessing — wheat→flour), South Fork road (4 rooms), Brightwater Cotton Farm (farmyard, cotton barn, drying shed, 3×3 cotton field grid, 4-room underground tunnel/vault with exit to south fork), Abandoned Farm (ruined buildings, 4×2 overgrown field grid). Connects west from town's road_far_west. Zone tag: `millholm`, district tag: `millholm_farms`. Millholm Woods district (`zones/millholm/woods.py`): ~93 rooms. Forest Path East (interface from town's road_far_east), 17-room winding main path (east through light woods to wooded foothills, alternating east/northeast/southeast directions), Millholm Sawmill (RoomProcessing — wood→timber, 2-room spur north), Millholm Smelter (RoomProcessing — ores→ingots including alloys, 2-room spur south), 10×6 southern woods exploration grid (60 rooms) with boundary redirects (west/east/south edges redirect 2 rooms back creating 3-room cycles for infinite-forest feel), POI rooms in grid (Game Trail Crossing, Stone Cairn, Fallen Giant, Berry Bramble, Rabbit Warren, Trapper's Hut, Old Snare Line, Fox Earth, Hollow Log, Spring-fed Pool). Grid row 1 connects north to main path rooms 5-14. Northern woods row (10 "Dense Woods" rooms north of main path rooms 5-14) — denser transition zone, all funnel north via one-way exits into single Edge of the Deep Woods entry room. Deep woods entry south exit returns to middle of northern row (asymmetric). Deep woods entry north: procedural passage (DungeonTriggerExit) to deep_woods_clearing, wired in zones/millholm/soft_deploy.py. Connects east from town's road_far_east. Zone tag: `millholm`, district tag: `millholm_woods`. Millholm Sewers district (`zones/millholm/sewers.py`): ~26 rooms. Sewer proper (18 rooms, terrain UNDERGROUND): main north-south spine (Sewer Entrance→Main Drain→Drain Junction→Flooded Tunnel→Deep Sewer→Overflow Chamber→Crumbling Wall) with 3 dead-end branches (Blocked Grate, Rat Nest, Collapsed Section); cistern branch (Old Cistern→Waterlogged Passage→Fungal Grotto→Narrow Crawlway→Ancient Drain→Overflow Chamber) with 2 dead ends (Submerged Alcove, Bricked-Up Passage) — connects abandoned house entrance to main spine. Thieves' Lair (8 rooms, terrain DUNGEON): hidden behind crumbling wall (find_dc=20), Thieves' Tunnel→Guard Post→Thieves' Hall hub with Planning Room (east), Barracks (west), Training Alcove (east of guard post), Stolen Goods (south)→Shadow Mistress's Chamber (east). Cross-district hidden doors in `zones/millholm/soft_deploy.py`: cellar stairwell→sewer entrance (west, find_dc=16), abandoned house→old cistern (down, find_dc=18). Both routes are 10 moves to Thieves' Hall. Zone tag: `millholm`, district tag: `millholm_sewers`. Millholm Abandoned Mine district (`zones/millholm/mine.py`): 17 rooms. Surface (3): Abandoned Miners' Camp (hub, arrival from deep woods), Windroot Hollow (RoomHarvesting — windroot resource_id=15, gather), Mine Entrance. Upper Mine / Copper Level (5, terrain UNDERGROUND): Entry Shaft, Copper Drift (RoomHarvesting — copper ore resource_id=23, mine), Copper Seam (RoomHarvesting — copper ore), Timbered Corridor, Ore Cart Track. Kobold Territory (3): Kobold Lookout, Flooded Gallery (dead end), Descent Shaft (down). Lower Mine / Tin Level (4): Lower Junction, Tin Seam (RoomHarvesting — tin ore resource_id=25, mine), Tin Vein (RoomHarvesting — tin ore), Kobold Warren. Deep Mine / Mystery (2): Ancient Passage (pre-human stonework matching sewer ruins), Sealed Door (future content hook). All harvest rooms resource_count=0 — spawn script sets amounts. Connection point: miners_camp (west, procedural passage from deep_woods_clearing — wired in zones/millholm/soft_deploy.py). Zone tag: `millholm`, district tag: `millholm_mine`. All game world harvest rooms (wheat, cotton, wood, ores, windroot, arcane dust) use resource_count=0 — the resource spawn script dynamically sets actual amounts based on economy and demand. Faerie Hollow district (`zones/millholm/faerie_hollow.py`): 5 rooms. Deep Woods Clearing (static midpoint between procedural deep woods passages, named "Deep Woods" to blend in, tagged `millholm_deep_woods`), Shimmering Threshold (transition room), Faerie Hollow (main chamber, faerie NPCs future), Moonlit Glade (offering altar, quest interaction point), Crystalline Grotto (RoomHarvesting — arcane dust resource_id=16, gather). Entrance from clearing is an ExitDoor with `is_invisible=True` (requires DETECT_INVIS condition to see), always open, direction north, key "a shimmer in the air". Return exit is visible. Zone tag: `millholm`, district tags: `millholm_deep_woods` (clearing) and `millholm_faerie_hollow` (hollow rooms). Millholm Southern District (`zones/millholm/southern.py`): ~30 rooms. Two entrances: town's south_road→Rat Run and farms' south_fork_end→Countryside Road (both wired in zones/millholm/soft_deploy.py). Rougher Town (6, URBAN): Rat Run, Low Market crossroads, Fence's Stall, Gaol, The Broken Crown tavern, South Gate. Countryside (4, RURAL): Countryside Road, Farmstead Fork, Bandit Holdfast, Bandit Camp. Moonpetal Fields (7, PLAINS): Moonpetal Approach + 2x3 RoomHarvesting grid (moonpetal resource_id=12, gather) — primary moonpetal supply for all potions. Gnoll Territory (5, PLAINS): Wild Grasslands, Gnoll Hunting Grounds (hub), Ravaged Farmstead, Gnoll Camp, Gnoll Lookout. Barrow Underground (5): Barrow Hill (PLAINS, hidden door find_dc=18), Barrow Entrance, Bone-Strewn Passage, Ancient Catacombs (Ancient Builders glyphs), Necromancer's Study (all UNDERGROUND). Shadowsward (2, PLAINS): Southern Approach, Shadowsward Gate (zone exit placeholder, SKILLED cartography). Zone tag: `millholm`, district tag: `millholm_southern`.
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
- Server lifecycle (`server/conf/at_server_startstop.py`): `at_server_init()` registers dungeon templates (cave_dungeon, deep_woods_passage, rat_cellar). `at_server_start()` runs on every boot: ensures global scripts (RegenerationService, HungerService, DayNightService, SeasonService, WeatherService, DurabilityDecayService, ResourceSpawnScript) exist via `_ensure_global_scripts()` (creates missing, skips existing — no duplicates), collapses stale dungeon instances, restarts corpse/purgatory/mob timers. **Spawned items (gold, resources on mobs/rooms) survive server restarts** — they are NOT cleared on boot. Use the `wipe_spawns` superuser command for manual cleanup, or `soft_deploy_world` which handles its own zone-level cleanup. Spawn cleanup utility lives in `utils/spawn_cleanup.py`. Global scripts are independent of world building — adding a new service means appending to the `_GLOBAL_SCRIPTS` list.
- Tutorial zone system: per-player instanced tutorial with LLM-powered guide NPC. Infrastructure: `TutorialInstanceScript` (lifecycle manager — create rooms, spawn guide NPC, strip items on exit, return resources, per-chunk graduation rewards once per account), `TutorialCompletionExit` (triggers instance collapse on traversal), `TutorialGuideNPC` (LLM-powered guide "Pip" that follows the player and speaks about each room using `guide_context`), tutorial hub (static room, idempotent builder, 3 `ExitTutorialStart` exits + 1 `ExitTutorialReturn` exit). Entry flow: new characters spawn in Harvest Moon Inn (bartender NPC "Rowan" greets via `llm_hook_arrive`), first-puppet simplified offer in `at_post_puppet()`, `enter tutorial` / `skip tutorial` / `leave tutorial` / `start tutorial 1|2|3` commands on character cmdset. Each room has `guide_context` (LLM prompt for the guide) and `tutorial_text` (static fallback if LLM unavailable). `llm_hook_arrive` wired in `FCMCharacter.at_post_move()` — iterates room contents calling `at_llm_player_arrive()` on LLM NPCs. Tutorial 1 (Survival Basics): 9 rooms (Welcome Hall → Observation Chamber → Supply Room → The Armoury → Open Courtyard → The Dim Passage → Training Arena → The Pantry → Tutorial Complete). Key items: Ring of Flight, Ring of Water Breathing, training longsword, leather cap, torch, training dummy mob, bread, gold. Graduation reward: 2 bread, 50 gold, wooden training dagger. Tutorial 2 (Economic Loop): 6 rooms (The Harvest Field [RoomHarvesting, wheat] → The Woodlot [RoomHarvesting, wood] → The Windmill [RoomProcessing, wheat→flour] → The Bakery [RoomProcessing, flour+wood→bread] → The Vault [RoomBank] → Tutorial Complete). First-run: 20 gold. Graduation reward: 100 gold, 10 wheat, 5 wood. Tutorial 3 (Growth & Social): 7 rooms (Hall of Records → The Speaking Chamber → Hall of Skills → The Training Grounds [TrainerNPC, blacksmith/carpenter/alchemist] → The Guild Hall [GuildmasterNPC, warrior] → The Companion Room [companion NPC] → Tutorial Complete). First-run: 1 general skill point + 50 gold. Graduation reward: 100 gold, 1 skill point. Fixtures: mirror, message board, skill tome. All tutorial items flagged `db.tutorial_item = True` and stripped on exit. Tutorial rooms use tags (`tutorial_room`, `tutorial_exit`, `tutorial_item`, `tutorial_mob`) for cleanup. Anti-exploitation: per-account flags gate first-run rewards and graduation rewards. LLM prompt templates: `llm/prompts/tutorial_guide.md`, `llm/prompts/bartender.md`, `llm/prompts/shopkeeper.md` (directs NPCs to guide players to shop commands rather than roleplaying transactions), `llm/prompts/roleplay_npc.md` (general roleplay, no game commands). Bartender spawn: `world/game_world/zones/millholm/npcs.py`. 96 tests.
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

## Effects System

> **See `design/EFFECTS_SYSTEM.md`** for the authoritative reference on: the 3-layer EffectsManagerMixin (condition flags, stat effect dispatch, named effects), convenience methods API, effect registry, break_effect/dispel pattern, decision tree for when to use what, NamedEffect enum management, on-apply callbacks, condition guidance (when NOT to add a Condition flag), poison timing fork, DamageResistanceMixin, and the damage pipeline (`take_damage()`).
>
> Key classes/mixins covered there: `EffectsManagerMixin`, `DamageResistanceMixin`, `NamedEffect` enum, `Condition` enum.
>
> **MANDATORY:** The EffectsManagerMixin is the ONLY approved system for effects on actors. Do NOT create ad-hoc alternatives. See the design doc for the full policy.

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

### Automatic Condition Messaging & Side Effects

> **See `design/EFFECTS_SYSTEM.md`** § Automatic Condition Messaging for: BaseActor add_condition/remove_condition overrides, visibility-aware timing, and condition-specific side effects (FLY fall, WATER_BREATHING breath timer).

### Stealth, Stash, Case/Pickpocket

> **See `design/COMBAT_SYSTEM.md`** § Stealth & HIDDEN Condition for: hide mechanics, movement while hidden, search reveals, attack from hide, stash command (object + actor concealment), case & pickpocket workflow.

### Breath Timer (typeclasses/scripts/breath_timer.py)

Per-character `BreathTimerScript` attached when diving underwater without WATER_BREATHING. Ticks every 2 seconds. Duration: `max(10, 30 + CON_modifier * 15)` seconds. After breath expires, deals `max(1, effective_hp_max // 20)` drowning damage per tick (~5% HP). Triggers `die("drowning")` when HP reaches 0.

## Crafting & Processing System

> **See `design/CRAFTING_SYSTEM.md`** for the authoritative reference on: recipe system (data format, helpers), enchanting (auto-granted, item split, three tiers, gem enchanting, gem insetting), RecipeBookMixin, RoomProcessing, RoomCrafting, consumable items (potions, recipe scrolls, spell scrolls), and prototype structure.
>
> **Recipe catalog:** See `design/SPELL_SKILL_DESIGN.md` for the full recipe list per crafting skill.

## Magic System Architecture

> **See `design/SPELL_SKILL_DESIGN.md`** for the authoritative reference on: class-based spell architecture, registry pattern, SpellbookMixin API, mage vs cleric differences, memory slot system, spell scroll NFTs, spell implementation patterns (cooldowns, duration conventions, recast refresh, range rules, AoE types), per-school spell lists with implementation status (29 of 50 implemented, 318+ tests), and the spell backlog grouped by blocking dependency.

**Adding a new spell:**
1. Create `world/spells/<school>/<spell_name>.py`
2. Decorate class with `@register_spell`
3. Define `key`, `name`, `school`, `min_mastery`, `mana_cost`, `target_type`
4. Implement `_execute(self, caster, target)` → returns `(bool, dict)` with first/second/third person messages
5. Import in the school folder's `__init__.py`

## Weapon Skill Architecture

> **See `design/COMBAT_SYSTEM.md`** for the authoritative reference on: weapon type hierarchy (24 types), mastery vs individual weapon power, mastery-related methods, crit threshold system, dual-wield system, finesse weapons, unarmed weapon singleton, and reaction system architecture.
>
> **Key utility:** `get_weapon(actor)` in `combat_utils.py` — returns wielded weapon, `UNARMED` singleton (PC with no weapon), or `None` (animal mobs). All combat code uses this instead of direct slot access.

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

## NPC & Quest System

> **See `design/NPC_QUEST_SYSTEM.md`** for the authoritative reference on: NPC architecture (BaseNPC, CmdSet visibility pattern, service NPCs vs combat mobs), NPC hierarchy (TrainerNPC, ShopkeeperNPC, GuildmasterNPC, BartenderNPC, QuestGivingShopkeeper, BakerNPC, CombatMob), training system, AMM trading, QuestGiverMixin, quest engine (FCMQuest, FCMQuestHandler, templates), and all implemented quests (warrior/thief/mage/cleric initiation, rat cellar, baker's flour, oakwright's timber).
>
> **Critical Evennia gotcha:** NPCs need `call:true()` lock + `_EmptyNPCCmdSet` default for command visibility. See the design doc for details.

## Documentation Hierarchy

- **Design docs** (`design/*.md`) are the **primary source of truth** for design, intent, constraints, and architecture decisions.
- **This file (CLAUDE.md)** is kept as lean as possible — uses `> **See design/FOO.md**` callout references to design docs. Only contains detail for things NOT captured in design docs.
- **PLANNING docs** (`ops/PLANNING/`) capture future ideas and in-progress work state (lower priority).
- **When making changes:** first update the appropriate design doc, then update CLAUDE.md references, then PLANNING if relevant. If no suitable design doc exists, ask the user where to capture the information.

## Coding Conventions

- **Prefer enums over raw strings** for validation and typo prevention. When a field references a fixed set of values (ability scores, weapon types, alignments, damage types, skills, etc.), use the corresponding enum rather than raw strings. Examples: `WeaponType.BATTLEAXE` not `"battleaxe"`, `Ability.STR` not `"strength"`, `skills.STEALTH.value` not `"stealth"`. Enum `.value` can be extracted when writing to storage (e.g. `weapon.value` for dict keys). Skill commands should set `skill = skills.ENUM.value` (not a raw string) so renaming a skill in the enum automatically propagates.
- **All exits MUST be created through helper functions** in `utils/exit_helpers.py`. Never use bare `create_object()` for exits in zone builders. If a new exit type isn't covered by an existing helper, create the helper first, then use it. Available helpers: `connect_bidirectional_exit`, `connect_bidirectional_door_exit`, `connect_bidirectional_trapped_door_exit`, `connect_bidirectional_tripwire_exit`, `connect_oneway_loopback_exit`. See `design/EXIT_ARCHITECTURE.md` § Builder Helpers for full documentation.

## Future Roadmap

- **More spells** — Evocation complete at BASIC/SKILLED/EXPERT/MASTER/GM tiers (Flame Burst moved to SKILLED). Remaining evocation: Lightning Bolt (SKILLED), Chain Lightning (EXPERT). Cleric/paladin domains planned with BASIC/EXPERT/GM spells: Divine Healing (Purify, Mass Heal, Death Ward), Divine Protection (Sanctuary, Holy Aura, Divine Aegis), Divine Judgement (paladin only — Smite, Holy Fire, Wrath of God), Divine Revelation (Holy Insight), Divine Dominion (Command, Hold Person, Word of God). Nature Magic for druid/ranger: Entangle, Call Lightning, Earthquake. `spellinfo` command planned (structure ready — description/mechanics fields on all spells).
- **Weapon mastery effects** — ALL 24 weapon types DONE (was 25 — katana + wakizashi merged into ninjatō). Every weapon has unique mastery mechanics.
- **Combat expansion** — multi-attack (attacks_per_round > 1), combat skill commands (bash, assassinate, etc.), spell casting in combat, combat prompt/status display, LLM-driven mob AI. Height combat implemented (see `design/COMBAT_SYSTEM.md` § Height Combat, `design/VERTICAL_MOVEMENT.md` § HeightAwareMixin, `design/NPC_MOB_ARCHITECTURE.md` § AggressiveMixin). Future phases: height-aware visibility, get/drop/loot height gating.
- **Blockchain sync service** — built as `FCM-Blockchain-Sync-Service/` (standalone Django app). Polls `eth_getLogs` for events on all five contracts, updates `GoldChainState` and `ResourceChainState` (sole writer for these tables), and stamps reconciliation ledger (`GoldChainTransferLog`, `ResourceChainTransferLog`) with `chain_adjusted=True`. Game-side deposit/withdraw methods stamp `game_adjusted=True`. 46 tests. See `FCM-Blockchain-Sync-Service/CLAUDE.md` for details.
- **More recipes** — expand crafting recipes across all skills and mastery tiers (bronze weapons, steel weapons, more jewellery, etc.)
- **NPC system** — BaseNPC + TrainerNPC + GuildmasterNPC complete. QuestGiverMixin extracts quest accept/abandon/view/turn-in into a shared mixin used by GuildmasterNPC, BartenderNPC, and QuestGivingShopkeeper. LLM-powered NPCs: BartenderNPC (Rowan, quest-aware with per-player prompt states), BakerNPC (Bron, QuestGivingShopkeeper subclass with AMM shop + quest context). ShopkeeperNPC with full AMM integration (list/quote/accept/buy/sell commands). CombatMob with AI state machine, combat handler integration, corpse-on-death, and respawn implemented (Rabbit, Wolf, DireWolf). Mobs use same command interface as players. Item/resource drops handled by separate spawn scripts (not traditional loot tables). Future: XP rewards, LLM AI (zero refactoring needed — just swap decision-maker).
- **NPC market maker AMM** — resource trading via XRPL AMM liquidity pools (ShopkeeperNPC). Quote→accept flow, instant buy/sell, "sell all". OfferCreate swap execution with 6-operation accounting. Superuser tools: `amm_check`, `reconcile`, `test_amm_trades`. See **design/ECONOMY.md** for economic design (pricing model, tracker tokens, market tiers, spawn algorithms). 17 AMM service + 19 shopkeeper command tests.
- **Remort system** — perk choices on remort (extra point buy, bonus HP/Mana/Move) and content gating via `min_remorts`. Infrastructure exists (num_remorts on character, min_remorts on classes/items/races) but the actual remort flow is not yet implemented.
