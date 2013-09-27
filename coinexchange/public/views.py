from django.http import HttpResponse, Http404
from django.template import RequestContext, loader

from django.template import Context

import bitcoinrpc

def home(request):
    t = loader.get_template("coinexchange/root.html")
    c = RequestContext(request, dict())
    return HttpResponse(t.render(c))

