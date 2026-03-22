"""
Database router for the XRPL blockchain app.

Routes all xrpl models to the ``xrpl`` database alias
defined in settings.py, keeping them separate from Evennia's default
game database and the Polygon blockchain database.

Migrate with:  evennia migrate --database xrpl
"""


class XRPLRouter:
    """Route xrpl models to the 'xrpl' database."""

    app_label = "xrpl"

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
