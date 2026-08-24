"""
NFTPetMirrorMixin — NFT mirror state machine for pets.

Inherits from NFTMirrorMixin. Overrides dispatch methods with pet-specific
ownership logic (owner_key instead of location-chain resolution). No-ops
methods that don't apply to pets. Inherits helpers unchanged.

Pets are actors in rooms — they are NEVER in character.contents. Ownership
is tracked via owner_key, not by the object's location in a character.

Composed into:
    BasePet(NFTPetMirrorMixin, FollowableMixin, BaseNPC)
"""

from django.conf import settings
from django.db import transaction
from evennia.typeclasses.attributes import AttributeProperty

from blockchain.xrpl.services.reconciliation import record_failure
from typeclasses.mixins.nft_mirror import NFTMirrorMixin
from utils.attribute_cache import discard_cached_attributes
from utils.targeting.predicates import p_is_character


class NFTPetMirrorMixin(NFTMirrorMixin):
    """
    Pet-specific NFT mirror tracking. Inherits NFTMirrorMixin and overrides
    dispatch logic for pet ownership model.

    Inherited unchanged: token_id, _get_owner_wallet, _get_character_key,
    assign_to_blank_token, _load_from_mirror, get_nft_mirror,
    _log_error, _classify
    """

    # ── New attribute ──
    owner_key = AttributeProperty(None)  # character key of owner

    # ================================================================== #
    #  Overridden — pet-specific dispatch
    # ================================================================== #

    def at_post_move(self, source_location, move_type="move", **kwargs):
        """Pet-specific mirror dispatch.

        Skips NFTMirrorMixin's location-chain dispatch. Classifies source
        and dest via simple isinstance checks. Chains to BaseNPC's
        at_post_move for actor hooks (follower cascade etc).
        """
        # Chain to grandparent (BaseNPC), skipping NFTMirrorMixin's dispatch
        super(NFTMirrorMixin, self).at_post_move(
            source_location, move_type=move_type, **kwargs
        )

        if self.token_id is None:
            return

        dest = self.location
        source_type = self._classify_location(source_location)
        dest_type = self._classify_location(dest)

        # Creation: source is None — pet entering game for first time
        if source_type is None:
            self._handle_creation(dest_type, dest, **kwargs)
            return

        # Room to room: no-op (following owner, still CHARACTER)
        if source_type == "ROOM" and dest_type == "ROOM":
            return

        # Actual transition (stable/retrieve)
        self._execute_transition(source_type, dest_type)

    def _resolve_delete_disposition(self):
        """Where a deleted pet's token goes. Read before the deletion.

        A pet is always standing in a room, so the location chain would call
        every pet unowned. Ownership comes from owner_key instead.

        Returns:
            str: "CHARACTER" (owned), "ACCOUNT" (stabled) or "WORLD"
                (no owner — should not happen).
        """
        location_type = self._classify_location(self.location)
        if location_type == "ACCOUNT":
            return "ACCOUNT"
        if self.owner_key:
            return "CHARACTER"
        return "WORLD"

    def _mirror_on_delete(self, disposition, token_id, tx_hash):
        """Return a deleted pet's token to the vault.

        Owned pet in world → craft_input (CHARACTER → unallocated)
        Stabled pet exported → withdraw_to_chain (ACCOUNT → ONCHAIN)

        Args:
            disposition (str): what _resolve_delete_disposition() returned.
            token_id (str): the token, captured before the deletion.
            tx_hash (str): pending export hash, captured before the deletion.
        """
        from blockchain.xrpl.services.nft import NFTService
        from evennia.utils import logger

        if disposition == "CHARACTER":
            # Owned pet in world — death, admin delete, etc
            NFTService.craft_input(token_id, settings.XRPL_VAULT_ADDRESS)
        elif disposition == "ACCOUNT":
            # Stabled pet being exported to external wallet
            NFTService.withdraw_to_chain(token_id, tx_hash)
        else:
            # A pet with no owner should not exist. Despawn it, but say so.
            logger.log_err(
                f"PET MIRROR ERROR: Unowned pet #{token_id} deleted. "
                f"Performing safety despawn."
            )
            NFTService.despawn(token_id)

    def _delete_failure_wallet(self):
        """The wallet to name on a failed deletion, or an empty string."""
        return self._get_owner_wallet() or ""

    @staticmethod
    def _resolve_owner(obj):
        """Disabled for pets — location-chain resolution doesn't apply."""
        raise NotImplementedError(
            "_resolve_owner() is disabled on pets. "
            "Use _resolve_pet_owner() instead — pet ownership "
            "is tracked via owner_key, not location chain."
        )

    def _resolve_pet_owner(self):
        """Resolve pet ownership via owner_key.

        Returns:
            (type_string, owner_object) — ("CHARACTER", character) or
            ("WORLD", None) if no owner (should not happen in normal use).
        """
        if not self.owner_key:
            return ("WORLD", None)
        owner = self._get_owner_character()
        return ("CHARACTER", owner)

    def _handle_creation(self, dest_type, dest, **kwargs):
        """Pet entering game for first time.

        Room dest → tamed/summoned → craft_output (owner's wallet)
        Account dest → imported from chain → deposit_from_chain

        Failures propagate. This runs inside the transaction opened by
        NFTMirrorMixin.move_to(), which rolls the creation back — a pet
        nobody owns in the record should not be standing in the world.
        """
        from blockchain.xrpl.services.nft import NFTService

        if dest_type == "ROOM":
            wallet = self._get_owner_wallet()
            char_key = self.owner_key
            NFTService.craft_output(
                self.token_id, wallet, char_key,
            )

        elif dest_type == "ACCOUNT":
            wallet = dest.wallet_address if hasattr(dest, "wallet_address") else None
            tx_hash = kwargs.get("tx_hash")
            NFTService.deposit_from_chain(
                self.token_id, wallet,
                settings.XRPL_VAULT_ADDRESS, tx_hash,
            )

    def _execute_transition(self, source_type, dest_type):
        """Pet movement transitions.

        ROOM → ACCOUNT: stable → bank()
        ACCOUNT → ROOM: retrieve → unbank()
        (ROOM → ROOM is handled as no-op in at_post_move before this is called)

        Failures propagate. This runs inside the transaction opened by
        NFTMirrorMixin.move_to(), which rolls the move back rather than
        leaving the pet stabled with the record saying otherwise.
        """
        from blockchain.xrpl.services.nft import NFTService

        if source_type == "ROOM" and dest_type == "ACCOUNT":
            # Stabling — CHARACTER → ACCOUNT
            NFTService.bank(self.token_id)

        elif source_type == "ACCOUNT" and dest_type == "ROOM":
            # Retrieving — ACCOUNT → CHARACTER
            NFTService.unbank(self.token_id, self.owner_key)

    @staticmethod
    def _is_same_owner(source_type, source_owner, dest_type, dest_owner):
        """Disabled for pets — room-to-room no-op handled in at_post_move."""
        raise NotImplementedError(
            "_is_same_owner() is disabled on pets. "
            "Pet room-to-room no-op is handled directly in at_post_move."
        )

    # ================================================================== #
    #  Overridden — no-op (intentionally disabled for pets)
    # ================================================================== #

    def _cascade_container_transition(self, *args, **kwargs):
        # No-op — pets don't cascade container contents yet.
        # Future: panniers/saddlebags will need this.
        pass

    def _cascade_fungibles(self, *args, **kwargs):
        # No-op — pets don't carry fungibles yet.
        pass

    @staticmethod
    def _cascade_fungible_gold(*args, **kwargs):
        # No-op — disabled for pets.
        pass

    @staticmethod
    def _cascade_fungible_resource(*args, **kwargs):
        # No-op — disabled for pets.
        pass

    # ================================================================== #
    #  New — pet-specific methods
    # ================================================================== #

    def transfer_ownership(self, new_owner):
        """Transfer pet to a new owner. Pet stays in the same room.

        The pet does not move, so no move hook fires and this is the only
        place the ownership change is recorded. Local state and the
        ownership write are held in one transaction on the default
        connection, the ownership write last — see design/database.md
        § Transactions and Split Aliases.

        Args:
            new_owner (Character): who the pet belongs to now.

        Returns:
            bool: True if ownership changed. False leaves the pet with its
                original owner, in the state it was already in, and writes
                a ReconciliationFailure row.
        """
        from blockchain.xrpl.services.nft import NFTService

        # Captured before anything changes, so a failed transfer can put
        # the pet back as it was. A pet told to wait beside its owner must
        # not come back following them.
        original_owner_key = self.owner_key
        original_state = self.pet_state

        transferred = True
        try:
            with transaction.atomic():
                if hasattr(self, "force_dismount") and getattr(
                    self, "is_mounted", False
                ):
                    self.force_dismount()
                self.stop_following()

                # Read the old wallet before owner_key changes, and the new
                # one after — _get_owner_wallet() resolves through owner_key.
                old_wallet = self._get_owner_wallet()
                self.owner_key = new_owner.key

                NFTService.transfer(
                    self.token_id, old_wallet, original_owner_key,
                    self._get_owner_wallet(),
                    self._get_character_key(new_owner),
                )
        except Exception as err:
            transferred = False
            # The rows are back; the in-memory Attributes are not, and the
            # settle below reads owner_key.
            discard_cached_attributes(self)
            record_failure(
                "pet_transfer_ownership",
                self._get_owner_wallet(),
                err,
                character_key=original_owner_key,
                tx_hash=None,
            )

        # Runs either way. Ownership is read back rather than assumed: on a
        # rollback owner_key is the original owner again, and the pet is
        # restored to the state it was in rather than recomputed.
        owner = self._get_owner_character()
        if self.owner_key == original_owner_key:
            if original_state == "following" and owner:
                self.start_following(owner)
            self.pet_state = original_state
        elif owner and owner.location == self.location:
            self.start_following(owner)
            self.pet_state = "following"
        else:
            self.pet_state = "waiting"

        return transferred

    def _get_owner_character(self):
        """Find owner Character object from owner_key.
        Returns None if not found (offline, deleted, etc).
        """
        if not self.owner_key:
            return None
        from evennia import search_object
        results = search_object(self.owner_key, exact=True)
        for obj in results:
            if p_is_character(obj, self):
                return obj
        return None

    def _get_owner_wallet(self):
        """Get wallet address for this pet's owner.
        Finds character from owner_key, then gets wallet from their account.
        Returns wallet address string or None.
        """
        owner = self._get_owner_character()
        if owner is None:
            return None
        return super()._get_owner_wallet(owner)

    def _classify_location(self, obj):
        """Classify a location for pet mirror dispatch.

        None → None (creation — pet entering game)
        AccountBank → "ACCOUNT" (stabled)
        Anything else → "ROOM" (active in world)
        """
        if obj is None:
            return None
        from typeclasses.accounts.account_bank import AccountBank
        if isinstance(obj, AccountBank):
            return "ACCOUNT"
        return "ROOM"

    @staticmethod
    def spawn_pet(token_id, room, owner_key, **kwargs):
        """Create a pet actor from an NFT mirror row and place it in a room.

        Reads NFTGameState to get typeclass, name, metadata.
        Sets owner_key BEFORE move_to so at_post_move resolves ownership.

        Args:
            token_id: NFT token ID (from assign_to_blank_token)
            room: room to spawn the pet in
            owner_key: character key of the owner

        Returns:
            The created pet actor, or None if mirror row not found.
        """
        from evennia.prototypes.spawner import spawn as evennia_spawn
        from blockchain.xrpl.models import NFTGameState

        try:
            nft = NFTGameState.objects.select_related("item_type").get(
                nftoken_id=str(token_id),
            )
        except NFTGameState.DoesNotExist:
            return None

        spawn_dict = {"location": None}

        if nft.item_type:
            if nft.item_type.prototype_key:
                spawn_dict["prototype_parent"] = nft.item_type.prototype_key
            else:
                spawn_dict["typeclass"] = (
                    nft.item_type.typeclass
                    or "typeclasses.actors.pets.base_pet.BasePet"
                )
            spawn_dict["key"] = nft.item_type.name
            spawn_dict["desc"] = nft.item_type.description or ""
        else:
            spawn_dict["typeclass"] = "typeclasses.actors.pets.base_pet.BasePet"
            spawn_dict["key"] = f"Pet #{token_id}"

        obj = evennia_spawn(spawn_dict)[0]

        # Set NFT identity + owner BEFORE move_to triggers at_post_move
        obj.token_id = token_id
        obj.owner_key = owner_key

        # Apply per-instance metadata (pet level, stats, etc)
        meta = nft.metadata or {}
        for key, value in meta.items():
            obj.attributes.add(key, value)

        # move_to triggers at_post_move → craft_output
        obj.move_to(room, **kwargs)

        return obj

    # ================================================================== #
    #  Guards
    # ================================================================== #

    def at_pre_move(self, destination, **kwargs):
        """CRITICAL GUARD: pets can never enter character.contents.
        Only rooms and AccountBank are valid destinations.
        """
        from typeclasses.actors.character import FCMCharacter
        if isinstance(destination, FCMCharacter):
            return False
        return super().at_pre_move(destination, **kwargs)

    def at_pre_get(self, getter, **kwargs):
        """Block standard pickup."""
        getter.msg(f"You can't pick up {self.get_display_name(getter)}.")
        return False
