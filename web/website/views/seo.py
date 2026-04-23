"""
SEO endpoints — robots.txt and sitemap.xml.
"""

from django.contrib.sitemaps import Sitemap
from django.http import HttpResponse
from django.urls import reverse
from django.views.generic import View


class SeoMixin:
    """Inject page metadata into template context for SEO / social tags.

    Views set ``page_title`` and ``page_description`` as class attributes;
    base.html renders <meta name="description">, og:*, twitter:*, and the
    canonical URL derived from the request.
    """

    page_title: str = ""
    page_description: str = ""

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        if self.page_title:
            ctx["page_title"] = self.page_title
        if self.page_description:
            ctx["page_description"] = self.page_description
        return ctx


class StaticViewSitemap(Sitemap):
    """Sitemap over the public-facing, indexable website routes."""

    protocol = "https"

    def get_domain(self, site=None):
        return "fcmud.world"

    _routes = [
        ("index", 1.0, "weekly"),
        ("vision", 0.8, "monthly"),
        ("about", 0.7, "monthly"),
        ("docs", 0.7, "weekly"),
        ("docs_gameplay", 0.6, "weekly"),
        ("docs_blockchain", 0.6, "weekly"),
        ("docs_client_api", 0.5, "monthly"),
        ("markets", 0.7, "daily"),
        ("costs", 0.7, "monthly"),
        ("xaman", 0.5, "monthly"),
        ("terms", 0.3, "yearly"),
        ("privacy", 0.3, "yearly"),
        ("eligible_jurisdictions", 0.3, "yearly"),
    ]

    def items(self):
        return self._routes

    def location(self, item):
        return reverse(item[0])

    def priority(self, item):
        return item[1]

    def changefreq(self, item):
        return item[2]


class RobotsTxtView(View):
    def get(self, request, *args, **kwargs):
        lines = [
            "User-agent: *",
            "Disallow: /admin/",
            "Disallow: /webclient/",
            "Disallow: /webclientsplit/",
            "Disallow: /api/",
            "Allow: /",
            "",
            "Sitemap: https://fcmud.world/sitemap.xml",
            "",
        ]
        return HttpResponse("\n".join(lines), content_type="text/plain")
