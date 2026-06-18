# CLAUDE.md

> **Project-wide working rules and cross-repo context live in the FCM umbrella repo's `CLAUDE.md`**,
> loaded automatically when you work from the umbrella root. If you opened this repo directly instead
> of via the umbrella, relaunch from the umbrella root for the full context. This file holds only this
> repo's specific instructions.

Core rules, critical patterns, and an index into the full design/ops docs. Keep this file lean — it loads into every prompt. If a topic has a design doc, put detail there and leave only a pointer here.

## Project Overview

**FullCircleMUD** — a text MUD built on Evennia (Python/Django) with real blockchain item ownership on **XRPL**. Domain: **fcmud.world**. This folder (`src/game/`) is the Evennia game module; run `evennia start` from `FCM/src/`.

For folder structure see [ops/ARCHITECTURE.md](../../ops/DEVELOPMENT/ARCHITECTURE.md). For CLI/setup see [ops/DEV_SETUP.md](../../ops/DEVELOPMENT/DEV_SETUP.md). For tests see [ops/TESTING.md](../../ops/DEVELOPMENT/TESTING.md) — **always `tee` multi-package test runs to a file; piping through `grep` eats tracebacks.**

## Security Rules

- **NEVER** run `git diff`, `cat`, `read`, or any command that would display the contents of `server/conf/secret_settings.py`. It is encrypted with git-crypt and holds private keys. When committing changes to it, stage and commit without viewing the diff.

---

## Development Approach

**Architectural decisions go to the user, not me.** Significant design and architectural choices belong to the user for explicit consensus. Present options with honest tradeoffs and let the user direct — never lock in a choice unilaterally, even if framed as a "recommendation" inside a plan or proposal. Two compounding risks make this load-bearing on a 15-repo project:

1. **LLM context gap.** I cannot hold the whole project in context. The user remembers history, constraints, and prior decisions I have lost. That institutional memory is the value the human-in-the-loop provides.
2. **Comprehension debt.** When I make decisions without the user going through the understanding process, the user accrues blind spots over their own codebase and can no longer fill the role above. The slow path of consensus is cheaper than the debt accrued by unilateral speed.

How to apply: present options as options, not as "the design choice"; use AskUserQuestion when the call is non-trivial; if I'd normally pick a default, say "this is open — your call" instead. Trivial mechanical choices within an already-agreed approach (naming, formatting, comment phrasing, helper placement inside a file) are fine to make — the line is *does this shape the architecture or the user's mental model of it?* If yes, it's theirs. The recurring failure mode to watch for: a plan with a "Design choice" section that prescribes an option dressed in supporting rationale. That's unilateral even when it reads as analysis.

**Evennia-first.** Before designing or implementing any solution, explore what Evennia already provides natively. Do not build something Evennia has already solved. Check `evennia/` in the venv (`src/venv/Lib/site-packages/evennia/`), search for existing helpers on `DefaultObject`/`DefaultCharacter`/`DefaultRoom`/`DefaultScript`, read the relevant Evennia manager or utility module, and understand how Evennia's sub-methods (e.g. `get_search_candidates`, `at_object_creation`, `at_post_move`) can be overridden or composed. Where Evennia provides partial functionality, prefer **thin wrappers, narrow overrides of sub-methods, and composition over reimplementation**. Build custom solutions only for the gaps Evennia doesn't cover, and document those gaps in the relevant design doc. See [docs/unified-search-system.md](../../docs/unified-search-system.md) § What Evennia Already Provides for an example of this discipline applied.

---

## CRITICAL Rules (never violate)

### Service Encapsulation — game code NEVER calls service classes directly

All blockchain service calls go through an encapsulation layer:

| Asset type | Encapsulation layer | Service called |
|---|---|---|
| Gold | `FungibleInventoryMixin` | `GoldService` |
| Resources | `FungibleInventoryMixin` | `ResourceService` |
| NFT items | `NFTMirrorMixin` (via `BaseNFTItem`) | `NFTService` |
| NFT pets | `NFTPetMirrorMixin` (via `BasePet`) | `NFTService` |

