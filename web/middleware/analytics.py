"""Google Analytics context processor.

Injects ``google_analytics_id`` into every template context, read from the
``GOOGLE_ANALYTICS_ID`` environment variable.  When the variable is unset or
empty (e.g. local dev), no GA script is rendered — the template guard
``{% if google_analytics_id %}`` keeps the snippet out of the page entirely.
"""

import os


def google_analytics_context(request):
    """Template context processor — provides the GA Measurement ID."""
    return {
        "google_analytics_id": os.environ.get("GOOGLE_ANALYTICS_ID", ""),
    }
