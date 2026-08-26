r"""
Evennia settings file.

The available options are found in the default settings file found
here:

https://www.evennia.com/docs/latest/Setup/Settings-Default.html

Remember:

Don't copy more from the default file than you actually intend to
change; this will make sure that you don't overload upstream updates
unnecessarily.

When changing a setting requiring a file system path (like
path/to/actual/file.py), use GAME_DIR and EVENNIA_DIR to reference
your game folder and the Evennia library folders respectively. Python
paths (path.to.module) should be given relative to the game's root
folder (typeclasses.foo) whereas paths within the Evennia library
needs to be given explicitly (evennia.foo).

If you want to share your game dir, including its settings, you can
put secret game- or server-specific settings in secret_settings.py.

"""

import json
import os
import sys

# ── macOS only: use a bundled, non-Apple SQLite build ────────────────
#
# macOS ships /usr/lib/libsqlite3.dylib, which runs sqlite3_initialize()
# through libdispatch. libdispatch cannot survive fork(), and twistd
# daemonizes with a double fork and never exec()s — so once any SQLite
# connection has been opened, every SQLite call in the daemonized child
# blocks forever on a dispatch queue nothing will service. There is no
# exception, no timeout and nothing in any log: `evennia start` just
# prints "Server starting  ..." and never returns.
#
# A connection is always open by then: evennia._init() imports
# evennia/utils/gametime.py, which runs a ServerConfig query at module
# scope.
#
# sqlean.py ships a statically-linked SQLite, so Apple's library is never
# loaded. This must run before anything imports sqlite3 — once the stdlib
# module is cached, Django's backend gets Apple's build regardless.
#
# Lives here rather than in settings_common_shard_config.py because this
# file is the one every role loads (monolith directly; router and shards
# through the cascade), and monolith forks too.
#
# Inert on Linux: the requirements marker excludes the package there,
# so the import fails and this block is skipped.
# See libraries/evennia-shards/docs/deployment-topology.md § macOS.
#
# Skipped in Postgres mode as well. The shim protects SQLite connections
# across twistd's fork; when DATABASE_URL is set no SQLite connection is
# ever opened, so there is nothing for it to protect and no reason to
# swap out the stdlib module.
#
# It does NOT fix the same hazard for Postgres. `evennia start` against
# local Postgres on macOS hangs at "Server starting ..." in exactly the
# way described above — silent, no traceback, nothing in any log — and
# skipping this block changes nothing, which is how sqlean was ruled out
# as the cause. psycopg2-binary brings its own C libraries through the
# fork and has no statically-linked equivalent. Linux is unaffected, so
# deployed environments do not see it.
if sys.platform == "darwin" and not os.environ.get("DATABASE_URL"):
    try:
        import sqlean
        import sqlean.dbapi2

        # sqlean's DBAPI predates Connection.getlimit(), which Django 6
        # calls when sizing bulk_create batches. Its Connection is an
        # immutable C type, so the method goes on a subclass installed
        # via connect(factory=...).
        class _FCMSQLiteConnection(sqlean.dbapi2.Connection):
            def getlimit(self, category):
                return 999  # SQLite's conservative historical default

        _sqlean_connect = sqlean.dbapi2.connect

        def _connect(*args, **kwargs):
            kwargs.setdefault("factory", _FCMSQLiteConnection)
            return _sqlean_connect(*args, **kwargs)

        sqlean.dbapi2.connect = _connect
        sqlean.connect = _connect
        sqlean.SQLITE_LIMIT_VARIABLE_NUMBER = 9
        sqlean.dbapi2.SQLITE_LIMIT_VARIABLE_NUMBER = 9

        sys.modules["sqlite3"] = sqlean
        sys.modules["sqlite3.dbapi2"] = sqlean.dbapi2
    except ImportError:
        pass

import dj_database_url

# Use the defaults from Evennia unless explicitly overridden
from evennia.settings_default import *  # noqa: F403, F401 — provides DATABASES, GAME_DIR, etc.

