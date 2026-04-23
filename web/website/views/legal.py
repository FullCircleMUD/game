"""
Legal pages — Terms of Service, Privacy Policy, and Eligible Jurisdictions.
"""

from django.views.generic import TemplateView

from web.website.views.seo import SeoMixin


class TermsView(SeoMixin, TemplateView):
    template_name = "website/terms.html"
    page_description = (
        "Full Circle MUD Terms of Service — rules of play, acceptable use, "
        "account terms, and service limits."
    )


class PrivacyView(SeoMixin, TemplateView):
    template_name = "website/privacy.html"
    page_description = (
        "Full Circle MUD Privacy Policy — what data we collect, how we use "
        "it, and how we handle on-chain wallet addresses."
    )


class EligibleJurisdictionsView(SeoMixin, TemplateView):
    template_name = "website/eligible_jurisdictions.html"
    page_description = (
        "Full Circle MUD eligible jurisdictions — where the game can be "
        "legally offered and which regions are excluded."
    )
