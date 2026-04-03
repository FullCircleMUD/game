"""
Management command to import lore YAML files into the LoreMemory database.

Usage:
    evennia lore_import                              # import all YAML files
    evennia lore_import --file millholm/regional.yaml # import specific file
    evennia lore_import --dry-run                    # show what would happen
    evennia lore_import --lore-dir /path/to/lore     # override lore directory

Default lore directory: ``FCM/lore/`` (three levels up from GAME_DIR).
"""

import os

import yaml
from django.conf import settings
from django.core.management.base import BaseCommand


def _default_lore_dir():
    """Return the default lore directory path."""
    game_dir = getattr(settings, "GAME_DIR", os.getcwd())
    return os.path.normpath(os.path.join(game_dir, "..", "..", "lore"))


class Command(BaseCommand):
    help = "Import lore YAML files into the LoreMemory database."
    requires_system_checks = []  # skip Evennia URL/command checks

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            type=str,
            default=None,
            help="Import a specific YAML file (relative to lore dir).",
        )
        parser.add_argument(
            "--lore-dir",
            type=str,
            default=None,
            help="Override the lore directory path.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be imported without making changes.",
        )

    def handle(self, *args, **options):
        lore_dir = options["lore_dir"] or _default_lore_dir()
        dry_run = options["dry_run"]
        specific_file = options["file"]

        if not os.path.isdir(lore_dir):
            self.stderr.write(
                self.style.ERROR(f"Lore directory not found: {lore_dir}")
            )
            return

        self.stdout.write(f"Lore directory: {lore_dir}")
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN — no changes will be made"))

        # Collect YAML files
        if specific_file:
            yaml_files = [specific_file]
        else:
            yaml_files = []
            for root, _dirs, files in os.walk(lore_dir):
                for f in sorted(files):
                    if f.endswith((".yaml", ".yml")):
                        rel_path = os.path.relpath(
                            os.path.join(root, f), lore_dir
                        ).replace("\\", "/")
                        yaml_files.append(rel_path)

        if not yaml_files:
            self.stdout.write("No YAML files found.")
            return

        self.stdout.write(f"Found {len(yaml_files)} file(s) to process.\n")

        counts = {"created": 0, "updated": 0, "unchanged": 0, "failed": 0}

        for rel_path in yaml_files:
            full_path = os.path.join(lore_dir, rel_path)
            if not os.path.isfile(full_path):
                self.stderr.write(
                    self.style.ERROR(f"  File not found: {rel_path}")
                )
                counts["failed"] += 1
                continue

            self.stdout.write(f"  Processing: {rel_path}")
            try:
                with open(full_path, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)
            except Exception as e:
                self.stderr.write(
                    self.style.ERROR(f"    YAML parse error: {e}")
                )
                counts["failed"] += 1
                continue

            if not data or "entries" not in data:
                self.stderr.write(
                    self.style.WARNING(f"    No 'entries' key — skipping")
                )
                continue

            source = data.get("source", rel_path)

            for entry in data["entries"]:
                title = entry.get("title")
                content = entry.get("content", "").strip()
                scope_level = entry.get("scope_level", "continental")
                scope_tags = entry.get("scope_tags", [])

                if not title or not content:
                    self.stderr.write(
                        self.style.WARNING(
                            f"    Skipping entry with missing title or content"
                        )
                    )
                    counts["failed"] += 1
                    continue

                if dry_run:
                    self.stdout.write(
                        f"    [DRY RUN] {title} "
                        f"({scope_level}: {scope_tags or 'global'})"
                    )
                    counts["created"] += 1
                    continue

                try:
                    from ai_memory.services import store_lore

                    _entry, status = store_lore(
                        title=title,
                        content=content,
                        scope_level=scope_level,
                        scope_tags=scope_tags,
                        source=source,
                    )
                    counts[status] += 1

                    style = {
                        "created": self.style.SUCCESS,
                        "updated": self.style.WARNING,
                        "unchanged": lambda x: x,
                        "failed": self.style.ERROR,
                    }.get(status, lambda x: x)

                    self.stdout.write(
                        f"    {style(status.upper())}: {title}"
                    )
                except Exception as e:
                    self.stderr.write(
                        self.style.ERROR(f"    FAILED: {title} — {e}")
                    )
                    counts["failed"] += 1

        # Summary
        self.stdout.write("")
        self.stdout.write(
            f"Done. "
            f"Created: {counts['created']}, "
            f"Updated: {counts['updated']}, "
            f"Unchanged: {counts['unchanged']}, "
            f"Failed: {counts['failed']}"
        )
