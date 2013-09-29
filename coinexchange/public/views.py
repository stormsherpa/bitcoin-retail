from django.http import HttpResponse, Http404
from django.template import loader

from django.template import Context

import bitcoinrpc

from coinexchange.main.lib import CoinExchangeContext, StatusMessages

def home(request):
    t = loader.get_template("coinexchange/root.html")
    c = CoinExchangeContext(request, dict())
    return HttpResponse(t.render(c))

