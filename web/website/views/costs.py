"""
Costs page — subscription model, economy transparency, and reserve management.
"""

from django.views.generic import TemplateView


class CostsView(TemplateView):
    template_name = "website/costs.html"
