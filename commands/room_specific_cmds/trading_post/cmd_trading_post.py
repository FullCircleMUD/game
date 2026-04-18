"""
Trading Post commands — browse, post, and remove classified listings.

All TradingPost objects read from the same global BulletinListing table.
Post in one town, visible in every town.

Usage:
    browse [page]              — view active listings
    post <WTS/WTB> <message>   — create a listing (costs gold)
    remove <#>                 — remove your own listing
"""

from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from evennia.commands.command import Command
from evennia.utils import evtable

from commands.command import FCMCommandMixin

from blockchain.xrpl.models import BulletinListing

GOLD = settings.GOLD_DISPLAY
POSTING_FEE = 10  # gold cost to post a listing
LISTING_DURATION_DAYS = 7
LISTINGS_PER_PAGE = 20


class CmdBrowse(FCMCommandMixin, Command):
    """
    Browse trade listings on the Trading Post.

    Usage:
        browse [page]
        listings [page]
    """

    key = "browse"
    aliases = []
    locks = "cmd:all()"
    help_category = "Trading"

    def func(self):
        caller = self.caller
        now = timezone.now()

        # Get active (non-expired) listings
        active = BulletinListing.objects.filter(expires_at__gt=now)
        total = active.count()

        if total == 0:
            caller.msg("The Trading Post has no active listings.")
            return

        # Pagination
        page = 1
        if self.args and self.args.strip().isdigit():
            page = int(self.args.strip())

        total_pages = (total + LISTINGS_PER_PAGE - 1) // LISTINGS_PER_PAGE
        page = max(1, min(page, total_pages))
        start = (page - 1) * LISTINGS_PER_PAGE
        listings = list(active[start:start + LISTINGS_PER_PAGE])

        table = evtable.EvTable(
            "|w#|n", "|wType|n", "|wPosted by|n", "|wDate|n", "|wMessage|n",
            border="none",
            align="l",
        )
        table.reformat_column(0, width=5)
        table.reformat_column(1, width=5)
        table.reformat_column(2, width=14)
        table.reformat_column(3, width=8)
        table.reformat_column(4, width=46)

        for listing in listings:
            date_str = listing.created_at.strftime("%b %d")
            table.add_row(
                str(listing.id),
                listing.listing_type,
                listing.character_name[:12],
                date_str,
                listing.message[:44],
            )

        caller.msg(
            f"|w=== Trading Post ===|n\n{table}\n"
            f"|w--- Page {page} of {total_pages} ({total} listings) ---|n"
        )


class CmdPost(FCMCommandMixin, Command):
    """
    Post a listing on the Trading Post.

    Costs {POSTING_FEE} gold. Listings expire after {LISTING_DURATION_DAYS} days.

    Usage:
        post WTS <message>   — post a "Want to Sell" listing
        post WTB <message>   — post a "Want to Buy" listing
    """

    key = "post"
    locks = "cmd:all()"
    help_category = "Trading"

    def func(self):
        caller = self.caller

        if not self.args or len(self.args.strip()) < 5:
            caller.msg("Usage: post <WTS/WTB> <message>")
            return

        args = self.args.strip()
        parts = args.split(None, 1)
        listing_type = parts[0].upper()

        if listing_type not in ("WTS", "WTB"):
            caller.msg("Listing type must be WTS (want to sell) or WTB (want to buy).")
            return

        if len(parts) < 2 or not parts[1].strip():
            caller.msg("You must provide a message for your listing.")
            return

        message = parts[1].strip()
        if len(message) > 200:
            caller.msg("Message too long (200 character limit).")
            return

        # Gold fee
        if not caller.has_gold(POSTING_FEE):
            caller.msg(f"Posting a listing costs {POSTING_FEE} {GOLD['name']}. You don't have enough.")
            return

        caller.return_gold_to_sink(POSTING_FEE)

        # Create listing
        now = timezone.now()
        BulletinListing.objects.create(
            account_id=caller.account.id if caller.account else 0,
            character_name=caller.key,
            listing_type=listing_type,
            message=message,
            expires_at=now + timedelta(days=LISTING_DURATION_DAYS),
        )

        type_label = "Want to Sell" if listing_type == "WTS" else "Want to Buy"
        caller.msg(
            f"Listing posted ({type_label}): {message}\n"
            f"Fee: {POSTING_FEE} {GOLD['name']}. Expires in {LISTING_DURATION_DAYS} days."
        )


class CmdRemoveListing(FCMCommandMixin, Command):
    """
    Remove one of your own listings from the Trading Post.

    Usage:
        remove <listing #>
    """

    key = "remove"
    locks = "cmd:all()"
    help_category = "Trading"

    def func(self):
        caller = self.caller

        if not self.args or not self.args.strip().isdigit():
            caller.msg("Usage: remove <listing #>")
            return

        listing_id = int(self.args.strip())

        try:
            listing = BulletinListing.objects.get(id=listing_id)
        except BulletinListing.DoesNotExist:
            caller.msg(f"No listing #{listing_id} found.")
            return

        # Only the poster (or superuser) can remove
        account_id = caller.account.id if caller.account else 0
        if listing.account_id != account_id and not caller.is_superuser:
            caller.msg("You can only remove your own listings.")
            return

        subject = listing.message[:40]
        listing.delete()
        caller.msg(f"Listing #{listing_id} removed: {subject}")