# Register custom Django apps
INSTALLED_APPS = INSTALLED_APPS + [
    "blockchain.xrpl",
    "ai_memory",
    "subscriptions",
    "telemetry",
    "django.contrib.sitemaps",
    "evennia_world_builder",
    "evennia_mob_spawner",
    "evennia_archive",
]

# Bind to loopback only. nginx is the sole client of these ports and
# reaches them over 127.0.0.1; players arrive on 443 and are proxied in.
# AMP_INTERFACE is already 127.0.0.1 by Evennia's default.
WEBSERVER_INTERFACES = ['127.0.0.1']
WEBSOCKET_CLIENT_INTERFACE = '127.0.0.1'
LOCKDOWN_MODE = False

# ── Public hostname ──────────────────────────────────────────────────
# One variable names the deployment; everything below is derived from it,
# so a cutover to a new hostname is a one-word edit in /etc/fcm/env.
# Unset means local dev, where each derived setting keeps its old value.
#
# Every derived setting still honours its own env var, so a box can
# override any one of them without abandoning the pattern.
FCM_HOSTNAME = os.environ.get("FCM_HOSTNAME", "")

# The name the server advertises (website context, game listings).
SERVER_HOSTNAME = FCM_HOSTNAME or "localhost"

# Websocket URL for the webclient. nginx terminates TLS and demuxes by
# path, so this is a path on the game's own hostname.
WEBSOCKET_CLIENT_URL = os.environ.get(
    "WEBSOCKET_CLIENT_URL",
    f"wss://{FCM_HOSTNAME}/ws/" if FCM_HOSTNAME else "ws://localhost:4002",
)

# ── Database Configuration ────────────────────────────────────────────
# Each alias resolves its own connection, in this order:
#
#   1. DATABASE_URL_<ALIAS>  this alias gets its own Postgres instance
#   2. DATABASE_URL          share the default's Postgres instance
#   3. SQLite file           local dev, one file per alias
#
# So which alias lives on which instance is a deployment decision rather
# than a code one. Moving an alias onto separate compute is one variable
# plus a dump/restore (or a fresh migrate) — nothing here changes.
#
# `default` is deliberately bare DATABASE_URL with no _DEFAULT synonym:
# it is the established contract every deploy already sets.
# See design/database.md for the full architecture.
from server.conf import db_config

_DATABASE_URL = os.environ.get("DATABASE_URL")

# The non-default aliases, and the SQLite file each falls back to.
# `default` is absent because it is the special case below.
_DB_ALIASES = {
    "xrpl": "xrpl.db3",
    "ai_memory": "ai_memory.db3",
    "subscriptions": "subscriptions.db3",
    # Play sessions and the hourly snapshots. Kept off the xrpl database
    # because it is the record of who owns what and must survive a world
    # rebuild; telemetry is append-only measurement of the same economy,
    # and the two have no row that references the other.
    "telemetry": "telemetry.db3",
    # A clone of Evennia's own schema holding archived accounts and
    # characters, so a world rebuild does not cost us our players. Never
    # run as a game — starting a server against it would populate it.
    "archive": "archive.db3",
}

# `default` is handled here rather than through resolve_database() for two
# reasons: it takes bare DATABASE_URL with no _DEFAULT override, and in
# SQLite mode it must keep Evennia's own inherited evennia.db3 config
# rather than have a fresh one built over the top of it.
if _DATABASE_URL:
    _default_config = dj_database_url.parse(_DATABASE_URL)
    _default_config["CONN_MAX_AGE"] = db_config.CONN_MAX_AGE
    db_config.apply_session_options(_default_config)
    DATABASES["default"] = _default_config  # type: ignore[name-defined]

# resolve_database() lives in server/conf/db_config.py
for _alias, _sqlite_file in _DB_ALIASES.items():
    DATABASES[_alias] = db_config.resolve_database(  # type: ignore[name-defined]
        _alias, _sqlite_file, GAME_DIR, os.environ  # type: ignore[name-defined]
    )

