"""
Database router for the AI Memory app.

Routes all ai_memory models to the ``ai_memory`` database alias
defined in settings.py, keeping NPC memories separate from Evennia's
game database. This means memories survive a full game DB wipe.

Migrate with:  evennia migrate --database ai_memory
"""


class AiMemoryRouter:
    """Route ai_memory models to the 'ai_memory' database."""

    app_label = "ai_memory"

    def db_for_read(self, model, **hints):
        if model._meta.app_label == self.app_label:
            return self.app_label
        return None

    def db_for_write(self, model, **hints):
        if model._meta.app_label == self.app_label:
            return self.app_label
        return None

    def allow_relation(self, obj1, obj2, **hints):
        if (
            obj1._meta.app_label == self.app_label
            and obj2._meta.app_label == self.app_label
        ):
            return True
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if app_label == self.app_label:
            return db == self.app_label
        if db == self.app_label:
            return False
        return None
