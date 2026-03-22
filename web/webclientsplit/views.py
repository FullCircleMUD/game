from django.conf import settings
from django.http import Http404
from django.shortcuts import render


def webclientsplit(request):
    """Serve the split-panel webclient with vitals side panel."""
    if not settings.WEBCLIENT_ENABLED:
        raise Http404
    pagevars = {"browser_sessid": request.session.session_key}
    return render(request, "webclient/webclientsplit.html", pagevars)
