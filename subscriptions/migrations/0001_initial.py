"""
Consolidated initial migration for the subscriptions app.

Creates SubscriptionPlan and SubscriptionPayment models, then seeds
the monthly plan.
"""

import django.db.models
from django.db import migrations, models


def seed_plans(apps, schema_editor):
    Plan = apps.get_model("subscriptions", "SubscriptionPlan")
    db_alias = schema_editor.connection.alias
    Plan.objects.using(db_alias).create(
        key="monthly",
        display_name="Monthly",
        duration_days=30,
        price=20.00,
        is_active=True,
        sort_order=1,
    )


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="SubscriptionPlan",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("key", models.CharField(max_length=30, unique=True)),
                ("display_name", models.CharField(max_length=50)),
                ("duration_days", models.PositiveIntegerField()),
                (
                    "price",
                    models.DecimalField(decimal_places=2, max_digits=10),
                ),
                ("is_active", models.BooleanField(default=True)),
                ("sort_order", models.PositiveIntegerField(default=0)),
            ],
            options={
                "app_label": "subscriptions",
                "ordering": ["sort_order"],
            },
        ),
        migrations.CreateModel(
            name="SubscriptionPayment",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "account_id",
                    models.IntegerField(
                        help_text="Evennia AccountDB.id",
                    ),
                ),
                (
                    "account_name",
                    models.CharField(
                        help_text="Account name at time of payment",
                        max_length=80,
                    ),
                ),
                ("wallet_address", models.CharField(max_length=50)),
                ("plan_key", models.CharField(max_length=30)),
                (
                    "amount",
                    models.DecimalField(decimal_places=2, max_digits=10),
                ),
                ("currency_code", models.CharField(max_length=40)),
                (
                    "tx_hash",
                    models.CharField(max_length=64, unique=True),
                ),
                (
                    "old_expiry",
                    models.DateTimeField(
                        blank=True,
                        help_text="Subscription expiry before this payment",
                        null=True,
                    ),
                ),
                (
                    "new_expiry",
                    models.DateTimeField(
                        help_text="Subscription expiry after this payment",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "app_label": "subscriptions",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="subscriptionpayment",
            index=models.Index(
                fields=["account_id"], name="sub_payment_account_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="subscriptionpayment",
            index=models.Index(
                fields=["wallet_address"], name="sub_payment_wallet_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="subscriptionpayment",
            index=models.Index(
                fields=["created_at"], name="sub_payment_created_idx"
            ),
        ),
        migrations.RunPython(seed_plans, migrations.RunPython.noop),
    ]
