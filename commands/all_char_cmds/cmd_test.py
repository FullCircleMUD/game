from evennia import Command
from evennia.objects.models import ObjectDB
from evennia.utils.idmapper.models import SharedMemoryModel

from commands.command import FCMCommandMixin

# Check the idmapper module directly
import evennia.utils.idmapper.models as idmapper_module

class CmdTest(FCMCommandMixin, Command):
    """
    Fly up or down in a rooms

    Usage:
        stats
    """

    key = "test"
    locks = "cmd:all()"
    help_category = "Character"
    allow_while_sleeping = True

    def parse(self):
        """
        Separates the command input into first word and args.
        self.args is the raw string after the command key.
        """
        self.direction = self.args.strip().lower()  # second part of the command

    def func(self):
        """
        Hello World NFT DB-only proof-of-concept.
        `me` is the player calling @py
        """

        self.caller.msg("=== Step 1: Create DB-only object ===")

        # should create in db but not be in memory
        obj_db = ObjectDB.objects.create(
            db_key="Hello Sword",
            db_typeclass_path="evennia.objects.objects.DefaultObject"
        )

        obj_id = obj_db.id
        self.caller.msg(f"Created object with id: {obj_id}")

        # Check if it's in cache
        cached = ObjectDB.get_cached_instance(obj_id)
        self.caller.msg(f"In memory after create: {cached is not None}")

        # Flush it from cache
        obj_db.flush_from_cache()

        # Check again
        cached = ObjectDB.get_cached_instance(obj_id)
        self.caller.msg(f"In memory after flush: {cached is not None}")

        # See everything currently cached
        all_cached = ObjectDB.get_all_cached_instances()
        self.caller.msg(f"All cached ObjectDB count: {len(all_cached)}")
        for obj in all_cached:
            self.caller.msg(f"  - id:{obj.id} key:{obj.db_key}")

        # Reload from DB (re-caches it)
        obj_reloaded = ObjectDB.objects.get(id=obj_id)
        cached = ObjectDB.get_cached_instance(obj_id)
        self.caller.msg(f"In memory after get: {cached is not None}")

        # See everything currently cached
        all_cached = ObjectDB.get_all_cached_instances()
        self.caller.msg(f"All cached ObjectDB count: {len(all_cached)}")
        for obj in all_cached:
            self.caller.msg(f"  - id:{obj.id} key:{obj.db_key}")





        """
        obj_db.db.tokenID = 1
        obj_db.save()
        self.caller.msg(f"DB object created: {obj_db}, tokenID={obj_db.db.tokenID}")

        
        self.caller.msg("=== Step 2: Confirm not in memory ===")
        
        self.caller.msg("In memory?", obj_db.get_cached_obj() is not None)

        

        self.caller.msg("=== Step 3: Load into memory ===")
        obj_mem = obj_db.get_object()
        # Assign to superuser if available
        if self.caller and hasattr(self.caller, "character") and me.character:
            obj_mem.location = self.caller
        self.caller.msg("Loaded object into memory:", obj_mem)

        self.caller.msg("=== Step 4: Unload from memory ===")
        obj_mem.delete()
        self.caller.msg("Memory after delete:", obj_db.get_cached_obj())

        self.caller.msg("=== Step 5: DB still exists ===")
        self.caller.msg("DB exists?", ObjectDB.objects.filter(id=obj_db.id).exists())

        self.caller.msg("=== Step 6: Delete from DB ===")
        obj_db.delete()
        self.caller.msg("DB exists after deletion?", ObjectDB.objects.filter(id=obj_db.id).exists())
        """