"""
Costs page — subscription model, economy transparency, and reserve management.
"""

from django.views.generic import TemplateView

from web.website.views.seo import SeoMixin


class CostsView(SeoMixin, TemplateView):
    template_name = "website/costs.html"
    page_title = "Costs"
    page_description = (
        "How Full Circle MUD sustains itself — subscription tiers, "
        "economy transparency, and treasury / reserve management."
    )