**Why:** the layers pair every service call with a local Evennia state update. Calling a service directly desyncs the mirror DB from in-game attribute state.

**The only code that imports service classes:** the three mixin files above, plus test files.

**Legitimate boundary-crossing exceptions** (intentionally call services / `xrpl_tx` directly): import/export commands, shopkeeper commands, inn commands (AMM price queries), scheduled scripts (spawn/telemetry/saturation/reallocation), and superuser diagnostic commands (`reconcile`, `sync_nfts`, `run_spawns`, `run_telemetry`, `run_saturation`).

### Room/Object lookup — ALWAYS filter by district tag

Evennia's `db_key` is NOT globally unique. Multiple rooms/objects across zones can share a name. The unique identifier is the `dbref`.

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

Alternatives for guaranteed uniqueness: store the `dbref` at build time; add a unique tag; or search within a known room's `.contents`.

### Never use Django queryset bulk deletes on game objects

`ObjectDB.objects.filter(...).delete()` bypasses Evennia's object lifecycle hooks — `at_object_delete()` will not fire, creating orphaned mirror DB records. Always delete individually via `obj.delete()`. Queryset bulk deletes are acceptable ONLY in test `tearDown` for non-Evennia tables.

### Ability score modifiers — compute at check time, NEVER cache

Cached stats (`armor_class`, `initiative_bonus`, `total_hit_bonus`, `total_damage_bonus`, `max_carrying_capacity_kg`, …) store ONLY equipment and spell/potion bonuses. Ability score modifiers (`get_attribute_bonus(score) = floor((score-10)/2)`) and skill mastery bonuses are ALWAYS computed at the point of use.

**Three-layer architecture:**
1. **Tier 1 — Base** (`base_strength`, `base_armor_class`, …) permanent source of truth, set once at creation.
2. **Tier 2 — Current** (`strength`, `armor_class`, `total_hit_bonus`, …) rebuilt from scratch by `_recalculate_stats()` on every equip/unequip/buff change.
3. **Tier 3 — Effective** (`effective_ac`, `effective_hit_bonus`, …) `@property` that adds ability modifier + mastery at read time.

Why Tier 3 exists: ability modifiers are context-dependent (finesse weapons use DEX, monks may use WIS, etc.). Caching them would require cascading recalculation on every ability score change. Computed-at-check-time is simpler and correct.

Documented in code: `BaseActor._recalculate_stats()`, `BaseActor._accumulate_effect()`, `CarryingCapacityMixin`.

### Non-combat advantage/disadvantage — mandatory roll pattern

Two independent systems. **In combat:** advantage is tracked per-target on `CombatHandler` (`advantage_against = {target_id: rounds}`) and consumed by `execute_attack()`. **Out of combat:** boolean flags `db.non_combat_advantage` / `db.non_combat_disadvantage` on the actor.

Every non-combat d20 skill check (picklock, hide, search, pickpocket, stash, perception, …) MUST use `dice.roll_with_advantage_or_disadvantage()`. Raw `random.randint(1, 20)` or `dice.roll("1d20")` are NOT permitted for skill checks.

```python
from utils.dice_roller import dice

has_adv = getattr(character.db, "non_combat_advantage", False)
has_dis = getattr(character.db, "non_combat_disadvantage", False)
roll = dice.roll_with_advantage_or_disadvantage(advantage=has_adv, disadvantage=has_dis)
character.db.non_combat_advantage = False
character.db.non_combat_disadvantage = False
```

Resolution: `(True, True)` cancels to a normal roll. Both flags are consumed after the roll. Combat rolls (attack, flee checks, saving throws in combat) do NOT use this system.

---

## Core Patterns

### Multi-Perspective Messaging

Whenever a character performs a visible action, use multi-perspective messaging so each observer gets the right view.

