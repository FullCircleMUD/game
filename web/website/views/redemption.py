"""
Redemption page — placeholder until mainnet launch.
Middleware handles the Variant A 302 redirect before this view runs,
so this view is only reached by Variant B (eligible) visitors.
"""

from django.views.generic import TemplateView

from web.website.views.seo import SeoMixin


class RedemptionView(SeoMixin, TemplateView):
    template_name = "website/redemption.html"
    page_description = (
        "Full Circle MUD redemption information — placeholder until mainnet launch."
    )
