"""
NFTMirrorMixin — composable NFT mirror state machine.

Provides the full NFT lifecycle (mirror tracking, ownership transitions,
factory methods) as a mixin that can be composed into ANY Evennia object —
whether a DefaultObject (items) or DefaultCharacter (pets/actors).

All NFT mirror/ownership updates flow through two overrides, each of which
holds its game-side change and its ownership write in one transaction:

    move_to  — ALL location-based transitions (pickup, drop, transfer, bank,
               unbank, spawn, craft_output, reserve_to_account), written by
               at_post_move() which Evennia calls as move_to()'s last step
    delete   — ALL destruction transitions (despawn, craft_input,
               withdraw_to_chain), written by _mirror_on_delete() after the
               object is gone. at_object_delete() cannot host them: Evennia
               calls it first, before anything has been destroyed.

Extracted from BaseNFTItem to enable NFT-backed actors (pets, mounts) that
need actor infrastructure (HP, combat, following) alongside NFT tracking.

Composed into:
    BaseNFTItem(NFTMirrorMixin, ..., DefaultObject) — items
    BasePet(NFTMirrorMixin, ..., BaseNPC)           — pets/mounts (future)
"""

from evennia.typeclasses.attributes import AttributeProperty
from django.conf import settings
from django.db import transaction

from blockchain.xrpl.services.reconciliation import record_failure


from typeclasses.mixins.character_key import CharacterKeyMixin


