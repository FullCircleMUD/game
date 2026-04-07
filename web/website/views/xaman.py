"""
Xaman wallet setup guide — install, create wallet, and link to game account.
"""

from django.views.generic import TemplateView


class XamanView(TemplateView):
    template_name = "website/xaman.html"