```python
# Option A: Evennia's $You / $conj (used by wear/wield/hold/get/drop/remove/give)
caller.location.msg_contents(
    "$You() $conj(fire) a glowing missile at {target}!",
    from_obj=caller,
    mapping={"target": target},
)

# Option B: explicit message dict (used by spells)
caller.msg(result["first"])
if target and target != caller and result.get("second"):
    target.msg(result["second"])
if caller.location and result.get("third"):
    caller.location.msg_contents(
        result["third"],
        exclude=[caller, target] if target != caller else [caller],
    )
```

**IMPORTANT:** `from_obj=caller` is required not just for `$You()/$conj()` substitution but also for HIDDEN/INVISIBLE visibility filtering — `RoomBase.msg_contents()` checks `from_obj` before broadcasting. Without it, messages bypass filtering entirely.

For actions where an invisible actor still produces observable side-effects, use `RoomBase.msg_contents_with_invis_alt(normal_msg, invis_msg, from_obj=caller)` (see `cmd_craft.py`, `cmd_repair.py`, `cmd_process.py`).

### Non-blocking XRPL (`deferToThread`)

All XRPL network calls must use `threads.deferToThread()` so the Twisted reactor stays responsive. The sync wrappers in `xrpl_tx.py` / `xrpl_amm.py` are kept as-is — the non-blocking change is at each **callsite**.

```python
from twisted.internet import threads

def func(self):
    caller.msg("|cProcessing...|n")
    d = threads.deferToThread(blocking_fn, arg1, arg2)
    d.addCallback(lambda result: _on_success(caller, result))
    d.addErrback(lambda failure: _on_error(caller, failure))
```

**Thread safety:**
- XRPL / network calls and Django ORM queries run in worker threads (safe — connection-per-thread).
- Evennia `self.db` attribute access must stay on the reactor thread (do it in callbacks).
- All callbacks should check `caller.sessions.count() > 0` for disconnection safety.

**Y/N confirmations:** use `yield` in simple commands; use `get_input()` callbacks in async commands that `deferToThread` (`yield` is incompatible with deferred callbacks).

### Command Architecture

Custom cmdsets merge on top of Evennia defaults via `commands/default_cmdsets.py`:

- `commands/all_char_cmds/cmdset_character_custom.py` → `CharacterCmdSet`
- `commands/account_cmds/cmdset_account_custom.py` → `AccountCmdSet`
- `commands/unloggedin_cmds/cmdset_unloggedin_custom.py` → `UnloggedinCmdSet`
- Class skill cmdsets live in `commands/class_skill_cmdsets/`
- General skill cmdset: `commands/general_skill_cmds/cmdset_general_skills.py`

**Adding a new custom command:**
1. Create `commands/all_char_cmds/cmd_mycommand.py` with a `Command` subclass.
2. Import and `self.add(CmdMyCommand())` in `cmdset_character_custom.py`.
3. Always add instances `()`, not bare class references.

### Key Evennia gotchas

- Use `session.puppet` (not `session.puppets`) to get the character.
- `AttributeProperty` is accessed directly (`account.wallet_address`), not via `.db`.
- Room CmdSets merge automatically — no need to add/remove on player enter/exit.
- `at_after_move` is **deprecated** in Evennia 6.0 — use `at_post_move` instead.
- `at_object_creation()` fires BEFORE `create_object()`'s `attributes` kwarg is applied — `AttributeProperty` values are `None` during this hook. Always create `nohome=True`, set attributes, then `move_to()` when hooks need kwargs or attributes.
- `move_to(**kwargs)` forwards all kwargs to `at_post_move()` — use this to pass `tx_hash`.
- Creating with `location=` triggers `at_post_move` immediately with no way to pass kwargs.
- **NPCs need `call:true()` lock + `_EmptyNPCCmdSet` default** for command visibility. See [docs/npc-quest-system.md](../../docs/npc-quest-system.md).

### Wallet address lookup

```python
# Find an account from a wallet address
from evennia.accounts.models import AccountDB
account = AccountDB.objects.get_by_attribute(key="wallet_address", value=addr)

# Get a character's wallet from a command
wallet = caller.account.attributes.get("wallet_address")
```

### Transaction model

