"""
This is the starting point when a user enters a url in their web browser.

The urls is matched (by regex) and mapped to a 'view' - a Python function or
callable class that in turn (usually) makes use of a 'template' (a html file
with slots that can be replaced by dynamic content) in order to render a HTML
page to show the user.

This file includes the urls in website, webclient and admin. To override you
should modify urls.py in those sub directories.

Search the Django documentation for "URL dispatcher" for more help.

"""

from django.contrib.sitemaps.views import sitemap
from django.urls import include, path

# default evennia patterns
from evennia.web.urls import urlpatterns as evennia_default_urlpatterns

from web.website.views.seo import RobotsTxtView, StaticViewSitemap

# add patterns
urlpatterns = [
    # SEO
    path("robots.txt", RobotsTxtView.as_view(), name="robots_txt"),
    path(
        "sitemap.xml",
        sitemap,
        {"sitemaps": {"static": StaticViewSitemap}},
        name="sitemap",
    ),
    # website
    path("", include("web.website.urls")),
    # webclient
    path("webclient/", include("web.webclient.urls")),
    # split-panel webclient (vitals side panel)
    path("webclientsplit/", include("web.webclientsplit.urls")),
    # web admin
    path("admin/", include("web.admin.urls")),
    # add any extra urls here:
    # path("mypath/", include("path.to.my.urls.file")),
]

# 'urlpatterns' must be named such for Django to find it.
urlpatterns = urlpatterns + evennia_default_urlpatterns
