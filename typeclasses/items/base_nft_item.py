"""
BaseNFTItem — Evennia object representing an NFT in the game world.

Each instance maps 1:1 to an NFTMirror row via (token_id, chain_id, contract_address).
All NFT mirror/ownership updates flow through this class's Evennia hooks:

    at_post_move    — handles ALL location-based transitions (pickup, drop,
                      transfer, bank, unbank, spawn, craft_output, reserve_to_account)
    at_object_delete — handles ALL destruction transitions (despawn, craft_input,
                       account_to_reserve)
    at_object_creation — lock setup only (attributes not yet available)

Spawning an NFT item (blank pool → game world):
    1. assign_to_blank_token("Iron Longsword")
       → NFTService.assign_item_type() picks the lowest blank RESERVE token,
         writes item_type + default_metadata onto the NFTMirror row.
         Token stays in RESERVE. Returns token_id.

    2. spawn_into(token_id, location)
       → Reads NFTMirror to get prototype_key, typeclass, name, description.
         Uses Evennia's spawn() to create the object with prototype attrs
         (damage, speed, weight, etc.). Object is created WITHOUT a location
         so NFT attributes (token_id, chain_id, contract_address) can be set
         before at_post_move fires. Metadata (per-instance mutable state like
         durability) is applied as Evennia attributes after prototype attrs.
         Finally move_to(location) triggers at_post_move(source_location=None)
         which calls NFTService.spawn() to transition RESERVE → SPAWNED.

Despawning (game world → blank pool):
    Deleting the Evennia object (obj.delete()) triggers at_object_delete,
    which calls NFTService.despawn/craft_input/account_to_reserve depending
    on where the item is. All three wipe item_type and metadata back to None/{}
    via _reset_token_identity(), returning the token to the blank pool.

Subclass hierarchy:
    BaseNFTItem (this class — never instantiate directly)
    ├── TakeableNFTItem    — items characters can get/drop/give/bank
    │   ├── WeaponNFTItem
    │   ├── ArmorNFTItem   (future)
    │   └── ...
    └── WorldAnchoredNFTItem  — items with specialised commands (mounts, pets, property)
        ├── MountNFTItem   (future)
        ├── PetNFTItem     (future)
        └── ...

Usage (spawning items):
    from typeclasses.items.base_nft_item import BaseNFTItem

    token_id = BaseNFTItem.assign_to_blank_token("Iron Longsword")
    obj = BaseNFTItem.spawn_into(token_id, room)
"""

from evennia.objects.objects import DefaultObject
from evennia.typeclasses.attributes import AttributeProperty
from django.conf import settings

from typeclasses.mixins.hidden_object import HiddenObjectMixin
from typeclasses.mixins.height_aware_mixin import HeightAwareMixin
from typeclasses.mixins.item_restriction import ItemRestrictionMixin


