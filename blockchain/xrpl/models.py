from django.db import models


# ─── Currency Type (replaces ResourceType, includes gold) ────────────

class CurrencyType(models.Model):
    """
    Registry of XRPL issued currencies used in the game.

    Includes all 36 resources (mapped by resource_id) plus FCMGold.
    resource_id is NULL for gold. currency_code is the XRPL issued
    currency code (e.g. "FCMGold", "FCMWheat").

    Seeded via data migration.
    """

    currency_code = models.CharField(max_length=40, unique=True)
    resource_id = models.PositiveIntegerField(unique=True, null=True, blank=True)
    name = models.CharField(max_length=50)
    unit = models.CharField(max_length=30)
    description = models.TextField(blank=True, default="")
    weight_per_unit_kg = models.DecimalField(
        max_digits=6, decimal_places=3, default=0,
        help_text="Weight in kg per single unit of this currency.",
    )
    is_gold = models.BooleanField(default=False)

    class Meta:
        app_label = "xrpl"
        verbose_name = "Currency Type"
        verbose_name_plural = "Currency Types"
        ordering = ["currency_code"]

    def __str__(self):
        return f"{self.name} ({self.currency_code})"


# ─── NFT Item Type (identical to Polygon) ────────────────────────────

class NFTItemType(models.Model):
    """
    Registry of NFT item types. Maps an item template to its Evennia
    typeclass and prototype. Individual NFTGameState rows reference this
    via FK — the template holds canonical data, tokens hold per-instance
    overrides in metadata.

    Seeded via data migration.
    """

    name = models.CharField(max_length=100, unique=True)
    typeclass = models.CharField(max_length=255)
    prototype_key = models.CharField(max_length=255, null=True, blank=True)
    description = models.TextField(blank=True, default="")
    default_metadata = models.JSONField(default=dict)
    tracking_token = models.CharField(
        max_length=40, null=True, blank=True, unique=True,
        help_text="Proxy token currency code for AMM pricing. NULL = not tradeable.",
    )

    class Meta:
        app_label = "xrpl"
        verbose_name = "NFT Item Type"
        verbose_name_plural = "NFT Item Types"

    def __str__(self):
        return self.name


# ─── Fungible Game State (unified gold + resources) ──────────────────

class FungibleGameState(models.Model):
    """
    In-game state for all XRPL issued currencies (gold + resources).

    Tracks issuer-held balances subdivided by ownership and location.
    Rows with zero balance are deleted, not kept.

    One unified table replaces Polygon's separate GoldGameState and
    ResourceGameState. No chain_id or contract_address — XRPL config
    comes from settings.
    """

    LOCATION_RESERVE = "RESERVE"
    LOCATION_SPAWNED = "SPAWNED"
    LOCATION_ACCOUNT = "ACCOUNT"
    LOCATION_CHARACTER = "CHARACTER"
    LOCATION_SINK = "SINK"
    LOCATION_CHOICES = [
        (LOCATION_RESERVE, "Reserve"),
        (LOCATION_SPAWNED, "Spawned"),
        (LOCATION_ACCOUNT, "Account"),
        (LOCATION_CHARACTER, "Character"),
        (LOCATION_SINK, "Sink"),
    ]

    currency_code = models.CharField(max_length=40, db_index=True)
    wallet_address = models.CharField(max_length=50, db_index=True)
    location = models.CharField(
        max_length=10, choices=LOCATION_CHOICES, default=LOCATION_RESERVE,
    )
    character_key = models.CharField(max_length=255, null=True, blank=True)
    balance = models.DecimalField(max_digits=36, decimal_places=6)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "xrpl"
        verbose_name = "Fungible Game State"
        verbose_name_plural = "Fungible Game States"
        indexes = [
            models.Index(fields=["currency_code"], name="xrpl_fungib_currenc_idx"),
            models.Index(fields=["wallet_address"], name="xrpl_fungib_wallet__idx"),
        ]
        constraints = [
            # Valid location enum
            models.CheckConstraint(
                condition=models.Q(
                    location__in=["RESERVE", "SPAWNED", "ACCOUNT", "CHARACTER", "SINK"]
                ),
                name="xrpl_fungible_location_valid",
            ),
            # character_key populated iff location = CHARACTER
            models.CheckConstraint(
                condition=(
                    models.Q(location="CHARACTER", character_key__isnull=False)
                    | (~models.Q(location="CHARACTER") & models.Q(character_key__isnull=True))
                ),
                name="xrpl_fungible_character_key_iff_character",
            ),
            # balance must be positive (zero-balance rows are deleted)
            models.CheckConstraint(
                condition=models.Q(balance__gt=0),
                name="xrpl_fungible_balance_positive",
            ),
            # Unique: plain locations (RESERVE, SPAWNED, ACCOUNT)
            models.UniqueConstraint(
                fields=["currency_code", "wallet_address", "location"],
                condition=~models.Q(location="CHARACTER"),
                name="xrpl_fungible_unique_plain",
            ),
            # Unique: per character
            models.UniqueConstraint(
                fields=["currency_code", "wallet_address", "location", "character_key"],
                condition=models.Q(location="CHARACTER"),
                name="xrpl_fungible_unique_character",
            ),
        ]

    def __str__(self):
        loc = self.character_key or self.location
        return f"{self.currency_code} x{self.balance} {loc} ({self.wallet_address[:10]}...)"


