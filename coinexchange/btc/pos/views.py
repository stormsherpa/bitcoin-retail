
from django.http import HttpResponse, Http404
from django.template import loader
from django.shortcuts import redirect
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.views.generic import View

from coinexchange.views import LoginView, JsonResponse
from coinexchange.main.lib import CoinExchangeContext, StatusMessages
from coinexchange.btc.queue.bitcoind_client import BitcoindClient
from coinexchange.btc import clientlib

from coinexchange.btc.pos.forms import NewSalesTransactionForm

@login_required
def main(request):
    data = {
            'new_sales_form': NewSalesTransactionForm(),
            }
    t = loader.get_template("coinexchange/pos/main.html")
    c = CoinExchangeContext(request, data)
    return HttpResponse(t.render(c))