class BaseNFTItem(HeightAwareMixin, HiddenObjectMixin, ItemRestrictionMixin, DefaultObject):
    """
    Base class for all NFT-backed items in the game world.

    Attributes (persisted):
        token_id         — on-chain NFT token ID
        chain_id         — blockchain chain ID (137 = Polygon)
        contract_address — NFT contract proxy address
        nft_metadata     — full metadata dict from NFTMirror
    """

    token_id = AttributeProperty(None)
    chain_id = AttributeProperty(None)
    contract_address = AttributeProperty(None)
    weight = AttributeProperty(0.0)
    identify_mastery_gate = AttributeProperty(1)  # tier required to identify (1=BASIC)
    ground_description = AttributeProperty("")  # e.g. "A rusty sword lies here."

    # ================================================================== #
    #  Evennia Hooks
    # ================================================================== #

    def at_object_creation(self):
        """Called once when the object is first created."""
        super().at_object_creation()
        self.at_hidden_init()
        # NOTE: get lock is NOT set here — subclasses determine takeability.
        # TakeableNFTItem inherits Evennia's default get:true().
        # WorldAnchoredNFTItem overrides with get:false().
        #
        # AttributeProperty values (token_id, etc.) are not yet available
        # here — Evennia sets attributes from create_object() AFTER this hook.
        # at_post_move fires after attributes are set, so all mirror updates
        # happen there.

    def at_post_move(self, source_location, move_type="move", **kwargs):
        """
        Called after this item moves to a new location.

        This is the SINGLE POINT OF ENTRY for all NFT mirror updates that
        involve an item existing in-game. Evennia fires this hook both for
        normal moves (item.move_to()) AND during create_object() when a
        location is specified — in the creation case, source_location is None.

        Location types are resolved through containers via _resolve_owner():
            CHARACTER — item is on a character (or in a container on a character)
            ACCOUNT   — item is in a bank (or in a container in a bank)
            WORLD     — item is in a room / on the ground (or in a container
                        that's on the ground)

        The combination of (source_type, dest_type) determines which
        NFTService method to call:

        Creation (source is None → item entering the game):
            None → WORLD     = spawn              (RESERVE → SPAWNED)
            None → CHARACTER = craft_output       (RESERVE → CHARACTER)
            None → ACCOUNT   = deposit_from_chain (ONCHAIN → ACCOUNT)

        Movement (source is not None):
            WORLD     → CHARACTER = pickup    (SPAWNED → CHARACTER)
            CHARACTER → WORLD     = drop      (CHARACTER → SPAWNED)
            CHARACTER → CHARACTER = transfer  (CHARACTER → CHARACTER, diff wallet)
            CHARACTER → ACCOUNT   = bank      (CHARACTER → ACCOUNT)
            ACCOUNT   → CHARACTER = unbank    (ACCOUNT → CHARACTER)

        Ignored (no mirror change needed):
            WORLD → WORLD  (stays SPAWNED)
            same wallet     (e.g. inventory ↔ backpack on same character)
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
        # Check for same-entity no-op (e.g. inventory ↔ backpack)
        if self._is_same_owner(source_type, source_owner, dest_type, dest_owner):
            return

        self._execute_transition(
            source_type, source_owner, dest_type, dest_owner,
        )

        # If this item is a container, cascade the transition to contents
        self._cascade_container_transition(
            source_type, source_owner, dest_type, dest_owner,
        )

    def _handle_creation(self, dest_type, dest_owner, dest, **kwargs):
        """Handle NFT creation (source is None — item entering the game)."""
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
        Reusable by both at_post_move (for the item itself) and cascade
        logic (for items inside a container that moves).
        """
        from blockchain.xrpl.services.nft import NFTService

        # WORLD → WORLD: no-op (stays SPAWNED)
        if source_type == "WORLD" and dest_type == "WORLD":
            return

        # WORLD → CHARACTER: pickup
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

        # CHARACTER → WORLD: drop
        elif source_type == "CHARACTER" and dest_type == "WORLD":
            try:
                NFTService.drop(
                    self.token_id, self.chain_id,
                    self.contract_address, settings.XRPL_VAULT_ADDRESS,
                )
            except ValueError as err:
                self._log_error("drop", err)

        # CHARACTER → CHARACTER: transfer (different wallets)
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

        # CHARACTER → ACCOUNT: bank
        elif source_type == "CHARACTER" and dest_type == "ACCOUNT":
            try:
                NFTService.bank(
                    self.token_id, self.chain_id, self.contract_address,
                )
            except ValueError as err:
                self._log_error("bank", err)

        # ACCOUNT → CHARACTER: unbank
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
        If this item is a container, cascade the ownership transition to
        all NFT contents and fungibles inside.

        Called after the container's own transition completes.
        """
        if not getattr(self, "is_container", False):
            return

        # --- NFT cascade ---
        for obj in self.contents:
            if not isinstance(obj, BaseNFTItem) or obj.token_id is None:
                continue
            obj._execute_transition(
                source_type, source_owner, dest_type, dest_owner,
            )

        # --- Fungible cascade ---
        self._cascade_fungibles(source_type, source_owner,
                                dest_type, dest_owner)

    def _cascade_fungibles(self, source_type, source_owner,
                           dest_type, dest_owner):
        """
        Cascade fungible ownership changes when a container moves.

        Dispatches gold/resource service calls to match the container's
        new ownership. Local state (db.gold, db.resources) stays on the
        container — only the mirror ownership changes.
        """
        gold = 0
        resources = {}
        if hasattr(self, "get_gold"):
            gold = self.get_gold()
        if hasattr(self, "get_all_resources"):
            resources = self.get_all_resources()

        if gold <= 0 and not any(v > 0 for v in resources.values()):
            return  # nothing to cascade

        from blockchain.xrpl.services.gold import GoldService
        from blockchain.xrpl.services.resource import ResourceService

        chain_id = settings.BLOCKCHAIN_CHAIN_ID
        gold_contract = settings.CONTRACT_GOLD
        res_contract = settings.CONTRACT_RESOURCES
        vault = settings.XRPL_VAULT_ADDRESS

        # Resolve wallet/key for CHARACTER endpoints
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
            # --- Gold ---
            if gold > 0:
                self._cascade_fungible_gold(
                    source_type, dest_type,
                    source_wallet, source_key,
                    dest_wallet, dest_key,
                    gold, chain_id, gold_contract, vault,
                )

            # --- Resources ---
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

    @staticmethod
    def _is_same_owner(source_type, source_owner, dest_type, dest_owner):
        """
        Check if source and dest resolve to the same owner.

        WORLD → WORLD is always same-owner (both vault-owned).
        CHARACTER → CHARACTER compares wallet addresses.
        ACCOUNT → ACCOUNT compares wallet addresses.
        """
        if source_type == "WORLD" and dest_type == "WORLD":
            return True
        if source_type != dest_type:
            return False
        # Same type — compare identity
        if source_owner is None or dest_owner is None:
            return source_owner is dest_owner
        if source_type == "CHARACTER":
            from_wallet = BaseNFTItem._get_wallet(source_owner)
            to_wallet = BaseNFTItem._get_wallet(dest_owner)
            return from_wallet == to_wallet
        if source_type == "ACCOUNT":
            return (getattr(source_owner, "wallet_address", None)
                    == getattr(dest_owner, "wallet_address", None))
        return source_owner is dest_owner

    def at_object_delete(self):
        """
        Called just before this object is deleted. Return False to abort.

        The item's resolved ownership determines which service method to call:

            WORLD (room/ground)  → despawn            (SPAWNED → RESERVE)
            CHARACTER            → craft_input         (CHARACTER → RESERVE)
            ACCOUNT              → withdraw_to_chain   (ACCOUNT → ONCHAIN)

        If this item is a container, all contents are cleaned up first:
        fungibles are returned to reserve, NFT contents are cascade-deleted.
        """
        # --- Container cleanup: delete contents before the container itself ---
        if getattr(self, "is_container", False):
            # Return fungibles to reserve
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
            # Cascade-delete NFT contents
            for obj in list(self.contents):
                if isinstance(obj, BaseNFTItem):
                    obj.delete()

        # --- Now handle this item's own mirror transition ---
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
    #  Factory Methods — creating new NFT items
    # ================================================================== #

    @staticmethod
    def assign_to_blank_token(item_type_name):
        """
        Pick the next blank RESERVE token and assign it an item type.

        Writes item_type + default_metadata onto the NFTGameState row.
        Returns the token_id ready for spawn_into().

        Args:
            item_type_name: Name of the NFTItemType (e.g. "Iron Longsword")

        Raises:
            NFTItemType.DoesNotExist — unknown item type name
            ValueError — no blank tokens available in the reserve pool
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
        object with all prototype attributes applied (damage, speed,
        weight, etc.). Created without a location so we can set NFT
        attributes before at_post_move fires.

        The move_to() call triggers at_post_move which handles the
        service-layer state transition (e.g. RESERVE → SPAWNED or
        RESERVE → CHARACTER depending on what location is).

        Metadata from NFTMirror (per-instance mutable state like
        durability) is applied after prototype attributes.

        Args:
            token_id: NFTMirror token_id (returned by assign_to_blank_token)
            location: Evennia object to place the item (room, character, etc.)

        Returns:
            The created Evennia object, or None if the mirror row wasn't found.
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

        # Recycle bin as home — orphaned items get cleaned up
        recycle_results = search_object("nft_recycle_bin", exact=True)
        recycle_bin = recycle_results[0] if recycle_results else None

        # Build spawn dict — prototype provides typeclass + static stats,
        # item_type provides name + description, no location yet.
        spawn_dict = {"location": None}

        if nft.item_type:
            if nft.item_type.prototype_key:
                spawn_dict["prototype_parent"] = nft.item_type.prototype_key
            else:
                # No prototype — use typeclass directly
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

        # Evennia spawn() applies prototype attrs (damage, speed, etc.)
        obj = evennia_spawn(spawn_dict)[0]

        # Set NFT identity — must happen before move_to triggers at_post_move
        obj.token_id = token_id
        obj.chain_id = None
        obj.contract_address = None

        # Store prototype_key as a db attribute for recipe lookup (used by
        # cmd_repair to find the crafting recipe for this item).
        #
        # WARNING: Do NOT add "prototype_key" to spawn_dict above. Evennia's
        # spawner treats prototype_key + prototype_parent with the same value
        # as a circular self-reference and raises RuntimeError. The db attribute
        # below is the correct mechanism — Evennia's from_prototype tag is NOT
        # set by this spawn path and must not be relied upon.
        if nft.item_type and nft.item_type.prototype_key:
            obj.db.prototype_key = nft.item_type.prototype_key

        # Apply per-instance mutable state from metadata (e.g. durability)
        meta = nft.metadata or {}
        for key, value in meta.items():
            obj.attributes.add(key, value)

        # move_to triggers at_post_move(source_location=None) → service call
        # kwargs (e.g. tx_hash) are passed through to at_post_move hooks
        obj.move_to(location, **kwargs)

        return obj

    # ================================================================== #
    #  Location Classification Helpers
    # ================================================================== #

    @staticmethod
    def _classify(obj):
        """
        Classify an Evennia object into a location type for mirror updates.

        Returns:
            "CHARACTER" — obj is an FCMCharacter
            "ACCOUNT"   — obj is an AccountBank
            "WORLD"     — anything else (rooms, containers, None)
            None        — obj is None (used for creation detection)
        """
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
        """
        Resolve the effective owner of a location, walking through containers.

        Unlike _classify() which returns "WORLD" for containers, this walks
        up the .location chain until it finds a CHARACTER, ACCOUNT, or
        reaches a room/None.

        Returns:
            (type_string, owner_object) — e.g. ("CHARACTER", <FCMCharacter>)
            (None, None)                — obj is None (creation)
            ("WORLD", None)             — reached a room or the end of the chain

        For CHARACTER→CHARACTER comparisons, callers should compare wallet
        addresses on the resolved objects to detect same-entity no-ops.
        """
        if obj is None:
            return (None, None)

        current = obj
        while current is not None:
            classified = BaseNFTItem._classify(current)
            if classified != "WORLD":
                return (classified, current)
            current = getattr(current, "location", None)
        return ("WORLD", None)

    @staticmethod
    def _get_wallet(character):
        """
        Get a character's wallet address from their account.
        Characters belong to accounts, and the wallet lives on the account.
        """
        if character is None or character.account is None:
            return None
        return character.account.attributes.get("wallet_address")

    @staticmethod
    def _get_character_key(character):
        """
        Get the character_key used to identify this character in the mirror DB.
        Currently uses the character's name (character.key).
        Change this single method if a different identifier is needed later.
        """
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
        """Log a mirror update failure. Centralized for consistent formatting."""
        print(f"  NFT mirror {operation} failed for #{self.token_id}: {err}")

    # ================================================================== #
    #  Display
    # ================================================================== #

    def is_visible_to(self, character):
        """Hidden-state visibility check for room display filtering."""
        return self.is_hidden_visible_to(character)

    def get_display_name(self, looker=None, **kwargs):
        """Include token ID for builders, plain name for players."""
        name = super().get_display_name(looker, **kwargs)
        if looker and self.locks.check_lockstring(looker, "perm(Builder)"):
            return f"{name} |w[NFT #{self.token_id}]|n"
        return name
