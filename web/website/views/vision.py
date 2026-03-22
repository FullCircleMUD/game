"""
Vision page — origin story and project vision.
"""

from django.views.generic import TemplateView


class VisionView(TemplateView):
    template_name = "website/vision.html"
