"""
Railway deploy migration script.

Runs Django migrations directly, bypassing Evennia's launcher.
On Railway all database aliases share one Postgres instance, so
a single migrate call (with no routers) handles everything.

Ensures pgvector extension is installed before migrations run,
since ai_memory models depend on the vector type.

Called from railway.toml startCommand before evennia start.
"""

import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")

import django
django.setup()

from django.db import connections
from django.core.management import call_command

# Ensure pgvector extension exists before migrations try to use vector types.
# Use a raw psycopg2 connection with autocommit to avoid holding a transaction
# lock that blocks subsequent migration DDL.
print("--- Ensuring pgvector extension ---", flush=True)
try:
    conn = connections["default"]
    conn.ensure_connection()
    conn.connection.autocommit = True
    with conn.cursor() as cursor:
        cursor.execute("CREATE EXTENSION IF NOT EXISTS vector")
    conn.connection.autocommit = False
    conn.close()
    print("  pgvector: OK", flush=True)
except Exception as e:
    print(f"  pgvector: SKIPPED ({e})", flush=True)

print("--- Running migrations ---", flush=True)
try:
    call_command("migrate", verbosity=1)
    print("--- Migrations complete ---", flush=True)
except Exception as e:
    print(f"--- Migration FAILED: {e} ---", flush=True)
    traceback.print_exc()
    print("--- Continuing with server start despite migration failure ---", flush=True)
