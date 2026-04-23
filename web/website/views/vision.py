"""
Vision page — origin story and project vision.
"""

from django.views.generic import TemplateView

from web.website.views.seo import SeoMixin


class VisionView(SeoMixin, TemplateView):
    template_name = "website/vision.html"
    page_description = (
        "The vision behind Full Circle MUD — why we're rebuilding a 1990s-era "
        "text MUD with true blockchain ownership of gold, resources, and items."
    )