# ─── NFT Game State (replaces NFTMirror, no chain state) ─────────────

class NFTGameState(models.Model):
    """
    In-game state for XRPL NFTs (NFTokens).

    Each NFT is a single row. Moves update location, owner_in_game,
    and character_key fields. No on-chain mirror fields — the game
    queries XRPL directly when needed.
    """

    LOCATION_RESERVE = "RESERVE"
    LOCATION_SPAWNED = "SPAWNED"
    LOCATION_AUCTION = "AUCTION"
    LOCATION_ACCOUNT = "ACCOUNT"
    LOCATION_CHARACTER = "CHARACTER"
    LOCATION_ONCHAIN = "ONCHAIN"
    LOCATION_CHOICES = [
        (LOCATION_RESERVE, "Reserve"),
        (LOCATION_SPAWNED, "Spawned"),
        (LOCATION_AUCTION, "Auction"),
        (LOCATION_ACCOUNT, "Account"),
        (LOCATION_CHARACTER, "Character"),
        (LOCATION_ONCHAIN, "On Chain"),
    ]

    nftoken_id = models.CharField(max_length=64, unique=True)
    uri_id = models.PositiveIntegerField(
        unique=True, null=True, blank=True,
        help_text="Permanent ID matching the on-chain URI (/nft/<uri_id>).",
    )
    taxon = models.PositiveIntegerField()
    owner_in_game = models.CharField(max_length=50, null=True, blank=True)
    location = models.CharField(
        max_length=10, choices=LOCATION_CHOICES, default=LOCATION_RESERVE,
    )
    character_key = models.CharField(max_length=255, null=True, blank=True)
    item_type = models.ForeignKey(
        NFTItemType, on_delete=models.PROTECT, null=True, blank=True,
        related_name="nft_states",
    )
    metadata = models.JSONField(default=dict)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "xrpl"
        verbose_name = "NFT Game State"
        verbose_name_plural = "NFT Game States"
        indexes = [
            models.Index(fields=["owner_in_game"], name="xrpl_nftgam_owner_i_idx"),
            models.Index(fields=["taxon"], name="xrpl_nftgam_taxon_idx"),
        ]
        constraints = [
            # location must be a valid enum value
            models.CheckConstraint(
                condition=models.Q(
                    location__in=["RESERVE", "SPAWNED", "AUCTION", "ACCOUNT", "CHARACTER", "ONCHAIN"]
                ),
                name="xrpl_nft_location_valid",
            ),
            # character_key populated iff location = CHARACTER
            models.CheckConstraint(
                condition=(
                    models.Q(location="CHARACTER", character_key__isnull=False)
                    | (~models.Q(location="CHARACTER") & models.Q(character_key__isnull=True))
                ),
                name="xrpl_nft_character_key_iff_character",
            ),
            # owner_in_game null iff location = ONCHAIN
            models.CheckConstraint(
                condition=(
                    models.Q(location="ONCHAIN", owner_in_game__isnull=True)
                    | (~models.Q(location="ONCHAIN") & models.Q(owner_in_game__isnull=False))
                ),
                name="xrpl_nft_owner_iff_not_onchain",
            ),
        ]

    def __str__(self):
        return f"NFT {self.nftoken_id[:12]}... ({self.location})"


