"""
Geo-detection middleware and context processor.

Reads the Cloudflare CF-IPCountry header on every HTTP request and classifies
the visitor as Variant A (restricted) or Variant B (eligible).

In production, Cloudflare injects CF-IPCountry on every request when the DNS
proxy is enabled.  In development, falls back to settings.DEV_GEO_COUNTRY.
Fail-closed: unknown / missing country -> 'XX' -> Variant A (restricted).

Restricted paths (Variant A) receive a 302 redirect to the homepage.
"""

from django.conf import settings
from django.http import HttpResponseRedirect


# Paths that Variant A (restricted) users are hard-redirected away from.
_RESTRICTED_PATHS = (
    '/redemption/',
    '/eligible-jurisdictions/',
    '/kyc/',
)


class GeoDetectionMiddleware:
    """
    Sets request.geo_country and request.geo_variant on every request.

    geo_variant is 'B' for eligible countries, 'A' for everyone else.
    Restricted paths for Variant A receive a 302 to '/'.
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
    Template context processor -- injects geo_variant and geo_country
    into every template so partials like _menu.html can branch on them.
    """
    return {
        'geo_variant': getattr(request, 'geo_variant', 'A'),
        'geo_country': getattr(request, 'geo_country', 'XX'),
    }
