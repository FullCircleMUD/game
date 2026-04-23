"""
Documentation pages — hub and category sub-pages.
"""

from django.conf import settings
from django.views.generic import TemplateView

from web.website.views.seo import SeoMixin


class DocsView(SeoMixin, TemplateView):
    template_name = "website/docs.html"
    page_title = "Documentation"
    page_description = (
        "Full Circle MUD documentation hub — gameplay, blockchain, and client "
        "API reference for players, builders, and integrators."
    )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["github_url"] = getattr(settings, "GITHUB_URL", None)
        return ctx


class DocsGameplayView(SeoMixin, TemplateView):
    template_name = "website/docs_gameplay.html"
    page_title = "Gameplay Documentation"
    page_description = (
        "Gameplay documentation for Full Circle MUD — commands, combat, "
        "crafting, classes, and the new-player experience."
    )


class DocsBlockchainView(SeoMixin, TemplateView):
    template_name = "website/docs_blockchain.html"
    page_title = "Blockchain Documentation"
    page_description = (
        "Blockchain documentation for Full Circle MUD — XRP Ledger issuer "
        "and vault addresses, tokenomics, and on-chain item ownership."
    )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["issuer_address"] = settings.XRPL_ISSUER_ADDRESS
        ctx["vault_address"] = settings.XRPL_VAULT_ADDRESS
        return ctx


class DocsClientApiView(SeoMixin, TemplateView):
    template_name = "website/docs_client_api.html"
    page_title = "Client API"
    page_description = (
        "Client API reference for Full Circle MUD — telnet, webclient, and "
        "the protocols used to connect custom clients and bots."
    )