# ── Database routers ──────────────────────────────────────────────────
# A router is needed for exactly those aliases that are a physically
# different database from `default`. Both existing modes fall out of that
# rule unchanged: locally every alias is its own SQLite file, so all
# three are active; on one shared Postgres instance every alias is the
# same database, so none are.
#
# Enabling a router in the shared case would be actively harmful — its
# allow_migrate() would refuse to create the non-default tables while
# Django still recorded those migrations as applied.
#
# The corollary: an alias with an active router is not reached by a bare
# `migrate` and needs `migrate --database <alias>`. deploy_migrate.py
# reads that off DATABASE_ROUTERS so the two cannot drift.
_ROUTER_PATHS = {
    "xrpl": "blockchain.xrpl.db_router.XRPLRouter",
    "ai_memory": "ai_memory.db_router.AiMemoryRouter",
    "subscriptions": "subscriptions.db_router.SubscriptionsRouter",
    "telemetry": "telemetry.db_router.TelemetryRouter",
    # Unlike the three above, this router is deliberately not exclusive:
    # Evennia's own tables belong in the archive, since it is a clone of
    # Evennia's schema rather than a home for one app's models.
    "archive": "evennia_archive.db_router.ArchiveRouter",
}

# active_routers() lives in server/conf/db_config.py
DATABASE_ROUTERS = db_config.active_routers(DATABASES, _ROUTER_PATHS)  # type: ignore[name-defined]

# Django secret key — used to sign cookies/sessions.
# Deployed, set SECRET_KEY in /etc/fcm/env. Locally, override in
# secret_settings.local.
SECRET_KEY = os.environ.get("SECRET_KEY", "changeme-set-in-secret-settings")

# Host header allowlist — derived from FCM_HOSTNAME, '*' in dev. Set
# ALLOWED_HOSTS explicitly (comma-separated) only to serve more than one
# name, e.g. during a cutover where the old name must keep working.
ALLOWED_HOSTS = [
    h.strip()
    for h in os.environ.get("ALLOWED_HOSTS", FCM_HOSTNAME or "*").split(",")
    if h.strip()
]

# In-game traceback display — on in dev for visibility, off in prod to
# avoid leaking internals to players. Set IN_GAME_ERRORS=false in any
# deployed environment.
IN_GAME_ERRORS = os.environ.get("IN_GAME_ERRORS", "true").lower() in ("true", "1", "yes")

######################################################################
# Evennia base server config
######################################################################

# This is the name of your game. Make it catchy!
SERVERNAME = "FullCircleMUD"
# Short one-sentence blurb describing your game. Shown under the title
# on the website and could be used in online listings of your game etc.
GAME_SLOGAN = "A 21st Century take on a fantasy themed MUD."
# Disable Telnet
TELNET_ENABLED = False
# Disable SSH
SSH_ENABLED = False
WEBSOCKET_PROTOCOL_CLASS = "server.walletwebclient.WalletWebSocketClient"

# Read from the environment by Evennia's launcher when it auto-creates
# the superuser, and from settings by FCM's connect command.
EVENNIA_SUPERUSER_USERNAME = os.environ.get("EVENNIA_SUPERUSER_USERNAME", "")
EVENNIA_SUPERUSER_PASSWORD = os.environ.get("EVENNIA_SUPERUSER_PASSWORD", "")


# Default password for wallet-authenticated accounts.
# Wallet signature is the real auth — this just satisfies Evennia's Account.create().
DEFAULT_ACCOUNT_PASSWORD = os.environ.get("DEFAULT_ACCOUNT_PASSWORD", "CHANGE_ME")

# Typeclass for account objects (linked to a character) (fallback)
BASE_ACCOUNT_TYPECLASS = "typeclasses.accounts.accounts.Account"

# Typeclass for character objects linked to an account (fallback)
BASE_CHARACTER_TYPECLASS = "typeclasses.actors.character.FCMCharacter"

# overrides the evennia default whcih points to typeclasses.scripts.Script 
# which has been deleted (and is just a thin wrapper of DefaultScript anyway)
BASE_SCRIPT_TYPECLASS = "evennia.DefaultScript"

