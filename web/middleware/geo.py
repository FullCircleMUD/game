"""
Geo-detection middleware and context processor.

Reads the Cloudflare CF-IPCountry header on every HTTP request and classifies
the visitor as Variant A or Variant B based on their detected country.

In production, Cloudflare injects CF-IPCountry on every request when the DNS
proxy is enabled.  In development, falls back to settings.DEV_GEO_COUNTRY.
Fail-closed: unknown / missing country -> 'XX' -> Variant A.

The infrastructure supports per-path redirects for restricted variants via
_RESTRICTED_PATHS, but this is currently empty — all visitors see the same
content.  Paths can be added here if jurisdiction-specific restrictions are
needed in the future.
"""

from django.conf import settings
from django.http import HttpResponseRedirect


# Paths that Variant A users are hard-redirected away from.
# Currently empty — no jurisdiction-specific page restrictions in effect.
_RESTRICTED_PATHS = ()


class GeoDetectionMiddleware:
    """
    Sets request.geo_country and request.geo_variant on every request.

    geo_variant is 'B' for countries in GEO_ELIGIBLE_COUNTRIES, 'A' for
    everyone else.  Currently all visitors see the same content — the
    variant infrastructure is retained for future use if jurisdiction-
    specific restrictions become necessary.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # 1. Cloudflare header (production)
        cf_country = request.META.get('HTTP_CF_IPCOUNTRY', '').strip().upper()

        # 2. Dev fallback -- mirrors WalletWebSocketClient behaviour
        if not cf_country:
            cf_country = getattr(settings, 'DEV_GEO_COUNTRY', '')

        # 3. Fail-closed: empty / unknown -> 'XX' -> Variant A
        country = (cf_country or 'XX').strip().upper()

        eligible = getattr(settings, 'GEO_ELIGIBLE_COUNTRIES', set())
        variant = 'B' if country in eligible else 'A'

        request.geo_country = country
        request.geo_variant = variant

        # Hard-redirect restricted users away from financial-product pages.
        if variant == 'A':
            path = request.path_info
            for restricted in _RESTRICTED_PATHS:
                if path.startswith(restricted):
                    return HttpResponseRedirect('/')

        return self.get_response(request)


def geo_context(request):
    """
    Template context processor -- injects geo_variant, geo_country, and
    site-wide settings into every template.
    """
    return {
        'geo_variant': getattr(request, 'geo_variant', 'A'),
        'geo_country': getattr(request, 'geo_country', 'XX'),
        'discord_url': getattr(settings, 'DISCORD_URL', ''),
        'is_testnet': getattr(settings, 'IS_TESTNET', False),
    }
