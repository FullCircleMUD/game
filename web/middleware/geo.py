"""
Geo-detection middleware and context processor for FCM.

Production: reads CF-IPCountry header injected by Cloudflare DNS proxy.
Development: falls back to settings.DEV_GEO_COUNTRY mock.
Fail-closed: unknown country ('XX') → Variant A (restricted).

Variant A — restricted jurisdictions: no RLUSD/redemption/reserve copy.
Variant B — eligible jurisdictions: full financial product copy.
"""
from django.http import HttpResponseRedirect


# Paths that are hard-blocked for Variant A (restricted jurisdictions).
# Hitting any of these redirects silently to the homepage.
# NOTE: /costs/ is NOT listed — restricted users still need to subscribe.
_RESTRICTED_PATHS = [
    '/redemption/',
    '/reserve/',
    '/eligible-jurisdictions/',
    '/kyc/',
]


class GeoDetectionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        country = self._get_country(request)

        from django.conf import settings
        eligible = getattr(settings, 'GEO_ELIGIBLE_COUNTRIES', set())
        variant = 'B' if country in eligible else 'A'

        request.geo_country = country
        request.geo_variant = variant

        if variant == 'A':
            for path in _RESTRICTED_PATHS:
                if request.path.startswith(path):
                    return HttpResponseRedirect('/')

        return self.get_response(request)

    def _get_country(self, request):
        # Production: Cloudflare injects this on every request when DNS proxy is enabled.
        # Users cannot forge it because Cloudflare is in front of the origin.
        cf = request.META.get('HTTP_CF_IPCOUNTRY')
        if cf:
            return cf

        # Development: mock via Django setting.
        from django.conf import settings
        dev = getattr(settings, 'DEV_GEO_COUNTRY', None)
        if dev:
            return dev

        # Unknown — fail closed (Variant A).
        return 'XX'


def geo_context(request):
    """Context processor: injects geo_variant, geo_country, and site-wide config into every template."""
    from django.conf import settings
    return {
        'geo_variant': getattr(request, 'geo_variant', 'A'),
        'geo_country': getattr(request, 'geo_country', 'XX'),
        'discord_url': getattr(settings, 'DISCORD_URL', ''),
        'github_url': getattr(settings, 'GITHUB_URL', ''),
    }
