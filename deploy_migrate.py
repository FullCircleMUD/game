"""
Railway deploy migration script.

Runs Django migrations directly, bypassing Evennia's launcher which
may not correctly pass DATABASE_URL to all database aliases.

Called from railway.toml startCommand before evennia start.
"""

import os
import sys

# Ensure the game directory is on the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")

import django
django.setup()

from django.core.management import call_command
from django.db import connections

# Debug: confirm which database each alias is actually using
for alias in ["default", "xrpl", "ai_memory", "subscriptions"]:
    db = connections[alias].settings_dict
    engine = db.get("ENGINE", "unknown")
    name = db.get("NAME", "unknown")
    host = db.get("HOST", "")
    print(f"  [{alias}] engine={engine} name={name} host={host}")

print("\n--- Running migrations ---")

for db_alias in ["default", "xrpl", "ai_memory", "subscriptions"]:
    print(f"\n  Migrating: --database {db_alias}")
    call_command("migrate", database=db_alias, verbosity=2)

print("\n--- Migrations complete ---")
