"""
This reroutes from an URL to a python view-function/class.

The main web/urls.py includes these routes for all urls (the root of the url)
so it can reroute to all website pages.

"""

from django.urls import path

from evennia.web.website.urls import urlpatterns as evennia_website_urlpatterns

from web.website.views.docs import (
    DocsView,
    DocsGameplayView,
    DocsBlockchainView,
    DocsClientApiView,
)
from web.website.views.about import AboutView
from web.website.views.markets import MarketsView
from web.website.views.vision import VisionView
from web.website.views.costs import CostsView
from web.website.views.xaman import XamanView
from web.website.views.legal import TermsView, PrivacyView, EligibleJurisdictionsView

# add patterns here
urlpatterns = [
    path("vision/", VisionView.as_view(), name="vision"),
    path("about/", AboutView.as_view(), name="about"),
    path("docs/", DocsView.as_view(), name="docs"),
    path("docs/gameplay/", DocsGameplayView.as_view(), name="docs_gameplay"),
    path("docs/blockchain/", DocsBlockchainView.as_view(), name="docs_blockchain"),
    path("docs/client-api/", DocsClientApiView.as_view(), name="docs_client_api"),
    path("markets/", MarketsView.as_view(), name="markets"),
    path("costs/", CostsView.as_view(), name="costs"),
    path("xaman/", XamanView.as_view(), name="xaman"),
    path("terms/", TermsView.as_view(), name="terms"),
    path("privacy/", PrivacyView.as_view(), name="privacy"),
    path("eligible-jurisdictions/", EligibleJurisdictionsView.as_view(), name="eligible_jurisdictions"),
]

# read by Django
urlpatterns = urlpatterns + evennia_website_urlpatterns
