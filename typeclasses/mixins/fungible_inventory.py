"""
FungibleInventoryMixin — adds gold and resource tracking to any Evennia object.

Mix into Characters, Mobs, Rooms, Containers, Corpses, AccountBanks —
anything that can hold gold or resources. NFTs (unique items) are handled
separately by BaseNFTItem.

This mixin is the SINGLE POINT OF ENTRY for all gold and resource service
calls. Game code never calls GoldService or ResourceService directly —
it goes through the transfer/receive methods here, which keep both the
local Evennia state (self.db.gold, self.db.resources) and the blockchain
mirror DB in sync.

Public API:
    # Two-sided transfers (self → target, target must be an Evennia object)
    self.transfer_gold_to(target, amount)
    self.transfer_resource_to(target, rid, amount)

    # Return to reserve (self → vault RESERVE) — cleanup/despawn only
    self.return_gold_to_reserve(amount)
    self.return_resource_to_reserve(resource_id, amount)

    # Return to sink (self → vault SINK) — consumption/fees/crafting
    self.return_gold_to_sink(amount)
    self.return_resource_to_sink(resource_id, amount)

    # One-sided receives (reserve → self)
    self.receive_gold_from_reserve(amount)
    self.receive_resource_from_reserve(resource_id, amount)

    # Read-only
    self.get_gold()
    self.has_gold(amount)
    self.get_resource(resource_id)
    self.has_resource(resource_id, amount)
    self.get_all_resources()
    self.get_fungible_display()

Usage:
    class FCMCharacter(FungibleInventoryMixin, DefaultCharacter):
        ...
"""

from django.conf import settings

from blockchain.xrpl.currency_cache import get_resource_type, get_all_resource_types

GOLD = settings.GOLD_DISPLAY


