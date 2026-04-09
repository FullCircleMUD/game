"""FCM transaction memo utilities for XRPL audit trail.

Builds structured memos for all game XRPL transactions. Each memo
carries a type (operation category) and JSON payload for the
operator's audit trail. See design/TREASURY.md for the full spec.
"""

import json

from xrpl.models import Memo

# Memo type constants (match TREASURY.md spec)
MEMO_SWAP = "fcm/swap"
MEMO_SUBSCRIBE = "fcm/subscribe"
MEMO_EXPORT = "fcm/export"
MEMO_IMPORT = "fcm/import"
MEMO_NFT_EXPORT = "fcm/nft-export"
MEMO_NFT_IMPORT = "fcm/nft-import"
MEMO_TRUST = "fcm/trust"


def build_memo(memo_type, memo_data):
    """
    Build an FCM memo for xrpl-py Transaction models.

    Args:
        memo_type: Operation category string (e.g. "fcm/swap").
        memo_data: dict payload — serialized to compact JSON.

    Returns:
        xrpl.models.Memo ready to pass as memos=[memo] to any
        xrpl-py transaction constructor.
    """
    return Memo(
        memo_type=memo_type.encode("utf-8").hex(),
        memo_data=json.dumps(memo_data, separators=(",", ":")).encode("utf-8").hex(),
        memo_format="application/json".encode("utf-8").hex(),
    )


def memo_to_xaman(memo):
    """
    Convert an xrpl-py Memo to Xaman txjson Memos entry format.

    Returns:
        dict in the shape {"Memo": {"MemoType": ..., "MemoData": ..., "MemoFormat": ...}}
        suitable for inclusion in a Xaman txjson "Memos" array.
    """
    entry = {}
    if memo.memo_type:
        entry["MemoType"] = memo.memo_type
    if memo.memo_data:
        entry["MemoData"] = memo.memo_data
    if memo.memo_format:
        entry["MemoFormat"] = memo.memo_format
    return {"Memo": entry}
