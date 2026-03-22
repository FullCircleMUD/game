"""
About page — project details, technical foundation, and design pillars.
"""

from django.views.generic import TemplateView


class AboutView(TemplateView):
    template_name = "website/about.html"
