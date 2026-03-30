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

import os

import dj_database_url

# Use the defaults from Evennia unless explicitly overridden
from evennia.settings_default import *  # noqa: F403, F401 — provides DATABASES, GAME_DIR, etc.

# Register custom Django apps
INSTALLED_APPS = INSTALLED_APPS + ["blockchain.xrpl", "ai_memory"]

WEBSOCKET_CLIENT_INTERFACE = '0.0.0.0'
SERVER_HOSTNAME = '0.0.0.0'
LOCKDOWN_MODE = False

# ── Database Configuration ────────────────────────────────────────────
# DATABASE_URL controls the backend:
#   - Set (Railway/production): PostgreSQL for all 3 databases
#   - Not set (local dev): SQLite files, zero config
# See design/DATABASE.md for full architecture documentation.
_DATABASE_URL = os.environ.get("DATABASE_URL")

if _DATABASE_URL:
    # PostgreSQL mode — all three aliases share one physical PG database.
    # The routers ensure each app's tables migrate to the correct alias.
    _pg_config = dj_database_url.parse(_DATABASE_URL)
    _pg_config["CONN_MAX_AGE"] = 600

    DATABASES["default"] = _pg_config  # type: ignore[name-defined]
    DATABASES["xrpl"] = {**_pg_config}  # type: ignore[name-defined]
    DATABASES["ai_memory"] = {**_pg_config}  # type: ignore[name-defined]
else:
    # SQLite mode — local development. Default DB inherited from
    # evennia.settings_default (evennia.db3). Custom DBs below.
    # Migrate with: evennia migrate --database xrpl
    DATABASES["xrpl"] = {  # type: ignore[name-defined]
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": os.path.join(GAME_DIR, "server", "xrpl.db3"),  # type: ignore[name-defined]
    }
    # Migrate with: evennia migrate --database ai_memory
    DATABASES["ai_memory"] = {  # type: ignore[name-defined]
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": os.path.join(GAME_DIR, "server", "ai_memory.db3"),  # type: ignore[name-defined]
    }

DATABASE_ROUTERS = [
    "blockchain.xrpl.db_router.XRPLRouter",
    "ai_memory.db_router.AiMemoryRouter",
]

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

# Override in secret_settings.py
SUPERUSER_ACCOUNT_NAME = ""

# Default password for wallet-authenticated accounts.
# Wallet signature is the real auth — this just satisfies Evennia's Account.create().
# Override in secret_settings.py.
DEFAULT_ACCOUNT_PASSWORD = "CHANGE_ME"

# Typeclass for account objects (linked to a character) (fallback)
BASE_ACCOUNT_TYPECLASS = "typeclasses.accounts.accounts.Account"

# Typeclass for character objects linked to an account (fallback)
BASE_CHARACTER_TYPECLASS = "typeclasses.actors.character.FCMCharacter"

# this means a new account doesn;t auto generate a new character
AUTO_CREATE_CHARACTER_WITH_ACCOUNT = False
AUTO_PUPPET_ON_LOGIN = False
MAX_NR_CHARACTERS = 4
MAX_NR_SESSIONS_PER_ACCOUNT = 1
DEBUG = False
ADMINS = ('tim@timbaird.com')
PUPPET_LOOK_ON_IC = False

######################################################################
# XRPL / BLOCKCHAIN SETTINGS
######################################################################
# Override in secret_settings.py
XRPL_ROOT_ADDRESS = ""    # dev wallet (superuser default)

# ── Polygon Legacy (stubs — still referenced by old code paths) ──────
# TODO: Remove once fungible_inventory.py and base_nft_item.py old methods are cleaned up
BLOCKCHAIN_CHAIN_ID = 137
CONTRACT_GOLD      = "0x0000000000000000000000000000000000000000"
CONTRACT_NFT       = "0x0000000000000000000000000000000000000000"
CONTRACT_RESOURCES = "0x0000000000000000000000000000000000000000"
CONTRACT_VAULT     = "0x0000000000000000000000000000000000000000"
CONTRACT_TREASURY  = "0x0000000000000000000000000000000000000000"

# ── XRPL Configuration ──────────────────────────────────────────────
XRPL_IMPORT_EXPORT_ENABLED = False  # kill-switch for import/export — off for bot testing
# XRPL network endpoint — environment-specific, not secret.
# Defaults to testnet so local dev works without any env var.
# Railway production overrides to mainnet: wss://s1.ripple.com:51233
# Railway staging keeps the testnet default (or sets it explicitly).
XRPL_NETWORK_URL = os.environ.get(
    "XRPL_NETWORK_URL",
    "wss://s.altnet.rippletest.net:51233",
)
XRPL_ISSUER_ADDRESS = "rU3VtgY3LE63tmd7egjPUx37JqQXumokyJ"
XRPL_VAULT_ADDRESS = "rhYjpvpoU6FFjVSMvDRR1AUndgQx56TWaQ"   # game/bridge wallet (holds RESERVE/SPAWNED)
XRPL_GOLD_CURRENCY_CODE = "FCMGold"
XRPL_PGOLD_CURRENCY_CODE = "PGold"

XRPL_VAULT_WALLET_SEED = ""  # vault wallet seed for server-signed txns

# ── Xaman (XRPL Wallet) API ──────────────────────────────────────
# Register at https://apps.xaman.dev/ to obtain credentials.
# Actual values go in secret_settings.py.
XAMAN_API_KEY = "PLACEHOLDER"
XAMAN_API_SECRET = "PLACEHOLDER"


######################################################################
# LEGAL / COMPLIANCE SETTINGS
######################################################################

# Public-facing website URL — used for in-game ToS links and compliance notices.
GAME_WEBSITE_URL = "https://fcmud.world"

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
BOT_LOGIN_ENABLED = True  # master switch — set True to allow bot accounts to connect
BOT_ACCOUNT_USERNAMES = ["llm_bot_1", "llm_bot_2", "llm_bot_3", "llm_bot_4"]  # accounts that bypass wallet challenge when enabled


# LLM NPC Configuration
LLM_ENABLED = True                                 # master switch for all LLM NPCs
LLM_API_BASE_URL = "https://openrouter.ai/api/v1"  # OpenRouter endpoint
LLM_API_KEY = "" # set in secret_settings.py (OPENROUTER_API_KEY)
LLM_DEFAULT_MODEL = "openai/gpt-4o-mini"           # cheap + capable (proven in bot testing)
LLM_GLOBAL_MAX_CALLS_PER_MINUTE = 60               # across ALL NPCs combined
LLM_PER_NPC_MAX_CALLS_PER_MINUTE = 6               # per individual NPC
LLM_PER_NPC_COOLDOWN_SECONDS = 5                   # min gap between calls for same NPC
LLM_DAILY_COST_LIMIT_CENTS = 500                   # $5/day hard cap — disable all if exceeded

# Embedding settings — for vector memory (ai_memory app)
LLM_EMBEDDING_MODEL = "text-embedding-3-small"       # 1536 dims, ~$0.02/1M tokens
LLM_EMBEDDING_API_BASE_URL = "https://api.openai.com/v1"  # OpenAI direct (not OpenRouter)
LLM_EMBEDDING_API_KEY = "" #— set in secret_settings.py (defaults to LLM_API_KEY if not set)

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

# hunger cycle settings
HUNGER_TICK_INTERVAL = 1200  # IN SECONDS - ONCE EVERY 20 MINUTES = 3 X PER GAME DAY

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
]

######################################################################
# Settings given in secret_settings.py override those in this file.
######################################################################
try:
    from server.conf.secret_settings import *
except ImportError:
    print("secret_settings.py file not found or failed to import.")