All on-chain XRPL transactions (import/export) are signed by players via Xaman wallet. The game server creates payloads and polls for results but never holds private keys or pays transaction fees. See [docs/import-export.md](../../docs/import-export.md).

---

## Coding Conventions

- **Prefer enums over raw strings** for validation and typo prevention. When a field references a fixed set of values (ability scores, weapon types, alignments, damage types, skills, …), use the enum: `WeaponType.BATTLEAXE` not `"battleaxe"`, `Ability.STR` not `"strength"`, `skills.STEALTH.value` not `"stealth"`. Skill commands should set `skill = skills.ENUM.value` so renaming a skill in the enum propagates.
- **All exits are authored in YAML** (`exits:` blocks on rooms in the fcm-world repo) and built by `wb_build` via the `evennia-world-builder` library. Runtime exit creation (procedural dungeons, conditional rebinds) MUST go through helpers in `utils/exit_helpers.py` — never bare `create_object()`. If a new exit type isn't covered by an existing helper, create the helper first. Available helpers: `connect_bidirectional_exit`, `connect_bidirectional_door_exit`, `connect_bidirectional_trapped_door_exit`, `connect_bidirectional_tripwire_exit`, `connect_oneway_loopback_exit`. See [docs/exit-architecture.md](../../docs/exit-architecture.md) § Builder Helpers and [docs/world-deployment.md](../../docs/world-deployment.md) for the authoring pipeline.

---

## Documentation Hierarchy

- **Design docs** (`design/*.md`) are the **primary source of truth** for design, intent, constraints, and architecture.
- **This file (CLAUDE.md)** stays lean — core rules, critical patterns, and a pointer index. Detail lives in the design docs.
- **Ops docs** (`ops/*.md`) hold operational / developer-facing references (setup, testing, runbooks, help categories, folder map).
- **Planning** (`ops/PLANNING/`) captures future work state.
- **When making changes:** update the relevant design or ops doc first, then update CLAUDE.md pointers if needed. If no suitable doc exists, ask the user where to capture the information.

---

## Index — where to look for what

### Design (`design/`) — systems & mechanics

