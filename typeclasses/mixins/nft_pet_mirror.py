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

from evennia.typeclasses.attributes import AttributeProperty

from typeclasses.mixins.nft_mirror import NFTMirrorMixin


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

    def at_object_delete(self):
        """Pet deletion — mirror cleanup.

        Owned pet in world → craft_input (CHARACTER → unallocated)
        Stabled pet exported → withdraw_to_chain (ACCOUNT → ONCHAIN)
        """
        if self.token_id is None:
            return True

        from blockchain.xrpl.services.nft import NFTService
        from evennia.utils import logger

        location_type = self._classify_location(self.location)

        try:
            if self.owner_key and location_type != "ACCOUNT":
                # Owned pet in world — death, admin delete, etc
                NFTService.craft_input(
                    self.token_id, settings.XRPL_VAULT_ADDRESS,
                )
            elif location_type == "ACCOUNT":
                # Stabled pet being exported to external wallet
                tx_hash = getattr(self.ndb, "pending_tx_hash", None)
                NFTService.withdraw_to_chain(
                    self.token_id, tx_hash,
                )
            else:
                # This should never happen — pet without owner being deleted.
                # Safety despawn with logging to investigate.
                logger.log_err(
                    f"PET MIRROR ERROR: Unowned pet #{self.token_id} "
                    f"'{self.key}' deleted from {self.location}. "
                    f"owner_key={self.owner_key}, location_type={location_type}. "
                    f"Performing safety despawn."
                )
                NFTService.despawn(self.token_id)
        except ValueError as err:
            self._log_error("delete", err)

        return True

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
        """
        from blockchain.xrpl.services.nft import NFTService

        if dest_type == "ROOM":
            wallet = self._get_owner_wallet()
            char_key = self.owner_key
            try:
                NFTService.craft_output(
                    self.token_id, wallet, char_key,
                )
            except ValueError as err:
                self._log_error("craft_output", err)

        elif dest_type == "ACCOUNT":
            wallet = dest.wallet_address if hasattr(dest, "wallet_address") else None
            tx_hash = kwargs.get("tx_hash")
            try:
                NFTService.deposit_from_chain(
                    self.token_id, wallet,
                    settings.XRPL_VAULT_ADDRESS, tx_hash,
                )
            except ValueError as err:
                self._log_error("deposit_from_chain", err)

    def _execute_transition(self, source_type, dest_type):
        """Pet movement transitions.

        ROOM → ACCOUNT: stable → bank()
        ACCOUNT → ROOM: retrieve → unbank()
        (ROOM → ROOM is handled as no-op in at_post_move before this is called)
        """
        from blockchain.xrpl.services.nft import NFTService

        if source_type == "ROOM" and dest_type == "ACCOUNT":
            # Stabling — CHARACTER → ACCOUNT
            try:
                NFTService.bank(self.token_id)
            except ValueError as err:
                self._log_error("bank", err)

        elif source_type == "ACCOUNT" and dest_type == "ROOM":
            # Retrieving — ACCOUNT → CHARACTER
            char_key = self.owner_key
            try:
                NFTService.unbank(self.token_id, char_key)
            except ValueError as err:
                self._log_error("unbank", err)

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
        """Transfer pet to a new owner. Pet stays in same room.

        1. Force dismount if mounted
        2. Stop following old owner
        3. Look up old owner's wallet
        4. Update owner_key to new owner
        5. Look up new owner's wallet
        6. Call NFTService.transfer()
        7. Start following new owner if in same room
        """
        from blockchain.xrpl.services.nft import NFTService

        # Force dismount
        if hasattr(self, "force_dismount") and getattr(self, "is_mounted", False):
            self.force_dismount()

        # Stop following old owner
        self.stop_following()

        # Get old owner's wallet before changing owner_key
        old_wallet = self._get_owner_wallet()
        old_key = self.owner_key

        # Update ownership
        self.owner_key = new_owner.key

        # Get new owner's wallet
        new_wallet = self._get_owner_wallet(new_owner)
        new_key = self._get_character_key(new_owner)

        # Mirror update
        try:
            NFTService.transfer(
                self.token_id, old_wallet, old_key,
                new_wallet, new_key,
            )
        except ValueError as err:
            self._log_error("transfer", err)

        # Follow new owner if they're in the same room
        if new_owner.location == self.location:
            self.start_following(new_owner)
            self.pet_state = "following"
        else:
            self.pet_state = "waiting"

    def _get_owner_character(self):
        """Find owner Character object from owner_key.
        Returns None if not found (offline, deleted, etc).
        """
        if not self.owner_key:
            return None
        from evennia import search_object
        results = search_object(self.owner_key, exact=True)
        for obj in results:
            if getattr(obj, "is_pc", False):
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
        return self._get_owner_wallet(owner)

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
