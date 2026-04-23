"""
Xaman wallet setup guide — install, create wallet, and link to game account.
"""

from django.views.generic import TemplateView

from web.website.views.seo import SeoMixin


class XamanView(SeoMixin, TemplateView):
    template_name = "website/xaman.html"
    page_description = (
        "Set up Xaman wallet for Full Circle MUD — install the app, create "
        "an XRP Ledger wallet, and link it to your game account."
    )
