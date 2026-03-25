"""
NFT metadata endpoint — serves XLS-24d compliant JSON for XRPL
marketplace resolution.

GET /nft/<id>/  →  JSON metadata for NFTGameState with that primary key.

The URI baked into each minted NFToken points here, e.g.:
    https://api.fcmud.world/nft/42

Returns the XLS-24d metadata format that XRPL marketplaces
(xrp.cafe, onXRP, etc.) expect when resolving a token's URI.
"""

from django.conf import settings
from django.http import JsonResponse, Http404

from blockchain.xrpl.models import NFTGameState


# ── Typeclass path → human-readable category ────────────────────────

_CATEGORY_MAP = {
    "wearable": "Wearable",
    "holdable": "Holdable",
    "weapon": "Weapon",
    "consumable": "Consumable",
    "container": "Container",
    "ship": "Ship",
    "base_nft_item": "Item",
}

# ── Python type → XLS-24d value_type ────────────────────────────────

_VALUE_TYPE_MAP = {
    str: "string",
    int: "int",
    float: "decimal",
    bool: "string",
}


def _derive_category(typeclass_path):
    """Map a typeclass path to a display category."""
    if not typeclass_path:
        return "Item"
    path_lower = typeclass_path.lower()
    for fragment, label in _CATEGORY_MAP.items():
        if fragment in path_lower:
            return label
    return "Item"


def _build_attributes(nft, item_type):
    """Build the XLS-24d attributes list from item_type and per-instance metadata."""
    attrs = []

    if item_type:
        attrs.append({
            "attribute_name": "Category",
            "value_type": "string",
            "value": _derive_category(item_type.typeclass),
        })
        if item_type.prototype_key:
            attrs.append({
                "attribute_name": "Prototype",
                "value_type": "string",
                "value": item_type.prototype_key,
            })

    # Per-instance metadata overrides (gem effects, custom data, etc.)
    # Skip name/description (handled at top level) and complex nested structures.
    metadata = nft.metadata or {}
    for key, value in metadata.items():
        if key in ("name", "description"):
            continue
        value_type = _VALUE_TYPE_MAP.get(type(value))
        if value_type:
            attrs.append({
                "attribute_name": key.replace("_", " ").title(),
                "value_type": value_type,
                "value": str(value) if isinstance(value, bool) else value,
            })

    return attrs


def nft_metadata_view(request, token_id):
    """Serve XLS-24d NFT metadata JSON for the given game-side token ID."""
    try:
        nft = NFTGameState.objects.select_related("item_type").get(uri_id=token_id)
    except NFTGameState.DoesNotExist:
        raise Http404

    item_type = nft.item_type

    # Unassigned tokens never leave the game — treat as not issued.
    if not item_type:
        raise Http404

    metadata = nft.metadata or {}
    name = metadata.get("name", item_type.name)
    description = metadata.get(
        "description",
        item_type.description or f"A {item_type.name} from FullCircleMUD.",
    )

    data = {
        "type": "game_item",
        "name": name,
        "description": description,
        "collection": {
            "name": "FullCircleMUD",
            "family": "Game Items",
        },
        "properties": {},
    }

    # Image — convention: NFT_IMAGE_BASE_URL + prototype_key + .png
    if item_type.prototype_key:
        base_url = getattr(settings, "NFT_IMAGE_BASE_URL", "")
        if base_url:
            data["properties"]["primary_display"] = {
                "type": "image/png",
                "description": name,
                "primary_uri": f"{base_url}{item_type.prototype_key}.png",
            }

    # Attributes
    attributes = _build_attributes(nft, item_type)
    if attributes:
        data["properties"]["attributes"] = attributes

    return JsonResponse(data)
