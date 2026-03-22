"""
Legal pages — Terms of Service, Privacy Policy, and Eligible Jurisdictions.
"""

from django.views.generic import TemplateView


class TermsView(TemplateView):
    template_name = "website/terms.html"


class PrivacyView(TemplateView):
    template_name = "website/privacy.html"


class EligibleJurisdictionsView(TemplateView):
    template_name = "website/eligible_jurisdictions.html"
