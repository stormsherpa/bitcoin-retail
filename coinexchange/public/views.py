from django.http import HttpResponse, Http404
from django.template import loader

from django.template import Context

from coinexchange.main.lib import CoinExchangeContext, StatusMessages
from coinexchange.btc.models import SellOffer

def home(request):
    offers = SellOffer.objects.filter(is_active=True).order_by('price')
    t = loader.get_template("coinexchange/root.html")
    c = CoinExchangeContext(request, {'offers': offers})
    return HttpResponse(t.render(c))

def list_offers(request):
    offers = SellOffer.objects.filter(is_active=True).order_by('price')
    t = loader.get_template("coinexchange/list_offers.html")
    c = CoinExchangeContext(request, {'offers': offers})
    return HttpResponse(t.render(c))
