"""
Quick validation script for XRPL NFTGameState, FungibleGameState, and NFTItemType tables.

Usage (from Evennia):
    @py from blockchain.xrpl.check_mirror import check; check()
"""

from blockchain.xrpl.models import NFTGameState, NFTItemType, FungibleGameState


def check():
    print("\n=== NFTItemType Table ===\n")
    for it in NFTItemType.objects.all():
        print(f"  [{it.id}] {it.name}")
        print(f"      typeclass: {it.typeclass}")
        print(f"      prototype_key: {it.prototype_key}")
        print(f"      default_metadata: {it.default_metadata}")
        print()

    print("=== NFTGameState Table ===\n")
    total = NFTGameState.objects.count()
    blank = NFTGameState.objects.filter(item_type__isnull=True).count()
    assigned = NFTGameState.objects.filter(item_type__isnull=False).count()
    print(f"  Total: {total}  |  Blank: {blank}  |  Assigned: {assigned}\n")

    for nft in NFTGameState.objects.select_related("item_type").order_by("nftoken_id"):
        item_name = nft.item_type.name if nft.item_type else "(blank)"
        print(
            f"  #{nft.nftoken_id:<6s}  "
            f"loc={nft.location:<10s}  "
            f"type={item_name:<20s}  "
            f"owner={nft.owner_in_game}  "
            f"metadata={nft.metadata}"
        )

    print("\n=== FungibleGameState Table ===\n")
    for row in FungibleGameState.objects.order_by("currency_code", "location"):
        print(
            f"  {row.currency_code:<15s}  "
            f"loc={row.location:<10s}  "
            f"wallet={row.wallet_address}  "
            f"balance={row.balance}"
        )

    print("\n=== Done ===\n")