| Topic | Doc |
|---|---|
| Unified search & targeting (scopes, predicates, resolvers, name matching) | [UNIFIED_SEARCH_SYSTEM.md](../../docs/unified-search-system.md) |
| Combat, weapons, stealth, parry/riposte, height combat | [COMBAT_SYSTEM.md](../../docs/combat-system.md) |
| Effects, conditions, damage pipeline, DamageResistanceMixin | [EFFECTS_SYSTEM.md](../../docs/effects-system.md) |
| Spells, schools, spellbooks, scrolls, recipe catalog | [SPELL_SKILL_DESIGN.md](../../docs/spell-skill-design.md) |
| Crafting, processing, enchanting, recipes | [CRAFTING_SYSTEM.md](../../docs/crafting-system.md) |
| NPCs, quests, trainers, guildmasters, shopkeepers | [NPC_QUEST_SYSTEM.md](../../docs/npc-quest-system.md) |
| NPC/mob class hierarchy, AI mixins, tier system | [NPC_MOB_ARCHITECTURE.md](../../docs/npc-mob-architecture.md) |
| Combat AI memory, strategy bot | [COMBAT_AI_MEMORY.md](../../docs/combat-ai-memory.md) |
| LLM NPC lore memory, embeddings | [LORE_MEMORY.md](../../docs/lore-memory.md) |
| Inventory, equipment, wearslots, weight, NFT ownership model, durability | [INVENTORY_EQUIPMENT.md](../../docs/inventory-equipment.md) |
| Economy, pricing, markets, spawn algorithms, SINK, reallocation | [ECONOMY.md](../../docs/economy.md) |
| Unified spawn system (resources / gold / rare NFTs / knowledge) | [UNIFIED_ITEM_SPAWN_SYSTEM.md](../../docs/unified-item-spawn-system.md) |
| Mob spawning (population, respawn, area tags, hooks) | [SPAWN_MOBS.md](../../docs/spawn-mobs.md) |
| Economy telemetry, snapshots, velocity categories | [TELEMETRY.md](../../docs/telemetry.md) |
| Treasury, fiscal discipline, vault architecture | [TREASURY.md](../../docs/treasury.md) |
| Subscriptions, trials, gated commands | [SUBSCRIPTIONS.md](../../docs/subscriptions.md) |
| Import / export / wallet flow, deferToThread, replay protection | [IMPORT_EXPORT.md](../../docs/import-export.md) |
| Database architecture, 4-DB layout, pgvector | [DATABASE.md](../../docs/database.md) |
| World lore, zones, districts | [WORLD.md](../../docs/world.md) |
| New player experience, tutorial, Millholm onboarding | [NEW_PLAYER_EXPERIENCE.md](../../docs/new-player-experience.md) |
| Inter-zone travel, sail, cartography mastery gates | [INTERZONE_TRAVEL.md](../../docs/interzone-travel.md) |
| Intra-zone cartography, `survey` / `map` | [CARTOGRAPHY.md](../../docs/cartography.md) |
| Procedural dungeons, instance lifecycle | [PROCEDURAL_DUNGEONS.md](../../docs/procedural-dungeons.md) |
| Vertical movement, flying, swimming, climbing | [VERTICAL_MOVEMENT.md](../../docs/vertical-movement.md) |
| Exit types, doors, traps, builder helpers | [EXIT_ARCHITECTURE.md](../../docs/exit-architecture.md) |
| Room architecture, banking / crafting / harvesting rooms | [ROOM_ARCHITECTURE.md](../../docs/room-architecture.md) |
| World objects, fixtures, climbables, searchables | [WORLD_OBJECTS.md](../../docs/world-objects.md) |
| Pets and mounts | [PETS_AND_MOUNTS.md](../../docs/pets-and-mounts.md) |
| Alignment system | [ALIGNMENT_SYSTEM.md](../../docs/alignment-system.md) |
| Language system, garbling, racial languages | [LANGUAGE_SYSTEM.md](../../docs/language-system.md) |
| Survival (hunger, thirst) | [SURVIVAL_SYSTEM.md](../../docs/survival-system.md) |
| Weapon damage scaling by tier × mastery | [WEAPON_DAMAGE_SCALING.md](../../docs/weapon-damage-scaling.md) |
| Races, classes, point buy, remort | [CHARACTER_PROGRESSION.md](../../docs/character-progression.md) |
| Compliance strategy, token classification | [COMPLIANCE.md](../../docs/compliance.md) |
| Website, markets page, frontend | [WEBSITE.md](../../docs/website.md) |
| Connection transport, WebSocket-only rationale, telnet/SSH limitations | [CONNECTION_TRANSPORT.md](../../docs/connection-transport.md) |

### Ops (`ops/`) — dev, runbooks, infra

| Topic | Doc |
|---|---|
| Folder map / subsystem tree | [ARCHITECTURE.md](../../ops/DEVELOPMENT/ARCHITECTURE.md) |
| Developer setup, venv, CLI, migrations | [DEV_SETUP.md](../../ops/DEVELOPMENT/DEV_SETUP.md) |
| Running tests, base classes, common patterns | [TESTING.md](../../ops/DEVELOPMENT/TESTING.md) |
| Diagnosing slow operations — measure-bisect-pinpoint methodology | [PERFORMANCE_DIAGNOSIS.md](../../ops/DEVELOPMENT/PERFORMANCE_DIAGNOSIS.md) |
| Deployment, Railway, branching, multisig | [DEPLOYMENT.md](../../ops/DEVELOPMENT/DEPLOYMENT.md) |
| Compliance legal framework | [COMPLIANCE_LEGAL.md](../../ops/COMPLIANCE_LEGAL.md) |
| Compliance website checklist | [COMPLIANCE_WEBSITE_CHECKLIST.md](../../ops/COMPLIANCE_WEBSITE_CHECKLIST.md) |
| Release phasing (Pre-Alpha → Launch) | [DEVELOPMENT_PHASE_PLAN.md](../../ops/DEVELOPMENT/DEVELOPMENT_PHASE_PLAN.md) |
