"""
Redemption page — placeholder until mainnet launch.
Middleware handles the Variant A 302 redirect before this view runs,
so this view is only reached by Variant B (eligible) visitors.
"""

from django.views.generic import TemplateView


class RedemptionView(TemplateView):
    template_name = "website/redemption.html"