# this means a new account doesn;t auto generate a new character
AUTO_CREATE_CHARACTER_WITH_ACCOUNT = False
AUTO_PUPPET_ON_LOGIN = False
MAX_NR_CHARACTERS = 4
MAX_NR_SESSIONS_PER_ACCOUNT = 1
DEBUG = False
# A list, and the brackets are load-bearing: ('x') is the string 'x', not a
# tuple. Django validates ADMINS while logging any error response, so a
# malformed value turns every 4xx into a 500 whose traceback describes the
# mail handler rather than the original fault.
ADMINS = ["tim@timbaird.com"]
PUPPET_LOOK_ON_IC = False

######################################################################
# XRPL / BLOCKCHAIN SETTINGS
######################################################################
SUPERUSER_XRPL_WALLET_ADDRESS = os.environ.get("SUPERUSER_XRPL_WALLET_ADDRESS", "")  # dev wallet (superuser default)

# ── XRPL Configuration ──────────────────────────────────────────────
XRPL_IMPORT_EXPORT_ENABLED = os.environ.get("XRPL_IMPORT_EXPORT_ENABLED", "").lower() in ("true", "1")
# XRPL network endpoint. Mainnet everywhere — staging and production
# share one ledger, so this is the same in every environment.
XRPL_NETWORK_URL = "wss://xrplcluster.com" # alternative "wss://s1.ripple.com"
XRPL_ISSUER_ADDRESS = os.environ.get("XRPL_ISSUER_ADDRESS", "")
XRPL_VAULT_ADDRESS = os.environ.get("XRPL_VAULT_ADDRESS", "")
XRPL_GOLD_CURRENCY_CODE = "FCMGold"
XRPL_PGOLD_CURRENCY_CODE = "PGold"

XRPL_VAULT_WALLET_SEED = os.environ.get("XRPL_VAULT_WALLET_SEED", "")  # vault wallet seed for server-signed txns

# ── Multisig Co-Signing ──────────────────────────────────────────
# When enabled, vault transactions are multisigned via the co-signing service
# instead of single-signed by the vault seed directly.
# See design/DEPLOYMENT.md § Vault Signing & Multisig.
XRPL_MULTISIG_ENABLED = os.environ.get("XRPL_MULTISIG_ENABLED", "").lower() in ("true", "1")
XRPL_COSIGNER_URL = os.environ.get("XRPL_COSIGNER_URL", "")  # e.g. "https://cosigner.fcmud.world"
XRPL_COSIGNER_API_KEY = os.environ.get("XRPL_COSIGNER_API_KEY", "")

# ── Xaman (XRPL Wallet) API ──────────────────────────────────────
# Register at https://apps.xaman.dev/ to obtain credentials.
XAMAN_API_KEY = os.environ.get("XAMAN_API_KEY", "PLACEHOLDER")
XAMAN_API_SECRET = os.environ.get("XAMAN_API_SECRET", "PLACEHOLDER")

# ── Subscription Payment ──────────────────────────────────────────
# Master toggle — set to False to disable all subscription gating.
# Pre-alpha: False, Alpha: True, Beta: True
SUBSCRIPTION_ENABLED = os.environ.get("SUBSCRIPTION_ENABLED", "false").lower() in ("true", "1", "yes")
# Payment currency (RLUSD on XRPL mainnet).
SUBSCRIPTION_CURRENCY_CODE = "RLUSD"
SUBSCRIPTION_CURRENCY_ISSUER = "rMxCKbEDwqr76QuheSUMdEGf4B9xJ8m5De"  # RLUSD issuer, XRPL mainnet
# Payment destination — subscription revenue goes to the issuer wallet.
SUBSCRIPTION_PAYMENT_DESTINATION = XRPL_ISSUER_ADDRESS
# Free trial for new accounts (hours). Set to 0 to disable.
SUBSCRIPTION_TRIAL_HOURS = 48
# Superuser and bot accounts bypass subscription checks entirely.
SUBSCRIPTION_BYPASS_SUPERUSER = True


######################################################################
# LEGAL / COMPLIANCE SETTINGS
######################################################################