# ─── Fungible Transfer Log (unified gold + resource transfers) ───────

class FungibleTransferLog(models.Model):
    """
    Records in-game fungible transfers. These have no on-chain trace
    since currencies stay with the issuer throughout gameplay.
    """

    currency_code = models.CharField(max_length=40)
    from_wallet = models.CharField(max_length=50)
    to_wallet = models.CharField(max_length=50)
    amount = models.DecimalField(max_digits=36, decimal_places=6)
    transfer_type = models.CharField(max_length=30)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "xrpl"
        verbose_name = "Fungible Transfer Log"
        verbose_name_plural = "Fungible Transfer Logs"
        indexes = [
            models.Index(fields=["currency_code"], name="xrpl_fungtr_currenc_idx"),
            models.Index(fields=["from_wallet"], name="xrpl_fungtr_from_wa_idx"),
            models.Index(fields=["to_wallet"], name="xrpl_fungtr_to_wall_idx"),
            models.Index(fields=["timestamp"], name="xrpl_fungtr_timesta_idx"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(amount__gt=0),
                name="xrpl_fungible_transfer_amount_positive",
            ),
            models.CheckConstraint(
                condition=~models.Q(from_wallet=models.F("to_wallet")),
                name="xrpl_fungible_transfer_not_self",
            ),
        ]

    def __str__(self):
        return f"{self.currency_code} {self.amount} {self.transfer_type} at {self.timestamp}"


# ─── NFT Transfer Log ────────────────────────────────────────────────

class NFTTransferLog(models.Model):
    """
    Records in-game NFT transfers.
    """

    nftoken_id = models.CharField(max_length=64)
    from_wallet = models.CharField(max_length=50)
    to_wallet = models.CharField(max_length=50)
    transfer_type = models.CharField(max_length=30)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "xrpl"
        verbose_name = "NFT Transfer Log"
        verbose_name_plural = "NFT Transfer Logs"
        indexes = [
            models.Index(fields=["nftoken_id"], name="xrpl_nfttr_nftoken_idx"),
            models.Index(fields=["timestamp"], name="xrpl_nfttr_timesta_idx"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=~models.Q(from_wallet=models.F("to_wallet")),
                name="xrpl_nft_transfer_not_self",
            ),
        ]

    def __str__(self):
        return f"NFT {self.nftoken_id[:12]}... {self.transfer_type} at {self.timestamp}"


# ─── XRPL Transaction Log (crash recovery) ───────────────────────────

class XRPLTransactionLog(models.Model):
    """
    Tracks XRPL transactions initiated by the game for crash recovery.

    When a player imports/exports assets, the game creates a 'pending'
    row before submitting the XRPL transaction. On confirmation, status
    updates to 'confirmed'. On failure, 'failed'. Unresolved 'pending'
    rows after a crash can be reconciled by querying the ledger.
    """

    tx_hash = models.CharField(max_length=64, unique=True)
    tx_type = models.CharField(max_length=20)  # import, export, nft_import, nft_export
    currency_code = models.CharField(max_length=40, null=True, blank=True)
    nftoken_id = models.CharField(max_length=64, null=True, blank=True)
    amount = models.DecimalField(max_digits=36, decimal_places=6, null=True, blank=True)
    wallet_address = models.CharField(max_length=50)
    status = models.CharField(max_length=10, default="pending")  # pending, confirmed, failed
    ledger_index = models.PositiveBigIntegerField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "xrpl"
        verbose_name = "XRPL Transaction Log"
        verbose_name_plural = "XRPL Transaction Logs"
        indexes = [
            models.Index(fields=["status"], name="xrpl_xrpltx_status_idx"),
            models.Index(fields=["wallet_address"], name="xrpl_xrpltx_wallet_idx"),
        ]

    def __str__(self):
        return f"XRPL tx {self.tx_hash[:12]}... {self.tx_type} ({self.status})"


