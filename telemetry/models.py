from django.db import models

from telemetry import constants


# ─── Player Session ──────────────────────────────────────────────────

class PlayerSession(models.Model):
    """Tracks individual play sessions for economy telemetry.

    One row per character puppet event. at_post_puppet creates a row,
    at_post_unpuppet sets ended_at. Open sessions (ended_at=NULL)
    indicate currently online players or crash-orphaned sessions.

    Every shard writes its own rows here, so one reader sees the whole
    cluster's population.
    """

    account_id = models.IntegerField(
        help_text="Evennia account ID (AccountDB.id)",
    )
    character_key = models.CharField(
        max_length=80,
        help_text="Character db_key at session start",
    )
    started_at = models.DateTimeField()
    ended_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        app_label = "telemetry"
        indexes = [
            models.Index(fields=["started_at"], name="tele_session_started_idx"),
            models.Index(
                fields=["account_id", "started_at"],
                name="tele_session_acct_start_idx",
            ),
        ]

    def __str__(self):
        status = "open" if self.ended_at is None else "closed"
        return f"PlayerSession({self.character_key} {self.started_at:%H:%M} {status})"


# ─── Economy Snapshot (hourly global metrics) ──────────────────────

class EconomySnapshot(models.Model):
    """Hourly snapshot of global economy health metrics.

    One row per hour. Provides a pre-aggregated view for the spawn
    algorithm and admin monitoring.
    """

    hour = models.DateTimeField(unique=True)

    # Player activity
    players_online = models.IntegerField(
        default=0, help_text="Players online at snapshot time",
    )
    unique_players_1h = models.IntegerField(
        default=0, help_text="Distinct accounts active in past hour",
    )
    unique_players_24h = models.IntegerField(
        default=0, help_text="Distinct accounts active in past 24 hours",
    )
    unique_players_7d = models.IntegerField(
        default=0, help_text="Distinct accounts active in past 7 days",
    )

    # Gold overview
    gold_circulation = models.DecimalField(
        max_digits=36, decimal_places=6, default=0,
        help_text="Total gold in CHARACTER + ACCOUNT locations",
    )
    gold_reserve = models.DecimalField(
        max_digits=36, decimal_places=6, default=0,
        help_text="Total gold in RESERVE location",
    )
    gold_sinks_1h = models.DecimalField(
        max_digits=36, decimal_places=6, default=0,
        help_text="Gold in SINK location (consumed, awaiting reallocation)",
    )
    gold_spawned_1h = models.DecimalField(
        max_digits=36, decimal_places=6, default=0,
        help_text="Gold spawned (pickup from SPAWNED) in the past hour",
    )

    # Trade activity
    amm_trades_1h = models.IntegerField(
        default=0, help_text="Number of AMM trades in the past hour",
    )
    amm_volume_gold_1h = models.DecimalField(
        max_digits=36, decimal_places=6, default=0,
        help_text="Total gold volume through AMM in the past hour",
    )

    # Chain activity
    imports_1h = models.IntegerField(
        default=0, help_text="Fungible imports from chain in the past hour",
    )
    exports_1h = models.IntegerField(
        default=0, help_text="Fungible exports to chain in the past hour",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "telemetry"
        ordering = ["-hour"]

    def __str__(self):
        return f"EconomySnapshot({self.hour}: {self.players_online} online)"


# ─── Resource Snapshot (hourly per-resource metrics) ───────────────

class ResourceSnapshot(models.Model):
    """Hourly per-resource snapshot: circulation, velocity, AMM prices.

    One row per hour per currency code. Provides per-resource detail for
    the spawn algorithm and admin monitoring.
    """

    hour = models.DateTimeField()
    currency_code = models.CharField(max_length=40)

    # Circulation by location
    in_character = models.DecimalField(
        max_digits=36, decimal_places=6, default=0,
        help_text="Total in player inventories",
    )
    in_account = models.DecimalField(
        max_digits=36, decimal_places=6, default=0,
        help_text="Total in player banks",
    )
    in_spawned = models.DecimalField(
        max_digits=36, decimal_places=6, default=0,
        help_text="Total spawned in world (ground, mob loot, chests)",
    )
    in_reserve = models.DecimalField(
        max_digits=36, decimal_places=6, default=0,
        help_text="Total in game vault reserve",
    )
    in_sink = models.DecimalField(
        max_digits=36, decimal_places=6, default=0,
        help_text="Total consumed (fees, crafting, dust) awaiting reallocation",
    )

    # Velocity (past hour)
    produced_1h = models.DecimalField(
        max_digits=36, decimal_places=6, default=0,
        help_text="craft_output + pickup (from SPAWNED) in past hour",
    )
    consumed_1h = models.DecimalField(
        max_digits=36, decimal_places=6, default=0,
        help_text="craft_input in past hour",
    )
    traded_1h = models.DecimalField(
        max_digits=36, decimal_places=6, default=0,
        help_text="amm_buy + amm_sell volume (resource side) in past hour",
    )
    exported_1h = models.DecimalField(
        max_digits=36, decimal_places=6, default=0,
        help_text="withdraw_to_chain in past hour",
    )
    imported_1h = models.DecimalField(
        max_digits=36, decimal_places=6, default=0,
        help_text="deposit_from_chain in past hour",
    )

    # AMM price at snapshot time (null if pool doesn't exist)
    amm_buy_price = models.DecimalField(
        max_digits=36, decimal_places=6, null=True, blank=True,
        help_text="Gold cost to buy 1 unit from AMM",
    )
    amm_sell_price = models.DecimalField(
        max_digits=36, decimal_places=6, null=True, blank=True,
        help_text="Gold received from selling 1 unit to AMM",
    )

    # Spawn system metrics (written by SpawnService at end of cycle)
    spawn_budget = models.IntegerField(
        default=0, help_text="Calculator budget for this hour",
    )
    spawn_quest_debt = models.IntegerField(
        default=0, help_text="Budget redirected to quest rewards",
    )
    spawn_placed = models.IntegerField(
        default=0, help_text="Units actually placed on targets",
    )
    spawn_dropped = models.IntegerField(
        default=0, help_text="Surplus dropped (no targets with headroom)",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "telemetry"
        constraints = [
            models.UniqueConstraint(
                fields=["hour", "currency_code"],
                name="telemetry_unique_resource_hour",
            ),
        ]
        ordering = ["-hour"]

    def __str__(self):
        return f"ResourceSnapshot({self.hour}: {self.currency_code})"


# ─── Saturation Snapshot (hourly NFT item saturation) ────────────────

class SaturationSnapshot(models.Model):
    """Hourly saturation metrics for NFT item spawning.

    One row per tracked item per hour. Knowledge items (spells, recipes)
    track how many active players know the spell/recipe plus unlearned
    copies in player hands. Physical items track circulation count.
    """

    # Mirrored from telemetry.constants so a caller holding a row can name
    # a category without a second import. That module stays the source.
    CATEGORY_SPELL = constants.CATEGORY_SPELL
    CATEGORY_RECIPE = constants.CATEGORY_RECIPE
    CATEGORY_ITEM = constants.CATEGORY_ITEM
    CATEGORY_CHOICES = constants.CATEGORY_CHOICES

    hour = models.DateTimeField()
    item_key = models.CharField(max_length=80)
    category = models.CharField(max_length=10, choices=CATEGORY_CHOICES)
    active_players_7d = models.IntegerField()
    eligible_players = models.IntegerField(default=0)
    known_by = models.IntegerField(default=0)
    unlearned_copies = models.IntegerField(default=0)
    in_circulation = models.IntegerField(default=0)
    saturation = models.FloatField(default=0.0)

    # Spawn system metrics (written by SpawnService at end of cycle)
    spawn_budget = models.IntegerField(
        default=0, help_text="Calculator budget for this cycle",
    )
    spawn_quest_debt = models.IntegerField(
        default=0, help_text="Budget redirected to quest rewards",
    )
    spawn_placed = models.IntegerField(
        default=0, help_text="Units actually placed on targets",
    )
    spawn_dropped = models.IntegerField(
        default=0, help_text="Surplus dropped (no targets with headroom)",
    )

    class Meta:
        app_label = "telemetry"
        ordering = ["-hour"]
        constraints = [
            models.UniqueConstraint(
                fields=["hour", "item_key", "category"],
                name="telemetry_unique_saturation_hour_item",
            ),
        ]

    def __str__(self):
        return f"SaturationSnapshot({self.hour}: {self.category}/{self.item_key} sat={self.saturation:.2f})"