# Public-facing website URL — used for in-game ToS links and compliance notices.
# Overridable so a non-production environment points players at its own site
# rather than sending them to production for the terms they agreed to there.
GAME_WEBSITE_URL = os.environ.get(
    "GAME_WEBSITE_URL",
    f"https://{FCM_HOSTNAME}" if FCM_HOSTNAME else "https://fcmud.world",
)

# NFT image base URL — convention: {base_url}{prototype_key}.png
NFT_IMAGE_BASE_URL = "https://njqdijnpujooixoehbms.supabase.co/storage/v1/object/public/FCMImages/"

# Terms of Service version string. Bump this when the ToS changes.
# Future: at_account_login can check account.db.tos_version != TOS_VERSION
# and force re-acceptance before play is permitted.
TOS_VERSION = "draft-1"

######################################################################
# LLM / AI SETTINGS
######################################################################


# Bot / Virtual Client login
BOT_LOGIN_ENABLED = os.environ.get("BOT_LOGIN_ENABLED", "").lower() in ("true", "1")  # master switch
# Bot account names: set BOT_ACCOUNT_USERNAMES_JSON env var as a JSON array,
# e.g. '["llm_bot_1", "llm_bot_2"]'
_bot_names_json = os.environ.get("BOT_ACCOUNT_USERNAMES_JSON", "")
BOT_ACCOUNT_USERNAMES = json.loads(_bot_names_json) if _bot_names_json else []

# Bot wallet addresses: set BOT_WALLET_ADDRESSES_JSON env var as a JSON object,
# e.g. '{"llm_bot_1": "rABC...", "llm_bot_2": "rDEF..."}'
_bot_wallets_json = os.environ.get("BOT_WALLET_ADDRESSES_JSON", "")
BOT_WALLET_ADDRESSES = json.loads(_bot_wallets_json) if _bot_wallets_json else {}

# Bot passwords: set BOT_PASSWORDS_JSON env var as a JSON object,
# e.g. '{"llm_bot_1": "pass1", "llm_bot_2": "pass2"}'
# Default shared password used if a bot isn't in BOT_PASSWORDS.
BOT_DEFAULT_PASSWORD = os.environ.get("BOT_DEFAULT_PASSWORD", "changeme")
_bot_pw_json = os.environ.get("BOT_PASSWORDS_JSON", "")
BOT_PASSWORDS = json.loads(_bot_pw_json) if _bot_pw_json else {}


# LLM NPC Configuration
LLM_ENABLED = True                                 # master switch for all LLM NPCs
LLM_API_BASE_URL = "https://openrouter.ai/api/v1"  # OpenRouter endpoint
LLM_API_KEY = os.environ.get("LLM_API_KEY", "")
LLM_DEFAULT_MODEL = "openai/gpt-4o-mini"           # cheap + capable (proven in bot testing)
LLM_GLOBAL_MAX_CALLS_PER_MINUTE = 60               # across ALL NPCs combined
LLM_PER_NPC_MAX_CALLS_PER_MINUTE = 6               # per individual NPC
LLM_PER_NPC_COOLDOWN_SECONDS = 5                   # min gap between calls for same NPC
LLM_DAILY_COST_LIMIT_CENTS = 500                   # $5/day hard cap — disable all if exceeded

# Embedding settings — for vector memory (ai_memory app)
LLM_EMBEDDING_MODEL = "text-embedding-3-small"       # 1536 dims, ~$0.02/1M tokens
LLM_EMBEDDING_API_BASE_URL = "https://api.openai.com/v1"  # OpenAI direct (not OpenRouter)
LLM_EMBEDDING_API_KEY = os.environ.get("LLM_EMBEDDING_API_KEY", "")

# Skill XP — supplementary XP for using class skills (bash, spells, picklock, etc.)
SKILL_XP_ENABLED = True

######################################################################
# GAME PLAY SETTINGS
######################################################################

