"""
About page — project details, technical foundation, and design pillars.
"""

from django.views.generic import TemplateView

from web.website.views.seo import SeoMixin


class AboutView(SeoMixin, TemplateView):
    template_name = "website/about.html"
    page_title = "About"
    page_description = (
        "About Full Circle MUD — project background, technical foundation "
        "(Evennia + XRP Ledger), and the design pillars behind the game."
    )
