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

import dj_database_url

# Use the defaults from Evennia unless explicitly overridden
from evennia.settings_default import *  # noqa: F403, F401 — provides DATABASES, GAME_DIR, etc.

# Register custom Django apps
INSTALLED_APPS = INSTALLED_APPS + ["blockchain.xrpl", "ai_memory", "subscriptions"]

WEBSOCKET_CLIENT_INTERFACE = '0.0.0.0'
SERVER_HOSTNAME = '0.0.0.0'
LOCKDOWN_MODE = False

# ── Railway port binding ─────────────────────────────────────────────
# Railway assigns a dynamic $PORT — Evennia must listen on it.
if os.environ.get("PORT"):
    WEBSERVER_PORTS = [(int(os.environ["PORT"]), 4005)]

# Websocket URL for the webclient (Railway routes websocket via separate domain).
WEBSOCKET_CLIENT_URL = os.environ.get(
    "WEBSOCKET_CLIENT_URL",
    "ws://localhost:4002",
)

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
    DATABASES["subscriptions"] = {**_pg_config}  # type: ignore[name-defined]
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
    # Migrate with: evennia migrate --database subscriptions
    DATABASES["subscriptions"] = {  # type: ignore[name-defined]
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": os.path.join(GAME_DIR, "server", "subscriptions.db3"),  # type: ignore[name-defined]
    }

# Database routers — only needed locally where each alias is a separate
# SQLite file. On Railway all aliases share one Postgres instance, so
# routers would block migrations from creating tables.
if not _DATABASE_URL:
    DATABASE_ROUTERS = [
        "blockchain.xrpl.db_router.XRPLRouter",
        "ai_memory.db_router.AiMemoryRouter",
        "subscriptions.db_router.SubscriptionsRouter",
    ]

# Django secret key — used to sign cookies/sessions.
# On Railway, set SECRET_KEY env var. Locally, override in secret_settings.py.
SECRET_KEY = os.environ.get("SECRET_KEY", "changeme-set-in-secret-settings")

# Host header allowlist — '*' in dev, comma-separated list in prod
# (e.g. ALLOWED_HOSTS="game.fcmud.world,fcmud.up.railway.app").
ALLOWED_HOSTS = [h.strip() for h in os.environ.get("ALLOWED_HOSTS", "*").split(",") if h.strip()]

# In-game traceback display — on in dev for visibility, off in prod to
# avoid leaking internals to players. Set IN_GAME_ERRORS=false on Railway.
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

# Override in secret_settings.py or set SUPERUSER_ACCOUNT_NAME env var.
#SUPERUSER_ACCOUNT_NAME = os.environ.get("SUPERUSER_ACCOUNT_NAME", "")

EVENNIA_SUPERUSER_USERNAME = os.environ.get("EVENNIA_SUPERUSER_USERNAME", "")
EVENNIA_SUPERUSER_PASSWORD = os.environ.get("EVENNIA_SUPERUSER_PASSWORD", "")


# Default password for wallet-authenticated accounts.
# Wallet signature is the real auth — this just satisfies Evennia's Account.create().
DEFAULT_ACCOUNT_PASSWORD = os.environ.get("DEFAULT_ACCOUNT_PASSWORD", "CHANGE_ME")

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
SUPERUSER_XRPL_WALLET_ADDRESS = os.environ.get("SUPERUSER_XRPL_WALLET_ADDRESS", "")  # dev wallet (superuser default)

# ── XRPL Configuration ──────────────────────────────────────────────
XRPL_IMPORT_EXPORT_ENABLED = os.environ.get("XRPL_IMPORT_EXPORT_ENABLED", "").lower() in ("true", "1")
# XRPL network endpoint — environment-specific, not secret.
# Must be set via env var for deployed environments.
XRPL_NETWORK_URL = os.environ.get(
    "XRPL_NETWORK_URL",
    "wss://xrplcluster.com",
)
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
SUBSCRIPTION_CURRENCY_CODE = os.environ.get("SUBSCRIPTION_CURRENCY_CODE", "RLUSD")
SUBSCRIPTION_CURRENCY_ISSUER = os.environ.get(
    "SUBSCRIPTION_CURRENCY_ISSUER",
    "rMxCKbEDwqr76QuheSUMdEGf4B9xJ8m5De",  # RLUSD issuer on XRPL mainnet
)
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

######################################################################
# Local development overrides.
#
# In dev, secrets live in server/conf/secret_settings.local — a
# git-crypt encrypted file with a deliberately non-.py extension so
# Nixpacks/Railway source scanners don't try to parse the encrypted
# bytes as Python during build. We load it manually via importlib.util
# when running locally.
#
# On Railway (DATABASE_URL set) we skip this entirely — production
# secrets come from platform env vars.
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