class NFTMirrorMixin(CharacterKeyMixin):
    """
    Mixin providing full NFT mirror lifecycle tracking.

    Attributes (persisted):
        token_id — on-chain NFT token ID
    """

    token_id = AttributeProperty(None)

    # ================================================================== #
    #  Evennia Hooks — Mirror Transitions
    # ================================================================== #

    def move_to(self, destination, **kwargs):
        """
        Move this object, and let the ownership write veto the move.

        Why this override exists — none of it is visible at the call site:

        Evennia's move_to() calls at_post_move() as its last step, and
        at_post_move() is where this mixin writes the ownership change to
        the xrpl database. So the two writes that must agree — where the
        game says the object is, and who the ownership record says owns it
        — already happen in the right order, game first. All that is
        missing is a transaction around them, which is what this adds.

        No transaction can span two databases, so this is the nested shape
        used throughout: an outer transaction on the default connection,
        with the xrpl write opening its own inside it. Nothing writes after
        at_post_move() returns, which is the property that makes it safe.
        See design/database.md § Transactions and Split Aliases.

        The rollback keys off the return value rather than an exception,
        because move_to() never raises. Every step inside it is wrapped in
        Evennia's own try/except, which logs and returns False — so a
        failed ownership write would otherwise leave the object moved with
        nobody owning it, and nothing would be raised to say so.

        False also covers the ordinary refusals — at_pre_move declining, a
        failed lock — where nothing was written and the rollback costs
        nothing. And set_rollback() rather than raising keeps the contract
        every caller already relies on: a move that does not happen returns
        False, it does not explode.

        Args:
            destination (Object): where to move to.
            **kwargs: forwarded to Evennia's move_to().

        Returns:
            bool: True if the move and the ownership write both succeeded.
        """
        with transaction.atomic():
            moved = super().move_to(destination, **kwargs)
            if not moved:
                transaction.set_rollback(True)
            return moved

    def at_post_move(self, source_location, move_type="move", **kwargs):
        """
        Called after this object moves to a new location.

        This is the SINGLE POINT OF ENTRY for all NFT mirror updates that
        involve an object existing in-game. Evennia fires this hook both for
        normal moves (obj.move_to()) AND during create_object() when a
        location is specified — in the creation case, source_location is None.

        Location types are resolved through containers via _resolve_owner():
            CHARACTER — object is on a character (or in a container on a character)
            ACCOUNT   — object is in a bank (or in a container in a bank)
            WORLD     — object is in a room / on the ground

        The combination of (source_type, dest_type) determines which
        NFTService method to call.
        """
        super().at_post_move(source_location, move_type=move_type, **kwargs)

        if self.pk is None:
            # Obj was deleted during this move (e.g. recycle bin's
            # at_object_receive deletes synchronously). Nothing to mirror.
            return

        if self.token_id is None:
            return

        dest = self.location

        # Resolve ownership through containers
        source_type, source_owner = self._resolve_owner(source_location)
        dest_type, dest_owner = self._resolve_owner(dest)

        # ----- CREATION: source_location is None -----
        if source_location is None:
            self._handle_creation(dest_type, dest_owner, dest, **kwargs)
            return

        # ----- MOVEMENT -----
        if self._is_same_owner(source_type, source_owner, dest_type, dest_owner):
            return

        self._execute_transition(
            source_type, source_owner, dest_type, dest_owner,
        )

        # If this object is a container, cascade the transition to contents
        self._cascade_container_transition(
            source_type, source_owner, dest_type, dest_owner,
        )

    def _handle_creation(self, dest_type, dest_owner, dest, **kwargs):
        """
        Handle NFT creation (source is None — object entering the game).

        Service failures propagate. Evennia catches them at the top of
        move_to() and returns False, which rolls the creation back — see
        this mixin's move_to(). Swallowing them here would leave an object
        in the world that the ownership record knows nothing about.
        """
        from blockchain.xrpl.services.nft import NFTService

        if dest_type == "CHARACTER":
            wallet = self._get_owner_wallet(dest_owner)
            char_key = self._get_character_key(dest_owner)
            NFTService.craft_output(
                self.token_id, wallet, char_key,
            )

        elif dest_type == "ACCOUNT":
            wallet = dest_owner.wallet_address
            tx_hash = kwargs.get("tx_hash")
            NFTService.deposit_from_chain(
                self.token_id, wallet,
                settings.XRPL_VAULT_ADDRESS, tx_hash,
            )

        else:
            NFTService.spawn(self.token_id)

    def _execute_transition(self, source_type, source_owner,
                            dest_type, dest_owner):
        """
        Execute a single NFT mirror state transition.

        Dispatches the correct NFTService call based on source → dest types.

        Service failures propagate, so the move rolls back with them — see
        this mixin's move_to().
        """
        from blockchain.xrpl.services.nft import NFTService

        if source_type == "WORLD" and dest_type == "WORLD":
            return

        if source_type == "WORLD" and dest_type == "CHARACTER":
            wallet = self._get_owner_wallet(dest_owner)
            char_key = self._get_character_key(dest_owner)
            NFTService.pickup(
                self.token_id, wallet, char_key,
            )

        elif source_type == "CHARACTER" and dest_type == "WORLD":
            NFTService.drop(
                self.token_id, settings.XRPL_VAULT_ADDRESS,
            )

        elif source_type == "CHARACTER" and dest_type == "CHARACTER":
            from_wallet = self._get_owner_wallet(source_owner)
            from_key = self._get_character_key(source_owner)
            to_wallet = self._get_owner_wallet(dest_owner)
            to_key = self._get_character_key(dest_owner)
            NFTService.transfer(
                self.token_id, from_wallet, from_key,
                to_wallet, to_key,
            )

        elif source_type == "CHARACTER" and dest_type == "ACCOUNT":
            NFTService.bank(self.token_id)

        elif source_type == "ACCOUNT" and dest_type == "CHARACTER":
            char_key = self._get_character_key(dest_owner)
            NFTService.unbank(self.token_id, char_key)

    # ================================================================== #
    #  Container Cascade
    # ================================================================== #

    def _cascade_container_transition(self, source_type, source_owner,
                                      dest_type, dest_owner):
        """
        If this object is a container, cascade the ownership transition to
        all NFT contents and fungibles inside.
        """
        if not getattr(self, "is_container", False):
            return

        for obj in self.contents:
            if getattr(obj, "token_id", None) is None:
                continue
            if not hasattr(obj, "_execute_transition"):
                continue
            obj._execute_transition(
                source_type, source_owner, dest_type, dest_owner,
            )

        self._cascade_fungibles(source_type, source_owner,
                                dest_type, dest_owner)

    def _cascade_fungibles(self, source_type, source_owner,
                           dest_type, dest_owner):
        """Cascade fungible ownership changes when a container moves."""
        gold = 0
        resources = {}
        if hasattr(self, "get_gold"):
            gold = self.get_gold()
        if hasattr(self, "get_all_resources"):
            resources = self.get_all_resources()

        if gold <= 0 and not any(v > 0 for v in resources.values()):
            return

        vault = settings.XRPL_VAULT_ADDRESS

        source_wallet = (
            self._get_owner_wallet(source_owner) if source_type == "CHARACTER"
            else vault
        )
        source_key = (
            self._get_character_key(source_owner)
            if source_type == "CHARACTER" else None
        )
        dest_wallet = (
            self._get_owner_wallet(dest_owner) if dest_type == "CHARACTER"
            else vault
        )
        dest_key = (
            self._get_character_key(dest_owner)
            if dest_type == "CHARACTER" else None
        )

        # Failures propagate, so a container whose contents cannot be
        # re-attributed does not move — see this mixin's move_to().
        if gold > 0:
            self._cascade_fungible_gold(
                source_type, dest_type,
                source_wallet, source_key,
                dest_wallet, dest_key,
                gold, vault,
            )

        for rid, amt in resources.items():
            if amt > 0:
                self._cascade_fungible_resource(
                    source_type, dest_type,
                    source_wallet, source_key,
                    dest_wallet, dest_key,
                    rid, amt, vault,
                )

    @staticmethod
    def _cascade_fungible_gold(source_type, dest_type,
                               source_wallet, source_key,
                               dest_wallet, dest_key,
                               amount, vault):
        """Dispatch a single gold cascade service call."""
        from blockchain.xrpl.services.gold import GoldService

        if source_type == "CHARACTER" and dest_type == "WORLD":
            GoldService.drop(source_wallet, amount, vault, source_key)
        elif source_type == "WORLD" and dest_type == "CHARACTER":
            GoldService.pickup(dest_wallet, amount, vault, dest_key)
        elif source_type == "CHARACTER" and dest_type == "CHARACTER":
            GoldService.transfer(source_wallet, source_key, dest_wallet,
                                 dest_key, amount)
        elif source_type == "CHARACTER" and dest_type == "ACCOUNT":
            GoldService.bank(source_wallet, amount, source_key)
        elif source_type == "ACCOUNT" and dest_type == "CHARACTER":
            GoldService.unbank(dest_wallet, amount, dest_key)

    @staticmethod
    def _cascade_fungible_resource(source_type, dest_type,
                                   source_wallet, source_key,
                                   dest_wallet, dest_key,
                                   resource_id, amount, vault):
        """Dispatch a single resource cascade service call."""
        from blockchain.xrpl.services.resource import ResourceService

        if source_type == "CHARACTER" and dest_type == "WORLD":
            ResourceService.drop(source_wallet, resource_id, amount,
                                 vault, source_key)
        elif source_type == "WORLD" and dest_type == "CHARACTER":
            ResourceService.pickup(dest_wallet, resource_id, amount,
                                   vault, dest_key)
        elif source_type == "CHARACTER" and dest_type == "CHARACTER":
            ResourceService.transfer(source_wallet, source_key,
                                     dest_wallet, dest_key, resource_id,
                                     amount)
        elif source_type == "CHARACTER" and dest_type == "ACCOUNT":
            ResourceService.bank(source_wallet, resource_id, amount,
                                 source_key)
        elif source_type == "ACCOUNT" and dest_type == "CHARACTER":
            ResourceService.unbank(dest_wallet, resource_id, amount,
                                   dest_key)

    # ================================================================== #
    #  Deletion — Mirror Cleanup
    # ================================================================== #

    def delete(self):
        """
        Delete this object, and let the ownership write veto the deletion.

        The counterpart to move_to() above, and it needs an override for the
        opposite reason. Evennia calls at_object_delete() *first*, so the
        ownership writes cannot live there — they have to happen after the
        object is destroyed, which is only reachable from here.

        The order is: read everything the writes will need, destroy any NFT
        contents, destroy this object, then make every ownership write. That
        keeps the rule the rest of the codebase follows — the irreversible
        writes last, with nothing on the default connection after them.

        Destroying a container destroys what is inside it, so its gold and
        resources go back to the vault's books. Those amounts are read up
        front and written back at the end; the objects holding them do not
        need to exist by then, only the numbers.

        Its NFT contents are the exception that cannot be reordered. Each
        child has to be deleted while it still exists — otherwise Evennia's
        clear_contents() would relocate it to its home instead — and each
        commits its own ownership write on the way out. A parent deletion
        that fails after that point leaves the children gone. There is no
        arrangement that avoids it.

        A rollback restores the rows but not the Python instance: Django
        clears its pk and the idmapper has already evicted it. So on failure
        the object is re-fetched by the pk captured beforehand and its
        location's contents cache rebuilt, since that cache is in-memory and
        the rollback does not touch it. Whoever called delete() still holds
        the discarded instance and should not keep using it.

        See design/database.md § Transactions and Split Aliases.

        Returns:
            bool: True if the deletion and the ownership writes all
                succeeded. False leaves the object in the world.
        """
        if self.token_id is None:
            return super().delete()

        # Location type — CHARACTER, ACCOUNT or WORLD. Behind a method so
        # pets can answer it from owner_key instead of from where they are
        # standing. Read before anything is destroyed: afterwards there is
        # no location left to read.
        disposition = self._resolve_delete_disposition()
        saved_pk = self.pk
        wallet = self._delete_failure_wallet()

        # Captured too: token_id is an AttributeProperty, and after the
        # deletion its rows are gone, so reading it then raises.
        token_id = self.token_id
        tx_hash = getattr(self.ndb, "pending_tx_hash", None)
        held_gold, held_resources = self._held_fungibles()
        destroyed = False
        orphaned_children = []

        try:
            with transaction.atomic():
                orphaned_children = self._delete_nft_contents()
                destroyed = super().delete()
                if not destroyed:
                    transaction.set_rollback(True)
                    return destroyed
                self._return_held_fungibles(held_gold, held_resources)
                self._mirror_on_delete(disposition, token_id, tx_hash)
        except Exception as err:
            if destroyed:
                self._reinstate_after_failed_delete(saved_pk)
            self._reissue_orphaned_children(orphaned_children)
            record_failure(
                "nft_delete", wallet, err,
                character_key=None,
                tx_hash=None,
            )
            raise

        return destroyed

    def _held_fungibles(self):
        """
        What this object is holding, read before it is destroyed.

        Returns:
            tuple: (gold, {resource_id: amount}) — both empty for anything
                that is not a container carrying fungibles.
        """
        if not getattr(self, "is_container", False):
            return 0, {}

        gold = self.get_gold() if hasattr(self, "get_gold") else 0
        resources = (
            self.get_all_resources() if hasattr(self, "get_all_resources")
            else {}
        )
        return gold, {rid: amt for rid, amt in resources.items() if amt > 0}

    def _delete_nft_contents(self):
        """
        Destroy any NFT items inside this object.

        Runs before this object is destroyed, because Evennia's
        clear_contents() would otherwise send them to their home rather than
        destroying them. Each child's own delete() makes its own ownership
        write on the xrpl connection, which commits there and then — so this
        is the one part of a container deletion that cannot be left until
        the end, and the one part a later rollback cannot undo.

        What each child needs to be rebuilt is read first, because returning
        a token to the reserve pool blanks its item type and metadata. The
        object itself is the surviving copy of its own identity.

        Returns:
            list: one dict per deleted child — pk, item type name and
                metadata — for _reissue_orphaned_children() if the parent
                deletion then fails.
        """
        if not getattr(self, "is_container", False):
            return []

        deleted = []
        for obj in list(self.contents):
            if getattr(obj, "token_id", None) is None:
                continue

            mirror = self.get_nft_mirror(obj.token_id)
            deleted.append({
                "pk": obj.pk,
                "item_type": mirror.item_type.name if mirror and mirror.item_type else None,
                "metadata": dict(mirror.metadata or {}) if mirror else {},
            })
            obj.delete()

        return deleted

    @staticmethod
    def _reissue_orphaned_children(children):
        """
        Give a restored child a fresh token after a failed parent deletion.

        The child's own deletion committed on the xrpl connection before the
        parent failed, so its old token is already back in the reserve pool
        and blank. The rollback then restores the child object — leaving an
        item in the world holding a token that no longer belongs to it.

        Rather than destroy the item to match the record, it is given a new
        token from the pool and its identity written onto it. The player
        keeps the item; one token goes back and another comes out, which
        costs the economy nothing. What it carries afterwards is a different
        token id, which only shows if it is later exported.

        Never raises. This runs while an exception is on its way up, and the
        original failure matters more than the repair. A dry reserve pool is
        the one thing that stops it, and a dry pool is a larger problem than
        this path.

        Args:
            children (list): what _delete_nft_contents() returned.
        """
        from evennia.objects.models import ObjectDB
        from evennia.utils import logger

        for child in children:
            try:
                obj = ObjectDB.objects.filter(pk=child["pk"]).first()
                if obj is None or not child["item_type"]:
                    continue

                obj.token_id = NFTMirrorMixin.assign_to_blank_token(
                    child["item_type"],
                )
                if child["metadata"]:
                    obj.persist_metadata(child["metadata"])
            except Exception:
                logger.log_err(
                    f"Could not reissue a token for restored object "
                    f"#{child['pk']} after a failed container deletion. "
                    f"Its old token is in the reserve pool and the object "
                    f"is holding nothing valid."
                )

    @staticmethod
    def _return_held_fungibles(gold, resources):
        """
        Hand a destroyed container's gold and resources back to the vault.

        The container is already gone by this point, so this goes to the
        services directly — there is no local Evennia state left to keep in
        step, which is the only thing the mixin methods would have added.

        Args:
            gold (int): what _held_fungibles() found.
            resources (dict): resource_id to amount.
        """
        from blockchain.xrpl.services.gold import GoldService
        from blockchain.xrpl.services.resource import ResourceService

        vault = settings.XRPL_VAULT_ADDRESS

        if gold > 0:
            GoldService.despawn(gold, vault)

        for resource_id, amount in resources.items():
            ResourceService.despawn(resource_id, amount, vault)

    @staticmethod
    def _reinstate_after_failed_delete(saved_pk):
        """
        Put a rolled-back deletion back together on the Python side.

        The rows are already restored. What is not restored is the
        container's contents cache, which delete() emptied in memory when it
        set location to None.

        Args:
            saved_pk (int): the pk captured before the deletion.
        """
        from evennia.objects.models import ObjectDB

        obj = ObjectDB.objects.filter(pk=saved_pk).first()
        if obj is not None and obj.location is not None:
            obj.location.contents_cache.init()

    def _resolve_delete_disposition(self):
        """
        Where this object's token should go when it is destroyed.

        Read before the deletion, while there is still a location to read.
        Overridden by pets, which resolve ownership from owner_key rather
        than from where the object is sitting.

        Returns:
            str: "CHARACTER", "ACCOUNT" or "WORLD".
        """
        location_type, _owner = self._resolve_owner(self.location)
        return location_type

    def _delete_failure_wallet(self):
        """The wallet to name on a failed deletion, or an empty string."""
        _location_type, owner = self._resolve_owner(self.location)
        return self._get_owner_wallet(owner) or ""

    def _mirror_on_delete(self, disposition, token_id, tx_hash):
        """
        Return this object's token to the vault. The ownership write.

        Called from delete() as the last thing inside the transaction, so a
        failure here takes the deletion with it. Everything it needs is
        passed in — the object is already destroyed by this point, so
        nothing can be read off it.

        Args:
            disposition (str): what _resolve_delete_disposition() returned.
            token_id (str): the token, captured before the deletion.
            tx_hash (str): pending export hash, captured before the deletion.
        """
        from blockchain.xrpl.services.nft import NFTService

        if disposition == "CHARACTER":
            NFTService.craft_input(token_id, settings.XRPL_VAULT_ADDRESS)
        elif disposition == "ACCOUNT":
            NFTService.withdraw_to_chain(token_id, tx_hash)
        else:
            NFTService.despawn(token_id)

    # ================================================================== #
    #  Factory Methods
    # ================================================================== #

    @staticmethod
    def assign_to_blank_token(item_type_name):
        """
        Pick the next blank RESERVE token and assign it an item type.
        Returns the token_id ready for spawn_into().
        """
        from blockchain.xrpl.services.nft import NFTService
        return NFTService.assign_item_type(item_type_name)

    @staticmethod
    def spawn_into(token_id, location, **kwargs):
        """
        Create an Evennia object for an NFT and move it into a location.

        Reads the NFTMirror row to determine prototype_key, typeclass,
        name, and description. Uses Evennia's spawn() to create the
        object with all prototype attributes applied.
        """
        from evennia import search_object
        from evennia.prototypes.spawner import spawn as evennia_spawn
        from blockchain.xrpl.models import NFTGameState

        try:
            nft = NFTGameState.objects.select_related("item_type").get(
                nftoken_id=str(token_id),
            )
        except NFTGameState.DoesNotExist:
            return None

        recycle_results = search_object("nft_recycle_bin", exact=True)
        recycle_bin = recycle_results[0] if recycle_results else None

        spawn_dict = {"location": None}

        if nft.item_type:
            if nft.item_type.prototype_key:
                spawn_dict["prototype_parent"] = nft.item_type.prototype_key
            else:
                spawn_dict["typeclass"] = (
                    nft.item_type.typeclass
                    or "typeclasses.items.base_nft_item.BaseNFTItem"
                )
            spawn_dict["key"] = nft.item_type.name
            spawn_dict["desc"] = nft.item_type.description or ""
        else:
            spawn_dict["typeclass"] = "typeclasses.items.base_nft_item.BaseNFTItem"
            spawn_dict["key"] = f"NFT #{token_id}"

        if recycle_bin:
            spawn_dict["home"] = recycle_bin

        obj = evennia_spawn(spawn_dict)[0]

        obj.token_id = token_id

        if nft.item_type and nft.item_type.prototype_key:
            obj.db.prototype_key = nft.item_type.prototype_key

        meta = nft.metadata or {}
        for key, value in meta.items():
            obj.attributes.add(key, value)

        obj.move_to(location, **kwargs)

        # Give the typeclass a chance to convert JSON-flat metadata into
        # live object state (e.g. resolve dbref → room, list → set).
        # Runs AFTER move_to so at_post_move hooks don't clobber restored state.
        if hasattr(obj, "at_restore_from_metadata"):
            try:
                obj.at_restore_from_metadata(meta)
            except Exception as err:
                print(
                    f"  NFT restore_from_metadata failed for #{token_id}: {err}"
                )

        return obj

    # ================================================================== #
    #  Location Classification Helpers
    # ================================================================== #

    @staticmethod
    def _classify(obj):
        """Classify an Evennia object into a location type for mirror updates."""
        if obj is None:
            return None

        from typeclasses.actors.character import FCMCharacter
        from typeclasses.accounts.account_bank import AccountBank

        if isinstance(obj, FCMCharacter):
            return "CHARACTER"
        if isinstance(obj, AccountBank):
            return "ACCOUNT"
        return "WORLD"

    @staticmethod
    def _resolve_owner(obj):
        """Resolve the effective owner of a location, walking through containers."""
        if obj is None:
            return (None, None)

        current = obj
        while current is not None:
            classified = NFTMirrorMixin._classify(current)
            if classified != "WORLD":
                return (classified, current)
            current = getattr(current, "location", None)
        return ("WORLD", None)

    @staticmethod
    def _is_same_owner(source_type, source_owner, dest_type, dest_owner):
        """Check if source and dest resolve to the same owner."""
        if source_type == "WORLD" and dest_type == "WORLD":
            return True
        if source_type != dest_type:
            return False
        if source_owner is None or dest_owner is None:
            return source_owner is dest_owner
        if source_type == "CHARACTER":
            from_wallet = NFTMirrorMixin._get_owner_wallet(source_owner)
            to_wallet = NFTMirrorMixin._get_owner_wallet(dest_owner)
            return from_wallet == to_wallet
        if source_type == "ACCOUNT":
            return (getattr(source_owner, "wallet_address", None)
                    == getattr(dest_owner, "wallet_address", None))
        return source_owner is dest_owner

    @staticmethod
    def _get_owner_wallet(character):
        """Get a character's wallet address from their account."""
        if character is None or character.account is None:
            return None
        return character.account.attributes.get("wallet_address")

    # ================================================================== #
    #  Mirror Data Helpers
    # ================================================================== #

    def _load_from_mirror(self):
        """Pull name, description, and metadata from NFTGameState."""
        if self.token_id is None:
            return
        from blockchain.xrpl.models import NFTGameState

        try:
            nft = NFTGameState.objects.get(nftoken_id=str(self.token_id))
        except NFTGameState.DoesNotExist:
            return

        meta = nft.metadata or {}
        self.db.nft_metadata = meta

        if meta.get("name"):
            self.key = meta["name"]
        if meta.get("description"):
            self.db.desc = meta["description"]

    @staticmethod
    def get_nft_mirror(token_id):
        """Look up an NFTGameState row by token_id."""
        from blockchain.xrpl.services.nft import NFTService
        return NFTService.get_nft(token_id)

    def persist_metadata(self, patch):
        """
        Patch mirror DB metadata for this NFT. Values must be JSON-serializable
        (str/int/float/bool/list/dict of same). Pass None to delete a key.

        No-op if the instance has no token_id yet (e.g. during creation,
        before assign_to_blank_token has run). Errors are logged but not
        raised — metadata persistence is best-effort and must not break
        gameplay.
        """
        if self.token_id is None:
            return
        from blockchain.xrpl.services.nft import NFTService
        try:
            NFTService.update_metadata(self.token_id, patch)
        except Exception as err:
            self._log_error("update_metadata", err)

    def _log_error(self, operation, err):
        """Log a mirror update failure."""
        print(f"  NFT mirror {operation} failed for #{self.token_id}: {err}")
