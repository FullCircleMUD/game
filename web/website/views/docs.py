"""
Documentation pages — hub and category sub-pages.
"""

from django.conf import settings
from django.views.generic import TemplateView


class DocsView(TemplateView):
    template_name = "website/docs.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["github_url"] = getattr(settings, "GITHUB_URL", None)
        return ctx


class DocsGameplayView(TemplateView):
    template_name = "website/docs_gameplay.html"


class DocsBlockchainView(TemplateView):
    template_name = "website/docs_blockchain.html"


class DocsClientApiView(TemplateView):
    template_name = "website/docs_client_api.html"