# ── Gold Display ──────────────────────────────────────────────────────
GOLD_DISPLAY = {"name": "Gold", "unit": "coins", "description": "Gold coins."}
GOLD_WEIGHT_PER_UNIT_KG = 0.01  # 10 grams per coin (100 coins = 1 kg)


# Game Time — Day/Night Cycle
# 24x speed: 1 real hour = 1 game day (24 game hours)
TIME_FACTOR = 24
# Epoch: None = server first-start time. Set to a Unix timestamp for
# a fixed starting date (e.g. int(datetime(2026, 1, 1).timestamp())).
TIME_GAME_EPOCH = None

# Derive game time from wall clock rather than from accumulated uptime.
#
# Evennia's other mode tracks uptime in a per-process module global that every
# Server process writes back to a single ServerConfig row every 60 seconds. That
# is safe with one process and unsafe with several: under sharding the router and
# each shard overwrite one another every minute, and a process that reloads can
# read a lower total than it held — moving game time backwards. Seasons running
# backwards have no narrative cover.
#
# Wall-clock mode bypasses that accumulator entirely. Every term is a settings
# constant, a database constant written once at creation, or the OS clock — so
# all processes agree with no coordination and nothing to persist per tick.
#
# What it costs: game time advances while the server is down.
#
# Turning this off is NOT a one-line reversal under sharding — it reintroduces
# the multi-writer race, and would first require making the accumulator
# single-writer. See docs/scaling.md § Game time for that design.
TIME_IGNORE_DOWNTIMES = True

# Survival upkeep cycle (hunger today, thirst + future meters tomorrow)
SURVIVAL_TICK_INTERVAL = 1200  # IN SECONDS - ONCE EVERY 20 MINUTES = 3 X PER GAME DAY
HUNGER_TICK_INTERVAL = SURVIVAL_TICK_INTERVAL  # back-compat alias for forage cooldown / older imports

# combat tick interval (seconds) — how often each combatant acts.
# All weapons share the same tick. Float for fine-tuning (e.g. 3.5, 4.5).
COMBAT_TICK_INTERVAL = 4.0


######################################################################
# GEO-DETECTION SETTINGS
######################################################################

# Mock geo country for development (no Cloudflare in dev environment).
# 'PY' = eligible (Variant B — full financial copy)
# 'US' = restricted (Variant A — no RLUSD/redemption copy)
# 'XX' = unknown (fail-closed → Variant A)
# Remove or guard with `if DEBUG:` before production deploy — Cloudflare
# header takes precedence whenever it is present.
#DEV_GEO_COUNTRY = 'PY'
DEV_GEO_COUNTRY = 'US'

# Community links — update here when these change, no template edits needed.
DISCORD_URL = 'https://discord.gg/j8b5GkysM3'
GITHUB_URL = 'https://github.com/fullcirclemud'

# Whether to log player geo data (IP hash + country code) on login.
# Set to True if jurisdictional tracking is needed in the future.
# When False, the login_history attribute is not written to.
LOG_PLAYER_GEO_DATA = False

# Jurisdictions classified as Variant B (eligible).
# Configurable here so the list can be updated without code changes.
# Currently unused — all visitors see the same content.
GEO_ELIGIBLE_COUNTRIES = {
    'PY', 'UY', 'AR', 'BR', 'MX', 'CO', 'SV', 'GT', 'HN', 'PA', 'CR',  # Latin America
    'NG', 'KE', 'GH', 'ZA',                                                # Africa
    'PH', 'VN', 'TH', 'ID', 'MY',                                          # SE Asia
    'AE', 'GE',                                                             # Middle East / E. Europe
}

# Append geo middleware after Evennia's session/auth middleware.
MIDDLEWARE = list(MIDDLEWARE) + ['web.middleware.geo.GeoDetectionMiddleware']  # type: ignore[name-defined]

# Inject geo_variant + geo_country into every template context.
TEMPLATES[0]['OPTIONS']['context_processors'] += [  # type: ignore[index]
    'web.middleware.geo.geo_context',
    'web.middleware.analytics.google_analytics_context',
]


