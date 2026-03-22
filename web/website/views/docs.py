"""
Documentation pages — hub and category sub-pages.
"""

from django.views.generic import TemplateView


class DocsView(TemplateView):
    template_name = "website/docs.html"


class DocsGameplayView(TemplateView):
    template_name = "website/docs_gameplay.html"


class DocsBlockchainView(TemplateView):
    template_name = "website/docs_blockchain.html"


class DocsClientApiView(TemplateView):
    template_name = "website/docs_client_api.html"
