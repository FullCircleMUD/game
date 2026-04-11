"""
Railway deploy migration script.

Runs Django migrations directly, bypassing Evennia's launcher.
On Railway all database aliases share one Postgres instance, so
a single migrate call (with no routers) handles everything.

Called from railway.toml startCommand before evennia start.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")

import django
django.setup()

from django.core.management import call_command

print("--- Running migrations ---")
call_command("migrate", verbosity=1)
print("--- Migrations complete ---")