# ── Typeclasses ──────────────────────────────────────────────────────
# Exits built without an explicit typeclass (@dig, @open, @tunnel) get
# the same base every authored exit uses, so they inherit the height,
# size and encumbrance gating rather than bypassing the exit chain.
BASE_EXIT_TYPECLASS = "typeclasses.terrain.exits.exit_vertical_aware.ExitVerticalAware"


# ── World builder ────────────────────────────────────────────────────
# Reads YAML world content from the FullCircleMUD/fcm-world repo.
# WORLDBUILDER_GITHUB_PAT is the secret — set it in secret_settings.local
# locally, or in /etc/fcm/env when deployed. The reader kwargs
# dict is composed at the bottom of this file, AFTER secret_settings is
# loaded, so the PAT override propagates.
WORLDBUILDER_READER = "evennia_yaml_reader.github.GitHubReader"
WORLDBUILDER_REPO = "FullCircleMUD/fcm-world"
WORLDBUILDER_REF = os.environ.get("WORLDBUILDER_REF", "main")
WORLDBUILDER_GITHUB_PAT = os.environ.get("WORLDBUILDER_GITHUB_PAT", "")

# ── Mob spawner ──────────────────────────────────────────────────────
# Reads YAML mob spawn rules from the FullCircleMUD/fcm-mobs repo.
# MOB_SPAWNER_GITHUB_PAT is the secret — set it in secret_settings.local
# locally, or in /etc/fcm/env when deployed. The reader kwargs
# dict is composed at the bottom of this file, AFTER secret_settings is
# loaded, so the PAT override propagates.
MOB_SPAWNER_READER = "evennia_yaml_reader.github.GitHubReader"
MOB_SPAWNER_REPO = "FullCircleMUD/fcm-mobs"
MOB_SPAWNER_REF = os.environ.get("MOB_SPAWNER_REF", "main")
MOB_SPAWNER_GITHUB_PAT = os.environ.get("MOB_SPAWNER_GITHUB_PAT", "")


######################################################################
# Local development overrides.
#
# In dev, secrets live in server/conf/secret_settings.local — a
# git-crypt encrypted file. The non-.py extension keeps the encrypted
# bytes away from anything that scans the tree for Python source, so we
# load it manually via importlib.util.
#
# When DATABASE_URL is set (deployed) we skip this entirely — secrets
# come from the environment, loaded from /etc/fcm/env.
######################################################################
if not os.environ.get("DATABASE_URL"):
    import importlib.util as _importlib_util
    from importlib.machinery import SourceFileLoader as _SourceFileLoader

    _secret_path = os.path.join(
        os.path.dirname(__file__), "secret_settings.local"
    )
    if os.path.exists(_secret_path):
        try:
            # .local isn't a recognised Python source extension so we
            # have to hand spec_from_file_location an explicit loader.
            _loader = _SourceFileLoader("secret_settings", _secret_path)
            _spec = _importlib_util.spec_from_file_location(
                "secret_settings", _secret_path, loader=_loader
            )
            _mod = _importlib_util.module_from_spec(_spec)
            _spec.loader.exec_module(_mod)
            for _attr in dir(_mod):
                if not _attr.startswith("_"):
                    globals()[_attr] = getattr(_mod, _attr)
        except Exception as _err:  # pragma: no cover
            print(f"secret_settings.local failed to load: {_err}")

# Compose world-builder reader kwargs after secret_settings has loaded
# so any override of WORLDBUILDER_GITHUB_PAT / REPO / REF takes effect.
WORLDBUILDER_READER_KWARGS = {
    "repo": WORLDBUILDER_REPO,
    "ref": WORLDBUILDER_REF,
    "pat": WORLDBUILDER_GITHUB_PAT,
}

# Compose mob-spawner reader kwargs after secret_settings has loaded
# so any override of MOB_SPAWNER_GITHUB_PAT / REPO / REF takes effect.
MOB_SPAWNER_READER_KWARGS = {
    "repo": MOB_SPAWNER_REPO,
    "ref": MOB_SPAWNER_REF,
    "pat": MOB_SPAWNER_GITHUB_PAT,
}