class FungibleInventoryMixin:
    """
    Mixin that stores gold and resource amounts as Evennia Attributes
    and keeps the blockchain mirror DB in sync via service calls.

    Data storage:
        self.db.gold       — int, amount of gold held (default 0)
        self.db.resources  — dict {resource_id (int): amount (int)} (default {})
    """

    # ================================================================== #
    #  Initialization
    # ================================================================== #

    def at_fungible_init(self):
        """
        Call from at_object_creation() to initialize fungible storage.
        Safe to call multiple times — only sets defaults if not already present.
        """
        if self.db.gold is None:
            self.db.gold = 0
        if self.db.resources is None:
            self.db.resources = {}

    # ================================================================== #
    #  Object Classification Helpers
    # ================================================================== #

    @staticmethod
    def _classify_fungible(obj):
        """
        Classify an Evennia object for service method dispatch.

        Returns:
            "CHARACTER" — obj is an FCMCharacter (player-owned, has character_key)
            "ACCOUNT"   — obj is an AccountBank  (player-owned, no character_key)
            "WORLD"     — anything else (rooms, mobs, containers = vault-owned)
        """
        # Lazy imports to avoid circular dependencies
        from typeclasses.actors.character import FCMCharacter
        from typeclasses.accounts.account_bank import AccountBank

        if isinstance(obj, FCMCharacter):
            return "CHARACTER"
        if isinstance(obj, AccountBank):
            return "ACCOUNT"
        return "WORLD"

    def _get_wallet(self):
        """
        Get the wallet address associated with this object.

        Characters → player's wallet (from their account)
        AccountBank → player's wallet (stored directly)
        Everything else → vault address (rooms, mobs, etc. are vault-owned)
        """
        from typeclasses.actors.character import FCMCharacter
        from typeclasses.accounts.account_bank import AccountBank

        if isinstance(self, FCMCharacter):
            if self.account is None:
                return None
            return self.account.attributes.get("wallet_address")
        if isinstance(self, AccountBank):
            return self.wallet_address
        # Rooms, mobs, containers — vault owns whatever they hold
        return settings.XRPL_VAULT_ADDRESS

    def _get_character_key(self):
        """
        Get the character_key for service calls.
        Only characters have one — everything else returns None.
        Change this method if you want to use something other than
        the character name (e.g. dbref).
        """
        from typeclasses.actors.character import FCMCharacter

        if isinstance(self, FCMCharacter):
            return self.key
        return None

    # ================================================================== #
    #  Private Local State Helpers (no service calls)
    # ================================================================== #

    def _add_gold(self, amount):
        """Add gold to local Evennia state only. No service call."""
        self.db.gold = (self.db.gold or 0) + amount
        self._at_balance_changed()

    def _remove_gold(self, amount):
        """
        Remove gold from local Evennia state only. No service call.
        Raises ValueError if insufficient.
        """
        current = self.db.gold or 0
        if current < amount:
            raise ValueError(
                f"Insufficient gold: have {current}, need {amount}"
            )
        self.db.gold = current - amount
        self._at_balance_changed()

    def _add_resource(self, resource_id, amount):
        """Add a resource to local Evennia state only. No service call."""
        resources = self.db.resources or {}
        resources[resource_id] = resources.get(resource_id, 0) + amount
        self.db.resources = resources
        self._at_balance_changed()

    def _remove_resource(self, resource_id, amount):
        """
        Remove a resource from local Evennia state only. No service call.
        Raises ValueError if insufficient.
        """
        resources = self.db.resources or {}
        current = resources.get(resource_id, 0)
        if current < amount:
            rt = get_resource_type(resource_id)
            name = rt["name"] if rt else f"resource {resource_id}"
            raise ValueError(
                f"Insufficient {name}: have {current}, need {amount}"
            )
        new_amount = current - amount
        if new_amount == 0:
            resources.pop(resource_id, None)
        else:
            resources[resource_id] = new_amount
        self.db.resources = resources
        self._at_balance_changed()

    # ================================================================== #
    #  Read-Only Queries
    # ================================================================== #

    def get_gold(self):
        """Return current gold amount."""
        return self.db.gold or 0

    def has_gold(self, amount):
        """Check if this object has at least this much gold."""
        return self.get_gold() >= amount

    def get_resource(self, resource_id):
        """Return amount of a specific resource held."""
        resources = self.db.resources or {}
        return resources.get(resource_id, 0)

    def get_all_resources(self):
        """Return dict of {resource_id: amount} for all held resources."""
        return dict(self.db.resources or {})

    def has_resource(self, resource_id, amount):
        """Check if this object has at least this much of a resource."""
        return self.get_resource(resource_id) >= amount

    # ================================================================== #
    #  Gold Transfers
    # ================================================================== #

    def transfer_gold_to(self, target, amount):
        """
        Move gold from this object to target. Updates both local Evennia
        state and the blockchain mirror DB via the appropriate service call.

        target must be an Evennia object (Character, Room, AccountBank, etc.)
        To return gold to the vault reserve, use return_gold_to_reserve().

        Service method dispatch based on (source_type, target_type):

            WORLD     → CHARACTER      = pickup
            CHARACTER → WORLD          = drop
            CHARACTER → CHARACTER      = transfer
            CHARACTER → ACCOUNT        = bank
            ACCOUNT   → CHARACTER      = unbank
        """
        if amount <= 0:
            raise ValueError(f"transfer amount must be positive, got {amount}")
        if target is None:
            raise ValueError(
                "target cannot be None — use return_gold_to_reserve() "
                "to send gold back to the vault reserve"
            )

        from blockchain.xrpl.services.gold import GoldService

        chain_id = settings.BLOCKCHAIN_CHAIN_ID
        contract = settings.CONTRACT_GOLD
        vault = settings.XRPL_VAULT_ADDRESS

        source_type = self._classify_fungible(self)
        target_type = self._classify_fungible(target)

        source_wallet = self._get_wallet()
        source_key = self._get_character_key()
        target_wallet = target._get_wallet()
        target_key = target._get_character_key()

        # Dev guard: superuser wallet == vault → can't transfer gold
        if target_wallet == vault and target_type == "CHARACTER":
            if hasattr(target, "msg"):
                target.msg(
                    "|y[Dev] Gold transfer skipped — your wallet is "
                    "the vault address. Use a normal account to test.|n"
                )
            return

        if source_type == "WORLD" and target_type == "CHARACTER":
            # SPAWNED → CHARACTER (character picks up gold from ground)
            GoldService.pickup(
                target_wallet, amount, chain_id, contract, vault, target_key,
            )

        elif source_type == "CHARACTER" and target_type == "WORLD":
            # CHARACTER → SPAWNED (character drops gold on ground)
            GoldService.drop(
                source_wallet, amount, chain_id, contract, vault, source_key,
            )

        elif source_type == "CHARACTER" and target_type == "CHARACTER":
            # CHARACTER → CHARACTER (trade/give between players)
            GoldService.transfer(
                source_wallet, source_key, target_wallet, target_key,
                amount, chain_id, contract,
            )

        elif source_type == "CHARACTER" and target_type == "ACCOUNT":
            # CHARACTER → ACCOUNT (deposit into bank)
            GoldService.bank(
                source_wallet, amount, chain_id, contract, source_key,
            )

        elif source_type == "ACCOUNT" and target_type == "CHARACTER":
            # ACCOUNT → CHARACTER (withdraw from bank)
            GoldService.unbank(
                target_wallet, amount, chain_id, contract, target_key,
            )

        else:
            # WORLD → WORLD (shouldn't happen for gold — no-op)
            # ACCOUNT → ACCOUNT (shouldn't happen)
            # WORLD → ACCOUNT, ACCOUNT → WORLD (not a normal game flow)
            raise ValueError(
                f"Unsupported gold transfer: {source_type} → {target_type}"
            )

        # Update local state on both sides
        self._remove_gold(amount)
        target._add_gold(amount)

    def receive_gold_from_reserve(self, amount):
        """
        Gold arriving from reserve into this object. One-sided — there
        is no source Evennia object (reserve is vault-internal).

        Service method dispatch based on self type:
            WORLD     = spawn         (gold placed in room/on mob)
            CHARACTER = craft_output  (crafting produces gold)
            ACCOUNT   = reserve_to_account (future-proofing)
        """
        if amount <= 0:
            raise ValueError(f"receive amount must be positive, got {amount}")

        from blockchain.xrpl.services.gold import GoldService

        chain_id = settings.BLOCKCHAIN_CHAIN_ID
        contract = settings.CONTRACT_GOLD
        vault = settings.XRPL_VAULT_ADDRESS

        self_type = self._classify_fungible(self)

        if self_type == "WORLD":
            # RESERVE → SPAWNED (gold appears in room/on mob)
            GoldService.spawn(amount, chain_id, contract, vault)

        elif self_type == "CHARACTER":
            # RESERVE → CHARACTER (crafting produces gold for player)
            wallet = self._get_wallet()
            char_key = self._get_character_key()
            GoldService.craft_output(
                wallet, amount, chain_id, contract, vault, char_key,
            )

        elif self_type == "ACCOUNT":
            # RESERVE → ACCOUNT
            wallet = self._get_wallet()
            GoldService.reserve_to_account(
                wallet, amount, chain_id, contract, vault,
            )

        # Update local state
        self._add_gold(amount)

    # ================================================================== #
    #  Resource Transfers
    # ================================================================== #

    def transfer_resource_to(self, target, resource_id, amount):
        """
        Move a resource from this object to target. Updates both local
        Evennia state and the blockchain mirror DB via the appropriate
        service call.

        target must be an Evennia object (Character, Room, AccountBank, etc.)
        To return resources to the vault reserve, use return_resource_to_reserve().

        Same dispatch logic as transfer_gold_to, but every service call
        also takes resource_id.
        """
        if amount <= 0:
            raise ValueError(f"transfer amount must be positive, got {amount}")
        if target is None:
            raise ValueError(
                "target cannot be None — use return_resource_to_reserve() "
                "to send resources back to the vault reserve"
            )

        from blockchain.xrpl.services.resource import ResourceService

        chain_id = settings.BLOCKCHAIN_CHAIN_ID
        contract = settings.CONTRACT_RESOURCES
        vault = settings.XRPL_VAULT_ADDRESS

        source_type = self._classify_fungible(self)
        target_type = self._classify_fungible(target)

        source_wallet = self._get_wallet()
        source_key = self._get_character_key()
        target_wallet = target._get_wallet()
        target_key = target._get_character_key()

        # Dev guard: superuser wallet == vault → can't transfer resources
        if target_wallet == vault and target_type == "CHARACTER":
            if hasattr(target, "msg"):
                target.msg(
                    "|y[Dev] Resource transfer skipped — your wallet is "
                    "the vault address. Use a normal account to test.|n"
                )
            return

        if source_type == "WORLD" and target_type == "CHARACTER":
            # SPAWNED → CHARACTER (character picks up resources)
            ResourceService.pickup(
                target_wallet, resource_id, amount, chain_id, contract,
                vault, target_key,
            )

        elif source_type == "CHARACTER" and target_type == "WORLD":
            # CHARACTER → SPAWNED (character drops resources)
            ResourceService.drop(
                source_wallet, resource_id, amount, chain_id, contract,
                vault, source_key,
            )

        elif source_type == "CHARACTER" and target_type == "CHARACTER":
            # CHARACTER → CHARACTER (trade/give)
            ResourceService.transfer(
                source_wallet, source_key, target_wallet, target_key,
                resource_id, amount, chain_id, contract,
            )

        elif source_type == "CHARACTER" and target_type == "ACCOUNT":
            # CHARACTER → ACCOUNT (deposit into bank)
            ResourceService.bank(
                source_wallet, resource_id, amount, chain_id, contract,
                source_key,
            )

        elif source_type == "ACCOUNT" and target_type == "CHARACTER":
            # ACCOUNT → CHARACTER (withdraw from bank)
            ResourceService.unbank(
                target_wallet, resource_id, amount, chain_id, contract,
                target_key,
            )

        else:
            raise ValueError(
                f"Unsupported resource transfer: {source_type} → {target_type}"
            )

        # Update local state on both sides
        self._remove_resource(resource_id, amount)
        target._add_resource(resource_id, amount)

    def receive_resource_from_reserve(self, resource_id, amount):
        """
        Resource arriving from reserve into this object. One-sided.

        Service method dispatch based on self type:
            WORLD     = spawn         (resource placed in room/on mob)
            CHARACTER = craft_output  (crafting produces resource)
            ACCOUNT   = reserve_to_account (future-proofing)
        """
        if amount <= 0:
            raise ValueError(f"receive amount must be positive, got {amount}")

        from blockchain.xrpl.services.resource import ResourceService

        chain_id = settings.BLOCKCHAIN_CHAIN_ID
        contract = settings.CONTRACT_RESOURCES
        vault = settings.XRPL_VAULT_ADDRESS

        self_type = self._classify_fungible(self)

        if self_type == "WORLD":
            # RESERVE → SPAWNED
            ResourceService.spawn(
                resource_id, amount, chain_id, contract, vault,
            )

        elif self_type == "CHARACTER":
            # RESERVE → CHARACTER
            wallet = self._get_wallet()
            char_key = self._get_character_key()
            ResourceService.craft_output(
                wallet, resource_id, amount, chain_id, contract,
                vault, char_key,
            )

        elif self_type == "ACCOUNT":
            # RESERVE → ACCOUNT
            wallet = self._get_wallet()
            ResourceService.reserve_to_account(
                wallet, resource_id, amount, chain_id, contract, vault,
            )

        self._add_resource(resource_id, amount)

    # ================================================================== #
    #  Return to Reserve (self → vault RESERVE)
    # ================================================================== #
    #
    # Explicit methods for sending gold/resources back to the vault's
    # unallocated reserve. The asset doesn't disappear — it is actively
    # re-attributed to vault ownership with a RESERVE location flag,
    # making it available to be re-spawned elsewhere later.
    #
    # Used by: junk command, crafting (consuming inputs), quest costs,
    # or anything that removes an asset from in-game circulation.
    #
    # Service method dispatch based on self type:
    #   CHARACTER → RESERVE = craft_input   (player consumes asset)
    #   WORLD     → RESERVE = despawn       (asset removed from room/ground)
    #   ACCOUNT   → RESERVE = account_to_reserve

    def return_gold_to_reserve(self, amount):
        """
        Return gold from this object back to the vault's RESERVE.

        The gold is not destroyed — it is re-attributed to vault ownership
        with location=RESERVE in the mirror DB, available for re-spawning.

        This is the counterpart to receive_gold_from_reserve().
        """
        if amount <= 0:
            raise ValueError(f"return amount must be positive, got {amount}")

        from blockchain.xrpl.services.gold import GoldService

        chain_id = settings.BLOCKCHAIN_CHAIN_ID
        contract = settings.CONTRACT_GOLD
        vault = settings.XRPL_VAULT_ADDRESS

        self_type = self._classify_fungible(self)

        if self_type == "CHARACTER":
            # CHARACTER → RESERVE (junking, crafting, quest cost, etc.)
            wallet = self._get_wallet()
            char_key = self._get_character_key()
            GoldService.craft_input(
                wallet, amount, chain_id, contract, vault, char_key,
            )
        elif self_type == "ACCOUNT":
            # ACCOUNT → RESERVE
            wallet = self._get_wallet()
            GoldService.account_to_reserve(
                wallet, amount, chain_id, contract, vault,
            )
        else:
            # WORLD → RESERVE (despawn — gold removed from room/ground)
            GoldService.despawn(amount, chain_id, contract, vault)

        self._remove_gold(amount)

    def return_resource_to_reserve(self, resource_id, amount):
        """
        Return a resource from this object back to the vault's RESERVE.

        The resource is not destroyed — it is re-attributed to vault ownership
        with location=RESERVE in the mirror DB, available for re-spawning.

        This is the counterpart to receive_resource_from_reserve().
        """
        if amount <= 0:
            raise ValueError(f"return amount must be positive, got {amount}")

        from blockchain.xrpl.services.resource import ResourceService

        chain_id = settings.BLOCKCHAIN_CHAIN_ID
        contract = settings.CONTRACT_RESOURCES
        vault = settings.XRPL_VAULT_ADDRESS

        self_type = self._classify_fungible(self)

        if self_type == "CHARACTER":
            # CHARACTER → RESERVE (junking, crafting, quest cost, etc.)
            wallet = self._get_wallet()
            char_key = self._get_character_key()
            ResourceService.craft_input(
                wallet, resource_id, amount, chain_id, contract,
                vault, char_key,
            )
        elif self_type == "ACCOUNT":
            # ACCOUNT → RESERVE
            wallet = self._get_wallet()
            ResourceService.account_to_reserve(
                wallet, resource_id, amount, chain_id, contract, vault,
            )
        else:
            # WORLD → RESERVE (despawn — resource removed from room/ground)
            ResourceService.despawn(
                resource_id, amount, chain_id, contract, vault,
            )

        self._remove_resource(resource_id, amount)

    # ================================================================== #
    #  Return to Sink (self → vault SINK)
    # ================================================================== #
    #
    # Consumption methods for gold/resources that are spent, not returned
    # to circulation. Assets go to SINK location in the mirror DB, where
    # they accumulate until the periodic reallocation script drains them
    # back to RESERVE.
    #
    # Used by: gold fees, crafting inputs, resource consumption (eating,
    # refueling), junking, quest costs, AMM dust.
    #
    # Service method dispatch based on self type:
    #   CHARACTER → SINK = sink           (player consumes asset)
    #   WORLD     → SINK = sink_world     (spawned asset consumed)
    #   ACCOUNT   → SINK = sink_account   (account-level consumption)

    def return_gold_to_sink(self, amount):
        """
        Consume gold from this object into the vault's SINK.

        Unlike return_gold_to_reserve(), consumed gold goes to SINK —
        a holding location for spent assets. A periodic reallocation
        script drains SINK back to RESERVE.

        This is the correct method for fees, crafting costs, purchases,
        and any other gold consumption. Use return_gold_to_reserve()
        only for cleanup/despawn (corpse decay, dungeon teardown).
        """
        if amount <= 0:
            raise ValueError(f"sink amount must be positive, got {amount}")

        from blockchain.xrpl.services.gold import GoldService

        chain_id = settings.BLOCKCHAIN_CHAIN_ID
        contract = settings.CONTRACT_GOLD
        vault = settings.XRPL_VAULT_ADDRESS

        self_type = self._classify_fungible(self)

        if self_type == "CHARACTER":
            wallet = self._get_wallet()
            char_key = self._get_character_key()
            GoldService.sink(
                wallet, amount, chain_id, contract, vault, char_key,
            )
        elif self_type == "ACCOUNT":
            wallet = self._get_wallet()
            GoldService.sink_account(
                wallet, amount, chain_id, contract, vault,
            )
        else:
            # WORLD → SINK (spawned gold consumed without being looted)
            GoldService.sink_world(amount, chain_id, contract, vault)

        self._remove_gold(amount)

    def return_resource_to_sink(self, resource_id, amount):
        """
        Consume a resource from this object into the vault's SINK.

        Unlike return_resource_to_reserve(), consumed resources go to
        SINK — a holding location for spent assets. A periodic
        reallocation script drains SINK back to RESERVE.

        This is the correct method for crafting inputs, eating, refueling,
        junking, and any other resource consumption. Use
        return_resource_to_reserve() only for cleanup/despawn.
        """
        if amount <= 0:
            raise ValueError(f"sink amount must be positive, got {amount}")

        from blockchain.xrpl.services.resource import ResourceService

        chain_id = settings.BLOCKCHAIN_CHAIN_ID
        contract = settings.CONTRACT_RESOURCES
        vault = settings.XRPL_VAULT_ADDRESS

        self_type = self._classify_fungible(self)

        if self_type == "CHARACTER":
            wallet = self._get_wallet()
            char_key = self._get_character_key()
            ResourceService.sink(
                wallet, resource_id, amount, chain_id, contract,
                vault, char_key,
            )
        elif self_type == "ACCOUNT":
            wallet = self._get_wallet()
            ResourceService.sink_account(
                wallet, resource_id, amount, chain_id, contract, vault,
            )
        else:
            # WORLD → SINK (spawned resource consumed without being looted)
            ResourceService.sink_world(
                resource_id, amount, chain_id, contract, vault,
            )

        self._remove_resource(resource_id, amount)

    # ================================================================== #
    #  Chain Deposit / Withdraw (import / export)
    # ================================================================== #
    #
    # Chain-boundary operations triggered when a player imports
    # gold/resources from their on-chain wallet into the game, or exports
    # them back out. Called after tx confirmations with the tx_hash.

    def deposit_gold_from_chain(self, amount, tx_hash):
        """
        Player deposited gold on-chain into the vault → credits account.
        ONCHAIN → ACCOUNT. Called after tx confirmations.
        """
        from blockchain.xrpl.services.gold import GoldService

        wallet = self._get_wallet()
        GoldService.deposit_from_chain(
            wallet, amount, settings.XRPL_VAULT_ADDRESS, tx_hash,
        )
        self._add_gold(amount)

    def withdraw_gold_to_chain(self, amount, tx_hash):
        """
        Player withdrawing gold from account → on-chain wallet.
        ACCOUNT → ONCHAIN. Called after tx confirmations.
        """
        from blockchain.xrpl.services.gold import GoldService

        wallet = self._get_wallet()
        GoldService.withdraw_to_chain(
            wallet, amount, settings.XRPL_VAULT_ADDRESS, tx_hash,
        )
        self._remove_gold(amount)

    def deposit_resource_from_chain(self, resource_id, amount, tx_hash):
        """
        Player deposited resources on-chain into the vault → credits account.
        ONCHAIN → ACCOUNT. Called after tx confirmations.
        """
        from blockchain.xrpl.services.resource import ResourceService

        wallet = self._get_wallet()
        ResourceService.deposit_from_chain(
            wallet, resource_id, amount, settings.XRPL_VAULT_ADDRESS, tx_hash,
        )
        self._add_resource(resource_id, amount)

    def withdraw_resource_to_chain(self, resource_id, amount, tx_hash):
        """
        Player withdrawing resources from account → on-chain wallet.
        ACCOUNT → ONCHAIN. Called after tx confirmations.
        """
        from blockchain.xrpl.services.resource import ResourceService

        wallet = self._get_wallet()
        ResourceService.withdraw_to_chain(
            wallet, resource_id, amount, settings.XRPL_VAULT_ADDRESS, tx_hash,
        )
        self._remove_resource(resource_id, amount)

    # ================================================================== #
    #  AMM Pool Trading
    # ================================================================== #

    def buy_from_pool(self, resource_id, amount, gold_cost):
        """
        Buy a resource from the AMM pool using gold.

        The gold_cost is the pre-rounded integer price (ceil-rounded by the
        caller). The on-chain swap uses this as SendMax — if the AMM can't
        fill at this price or better, the swap fails safely.

        Args:
            resource_id: int — resource to buy.
            amount: int — amount of resource to buy.
            gold_cost: int — gold to charge (ceil-rounded).

        Returns:
            dict {gold_cost, resource_amount, tx_hash}

        Raises:
            ValueError if not a CHARACTER or insufficient gold.
            XRPLTransactionError if the on-chain swap fails.
        """
        self_type = self._classify_fungible(self)
        if self_type != "CHARACTER":
            raise ValueError("Only characters can trade via AMM pools")

        if self.get_gold() < gold_cost:
            raise ValueError(
                f"Not enough gold: have {self.get_gold()}, need {gold_cost}"
            )

        from blockchain.xrpl.services.amm import AMMService

        wallet = self._get_wallet()
        char_key = self._get_character_key()
        vault = settings.XRPL_VAULT_ADDRESS

        result = AMMService.buy_resource(
            wallet, char_key, resource_id, amount, gold_cost, vault,
        )

        # Update local Evennia state
        self._remove_gold(gold_cost)
        self._add_resource(resource_id, amount)

        return result

    def sell_to_pool(self, resource_id, amount, gold_received):
        """
        Sell a resource to the AMM pool for gold.

        The gold_received is the pre-rounded integer price (floor-rounded
        by the caller). The on-chain swap uses this as the minimum output.

        Args:
            resource_id: int — resource to sell.
            amount: int — amount of resource to sell.
            gold_received: int — gold to pay player (floor-rounded).

        Returns:
            dict {gold_received, resource_amount, tx_hash}

        Raises:
            ValueError if not a CHARACTER or insufficient resource.
            XRPLTransactionError if the on-chain swap fails.
        """
        self_type = self._classify_fungible(self)
        if self_type != "CHARACTER":
            raise ValueError("Only characters can trade via AMM pools")

        if self.get_resource(resource_id) < amount:
            raise ValueError(
                f"Not enough resource {resource_id}: "
                f"have {self.get_resource(resource_id)}, need {amount}"
            )

        from blockchain.xrpl.services.amm import AMMService

        wallet = self._get_wallet()
        char_key = self._get_character_key()
        vault = settings.XRPL_VAULT_ADDRESS

        result = AMMService.sell_resource(
            wallet, char_key, resource_id, amount, gold_received, vault,
        )

        # Update local Evennia state
        self._remove_resource(resource_id, amount)
        self._add_gold(gold_received)

        return result

    def get_pool_price(self, resource_id, amount, direction="buy"):
        """
        Query the current AMM price for a resource.

        Args:
            resource_id: int — resource to price.
            amount: int — amount to price.
            direction: "buy" or "sell".

        Returns:
            int — gold amount (ceil-rounded for buys, floor-rounded for sells).
        """
        from blockchain.xrpl.services.amm import AMMService

        if direction == "buy":
            return AMMService.get_buy_price(resource_id, amount)
        return AMMService.get_sell_price(resource_id, amount)

    # ================================================================== #
    #  Display
    # ================================================================== #

    def get_fungible_display(self):
        """
        Return a formatted string showing gold and resources held.

        Example output:
            Gold: 50
            Wheat: 7 bushels
            Iron Ore: 3 chunks
        """
        lines = []

        gold = self.get_gold()
        if gold > 0:
            lines.append(f"{GOLD['name']}: {gold} {GOLD['unit']}")

        resources = self.db.resources or {}
        for resource_id in sorted(resources.keys()):
            amount = resources[resource_id]
            if amount <= 0:
                continue
            rt = get_resource_type(resource_id)
            if rt:
                lines.append(f"{rt['name']}: {amount} {rt['unit']}")
            else:
                lines.append(f"Resource {resource_id}: {amount}")

        return "\n".join(lines) if lines else "Nothing."

    def get_room_fungible_display(self):
        """
        Return a formatted string for when fungibles are visible in a room.

        Example output:
            You see 7 bushels of Wheat here.
            You see 3 chunks of Iron Ore here.
        """
        lines = []

        gold = self.get_gold()
        if gold > 0:
            lines.append(f"You see {gold} {GOLD['unit']} of {GOLD['name']} here.")

        resources = self.db.resources or {}
        for resource_id in sorted(resources.keys()):
            amount = resources[resource_id]
            if amount <= 0:
                continue
            rt = get_resource_type(resource_id)
            if rt:
                lines.append(f"You see {amount} {rt['unit']} of {rt['name']} here.")
            else:
                lines.append(f"You see {amount} of resource {resource_id} here.")

        return "\n".join(lines) if lines else ""

    # ================================================================== #
    #  Weight
    # ================================================================== #

    def get_total_fungible_weight(self):
        """
        Calculate total weight of all fungibles (gold + resources) in kg.

        Uses GOLD_WEIGHT_PER_UNIT_KG from settings for gold, and
        weight_per_unit_kg from the resource cache for each resource type.
        """
        total = 0.0

        gold = self.get_gold()
        if gold > 0:
            total += gold * settings.GOLD_WEIGHT_PER_UNIT_KG

        resources = self.db.resources or {}
        for resource_id, amount in resources.items():
            if amount > 0:
                rt = get_resource_type(resource_id)
                if rt:
                    total += amount * rt["weight_per_unit_kg"]

        return total

    # ================================================================== #
    #  Hooks
    # ================================================================== #

    def _at_balance_changed(self):
        """
        Hook called after any fungible balance change. No-op by default.

        CarryingCapacityMixin overrides this to recalculate fungible weight
        whenever gold or resources are added/removed.
        """
        pass
