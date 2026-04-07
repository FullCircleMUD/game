"""
Subscription models — plan registry and payment transaction log.

All models route to the 'subscriptions' database via SubscriptionsRouter.
"""

from django.db import models


class SubscriptionPlan(models.Model):
    """
    Registry of subscription periods and pricing.

    Seeded via migration. Initially only 'monthly'.
    Extensible to weekly/quarterly/annual by adding rows.
    """

    key = models.CharField(max_length=30, unique=True)
    display_name = models.CharField(max_length=50)
    duration_days = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        app_label = "subscriptions"
        ordering = ["sort_order"]

    def __str__(self):
        return f"{self.display_name} ({self.duration_days}d @ {self.price})"


class SubscriptionPayment(models.Model):
    """
    Records every subscription payment transaction.

    One row per payment. The tx_hash is the XRPL transaction hash
    verified on-chain before the subscription is extended.
    """

    account_id = models.IntegerField(
        help_text="Evennia AccountDB.id",
    )
    account_name = models.CharField(
        max_length=80,
        help_text="Account name at time of payment",
    )
    wallet_address = models.CharField(max_length=50)
    plan_key = models.CharField(max_length=30)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency_code = models.CharField(max_length=40)
    tx_hash = models.CharField(max_length=64, unique=True)
    old_expiry = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Subscription expiry before this payment",
    )
    new_expiry = models.DateTimeField(
        help_text="Subscription expiry after this payment",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "subscriptions"
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["account_id"], name="sub_payment_account_idx"
            ),
            models.Index(
                fields=["wallet_address"], name="sub_payment_wallet_idx"
            ),
            models.Index(
                fields=["created_at"], name="sub_payment_created_idx"
            ),
        ]

    def __str__(self):
        return (
            f"SubscriptionPayment("
            f"{self.account_name} {self.plan_key} {self.created_at})"
        )
