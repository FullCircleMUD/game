"""
NFTMirrorMixin — composable NFT mirror state machine.

Provides the full NFT lifecycle (mirror tracking, ownership transitions,
factory methods) as a mixin that can be composed into ANY Evennia object —
whether a DefaultObject (items) or DefaultCharacter (pets/actors).

All NFT mirror/ownership updates flow through this mixin's hooks:

    at_post_move    — handles ALL location-based transitions (pickup, drop,
                      transfer, bank, unbank, spawn, craft_output, reserve_to_account)
    at_object_delete — handles ALL destruction transitions (despawn, craft_input,
                       account_to_reserve)

Extracted from BaseNFTItem to enable NFT-backed actors (pets, mounts) that
need actor infrastructure (HP, combat, following) alongside NFT tracking.

Composed into:
    BaseNFTItem(NFTMirrorMixin, ..., DefaultObject) — items
    BasePet(NFTMirrorMixin, ..., BaseNPC)           — pets/mounts (future)
"""

from evennia.typeclasses.attributes import AttributeProperty
from django.conf import settings


class NFTMirrorMixin:
    """
    Mixin providing full NFT mirror lifecycle tracking.

    Attributes (persisted):
        token_id         — on-chain NFT token ID
        chain_id         — blockchain chain ID
        contract_address — NFT contract proxy address
    """

    token_id = AttributeProperty(None)
    chain_id = AttributeProperty(None)
    contract_address = AttributeProperty(None)

    # ================================================================== #
    #  Evennia Hooks — Mirror Transitions
    # ================================================================== #

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
        """Handle NFT creation (source is None — object entering the game)."""
        from blockchain.xrpl.services.nft import NFTService

        if dest_type == "CHARACTER":
            wallet = self._get_wallet(dest_owner)
            char_key = self._get_character_key(dest_owner)
            try:
                NFTService.craft_output(
                    self.token_id, wallet, self.chain_id,
                    self.contract_address, char_key,
                )
            except ValueError as err:
                self._log_error("craft_output", err)

        elif dest_type == "ACCOUNT":
            wallet = dest_owner.wallet_address
            tx_hash = kwargs.get("tx_hash")
            try:
                NFTService.deposit_from_chain(
                    self.token_id, wallet,
                    settings.XRPL_VAULT_ADDRESS, tx_hash,
                )
            except ValueError as err:
                self._log_error("deposit_from_chain", err)

        else:
            try:
                NFTService.spawn(
                    self.token_id, self.chain_id, self.contract_address,
                )
            except ValueError as err:
                self._log_error("spawn", err)

    def _execute_transition(self, source_type, source_owner,
                            dest_type, dest_owner):
        """
        Execute a single NFT mirror state transition.

        Dispatches the correct NFTService call based on source → dest types.
        """
        from blockchain.xrpl.services.nft import NFTService

        if source_type == "WORLD" and dest_type == "WORLD":
            return

        if source_type == "WORLD" and dest_type == "CHARACTER":
            wallet = self._get_wallet(dest_owner)
            char_key = self._get_character_key(dest_owner)
            try:
                NFTService.pickup(
                    self.token_id, wallet, self.chain_id,
                    self.contract_address, char_key,
                )
            except ValueError as err:
                self._log_error("pickup", err)

        elif source_type == "CHARACTER" and dest_type == "WORLD":
            try:
                NFTService.drop(
                    self.token_id, self.chain_id,
                    self.contract_address, settings.XRPL_VAULT_ADDRESS,
                )
            except ValueError as err:
                self._log_error("drop", err)

        elif source_type == "CHARACTER" and dest_type == "CHARACTER":
            from_wallet = self._get_wallet(source_owner)
            from_key = self._get_character_key(source_owner)
            to_wallet = self._get_wallet(dest_owner)
            to_key = self._get_character_key(dest_owner)
            try:
                NFTService.transfer(
                    self.token_id, from_wallet, from_key,
                    to_wallet, to_key, self.chain_id,
                    self.contract_address,
                )
            except ValueError as err:
                self._log_error("transfer", err)

        elif source_type == "CHARACTER" and dest_type == "ACCOUNT":
            try:
                NFTService.bank(
                    self.token_id, self.chain_id, self.contract_address,
                )
            except ValueError as err:
                self._log_error("bank", err)

        elif source_type == "ACCOUNT" and dest_type == "CHARACTER":
            char_key = self._get_character_key(dest_owner)
            try:
                NFTService.unbank(
                    self.token_id, self.chain_id,
                    self.contract_address, char_key,
                )
            except ValueError as err:
                self._log_error("unbank", err)

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

        from blockchain.xrpl.services.gold import GoldService
        from blockchain.xrpl.services.resource import ResourceService

        chain_id = settings.BLOCKCHAIN_CHAIN_ID
        gold_contract = settings.CONTRACT_GOLD
        res_contract = settings.CONTRACT_RESOURCES
        vault = settings.XRPL_VAULT_ADDRESS

        source_wallet = (
            self._get_wallet(source_owner) if source_type == "CHARACTER"
            else vault
        )
        source_key = (
            self._get_character_key(source_owner)
            if source_type == "CHARACTER" else None
        )
        dest_wallet = (
            self._get_wallet(dest_owner) if dest_type == "CHARACTER"
            else vault
        )
        dest_key = (
            self._get_character_key(dest_owner)
            if dest_type == "CHARACTER" else None
        )

        try:
            if gold > 0:
                self._cascade_fungible_gold(
                    source_type, dest_type,
                    source_wallet, source_key,
                    dest_wallet, dest_key,
                    gold, chain_id, gold_contract, vault,
                )

            for rid, amt in resources.items():
                if amt > 0:
                    self._cascade_fungible_resource(
                        source_type, dest_type,
                        source_wallet, source_key,
                        dest_wallet, dest_key,
                        rid, amt, chain_id, res_contract, vault,
                    )
        except ValueError as err:
            self._log_error("cascade_fungibles", err)

    @staticmethod
    def _cascade_fungible_gold(source_type, dest_type,
                               source_wallet, source_key,
                               dest_wallet, dest_key,
                               amount, chain_id, contract, vault):
        """Dispatch a single gold cascade service call."""
        from blockchain.xrpl.services.gold import GoldService

        if source_type == "CHARACTER" and dest_type == "WORLD":
            GoldService.drop(source_wallet, amount, chain_id, contract,
                             vault, source_key)
        elif source_type == "WORLD" and dest_type == "CHARACTER":
            GoldService.pickup(dest_wallet, amount, chain_id, contract,
                               vault, dest_key)
        elif source_type == "CHARACTER" and dest_type == "CHARACTER":
            GoldService.transfer(source_wallet, source_key, dest_wallet,
                                 dest_key, amount, chain_id, contract)
        elif source_type == "CHARACTER" and dest_type == "ACCOUNT":
            GoldService.bank(source_wallet, amount, chain_id, contract,
                             source_key)
        elif source_type == "ACCOUNT" and dest_type == "CHARACTER":
            GoldService.unbank(dest_wallet, amount, chain_id, contract,
                               dest_key)

    @staticmethod
    def _cascade_fungible_resource(source_type, dest_type,
                                   source_wallet, source_key,
                                   dest_wallet, dest_key,
                                   resource_id, amount,
                                   chain_id, contract, vault):
        """Dispatch a single resource cascade service call."""
        from blockchain.xrpl.services.resource import ResourceService

        if source_type == "CHARACTER" and dest_type == "WORLD":
            ResourceService.drop(source_wallet, resource_id, amount,
                                 chain_id, contract, vault, source_key)
        elif source_type == "WORLD" and dest_type == "CHARACTER":
            ResourceService.pickup(dest_wallet, resource_id, amount,
                                   chain_id, contract, vault, dest_key)
        elif source_type == "CHARACTER" and dest_type == "CHARACTER":
            ResourceService.transfer(source_wallet, source_key,
                                     dest_wallet, dest_key, resource_id,
                                     amount, chain_id, contract)
        elif source_type == "CHARACTER" and dest_type == "ACCOUNT":
            ResourceService.bank(source_wallet, resource_id, amount,
                                 chain_id, contract, source_key)
        elif source_type == "ACCOUNT" and dest_type == "CHARACTER":
            ResourceService.unbank(dest_wallet, resource_id, amount,
                                   chain_id, contract, dest_key)

    # ================================================================== #
    #  Deletion — Mirror Cleanup
    # ================================================================== #

    def at_object_delete(self):
        """
        Called just before this object is deleted. Return False to abort.

        Handles container cleanup and mirror state transition.
        """
        # --- Container cleanup: delete contents before the container itself ---
        if getattr(self, "is_container", False):
            if hasattr(self, "get_gold") and self.get_gold() > 0:
                try:
                    self.return_gold_to_reserve(self.get_gold())
                except (ValueError, AttributeError) as err:
                    self._log_error("container_gold_cleanup", err)
            if hasattr(self, "get_all_resources"):
                for rid, amt in list(self.get_all_resources().items()):
                    if amt > 0:
                        try:
                            self.return_resource_to_reserve(rid, amt)
                        except (ValueError, AttributeError) as err:
                            self._log_error("container_resource_cleanup", err)
            for obj in list(self.contents):
                if getattr(obj, "token_id", None) is not None:
                    obj.delete()

        # --- Now handle this object's own mirror transition ---
        if self.token_id is None:
            return True

        from blockchain.xrpl.services.nft import NFTService

        location_type, _owner = self._resolve_owner(self.location)

        try:
            if location_type == "CHARACTER":
                NFTService.craft_input(
                    self.token_id, self.chain_id,
                    self.contract_address, settings.XRPL_VAULT_ADDRESS,
                )
            elif location_type == "ACCOUNT":
                tx_hash = getattr(self.ndb, "pending_tx_hash", None)
                NFTService.withdraw_to_chain(
                    self.token_id, tx_hash,
                )
            else:
                NFTService.despawn(
                    self.token_id, self.chain_id, self.contract_address,
                )
        except ValueError as err:
            self._log_error("delete", err)

        return True

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
        return NFTService.assign_item_type(
            item_type_name,
            None,
            None,
        )

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
        obj.chain_id = None
        obj.contract_address = None

        if nft.item_type and nft.item_type.prototype_key:
            obj.db.prototype_key = nft.item_type.prototype_key

        meta = nft.metadata or {}
        for key, value in meta.items():
            obj.attributes.add(key, value)

        obj.move_to(location, **kwargs)

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
            from_wallet = NFTMirrorMixin._get_wallet(source_owner)
            to_wallet = NFTMirrorMixin._get_wallet(dest_owner)
            return from_wallet == to_wallet
        if source_type == "ACCOUNT":
            return (getattr(source_owner, "wallet_address", None)
                    == getattr(dest_owner, "wallet_address", None))
        return source_owner is dest_owner

    @staticmethod
    def _get_wallet(character):
        """Get a character's wallet address from their account."""
        if character is None or character.account is None:
            return None
        return character.account.attributes.get("wallet_address")

    @staticmethod
    def _get_character_key(character):
        """Get the character_key used to identify this character in the mirror DB."""
        if character is None:
            return None
        return character.key

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
    def get_nft_mirror(token_id, chain_id=None, contract_address=None):
        """Look up an NFTGameState row by token_id."""
        from blockchain.xrpl.services.nft import NFTService
        return NFTService.get_nft(token_id, chain_id, contract_address)

    def _log_error(self, operation, err):
        """Log a mirror update failure."""
        print(f"  NFT mirror {operation} failed for #{self.token_id}: {err}")