# ─── Bulletin Board Listings ──────────────────────────────────────────

class BulletinListing(models.Model):
    """
    Trading Post classified listing.

    Global data — all TradingPost objects read from this table.
    Listings auto-expire after a set number of days.
    """

    LISTING_TYPES = [
        ("WTS", "Want to Sell"),
        ("WTB", "Want to Buy"),
    ]

    account_id = models.IntegerField(help_text="Evennia account ID of poster")
    character_name = models.CharField(max_length=80, help_text="Character name at time of posting")
    listing_type = models.CharField(max_length=3, choices=LISTING_TYPES)
    message = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    class Meta:
        app_label = "xrpl"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["expires_at"]),
        ]

    def __str__(self):
        return f"BulletinListing({self.listing_type}: {self.character_name})"


# ─── Enchantment Slot (compliance-driven pre-disclosure) ────────────

class EnchantmentSlot(models.Model):
    """
    Pre-disclosed next outcome for a probabilistic enchantment table.

    One row per (output_table, mastery_level) pair. All enchanters
    server-wide compete for the same row — race resolved via
    select_for_update() and the slot_number tiebreaker.

    The roll happens AFTER consumption, never before purchase, so the
    outcome a player sees in the preview is the outcome they receive.
    Required by ECONOMY.md to stay clear of gambling-law constraints.
    """

    output_table = models.CharField(max_length=64)
    mastery_level = models.PositiveSmallIntegerField()
    slot_number = models.PositiveIntegerField(default=1)
    current_outcome = models.JSONField()
    rolled_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "xrpl"
        constraints = [
            models.UniqueConstraint(
                fields=["output_table", "mastery_level"],
                name="xrpl_enchant_slot_unique_table_mastery",
            ),
        ]

    def __str__(self):
        return (
            f"EnchantmentSlot({self.output_table}/m{self.mastery_level} "
            f"#{self.slot_number})"
        )


# ─── Reconciliation Failure ────────────────────────────────────────

class ReconciliationFailure(models.Model):
    """
    One row per operation that left on-chain and in-game state disagreeing.

    The happy path is already recorded — on the ledger, and in the transfer
    and transaction logs. This is the exceptions list: the single place to
    ask "has anything failed?", because everything here needs a person to
    put it right.

    Only failures a person could act on are recorded. An AMM swap that
    happens without its recording is not one: it moves assets the game
    already owns between its own vault and its own pool, and nobody would
    unwind it by hand. A chain deposit or withdrawal is, because the
    player's own assets have moved and the game does not reflect it.

    Lives in the xrpl database on purpose. A world rebuild cannot take the
    list with it, and the list is only useful beside the data it is
    reconciled against.
    """

    operation = models.CharField(
        max_length=40, help_text="Method that failed, e.g. deposit_gold_from_chain",
    )
    wallet_address = models.CharField(max_length=50, db_index=True)
    character_key = models.CharField(max_length=255, null=True, blank=True)
    currency_code = models.CharField(max_length=40, null=True, blank=True)
    amount = models.DecimalField(
        max_digits=36, decimal_places=6, null=True, blank=True,
    )
    tx_hash = models.CharField(max_length=64, null=True, blank=True)
    error = models.TextField(help_text="Exception text, for whoever picks this up")

    resolved = models.BooleanField(
        default=False, help_text="Set once someone has put it right",
    )
    resolved_note = models.TextField(blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "xrpl"
        verbose_name = "Reconciliation Failure"
        verbose_name_plural = "Reconciliation Failures"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["resolved"], name="xrpl_reconfail_resolved_idx"),
        ]

    def __str__(self):
        state = "resolved" if self.resolved else "OPEN"
        return (
            f"[{state}] {self.operation} {self.wallet_address} "
            f"{self.amount or ''} {self.currency_code or ''}".strip()
        )
