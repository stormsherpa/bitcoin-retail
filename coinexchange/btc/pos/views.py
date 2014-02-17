
import json

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
from coinexchange.btc.pos.models import SalesTransaction, TransactionBatch
from coinexchange.btc.pos import lib

@login_required
def main(request):
    data = {
            'new_sales_form': NewSalesTransactionForm(),
            }
    t = loader.get_template("coinexchange/pos/main.html")
    c = CoinExchangeContext(request, data)
    return HttpResponse(t.render(c))

def admin(request):
    profile = request.user.get_profile()
    data = {'unbatched_tx': [x for x in lib.get_unbatched_transactions(profile)],
            }
    t = loader.get_template("coinexchange/pos/admin.html")
    c = CoinExchangeContext(request, data)
    return HttpResponse(t.render(c))

def make_batch(request):
    profile = request.user.get_profile()
    batch_tx = [x for x in lib.get_unbatched_transactions(profile)]
    batch_tx_ids = [x.btc_txid for x in batch_tx]
    raw_tx = clientlib.send_all_tx_inputs(batch_tx_ids, '1G2ewpmBh3c6m4jZZsmEJ1MFHnrj4e7NvD')
    print raw_tx
    response = {"batch_tx_ids": batch_tx_ids}
    http_response = HttpResponse(json.dumps(response)+"\n")
    http_response['Content-Type'] = 'application/json'
    return http_response
