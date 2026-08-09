"""
Test settings for the shard role.

Inherits the production shard0 configuration and overrides only what
distorts tests in ways unrelated to what they assert. Everything else —
INSTALLED_APPS, DATABASES, the shard_id schema — is production's.

    evennia test --settings settings_test_shard0 tests

Settings cascade:

    settings.py (base FCM config)
    settings_common_shard_config.py
    settings_shard0.py (production shard role)
    settings_test_shard0.py (this file)
"""

# Import order is load-bearing. settings_shard0 imports the evennia_shards
# package, which pulls in evennia.utils.logger, which reads a Django setting
# while this module is still executing. Django answers that read by building
# its Settings object from this module as it currently stands — so the base
# config must already be in this namespace, or the read fails on a module
# with no attributes yet. Establish the base first, then the role.
from server.conf.settings import *  # noqa: F401, F403 — base FCM config
from server.conf.settings_shard0 import *  # noqa: F401, F403 — production shard role

# The shard role requires auto-puppet: the ticket auth flow logs the
# player in, then at_post_login reads _last_puppet to puppet the chosen
# character. Correct in production, distorting in tests — EvenniaTest.setUp
# performs a login, so every test would puppet, firing at_post_puppet and
# its telemetry write to `xrpl`. Django then blocks that query for any
# test class that has not declared `databases`, failing it in setUp before
# its own assertions run.
#
# A test that genuinely exercises the puppet path re-enables it for itself
# with @override_settings(AUTO_PUPPET_ON_LOGIN=True) and declares the
# databases it touches.
AUTO_PUPPET_ON_LOGIN = False
